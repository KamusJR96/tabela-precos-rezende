import os

class Config:
    """
    Centraliza as configurações da aplicação e credenciais de banco de dados.
    Idealmente, em produção, estes valores devem vir de variáveis de ambiente (os.environ).
    """
    
    # Credenciais de Acesso ao TiDB Cloud
    DB_USER = "2qdF9PtNdgdsKZ4.root"
    DB_PASSWORD = "9mMKw5dKBL7vhAZb"
    DB_HOST = "gateway01.us-east-1.prod.aws.tidbcloud.com"
    DB_PORT = 4000
    DB_NAME = "test"
    
    # Configuração de Certificados SSL para conexão segura
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SSL_CERT = os.path.join(BASE_DIR, "isrgrootx1.pem")
    
    # Dicionário de configuração para o conector MySQL
    DB_CONFIG = {
        'user': DB_USER,
        'password': DB_PASSWORD,
        'host': DB_HOST,
        'port': DB_PORT,
        'database': DB_NAME,
        'ssl_ca': SSL_CERT
    }