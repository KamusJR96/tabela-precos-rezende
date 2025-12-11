import mysql.connector
from config import Config

def get_connection():
    return mysql.connector.connect(**Config.DB_CONFIG)

def inicializar_banco():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marcas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) UNIQUE NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        sku VARCHAR(50) PRIMARY KEY,
        nome VARCHAR(200) NOT NULL,
        marca_id INT,
        custo DECIMAL(10, 2) DEFAULT 0.00,
        icms_entrada DECIMAL(5, 2) DEFAULT 0.00,
        st DECIMAL(5, 2) DEFAULT 0.00,
        ipi DECIMAL(5, 2) DEFAULT 0.00,
        difal DECIMAL(5, 2) DEFAULT 0.00,
        icms_saida DECIMAL(5, 2) DEFAULT 0.00,
        frete_ml DECIMAL(10, 2) DEFAULT 0.00,
        preco_classico DECIMAL(10, 2) DEFAULT 0.00,
        preco_premium DECIMAL(10, 2) DEFAULT 0.00,
        preco_conc_classico DECIMAL(10, 2) DEFAULT 0.00,
        preco_conc_premium DECIMAL(10, 2) DEFAULT 0.00,
        FOREIGN KEY (marca_id) REFERENCES marcas(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario VARCHAR(50) UNIQUE NOT NULL,
        senha_hash VARCHAR(255) NOT NULL,
        cargo VARCHAR(20) DEFAULT 'consulta'
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    inicializar_banco()