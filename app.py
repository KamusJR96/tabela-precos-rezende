from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from models.produto_model import get_connection, inicializar_banco
import mysql.connector

app = Flask(__name__)
app.secret_key = 'ml_app_key' 
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar o sistema."

class Usuario(UserMixin):
    def __init__(self, id, usuario, cargo):
        self.id = id
        self.usuario = usuario
        self.cargo = cargo

@login_manager.user_loader
def carregar_usuario(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario, cargo FROM usuarios WHERE id = %s", (user_id,))
    dados = cursor.fetchone()
    conn.close()
    if dados:
        return Usuario(id=dados[0], usuario=dados[1], cargo=dados[2])
    return None

def atualizar_schema_db():
    conn = get_connection()
    cursor = conn.cursor()
    try: cursor.execute("ALTER TABLE produtos ADD COLUMN difal DECIMAL(5, 2) DEFAULT 0.00")
    except: pass
    try: cursor.execute("ALTER TABLE produtos ADD COLUMN preco_conc_classico DECIMAL(10, 2) DEFAULT 0.00")
    except: pass
    try: cursor.execute("ALTER TABLE produtos ADD COLUMN preco_conc_premium DECIMAL(10, 2) DEFAULT 0.00")
    except: pass
    conn.commit()
    conn.close()

def calcular_status_margem(produto):
    PIS_COFINS = 9.25 / 100
    TAXA_CLASSICO = 11.5 / 100
    TAXA_PREMIUM = 16.5 / 100

    try:
        custo = float(produto['custo'])
        icms_ent = float(produto['icms_entrada']) / 100
        ipi = float(produto['ipi']) / 100
        difal = float(produto.get('difal', 0) or 0) / 100
        icms_sai = float(produto['icms_saida']) / 100
        frete_ml = float(produto['frete_ml'])
        st = 0.0 if session.get('ignorar_st') else float(produto['st']) / 100
        val_icms_ent = custo * icms_ent
        val_ipi = custo * ipi
        base_piscofins_ent = custo - val_icms_ent + val_ipi
        cred_piscofins = base_piscofins_ent * PIS_COFINS
        val_st = custo * st
        val_liquido = custo - val_icms_ent - cred_piscofins + val_ipi + val_st

        def get_status(preco_venda, taxa_ml):
            if preco_venda <= 0: return 'flat'
            val_icms_sai = preco_venda * icms_sai
            base_piscofins_sai = preco_venda - val_icms_sai
            deb_piscofins = base_piscofins_sai * PIS_COFINS
            val_difal = preco_venda * difal
            val_taxa = preco_venda * taxa_ml
            custo_total = val_liquido + frete_ml + val_taxa + deb_piscofins + val_icms_sai + val_difal
            margem = ((preco_venda - custo_total) / preco_venda) * 100
            
            if margem > 0.5: return 'up'
            elif margem < -0.5: return 'down'
            else: return 'flat'

        return {
            'classico': get_status(float(produto['preco_classico']), TAXA_CLASSICO),
            'premium': get_status(float(produto['preco_premium']), TAXA_PREMIUM)
        }
    except:
        return {'classico': 'flat', 'premium': 'flat'}

@app.route('/conectar')
def conectar():
    return "Conectado e Operante", 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_form = request.form.get('usuario')
        senha_form = request.form.get('senha')
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, usuario, senha_hash, cargo FROM usuarios WHERE usuario = %s", (usuario_form,))
        dado_user = cursor.fetchone()
        conn.close()
        
        if dado_user and check_password_hash(dado_user[2], senha_form):
            user_obj = Usuario(id=dado_user[0], usuario=dado_user[1], cargo=dado_user[3])
            login_user(user_obj)
            return redirect(url_for('index'))
        
        flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    busca = request.args.get('q')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if busca:
        termo = f"%{busca.lower()}%"
        sql = """SELECT p.*, m.nome as marca_nome FROM produtos p LEFT JOIN marcas m ON p.marca_id = m.id 
                 WHERE LOWER(p.sku) LIKE %s OR LOWER(p.nome) LIKE %s OR LOWER(m.nome) LIKE %s ORDER BY p.nome ASC"""
        cursor.execute(sql, (termo, termo, termo))
    else:
        sql = "SELECT p.*, m.nome as marca_nome FROM produtos p LEFT JOIN marcas m ON p.marca_id = m.id ORDER BY p.nome ASC"
        cursor.execute(sql)
        
    produtos = cursor.fetchall()

    for p in produtos:
        status = calcular_status_margem(p)
        p['status_classico'] = status['classico']
        p['status_premium'] = status['premium']

    conn.close()
    return render_template('lista.html', produtos=produtos, busca_atual=busca, 
                           simulacao_st=session.get('ignorar_st', False), usuario_atual=current_user)

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produtos")
    produtos = cursor.fetchall()
    conn.close()
    ignorar_st = session.get('ignorar_st', False)
    total_classico = 0; total_premium = 0
    pos_classico = 0; neg_classico = 0; pos_premium = 0; neg_premium = 0
    
    CONST = {'PIS': 9.25/100, 'CL': 11.5/100, 'PR': 16.5/100}

    for p in produtos:
        custo = float(p['custo'])
        icms_ent = float(p['icms_entrada']) / 100
        st = 0.0 if ignorar_st else float(p['st']) / 100
        ipi = float(p['ipi']) / 100
        difal = float(p.get('difal', 0) or 0) / 100
        icms_sai = float(p['icms_saida']) / 100
        frete = float(p['frete_ml'])
        pr_cl = float(p['preco_classico'])
        pr_pr = float(p['preco_premium'])
        
        total_classico += pr_cl; total_premium += pr_pr

        val_liq = custo - (custo*icms_ent) - ((custo-(custo*icms_ent)+(custo*ipi))*CONST['PIS']) + (custo*ipi) + (custo*st)
        
        # Clássico
        if pr_cl > 0:
            c_tot = val_liq + frete + (pr_cl*CONST['CL']) + ((pr_cl-(pr_cl*icms_sai))*CONST['PIS']) + (pr_cl*icms_sai) + (pr_cl*difal)
            mg = ((pr_cl - c_tot)/pr_cl)*100
            if mg >= 0: pos_classico += 1
            else: neg_classico += 1
            
        # Premium
        if pr_pr > 0:
            c_tot = val_liq + frete + (pr_pr*CONST['PR']) + ((pr_pr-(pr_pr*icms_sai))*CONST['PIS']) + (pr_pr*icms_sai) + (pr_pr*difal)
            mg = ((pr_pr - c_tot)/pr_pr)*100
            if mg >= 0: pos_premium += 1
            else: neg_premium += 1

    qtd = len(produtos)
    dados = {
        'tm_classico': total_classico/qtd if qtd else 0,
        'tm_premium': total_premium/qtd if qtd else 0,
        'pizza_classico': [pos_classico, neg_classico],
        'pizza_premium': [pos_premium, neg_premium],
        'total_produtos': qtd
    }
    return render_template('dashboard.html', dados=dados, simulacao_st=ignorar_st)

@app.route('/api/toggle_st', methods=['POST'])
@login_required
def toggle_st():
    estado_atual = session.get('ignorar_st', False)
    session['ignorar_st'] = not estado_atual
    return jsonify({'novo_estado': session['ignorar_st']})

@app.route('/novo')
@login_required
def novo_produto():
    return render_template('cadastro.html', usuario_atual=current_user)

@app.route('/editar/<sku>')
@login_required
def editar_produto(sku):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT p.*, m.nome as marca_nome FROM produtos p LEFT JOIN marcas m ON p.marca_id = m.id WHERE p.sku = %s"
    cursor.execute(sql, (sku,))
    produto = cursor.fetchone()
    conn.close()
    if produto: 
        return render_template('cadastro.html', produto=produto, simulacao_st=session.get('ignorar_st'), usuario_atual=current_user)
    else: 
        return "Produto não localizado", 404

@app.route('/configuracoes')
@login_required
def configuracoes():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM marcas ORDER BY nome ASC")
    marcas = cursor.fetchall()
    conn.close()
    return render_template('configuracoes.html', marcas=marcas)

@app.route('/marca/adicionar', methods=['POST'])
@login_required
def adicionar_marca():
    if current_user.cargo != 'admin': return redirect(url_for('configuracoes'))
    
    nome = request.form.get('nome')
    if nome:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO marcas (nome) VALUES (%s)", (nome,))
            conn.commit()
        except: pass
        finally: conn.close()
    return redirect(url_for('configuracoes'))

@app.route('/marca/deletar/<int:id>')
@login_required
def deletar_marca(id):
    if current_user.cargo != 'admin': return redirect(url_for('configuracoes'))
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM marcas WHERE id = %s", (id,))
        conn.commit()
    except: pass
    finally: conn.close()
    return redirect(url_for('configuracoes'))

@app.route('/api/marcas', methods=['GET'])
@login_required
def get_marcas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT nome FROM marcas ORDER BY nome ASC")
    marcas = cursor.fetchall()
    conn.close()
    return jsonify([m['nome'] for m in marcas])

@app.route('/salvar', methods=['POST'])
@login_required
def salvar_produto():
    if current_user.cargo != 'admin':
        return jsonify({'erro': 'Acesso negado: Modo Consulta não permite salvar alterações.'}), 403

    dados = request.json
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT sku FROM produtos WHERE sku = %s", (dados['sku'],))
        if cursor.fetchone(): return jsonify({'erro': 'SKU já cadastrado.'}), 409

        cursor.execute("SELECT id FROM marcas WHERE nome = %s", (dados['marca'],))
        res = cursor.fetchone()
        marca_id = res[0] if res else None

        sql = """INSERT INTO produtos 
            (sku, nome, marca_id, custo, icms_entrada, st, ipi, difal, icms_saida, frete_ml, 
             preco_classico, preco_premium, preco_conc_classico, preco_conc_premium)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        valores = (dados['sku'], dados['nome'], marca_id, dados['custo'], dados['icms_ent'], dados['st'], dados['ipi'], 
            dados['difal'], dados['icms_sai'], dados['frete_ml'], dados['preco_classico'], dados['preco_premium'],
            dados['preco_conc_classico'], dados['preco_conc_premium'])
        cursor.execute(sql, valores)
        conn.commit()
        return jsonify({'msg': 'Sucesso.'}), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/atualizar', methods=['POST'])
@login_required
def atualizar_produto():
    if current_user.cargo != 'admin':
        return jsonify({'erro': 'Acesso negado: Modo Consulta não permite salvar alterações.'}), 403

    dados = request.json
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM marcas WHERE nome = %s", (dados['marca'],))
        res = cursor.fetchone()
        marca_id = res[0] if res else None

        sql = """UPDATE produtos SET nome=%s, marca_id=%s, custo=%s, icms_entrada=%s, st=%s, ipi=%s, 
                difal=%s, icms_saida=%s, frete_ml=%s, preco_classico=%s, preco_premium=%s,
                preco_conc_classico=%s, preco_conc_premium=%s WHERE sku=%s"""
        valores = (dados['nome'], marca_id, dados['custo'], dados['icms_ent'], dados['st'], dados['ipi'], 
            dados['difal'], dados['icms_sai'], dados['frete_ml'], dados['preco_classico'], dados['preco_premium'],
            dados['preco_conc_classico'], dados['preco_conc_premium'], dados['sku'])
        cursor.execute(sql, valores)
        conn.commit()
        return jsonify({'msg': 'Sucesso.'}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/deletar_produto/<sku>')
@login_required
def deletar_produto(sku):
    if current_user.cargo != 'admin':
        return "Acesso Negado", 403

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM produtos WHERE sku = %s", (sku,))
        conn.commit()
    except: pass
    finally: conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Inicializando sistema...")
    inicializar_banco()
    atualizar_schema_db()
    app.run(debug=True, host='0.0.0.0', port=5000)