const CONSTANTES_FISCAIS = {
    PIS_COFINS: 9.25 / 100,
    TAXA_CLASSICO: 11.5 / 100,
    TAXA_PREMIUM: 16.5 / 100
};

document.addEventListener("DOMContentLoaded", function() {
    const inputs = document.querySelectorAll(".calc-input");
    inputs.forEach(input => {
        input.addEventListener("input", calcularPrecificacao);
    });
    
    carregarMarcas();
    
    // Pequeno delay para garantir renderização correta dos cálculos iniciais
    setTimeout(calcularPrecificacao, 200); 
});

function getVal(id) {
    let el = document.getElementById(id);
    if (!el) return 0; // Proteção extra caso o ID não exista
    let val = parseFloat(el.value);
    return isNaN(val) ? 0 : val;
}

function fmtMoeda(valor) {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function calcularPrecificacao() {
    // --- Coleta de Dados de Entrada ---
    let custo = getVal("custo");
    let icmsEntPct = getVal("icms_ent") / 100;
    
    // LÓGICA DE SIMULAÇÃO DE RESSARCIMENTO ST
    let elSimulacao = document.getElementById("flag_simulacao_st");
    let modoSimulacao = elSimulacao ? elSimulacao.value === "true" : false;

    let stPct = modoSimulacao ? 0.0 : getVal("st") / 100;

    let ipiPct = getVal("ipi") / 100;
    let difalPct = getVal("difal") / 100;
    let icmsSaiPct = getVal("icms_sai") / 100;
    let freteML = getVal("frete_ml");

    // --- Apuração de Custo Líquido (Base) ---
    let valorICMSEnt = custo * icmsEntPct;
    let valorIPI = custo * ipiPct;
    let valorST = custo * stPct;

    let basePisCofinsEnt = custo - valorICMSEnt + valorIPI;
    let creditoPisCofins = basePisCofinsEnt * CONSTANTES_FISCAIS.PIS_COFINS;

    let valorLiquido = custo - valorICMSEnt - creditoPisCofins + valorIPI + valorST;

    // --- Cálculo por Modalidade ---
    const calcularModalidade = (precoVenda, taxaPct) => {
        let taxaML = precoVenda * taxaPct;
        let valorICMSSai = precoVenda * icmsSaiPct;
        
        let basePisCofinsSai = precoVenda - valorICMSSai;
        let debitoPisCofins = basePisCofinsSai * CONSTANTES_FISCAIS.PIS_COFINS;
        
        let valorDifal = precoVenda * difalPct;

        let custoTotal = valorLiquido + freteML + taxaML + debitoPisCofins + valorICMSSai + valorDifal;
        let margem = precoVenda > 0 ? ((precoVenda - custoTotal) / precoVenda) * 100 : 0;

        return {
            taxaML,
            custoTotal,
            margem,
            detalhamento: { valorICMSSai, debitoPisCofins, valorDifal }
        };
    };

    let precoClassico = getVal("preco_classico");
    let resClassico = calcularModalidade(precoClassico, CONSTANTES_FISCAIS.TAXA_CLASSICO);

    let precoPremium = getVal("preco_premium");
    let resPremium = calcularModalidade(precoPremium, CONSTANTES_FISCAIS.TAXA_PREMIUM);

    // --- Renderização ---
    document.getElementById("taxa_classico").value = fmtMoeda(resClassico.taxaML);
    document.getElementById("custo_aprox_classico").value = fmtMoeda(resClassico.custoTotal);
    atualizarIndicadorMargem("margem_classico", resClassico.margem);

    document.getElementById("taxa_premium").value = fmtMoeda(resPremium.taxaML);
    document.getElementById("custo_aprox_premium").value = fmtMoeda(resPremium.custoTotal);
    atualizarIndicadorMargem("margem_premium", resPremium.margem);

    const atualizarRaioX = (sufixo, res) => {
        if(document.getElementById(`val_icms_ent_${sufixo}`)) {
            document.getElementById(`val_icms_ent_${sufixo}`).innerText = fmtMoeda(valorICMSEnt);
            document.getElementById(`val_st_${sufixo}`).innerText = fmtMoeda(valorST);
            document.getElementById(`val_ipi_${sufixo}`).innerText = fmtMoeda(valorIPI);
            document.getElementById(`val_piscofins_ent_${sufixo}`).innerText = fmtMoeda(creditoPisCofins);
            document.getElementById(`val_icms_sai_${sufixo}`).innerText = fmtMoeda(res.detalhamento.valorICMSSai);
            document.getElementById(`val_piscofins_sai_${sufixo}`).innerText = fmtMoeda(res.detalhamento.debitoPisCofins);
            document.getElementById(`val_difal_${sufixo}`).innerText = fmtMoeda(res.detalhamento.valorDifal);
        }
    };

    atualizarRaioX('class', resClassico);
    atualizarRaioX('prem', resPremium);
}

function atualizarIndicadorMargem(elementId, valor) {
    let el = document.getElementById(elementId);
    if(el) {
        el.innerText = valor.toFixed(2) + "%";
        el.style.color = valor >= 0 ? "#198754" : "#dc3545"; 
    }
}

function pesquisarNoML() {
    let termo = document.getElementById("nome").value.trim();
    if (!termo) { alert("Digite um termo para pesquisar."); return; }
    let url = `https://lista.mercadolivre.com.br/${encodeURIComponent(termo)}`;
    window.open(url, '_blank');
}

async function carregarMarcas() {
    try {
        let response = await fetch('/api/marcas');
        let marcas = await response.json();
        let select = document.getElementById("marca");
        let marcaSelecionada = document.getElementById("marca_selecionada").value;
        select.innerHTML = '<option value="" disabled selected>Selecione...</option>';
        marcas.forEach(marca => {
            let option = document.createElement("option");
            option.value = marca;
            option.text = marca;
            if (marca === marcaSelecionada) option.selected = true;
            select.appendChild(option);
        });
    } catch (e) { console.error("Falha ao carregar lista de marcas", e); }
}

async function salvarProduto() {
    let modoEdicao = document.getElementById("modo_edicao").value === "true";
    let endpoint = modoEdicao ? '/atualizar' : '/salvar';
    let dados = {
        sku: document.getElementById("sku").value.trim(),
        nome: document.getElementById("nome").value.trim(),
        marca: document.getElementById("marca").value,
        custo: getVal("custo"),
        icms_ent: getVal("icms_ent"), st: getVal("st"), ipi: getVal("ipi"),
        difal: getVal("difal"), icms_sai: getVal("icms_sai"), frete_ml: getVal("frete_ml"),
        preco_classico: getVal("preco_classico"), preco_conc_classico: getVal("preco_conc_classico"), 
        preco_premium: getVal("preco_premium"), preco_conc_premium: getVal("preco_conc_premium") 
    };
    if (!dados.sku || !dados.nome || !dados.marca) { alert("Campos obrigatórios: SKU, Nome e Marca."); return; }
    try {
        let response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
        let res = await response.json();
        if (response.ok) { alert("Operação realizada com sucesso."); window.location.href = "/"; } 
        else { alert("Erro na operação: " + res.erro); }
    } catch (e) { alert("Erro de comunicação com o servidor: " + e); }
}

// --- FUNÇÃO NOVA CORRIGIDA: ANÁLISE ANALÍTICA ---
function atualizarAnaliseAnalitica() {
    // 1. Identificar cenário ativo (Clássico ou Premium)
    // Verifica a classe 'active' do Bootstrap na aba
    let tabPremium = document.querySelector('#premium');
    let isPremium = tabPremium && tabPremium.classList.contains('active');
    
    let sufixo = isPremium ? '_premium' : '_classico';
    let taxaPct = isPremium ? CONSTANTES_FISCAIS.TAXA_PREMIUM : CONSTANTES_FISCAIS.TAXA_CLASSICO;

    // 2. Coletar Dados (Valores já calculados na tela)
    let nome = document.getElementById("nome").value || "Produto";
    let sku = document.getElementById("sku").value || "--";
    let marcaEl = document.getElementById("marca");
    let marca = marcaEl.options[marcaEl.selectedIndex]?.text || "Geral";
    
    // Valores monetários principais
    let precoVenda = getVal("preco" + sufixo);
    let custoAquisicao = getVal("custo");
    let frete = getVal("frete_ml");
    
    // Pega o Custo Total Aprox que o sistema JÁ calculou (Break-even)
    // Para pegar o valor exato do input que pode estar formatado como "R$ 1.000,00", 
    // precisamos limpar a formatação se for pegar o .value string, ou usar getVal se for input number.
    // O campo custo_aprox é text readonly formatado. Melhor recalcular aqui para precisão numérica.
    
    // Recalculo rápido preciso para o gráfico:
    let icmsSaiPct = getVal("icms_sai") / 100;
    let difalPct = getVal("difal") / 100;
    let taxaML = precoVenda * taxaPct;
    let valICMSSai = precoVenda * icmsSaiPct;
    let valDifal = precoVenda * difalPct;
    // PIS/COF (recalculando base e crédito/débito para ter o valor líquido exato)
    // Mas para simplificar visualização: Taxas = Tudo que não é Custo, Frete ou Margem.
    
    // Vamos confiar no valor total calculado pela função principal que roda antes desta
    // Mas como o input tem "R$", vamos pegar o valor numérico recalculando a mesma lógica do calcularModalidade
    // Isso garante que o gráfico bata 100% com a margem exibida.
    
    let icmsEntPct = getVal("icms_ent") / 100;
    let stPct = document.getElementById("flag_simulacao_st").value === "true" ? 0.0 : getVal("st") / 100;
    let ipiPct = getVal("ipi") / 100;
    
    let valorICMSEnt = custoAquisicao * icmsEntPct;
    let valorIPI = custoAquisicao * ipiPct;
    let valorST = custoAquisicao * stPct;
    let basePisCofinsEnt = custoAquisicao - valorICMSEnt + valorIPI;
    let creditoPisCofins = basePisCofinsEnt * CONSTANTES_FISCAIS.PIS_COFINS;
    let valorLiquido = custoAquisicao - valorICMSEnt - creditoPisCofins + valorIPI + valorST;
    
    let basePisCofinsSai = precoVenda - valICMSSai;
    let debitoPisCofins = basePisCofinsSai * CONSTANTES_FISCAIS.PIS_COFINS;
    
    let custoTotalReal = valorLiquido + frete + taxaML + debitoPisCofins + valICMSSai + valDifal;
    let valMargem = precoVenda - custoTotalReal;

    // 3. Preencher Textos do Modal
    document.getElementById("ana_marca").innerText = marca.toUpperCase();
    document.getElementById("ana_sku").innerText = `${nome} (${sku})`;
    document.getElementById("ana_preco").innerText = fmtMoeda(precoVenda);
    
    document.getElementById("ana_custo").innerText = fmtMoeda(custoAquisicao);
    document.getElementById("ana_icms_ent").innerText = getVal("icms_ent").toFixed(2);
    document.getElementById("ana_st").innerText = getVal("st").toFixed(2);
    document.getElementById("ana_difal").innerText = getVal("difal").toFixed(2);
    document.getElementById("ana_icms_sai").innerText = getVal("icms_sai").toFixed(2);
    
    document.getElementById("ana_frete").innerText = fmtMoeda(frete);
    document.getElementById("ana_taxa").innerText = fmtMoeda(taxaML);
    document.getElementById("ana_custo_total").innerText = fmtMoeda(custoTotalReal);

    // 4. Lógica das Barras (%)
    // Agora a soma será exata: Custo + Frete + Impostos + Margem = Preço Venda
    if (precoVenda > 0) {
        let pCusto = (custoAquisicao / precoVenda) * 100;
        let pFrete = (frete / precoVenda) * 100;
        let pMargem = (valMargem / precoVenda) * 100;
        
        // Impostos é todo o resto. 
        // Impostos = CustoTotal - CustoAquisicao - Frete.
        // Assim garantimos que a barra nunca fica negativa a não ser que o imposto seja negativo (impossível)
        let valImpostos = custoTotalReal - custoAquisicao - frete;
        let pImpostos = (valImpostos / precoVenda) * 100;

        setBar("custo", pCusto, "bg-secondary");
        setBar("impostos", pImpostos, "bg-secondary");
        setBar("frete", pFrete, "bg-secondary");
        
        // Margem tem cor dinâmica
        let barM = document.getElementById("bar_margem");
        let txtM = document.getElementById("perc_margem");
        txtM.innerText = pMargem.toFixed(2) + "%";
        
        // A barra sempre tem tamanho positivo visualmente
        barM.style.width = Math.abs(pMargem) + "%";
        
        if (pMargem >= 0) {
            barM.className = "progress-bar bg-success";
            txtM.className = "fw-bold text-success";
        } else {
            barM.className = "progress-bar bg-danger";
            txtM.className = "fw-bold text-danger";
        }

    } else {
        // Zera tudo se não tiver preço
        ['custo', 'impostos', 'frete', 'margem'].forEach(id => {
            document.getElementById("bar_" + id).style.width = "0%";
            document.getElementById("perc_" + id).innerText = "0%";
        });
    }
}

// Helper visual para as barras (exceto margem)
function setBar(id, val, cls) {
    // Evita barra negativa visual
    let w = val < 0 ? 0 : val;
    // Trava em 100% visualmente para não estourar layout
    if (w > 100) w = 100;
    
    document.getElementById("bar_" + id).style.width = w + "%";
    document.getElementById("bar_" + id).className = "progress-bar " + cls;
    document.getElementById("perc_" + id).innerText = val.toFixed(2) + "%";
}