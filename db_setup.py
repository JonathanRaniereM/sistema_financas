import mysql.connector

def create_tables():
    try:
        # Conectar ao banco de dados
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='123456',
            database='sistema_financas',
            auth_plugin='mysql_native_password',
            use_pure=True,
            client_flags=[mysql.connector.ClientFlag.LOCAL_FILES]
            )
    
        cursor = conn.cursor()

        # Criar tabela Ano
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Ano (
            idAno INT AUTO_INCREMENT PRIMARY KEY,
            ano VARCHAR(4) NOT NULL UNIQUE
        )''')

        # Criar tabela Meses
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Meses (
            idMes INT AUTO_INCREMENT PRIMARY KEY,
            mes VARCHAR(20) NOT NULL,
            idAno INT NOT NULL,
            FOREIGN KEY (idAno) REFERENCES Ano (idAno)
        )''')

        # Criar tabela Item com as novas colunas VALOR e QNT_DIVIDIDA
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Item (
            idItem INT AUTO_INCREMENT PRIMARY KEY,
            DOC VARCHAR(255),
            CLIENTE VARCHAR(255),
            FORMA_PAGAMENTO VARCHAR(50),
            DATA DATE,
            TIPO ENUM('ENTRADA', 'SAIDA'),
            ID_MES INT,
            VALOR DECIMAL(10, 2), 
            QNT_DIVIDIDA VARCHAR(255),  
            FECHADO BOOLEAN DEFAULT 0,
            FOREIGN KEY (ID_MES) REFERENCES Meses (idMes)
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user VARCHAR(255) NOT NULL,
            senha VARCHAR(255) NOT NULL
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS SaldoDiario (
            idSaldo INT AUTO_INCREMENT PRIMARY KEY,
            ID_MES INT,
            data DATE NOT NULL,
            entradas DECIMAL(10, 2),
            saidas DECIMAL(10, 2),
            saldo_atual DECIMAL(10, 2),
            SELECIONADO BOOLEAN DEFAULT 0,
            FOREIGN KEY (ID_MES) REFERENCES Meses (idMes)
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Caixa (
            idCaixa INT AUTO_INCREMENT PRIMARY KEY,
            distribuicao VARCHAR(255),
            saldo DECIMAL(10, 2)
        )''')


        print("Tabelas criadas com sucesso.")
    except mysql.connector.Error as err:
        print(f"Erro: {err}")
    finally:
        cursor.close()
        conn.close()

# Em seguida, crie as tabelas no banco de dados
create_tables()

