
from PyQt5 import QtCore, QtGui, QtWidgets
import mysql.connector
import datetime as dtTeste
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QSize
from datetime import datetime as dt
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import QMessageBox, QLineEdit, QVBoxLayout, QComboBox, QApplication, QInputDialog
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QFile, QIODevice
from PyQt5.QtGui import QPixmap
import os
import tempfile



import locale


from PyQt5 import QtWidgets, QtGui

import subprocess
import os
import sys
import mysql.connector

def create_tables():
    try:
        # Conectar ao banco de dados
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='bd.hermannmarmoraria@32231009',
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



def limpa_itens_selecionado(conn):
    cursor = conn.cursor()
    # Define todos como não selecionados
    cursor.execute("UPDATE SaldoDiario SET SELECIONADO = false")

    conn.commit()
    cursor.close()

def verificar_e_inserir_valores_distribuicao_com_saldo(conn):
    cursor = conn.cursor()
    
    # Lista de valores a serem verificados e possivelmente inseridos
    valores_distribuicao = ["Dinheiro", "Cheques", "Moeda", "Banco", "Cartão de Crédito"]
    
    for valor in valores_distribuicao:
        # Verifica se o valor já existe na coluna distribuicao da tabela Caixa
        cursor.execute("""
        SELECT COUNT(*)
        FROM Caixa
        WHERE distribuicao = %s
        """, (valor,))
        resultado = cursor.fetchone()[0]
        
        # Se o valor não existe, insere-o na tabela Caixa com saldo 0
        if resultado == 0:
            cursor.execute("""
            INSERT INTO Caixa (distribuicao, saldo)
            VALUES (%s, 0)
            """, (valor,))
            print(f"Valor '{valor}' inserido na tabela Caixa com saldo inicial 0.")
    
    conn.commit()
    print("Verificação e inserção de valores de distribuição com saldo inicial concluídas.")



def atualizar_saldo_diario(conn):
    cursor = conn.cursor()

    # Passo 1: Selecionar todas as datas distintas ordenadas
    cursor.execute("""
    SELECT DISTINCT DATA
    FROM Item
    ORDER BY DATA
    """)
    datas = [row[0] for row in cursor.fetchall()]

    for data in datas:
        # Passo 2: Obter o ID_MES para a data
        cursor.execute("""
        SELECT DISTINCT ID_MES
        FROM Item
        WHERE DATA = %s
        LIMIT 1
        """, (data,))
        id_mes = cursor.fetchone()[0]

        # Passo 3: Calcular as somas de entradas e saídas para a data
        cursor.execute("""
        SELECT SUM(CASE WHEN TIPO='ENTRADA' THEN VALOR ELSE 0 END) AS entradas,
               SUM(CASE WHEN TIPO='SAIDA' THEN VALOR ELSE 0 END) AS saidas
        FROM Item
        WHERE DATA = %s
        """, (data,))
        entradas, saidas = cursor.fetchone()

        saldo_atual = entradas - saidas

        # Passo 4: Verificar se já existe um registro para a data
        cursor.execute("SELECT idSaldo FROM SaldoDiario WHERE data = %s", (data,))
        resultado = cursor.fetchone()

        if resultado is None:
            # Insere novo registro incluindo ID_MES
            cursor.execute("""
            INSERT INTO SaldoDiario (ID_MES, data, entradas, saidas, saldo_atual)
            VALUES (%s, %s, %s, %s, %s)
            """, (id_mes, data, entradas, saidas, saldo_atual))
        else:
            # Atualiza registro existente incluindo ID_MES
            idSaldo = resultado[0]
            cursor.execute("""
            UPDATE SaldoDiario
            SET ID_MES = %s, entradas = %s, saidas = %s, saldo_atual = %s
            WHERE idSaldo = %s
            """, (id_mes, entradas, saidas, saldo_atual, idSaldo))

    conn.commit()
    cursor.close()



        

def abrir_pdf(filepath):
    if sys.platform == "win32":
        os.startfile(filepath)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filepath])
  
meses_mapping = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Março",
    "04": "Abril",
    "05": "Maio",
    "06": "Junho",
    "07": "Julho",
    "08": "Agosto",
    "09": "Setembro",
    "10": "Outubro",
    "11": "Novembro",
    "12": "Dezembro"
    }      

  
        
        
def gerar_relatorio_anual_pdf(central_widget,rows, anoSelecionado, soma_entradas_ano, soma_saidas_ano, soma_total_ano):
    try:
    # Tenta definir a localidade para pt_BR.UTF-8
     locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
     try:
        # Tenta uma alternativa comum no Windows
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
     except locale.Error:
        # Usa a localidade padrão do sistema se as específicas falharem
        locale.setlocale(locale.LC_ALL, '')
    
    nome_arquivo_default = f"Relatório_Anual_{anoSelecionado}.pdf"
    filepath, _ = QFileDialog.getSaveFileName(central_widget, "Salvar PDF", nome_arquivo_default, "PDF Files (*.pdf)")
    if not filepath:
        return
    
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    data_atual_formatada = dt.now().strftime("%d/%m/%Y %H:%M")
    
        # Inserir logo
        # Extrai a imagem do recurso Qt para um arquivo temporário
    temp_dir = tempfile.gettempdir()
    logo_path = os.path.join(temp_dir, "logo_GM_JPEG.jpg")
    file = QFile(":/images_home/logo_GM_JPEG.jpg")
    if file.open(QIODevice.ReadOnly):
                data = file.readAll()
                file.close()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                pixmap.save(logo_path, "JPG")
                
    c.drawImage(logo_path, 50, height - 60, width=70, height=30)  # Ajuste a posição e tamanho conforme necessário

        # Título e data de geração
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 40, f"Relatório Resumo Anual {anoSelecionado}")
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 50, height - 40, "Gerado em: " + data_atual_formatada)

    # SubHeader com informações da empresa
    subheader_y = height - 55  # Ajuste para distância do header
    c.setFont("Helvetica", 6)  # Fonte menor para o subheader

    subheader_info = [
        "Razão Social: Marmoraria Gramarmores LTDA - CNPJ: 40.905.989/0001-05",
        "Logradouro: Rua Trinta e Cinco, 41 - Bairro: Jardim Olimpico - CEP: 39406-538",
        "Montes Claros - MG",
        "E-mail: celino84@hotmail.com (Enviar E-mail) - Contato: (38) 99815-9931 (Ligar) (Whatsapp)"
    ]

    for info in subheader_info:
        c.drawCentredString(width / 2, subheader_y, info)
        subheader_y -= 8  # Espaçamento menor entre linhas
        
    # Linha divisória abaixo do subheader
    c.line(50, subheader_y - 5, width - 50, subheader_y - 5)


    
    
    
    
    y_position = height - 120  # Inicia abaixo do cabeçalho

    meses = sorted(set(row[3].split('/')[1] for row in rows))  # Extrai os meses dos dados
    
    
    for mes in meses:
        if y_position < 200:  # Verifica se há espaço suficiente para iniciar uma nova tabela
            c.showPage()
            y_position = height - 40
        
        # Título do mês
        mes_nome = meses_mapping.get(mes, "Mês desconhecido")
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width / 2, y_position, mes_nome)
        y_position -= 20
        
        # Linha divisória após cabeçalho
        c.line(50, y_position, width - 50, y_position)
        y_position -= 20
      
        
        # Cabeçalho da tabela
        c.setFont("Helvetica", 9)
        headers = ["DOC Nº", "Cliente", "Forma Pagamento", "Data", "Valor", "Qtd Parcelas"]
        x_offset = 50
        col_widths = [80, 150, 100, 80, 80, 100]  # Larguras das colunas
        for i, header in enumerate(headers):
                c.drawString(x_offset, y_position, header)
                x_offset += col_widths[i]
        y_position -= 15
        

        min_height_before_new_page = 20  # Define a altura mínima antes de criar uma nova página
        # Dados da tabela para o mês atual
        for row in filter(lambda r: r[3].split('/')[1] == mes, rows):
                
                
                    # Verifica se é necessário criar uma nova página
            if y_position < min_height_before_new_page:
                        c.showPage()  # Cria uma nova página
                        c.setFont("Helvetica", 8)  # Redefine a fonte após criar uma nova página
                        
                        # Redefine y_position para o topo da nova página
                        y_position = height - 140
                        
                        # Opcional: Repetir o cabeçalho da tabela ou qualquer outro elemento aqui
                        # Código para repetir cabeçalho ou elementos necessários
                        c.setFont("Helvetica", 8)
                 
                        for i, header in enumerate(headers):
                         c.drawString(x_offset, y_position, header)
                         x_offset += col_widths[i]
            
                         
               
            x_offset = 50
            for index, item in enumerate(row[:-1]):  # Exclui a coluna FECHADO
                 if index == 4:  # Coluna do valor monetário
                        valor_formatado = locale.format_string('%.2f', float(item), grouping=True)
                        item = f"R$ {valor_formatado}"
                 c.drawString(x_offset, y_position, str(item))
                 x_offset += col_widths[index]
            y_position -= 20
        
        # Linha divisória antes de mudar para o próximo mês
        c.line(50, y_position, width - 50, y_position)
        y_position -= 20
    
    # Rodapé final com somatórios anuais
    if y_position < 100:  # Nova página se não houver espaço
        c.showPage()
        y_position = height - 40
    
    c.setFont("Helvetica-Bold", 10)
      # Rodapé com somatórios
    
    rodape_y_position = y_position - 25
        # Textos a serem exibidos
    entradas_text = f"ENTRADAS: +R${locale.format_string('%.2f', soma_entradas_ano, grouping=True)}"
    saidas_text = f"SAÍDAS: -R${locale.format_string('%.2f', soma_saidas_ano, grouping=True)}"
    total_text = f"TOTAL: {'+' if soma_total_ano >= 0 else '-'}R$ {locale.format_string('%.2f', abs(soma_total_ano), grouping=True)}"

        # Cálculo para o texto de entradas à esquerda
    c.drawString(50, rodape_y_position, entradas_text)


    c.drawString(width / 2 - c.stringWidth(saidas_text) / 2, rodape_y_position, saidas_text)


    c.drawString(width - 50 - c.stringWidth(total_text), rodape_y_position, total_text)

        # Linha divisória abaixo do rodapé
    c.line(50, rodape_y_position - 15, width - 50, rodape_y_position - 15)

    c.save()
    QMessageBox.information(central_widget,"PDF Gerado", f"O PDF dos gastos foi gerado com sucesso em: {filepath}")
    abrir_pdf(filepath)
    # Adicione aqui a chamada para abrir o PDF automaticamente, se necessário

def gerar_relatorio_pdf(central_widget,rows, anoSelecionado, mesSelecionado, soma_entradas_mes, soma_saidas_mes, soma_total_mes):

            
        
    # Define o nome padrão do arquivo com o caminho padrão para a pasta de Downloads do usuário
        nome_arquivo_default = f"Relatório_{mesSelecionado}_{anoSelecionado}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(central_widget, "Salvar PDF", nome_arquivo_default, "PDF Files (*.pdf)")
        if not filepath:  # Se nenhum local foi escolhido (operação cancelada)
            return  # Não faça nad
    
        c = canvas.Canvas(filepath, pagesize=letter)

        width, height = letter  # Keep the page size
        try:
    # Tenta definir a localidade para pt_BR.UTF-8
         locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
         try:
        # Tenta uma alternativa comum no Windows
           locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
         except locale.Error:
        # Usa a localidade padrão do sistema se as específicas falharem
          locale.setlocale(locale.LC_ALL, '')
        data_atual_formatada = dt.now().strftime("%d/%m/%Y %H:%M")

        # Inserir logo
        # Extrai a imagem do recurso Qt para um arquivo temporário
        temp_dir = tempfile.gettempdir()
        logo_path = os.path.join(temp_dir, "logo_GM_JPEG.jpg")
        file = QFile(":/images_home/logo_GM_JPEG.jpg")
        if file.open(QIODevice.ReadOnly):
           data = file.readAll()
           file.close()
           pixmap = QPixmap()
           pixmap.loadFromData(data)
           pixmap.save(logo_path, "JPG")
           
        c.drawImage(logo_path, 50, height - 60, width=70, height=30)  # Ajuste a posição e tamanho conforme necessário

        # Título e data de geração
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, height - 40, f"Relatório de {mesSelecionado} {anoSelecionado}")
        c.setFont("Helvetica", 8)
        c.drawRightString(width - 50, height - 40, "Gerado em: " + data_atual_formatada)

        # SubHeader com informações da empresa
        subheader_y = height - 55  # Ajuste para distância do header
        c.setFont("Helvetica", 6)  # Fonte menor para o subheader

        subheader_info = [
                "Razão Social: Marmoraria Gramarmores LTDA - CNPJ: 40.905.989/0001-05",
                "Logradouro: Rua Trinta e Cinco, 41 - Bairro: Jardim Olimpico - CEP: 39406-538",
                "Montes Claros - MG",
                "E-mail: celino84@hotmail.com (Enviar E-mail) - Contato: (38) 99815-9931 (Ligar) (Whatsapp)"
        ]

        for info in subheader_info:
                c.drawCentredString(width / 2, subheader_y, info)
                subheader_y -= 8  # Espaçamento menor entre linhas

        # Linha divisória abaixo do subheader
        c.line(50, subheader_y - 5, width - 50, subheader_y - 5)


        # Cabeçalhos da tabela
        y_position = height - 140
        x_offset = 50  # Ajuste para alinhar à esquerda
        col_widths = [80, 150, 100, 80, 80, 100]  # Larguras das colunas
        headers = ['DOC Nº', 'Cliente', 'Forma Pagamento', 'Data', 'Valor', 'Qtd Parcelas']
        
        c.setFont("Helvetica-Bold", 10)
        for i, header in enumerate(headers):
                c.drawString(x_offset, y_position, header)
                x_offset += col_widths[i]

        # Dados da tabela
        c.setFont("Helvetica", 8)
        y_position -= 20
        min_height_before_new_page = 20  # Define a altura mínima antes de criar uma nova página
        for row in rows:
               
                
                    # Verifica se é necessário criar uma nova página
                if y_position < min_height_before_new_page:
                        c.showPage()  # Cria uma nova página
                        c.setFont("Helvetica", 8)  # Redefine a fonte após criar uma nova página
                        
                        # Redefine y_position para o topo da nova página
                        y_position = height - 140
                        
                        # Opcional: Repetir o cabeçalho da tabela ou qualquer outro elemento aqui
                        # Código para repetir cabeçalho ou elementos necessários
                        c.setFont("Helvetica", 8)
                 
                        for i, header in enumerate(headers):
                         c.drawString(x_offset, y_position, header)
                         x_offset += col_widths[i]
            
                         
                x_offset = 50  # Reset para alinhar à esquerda para cada linha
                for index, item in enumerate(row[:-1]):  # Exclui a coluna FECHADO
                 if index == 4:  # Coluna do valor monetário
                        valor_formatado = locale.format_string('%.2f', float(item), grouping=True)
                        item = f"R$ {valor_formatado}"
                 c.drawString(x_offset, y_position, str(item))
                 x_offset += col_widths[index]
                y_position -= 20

        # Linha divisória acima do rodapé
        c.line(50, y_position - 10, width - 50, y_position - 10)

        # Rodapé com somatórios
    
        rodape_y_position = y_position - 25
        # Textos a serem exibidos
        entradas_text = f"ENTRADAS: +R${locale.format_string('%.2f', soma_entradas_mes, grouping=True)}"
        saidas_text = f"SAÍDAS: -R${locale.format_string('%.2f', soma_saidas_mes, grouping=True)}"
        total_text = f"TOTAL: {'+' if soma_total_mes >= 0 else '-'}R$ {locale.format_string('%.2f', abs(soma_total_mes), grouping=True)}"
        
        # Cálculo para o texto de entradas à esquerda
        c.drawString(50, rodape_y_position, entradas_text)


        c.drawString(width / 2 - c.stringWidth(saidas_text) / 2, rodape_y_position, saidas_text)


        c.drawString(width - 50 - c.stringWidth(total_text), rodape_y_position, total_text)
       
        # Linha divisória abaixo do rodapé
        c.line(50, rodape_y_position - 15, width - 50, rodape_y_position - 15)


        c.save()
        QMessageBox.information(central_widget,"PDF Gerado", f"O PDF dos gastos foi gerado com sucesso em: {filepath}")
        abrir_pdf(filepath)
        
        
def obter_dados_para_relatorio_anual(conn, ano_id_selecionado):
    cursor = conn.cursor()
    
    # Obtendo os registros para o ano selecionado
    cursor.execute('''
    SELECT DOC, CLIENTE, FORMA_PAGAMENTO, DATE_FORMAT(DATA, '%d/%m/%Y'), VALOR, QNT_DIVIDIDA, TIPO
    FROM Item
    INNER JOIN Meses ON Item.ID_MES = Meses.idMes
    WHERE Meses.idAno = %s
    ORDER BY DATE_FORMAT(DATA, '%d/%m/%Y') DESC''', (ano_id_selecionado,))

    rows = cursor.fetchall()

    # Calculando somas de entradas, saídas e total para o ano
    cursor.execute('''
    SELECT SUM(VALOR)
    FROM Item
    INNER JOIN Meses ON Item.ID_MES = Meses.idMes
    WHERE TIPO = 'ENTRADA' AND Meses.idAno = %s''', (ano_id_selecionado,))
    soma_entradas_ano = cursor.fetchone()[0] or 0

    cursor.execute('''
    SELECT SUM(VALOR)
    FROM Item
    INNER JOIN Meses ON Item.ID_MES = Meses.idMes
    WHERE TIPO = 'SAIDA' AND Meses.idAno = %s''', (ano_id_selecionado,))
    soma_saidas_ano = cursor.fetchone()[0] or 0

    soma_total_ano = soma_entradas_ano - soma_saidas_ano

    cursor.close()
    return rows, soma_entradas_ano, soma_saidas_ano, soma_total_ano


def obter_dados_para_relatorio(conn, ano_id_selecionado, mes_id_selecionado):
    cursor = conn.cursor()
    
    # Obtendo os registros para o ano e mês selecionados
    cursor.execute('''
    SELECT DOC, CLIENTE, FORMA_PAGAMENTO, DATE_FORMAT(DATA, '%d/%m/%Y'), VALOR, QNT_DIVIDIDA, TIPO
    FROM Item
    WHERE ID_MES = %s
    ORDER BY DATE_FORMAT(DATA, '%d/%m/%Y') DESC''', (mes_id_selecionado,))

    rows = cursor.fetchall()


    # Calculando somas de entradas, saídas e total
    cursor.execute('''
    SELECT SUM(VALOR)
    FROM Item
    WHERE TIPO = 'ENTRADA' AND ID_MES = %s''', (mes_id_selecionado,))
    soma_entradas_mes = cursor.fetchone()[0] or 0

    cursor.execute('''
    SELECT SUM(VALOR)
    FROM Item
    WHERE TIPO = 'SAIDA' AND ID_MES = %s''', (mes_id_selecionado,))
    soma_saidas_mes = cursor.fetchone()[0] or 0

    soma_total_mes = soma_entradas_mes - soma_saidas_mes

    cursor.close()
    return rows, soma_entradas_mes, soma_saidas_mes, soma_total_mes


def obter_id_ano_mes_selecionado(conn, anoSelecionado, nomeMesSelecionado):
        # Inicializa os IDs como None para o caso de não encontrá-los
        ano_id_selcionado = None
        mes_id_selcionado = None

        try:
                cursor = conn.cursor()
                
                # Busca o ID do ano
                cursor.execute("SELECT idAno FROM Ano WHERE ano = %s", (anoSelecionado,))
                resultadoAno = cursor.fetchone()
                if resultadoAno:
                 ano_id_selcionado = resultadoAno[0]
                
                 # Busca o ID do mês com base no ano_id_selcionado
                 # Note que você precisa converter o nome do mês para o formato esperado pelo banco
                 cursor.execute("SELECT idMes FROM Meses WHERE mes = %s AND idAno = %s", (nomeMesSelecionado, ano_id_selcionado))
                 resultadoMes = cursor.fetchone()
                else:
                        return ano_id_selcionado, mes_id_selcionado
                        
                if resultadoMes:
                        mes_id_selcionado = resultadoMes[0]
                else:
                        return ano_id_selcionado, mes_id_selcionado
        except mysql.connector.Error as e:
                print(f"Erro ao buscar IDs: {e}")
        finally:
                cursor.close()
        
        return ano_id_selcionado, mes_id_selcionado   

meses_mapa = {
    "January": "Janeiro",
    "February": "Fevereiro",
    "March": "Março",
    "April": "Abril",
    "May": "Maio",
    "June": "Junho",
    "July": "Julho",
    "August": "Agosto",
    "September": "Setembro",
    "October": "Outubro",
    "November": "Novembro",
    "December": "Dezembro"
}

meses_mapping_ingles = {
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    "10": "October",
    "11": "November",
    "12": "December"
    }    


meses_mapping_portugues = {
    "janeiro": "Janeiro",
    "fevereiro": "Fevereiro",
    "março": "Março",
    "abril": "Abril",
    "May": "Maio",
    "June": "Junho",
    "July": "Julho",
    "August": "Agosto",
    "September": "Setembro",
    "October": "Outubro",
    "November": "Novembro",
    "December": "Dezembro"
}


def obter_id_ano_mes_atual(conn):
                    # Salva o locale atual do sistema


    # Define o locale para inglês
    try:
    # Tenta definir a localidade para inglês (Estados Unidos) no padrão UNIX
     locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
     try:
        # Tenta uma alternativa comum no Windows
        locale.setlocale(locale.LC_ALL, 'English_United States')
     except locale.Error:
        try:
            # Outra alternativa para Windows
            locale.setlocale(locale.LC_ALL, 'English')
        except locale.Error:
            # Se nada funcionar, usa a localidade padrão do sistema
            locale.setlocale(locale.LC_ALL, '')
    # Obtém o ano e mês atual
    data_atual = dt.now()
    ano_atual = data_atual.year
    mes_atual = data_atual.strftime("%B")  # Obtém o nome completo do mês
    

    
    try:
                # Tenta definir a localidade para pt_BR.UTF-8
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try:
                        # Tenta uma alternativa comum no Windows
                locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
        except locale.Error:
                        # Usa a localidade padrão do sistema se as específicas falharem
                locale.setlocale(locale.LC_ALL, '')
    

    cursor = conn.cursor()

    # Verifica se o ano atual já existe na tabela Ano
    cursor.execute("SELECT idAno FROM Ano WHERE ano = %s", (ano_atual,))
    ano_id = cursor.fetchone()

    # Se não existir, insira o ano na tabela Ano
    if not ano_id:
        cursor.execute("INSERT INTO Ano (ano) VALUES (%s)", (ano_atual,))
        ano_id = cursor.lastrowid
    else:
        ano_id = ano_id[0]

    # Verifica se o mês atual já existe na tabela Meses
    cursor.execute("SELECT idMes FROM Meses WHERE mes = %s AND idAno = %s", (mes_atual, ano_id))
    mes_id = cursor.fetchone()

    # Se não existir, insira o mês na tabela Meses
    if not mes_id:
        cursor.execute("INSERT INTO Meses (mes, idAno) VALUES (%s, %s)", (mes_atual, ano_id))
        mes_id = cursor.lastrowid
    else:
        mes_id = mes_id[0]

    cursor.close()
    return ano_id, mes_id



def buscarDadosFinanceiros():
            
        try:
                # Estabelece a conexão com o banco de dados
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas'
                )
                cursor = conn.cursor()
                
                
                # Define o locale para inglês
                try:
    # Tenta definir a localidade para inglês (Estados Unidos) no padrão UNIX
                  locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                except locale.Error:
                  try:
        # Tenta uma alternativa comum no Windows
                   locale.setlocale(locale.LC_ALL, 'English_United States')
                  except locale.Error:
                    try:
            # Outra alternativa para Windows
                      locale.setlocale(locale.LC_ALL, 'English')
                    except locale.Error:
            # Se nada funcionar, usa a localidade padrão do sistema
                     locale.setlocale(locale.LC_ALL, '')

                # Obtém os IDs do ano e mês atual
                ano_id, mes_id = obter_id_ano_mes_atual(conn)

                # Buscar as somas de entradas para o mês vigente
                cursor.execute("SELECT SUM(VALOR) FROM Item WHERE TIPO = 'ENTRADA' AND ID_MES = %s", (mes_id,))
                total_entradas = cursor.fetchone()[0] or 0

                # Buscar as somas de saídas para o mês vigente
                cursor.execute("SELECT SUM(VALOR) FROM Item WHERE TIPO = 'SAIDA' AND ID_MES = %s", (mes_id,))
                total_saidas = cursor.fetchone()[0] or 0

                # Calcular o total (entradas - saídas)
                total = total_entradas - total_saidas
                
                mes_numero = dt.now().strftime("%m")  # "02" para fevereiro, por exemplo

                # Utilizar o dicionário para mapear o número do mês para o nome em inglês
                mes_atual_ingles = meses_mapping_ingles[mes_numero]

                print("Nome do mês em inglês:", mes_atual_ingles)
                
                # Restaura o locale para o valor original
                try:
        # Tenta definir a localidade para pt_BR.UTF-8
                     locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
                except locale.Error:
                  try:
                # Tenta uma alternativa comum no Windows
                          locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
                  except locale.Error:
                # Usa a localidade padrão do sistema se as específicas falharem
                          locale.setlocale(locale.LC_ALL, '')

                # Traduz o nome do mês para português
                mes_atual_portugues = meses_mapa.get(mes_atual_ingles, "Mês desconhecido")
                

                return total_entradas, total_saidas, total, mes_atual_portugues

        except mysql.connector.Error as err:
                print(f"Erro ao buscar dados financeiros: {err}")
                return 0, 0, 0  # Retorna 0 para todas as somas em caso de erro
        finally:
                if conn.is_connected():
                 cursor.close()
                 conn.close()

class Ui_MainWindow(object):
        
        
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1930, 1082)
        MainWindow.showMaximized()
        self.nomeClientes = {}
        self.anoSelecionado = None  # Variável para armazenar o ano selecionado
        self.mesSelecionado = None  # Variável para armazenar o mês selecionado

        
        self.central_widget = QtWidgets.QWidget(MainWindow)
        MainWindow.setCentralWidget(self.central_widget)

        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Cria um QStackedWidget para conteúdos dinâmicos
        self.contentStack = QtWidgets.QStackedWidget(self.central_widget)
        self.layout.addWidget(self.contentStack)
        

        
                # Cria a parte superior fixa
        self.setupFixedTopPart()
        
        # Configura o conteúdo inicial
       
        self.setupInitialContent()
        self.atualizarInterfaceFinanceira()
        
        
        # Configura o menu e ações
        self.setupMenu(MainWindow)
        

        
    def setupMenu(self, MainWindow):
  
        self.menu_opcoes = QtWidgets.QMenuBar(MainWindow)
        self.menu_opcoes.setGeometry(QtCore.QRect(0, 0, 1930, 21))
        self.menu_opcoes.setObjectName("menu_opcoes")
        self.menu_opcoes_item0 = QtWidgets.QMenu(self.menu_opcoes)
        self.menu_opcoes_item0.setObjectName("menu_opcoes_item0")
        MainWindow.setMenuBar(self.menu_opcoes)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionProcurar = QtWidgets.QAction("actionProcurar", MainWindow)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/images_home/buscar.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionProcurar.setIcon(icon1)


        
        self.actionProcurar.triggered.connect(self.toggleSearchInput)
        self.actionProcurar.setShortcut('Ctrl+F')

        # Dentro de setupUi da Ui_MainWindow
        self.actionCadastrar = QtWidgets.QAction("Cadastrar", MainWindow)
        self.actionCadastrar.triggered.connect(self.showCadastroForm)
        self.actionCadastrar.triggered.connect(self.atualizarInterfaceFinanceira)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/images_home/create.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionCadastrar.setIcon(icon2)
      
        # Adicione esta linha para conectar o QAction ao método
       


        self.actionAtualizar = QtWidgets.QAction(MainWindow)
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":/images_home/refresh.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionAtualizar.setIcon(icon4)
        self.actionAtualizar.setObjectName("actionAtualizar")
        self.actionAtualizar.triggered.connect(self.atualizarTela)
        
        self.actionVer_Meses = QtWidgets.QAction("Ver_meses", MainWindow)
        self.actionVer_Meses.triggered.connect(self.showTelaVerMeses)
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap(":/images_home/olhinho.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionVer_Meses.setIcon(icon5)
        self.actionVer_Meses.setObjectName("actionVer_Meses")

        self.actionVerCaixa = QtWidgets.QAction(MainWindow)
        icon7 = QtGui.QIcon()
        icon7.addPixmap(QtGui.QPixmap(":/images_home/caixa.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionVerCaixa.setIcon(icon7)
        self.actionVerCaixa.setObjectName("actionVerCaixa")
        self.actionVerCaixa.triggered.connect(self.telaCaixaAbrir)
        self.actionDetalhes_do_Saldo = QtWidgets.QAction(MainWindow)
        icon8 = QtGui.QIcon()
        icon8.addPixmap(QtGui.QPixmap(":/images_home/saldo.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionDetalhes_do_Saldo.setIcon(icon8)
        self.actionDetalhes_do_Saldo.setObjectName("actionDetalhes_do_Saldo")
        self.actionDetalhes_do_Saldo.triggered.connect(self.detalhesSaldoAbrir)
        self.actionFechamento_do_Dia = QtWidgets.QAction(MainWindow)
        icon9 = QtGui.QIcon()
        icon9.addPixmap(QtGui.QPixmap(":/images_home/fechamento_dia.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionFechamento_do_Dia.setIcon(icon9)
        self.actionFechamento_do_Dia.setObjectName("actionFechamento_do_Dia")
        self.actionFechamento_do_Dia.triggered.connect(self.fechamentoDoDia)
        
        self.actionAlterar_senha = QtWidgets.QAction(MainWindow)
        icon10 = QtGui.QIcon()
        icon10.addPixmap(QtGui.QPixmap(":/images_home/chave.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionAlterar_senha.setIcon(icon10)
        self.actionAlterar_senha.setObjectName("actionAlterar_senha")
        self.actionAlterar_senha.triggered.connect(self.alterarSenha)
        
        self.menu_opcoes_item0.addAction(self.actionProcurar)
        self.menu_opcoes_item0.addAction(self.actionCadastrar)
        self.menu_opcoes_item0.addAction(self.actionAtualizar)
        self.menu_opcoes_item0.addAction(self.actionVer_Meses)
        self.menu_opcoes_item0.addAction(self.actionVerCaixa)
        self.menu_opcoes_item0.addAction(self.actionDetalhes_do_Saldo)
        self.menu_opcoes_item0.addAction(self.actionFechamento_do_Dia)
        self.menu_opcoes_item0.addAction(self.actionAlterar_senha)
        self.menu_opcoes.addAction(self.menu_opcoes_item0.menuAction())
        
        self.retranslateUiMenuSetup(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        

        
    def setupInitialContent(self):
        # Aqui você configura o conteúdo inicial, como a tabela que você mencionou
        # Este widget é adicionado ao self.contentStack   
        # AQUI SERIA O NOSSO CONTENT (QUE SEMPRE PODE SER REENDERIZADO) ESTE É O MAIN
        
        # Criação do widget que será o conteúdo inicial


        self.pushButton_voltar.setVisible(False)  # Oculta o botão ao retornar ao conteúdo inicial
        self.initialContentWidget = QtWidgets.QWidget()
        self.initialContentWidget.setObjectName("initialContentWidget")
        
        self.searchInput = QtWidgets.QLineEdit(self.initialContentWidget)
        self.searchInput.setGeometry(QtCore.QRect(440, 330, 1050, 30))  # Ajuste conforme necessário
        self.searchInput.setPlaceholderText("Pesquisar Cliente...")
        self.searchInput.setHidden(True)  # Esconde a input inicialmente
        self.searchInput.setStyleSheet("""
                QLineEdit {
                font: 8pt "Sans Serif Collection";
                color: rgb(51, 51, 51);
                border-radius: 5px;
                border: 1px solid #5c5c5c; /* Adiciona uma borda padrão */
                background-color: white; /* Fundo branco padrão */
                }
                QLineEdit:hover {
                background-color: #e0fffb; /* Azul suave ao passar o mouse */
                border: 1px solid #155f8e;
                }
                QLineEdit:pressed {
                background-color: #e0fffb; /* Azul um pouco mais forte ao clicar */
                border: 1px solid #155f8e;
                
                }
                """)

        self.searchInput.textChanged.connect(self.filterTableData)  # Conecta ao método de filtragem
        
        # Cria uma QScrollArea
        self.scrollArea = QtWidgets.QScrollArea(self.initialContentWidget)
        self.scrollArea.setGeometry(QtCore.QRect(440, 370, 1050, 500))
        self.scrollArea.setWidgetResizable(True)  # Permite que o widget interno se expanda
        # Após criar e configurar a QScrollArea
        self.scrollArea.setStyleSheet("""
        QScrollArea {
                border: transparent  /* Define a espessura e a cor da borda */
                
        }
        QScrollBar:vertical {
                width: 12px;  /* Largura da barra de rolagem vertical */
        }
        QScrollBar:horizontal {
                height: 12px;  /* Altura da barra de rolagem horizontal */
        }
        """)

        
        self.contentStack.setCurrentWidget(self.initialContentWidget)
        self.tableWidget = QtWidgets.QTableWidget(self.initialContentWidget)
        self.tableWidget.setGeometry(QtCore.QRect(440, 370, 1050, 500))
        self.tableWidget.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.tableWidget.setToolTip("")
        self.tableWidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tableWidget.setAutoFillBackground(False)
        self.tableWidget.verticalHeader().setVisible(False)

       
        
        # Adiciona a QTableWidget como widget da QScrollArea
        self.scrollArea.setWidget(self.tableWidget)
        

        self.tableWidget.setStyleSheet("font: 12pt \"Sans Serif Collection\";\n"
"color: rgb(51, 51, 51);")
        self.tableWidget.setLineWidth(0)
        self.tableWidget.setMidLineWidth(0)
        self.tableWidget.setAutoScroll(True)
        self.tableWidget.setAutoScrollMargin(16)
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
         

        self.tableWidget.setObjectName("tableWidget")
        
        

        # Adiciona o widget inicial ao QStackedWidget
        self.contentStack.addWidget(self.initialContentWidget)
        self.contentStack.setCurrentWidget(self.initialContentWidget)
        
        self.retranslateUiContentInitial(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        # Ajuste automático ou fixo para larguras de coluna
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        
  

        
               
               
    def setupFixedTopPart(self):
        # PARTE SUPERIOR (FIXA EM TODAS REENDERIZAÇÕES)
        
        # Utilizando um layout vertical para organizar os widgets fixos e o contentStack
        self.fixedLayout = QtWidgets.QVBoxLayout()
        
        self.label_header_home = QtWidgets.QLabel(self.central_widget)
        self.label_header_home.setGeometry(QtCore.QRect(0, 0, 1920, 200))
        
        self.label_header_home.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_header_home.setStyleSheet("background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba(2,0,36,1), stop:1 rgba(9,121,35,1), stop:2 rgba(0,212,255,1));\n"
"\n"
"font: 75 12pt \"Arial Narrow\";\n"
"\n"
"\n"
"color: rgb(255, 255, 255);"
"padding: 20px ;")
        self.label_header_home.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop)
        self.label_header_home.setObjectName("label_header_home")
        

        
        self.lineEdit_mes_header = QtWidgets.QLabel(self.central_widget)
        self.lineEdit_mes_header.setGeometry(QtCore.QRect(810, 40, 301, 61))
        self.lineEdit_mes_header.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.lineEdit_mes_header.setStyleSheet("background-color: transparent;\n"
"color: rgb(255, 255, 255);\n"
"\n"
"\n"
"font: 55 28pt \"Arial Black\";\n"
"border:none;\n"
"")
        self.lineEdit_mes_header.setAlignment(QtCore.Qt.AlignCenter)
        self.lineEdit_mes_header.setObjectName("lineEdit_mes_header")
       
        self.image_cifrao_header = QtWidgets.QTextBrowser(self.central_widget)
        self.image_cifrao_header.setGeometry(QtCore.QRect(1020, 20, 24, 24))
        self.image_cifrao_header.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.image_cifrao_header.setStyleSheet("background-color: transparent;\n"
"border-image: url(:/images_home/cifrao.png);\n"
"\n"
"color: rgb(255, 255, 255);\n"
"\n"
"\n"
"\n"
"border:none;\n"
"")
        self.image_cifrao_header.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.image_cifrao_header.setObjectName("image_cifrao_header")
        
        
        
        self.label_entradas = QtWidgets.QLabel(self.central_widget)
        self.label_entradas.setGeometry(QtCore.QRect(440, 130, 250, 150))
        self.label_entradas.setStyleSheet("font: 16pt \"Sans Serif Collection\";\n"
"background-color: rgb(255, 255, 255);\n"
"color: rgb(51, 51, 51);\n"
"border-radius:10px;"
"padding: 0 15px;")
        self.label_entradas.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_entradas.setIndent(8)
        self.label_entradas.setObjectName("label_entradas")
        self.lineEdit_entradas_valor = QtWidgets.QLabel(self.central_widget)
        self.lineEdit_entradas_valor.setGeometry(QtCore.QRect(460, 220, 221, 41))
        self.lineEdit_entradas_valor.setStyleSheet("background-color: transparent;\n"
"color: rgb(51, 51, 51);\n"
"\n"
"\n"
"\n"
"font: 22pt \"Arial Rounded MT Bold\";\n"
"border:none;")
        self.lineEdit_entradas_valor.setObjectName("lineEdit_entradas_valor")
        
        
        self.label_saidas = QtWidgets.QLabel(self.central_widget)
        self.label_saidas.setGeometry(QtCore.QRect(840, 130, 250, 150))
        self.label_saidas.setStyleSheet("font: 16pt \"Sans Serif Collection\";\n"
"background-color: rgb(255, 255, 255);\n"
"color: rgb(51, 51, 51);\n"
"border-radius:10px;"
"padding: 0 15px;")
        self.label_saidas.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_saidas.setIndent(8)
        self.label_saidas.setObjectName("label_saidas")
        self.lineEdit_saidas_valor = QtWidgets.QLabel(self.central_widget)
        self.lineEdit_saidas_valor.setGeometry(QtCore.QRect(860, 220, 221, 41))
        self.lineEdit_saidas_valor.setStyleSheet("background-color: transparent;\n"
"color: rgb(51, 51, 51);\n"
"\n"
"\n"
"\n"
"font: 22pt \"Arial Rounded MT Bold\";\n"
"border:none;"
)
        self.lineEdit_saidas_valor.setObjectName("lineEdit_saidas_valor")
        
        
        self.label_total = QtWidgets.QLabel(self.central_widget)
        self.label_total.setGeometry(QtCore.QRect(1250, 130, 250, 150))
        self.label_total.setStyleSheet("font: 16pt \"Sans Serif Collection\";\n"
"\n"
"color: rgb(255, 255, 255);\n"
"border-radius:10px;\n"
"background-color: rgb(246, 68, 68);"
"padding: 0 15px;")
        self.label_total.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_total.setIndent(8)
        self.label_total.setObjectName("label_total")
        self.label_total.setFont(QFont('Sans Serif Collection', 16))
        self.lineEdit_total_valor = QtWidgets.QLabel(self.central_widget)
        self.lineEdit_total_valor.setGeometry(QtCore.QRect(1270, 220, 221, 41))
        self.lineEdit_total_valor.setStyleSheet("background-color: transparent;\n"
"color: rgb(255, 255, 255);\n"
"\n"
"\n"
"\n"
"\n"
"font: 22pt \"Arial Rounded MT Bold\";\n"
"border:none;")
        self.lineEdit_total_valor.setObjectName("lineEdit_total_valor")
        
        
        self.image_cifrao_header_2 = QtWidgets.QTextBrowser(self.central_widget)
        self.image_cifrao_header_2.setGeometry(QtCore.QRect(1450, 150, 24, 24))
        self.image_cifrao_header_2.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.image_cifrao_header_2.setStyleSheet("background-color: transparent;\n"
"border-image: url(:/images_home/total.png);\n"
"\n"
"color: rgb(255, 255, 255);\n"
"\n"
"\n"
"\n"
"border:none;\n"
"")
        self.image_cifrao_header_2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.image_cifrao_header_2.setObjectName("image_cifrao_header_2")
        self.image_cifrao_header_3 = QtWidgets.QTextBrowser(self.central_widget)
        self.image_cifrao_header_3.setGeometry(QtCore.QRect(1040, 150, 24, 24))
        self.image_cifrao_header_3.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.image_cifrao_header_3.setStyleSheet("background-color: transparent;\n"
"border-image: url(:/images_home/down.png);\n"
"\n"
"color: rgb(255, 255, 255);\n"
"\n"
"\n"
"\n"
"border:none;\n"
"")
        self.image_cifrao_header_3.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.image_cifrao_header_3.setObjectName("image_cifrao_header_3")
        self.image_cifrao_header_4 = QtWidgets.QTextBrowser(self.central_widget)
        self.image_cifrao_header_4.setGeometry(QtCore.QRect(640, 150, 24, 24))
        self.image_cifrao_header_4.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.image_cifrao_header_4.setStyleSheet("background-color: transparent;\n"
"border-image: url(:/images_home/up.png);\n"
"\n"
"color: rgb(255, 255, 255);\n"
"\n"
"\n"
"\n"
"border:none;\n"
"")
        self.image_cifrao_header_4.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.image_cifrao_header_4.setObjectName("image_cifrao_header_4")
        
        #INICIALIZA BOTÃO VOLTAR PRO MAIN
        self.pushButton_voltar = QtWidgets.QPushButton(self.central_widget)
        self.pushButton_voltar.setGeometry(QtCore.QRect(30, 20, 64, 64))
        self.pushButton_voltar.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_voltar.setStyleSheet("border-image: url(:/images_home/voltar.png);")
        self.pushButton_voltar.setText("")
        self.pushButton_voltar.hide()  # Inicialmente invisível
        self.pushButton_voltar.setObjectName("pushButton_voltar")
        # Conectar o botão de voltar ao método showInitialContent
        self.pushButton_voltar.clicked.connect(self.setupInitialContent)
        self.pushButton_voltar.clicked.connect(self.atualizarInterfaceFinanceira)

        
        
        
        
        self.retranslateUiFixedTop(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        
        
        
        

        
        # FIM DA PARTE SUPERIOR         
        


   
    def showCadastroForm(self):
        # Este método deve preparar e exibir o formulário de cadastro
        # Primeiro, verifique se o formulário já foi criado. Se não, crie e adicione ao self.contentStack
        # Depois, mude o widget atual do self.contentStack para o formulário de cadastro
        
        #INICIALIZA TELA CADASTRO (INICIALIZA O CONTENT CADASTRO)
    
        self.pushButton_voltar.show()
 
        # Verifica se o widget de cadastro já foi criado
        if not hasattr(self, 'tela_cadastro_widget'):
                self.tela_cadastro_widget = QtWidgets.QWidget()
                self.tela_cadastro_widget.setObjectName("tela_cadastro_widget")
                

                self.comboBox_DocN = QtWidgets.QComboBox(self.tela_cadastro_widget)
                self.comboBox_DocN.setGeometry(QtCore.QRect(440, 390, 300, 60))  # Ajuste as dimensões conforme necessário
                self.comboBox_DocN.setObjectName("comboBox_DocN")
                self.comboBox_DocN.setStyleSheet("""
                QComboBox {
                font: 12pt "Sans Serif Collection";
                color: rgb(51, 51, 51);
                border: 1px solid #333; /* Adiciona uma borda padrão */
                border-radius: 5px;
                padding: 1px 18px 1px 3px; /* Ajusta o preenchimento */
                background-color: white; /* Fundo branco padrão */
                }

                QComboBox:hover {
                background-color: #e0fffb; /* Azul suave ao passar o mouse */
                border: 1px solid #155f8e;
                }

                QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px; /* Largura do botão dropdown */
                border-left-width: 0.5px;
                border-top-right-radius: 4px; /* Arredonda o canto superior direito */
                border-bottom-right-radius: 4px; /* Arredonda o canto inferior direito */
                }

                QComboBox::down-arrow {
                image: url(:/images_home/down_combobox.png); /* Caminho para o ícone da seta */
                width: 16px; /* Largura do ícone da seta */
                height: 16px; /* Altura do ícone da seta */
                }

                QComboBox::down-arrow:on { /* Altera o ícone quando o menu está aberto */
                top: 1px; /* Muda a posição do ícone da seta para cima */
                }
                """)



                self.comboBox_DocN.addItem("PT")
                self.comboBox_DocN.addItem("PP")
                self.comboBox_DocN.addItem("PR")
                self.legenda_docN = QtWidgets.QLabel(self.tela_cadastro_widget)
                self.legenda_docN.setGeometry(QtCore.QRect(440, 360, 120, 30))
                self.legenda_docN.setLayoutDirection(QtCore.Qt.LeftToRight)
                self.legenda_docN.setStyleSheet("background-color: transparent;\n"
        "font: 12pt \"HP Simplified\";\n"
        "color: rgb(51, 51, 51);\n"
        "\n"
        "\n"
        "\n"
        "border:none;\n"
        "")
                self.legenda_docN.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
                self.legenda_docN.setObjectName("legenda_docN")
                self.legenda_cliente = QtWidgets.QLabel(self.tela_cadastro_widget)
                self.legenda_cliente.setGeometry(QtCore.QRect(440, 490, 120, 30))
                self.legenda_cliente.setLayoutDirection(QtCore.Qt.LeftToRight)
                self.legenda_cliente.setStyleSheet("background-color: transparent;\n"
        "font: 12pt \"HP Simplified\";\n"
        "color: rgb(51, 51, 51);\n"
        "\n"
        "\n"
        "\n"
        "border:none;\n"
        "")
                self.legenda_cliente.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
                self.legenda_cliente.setObjectName("legenda_cliente")
                self.textEdit_Cliente = QtWidgets.QLineEdit(self.tela_cadastro_widget)
                self.textEdit_Cliente.setGeometry(QtCore.QRect(440, 520, 300, 60))
                self.textEdit_Cliente.setObjectName("textEdit_Cliente")
                self.textEdit_Cliente.setStyleSheet("""
                QLineEdit {
                font: 12pt "Sans Serif Collection";
                color: rgb(51, 51, 51);
                border-radius: 5px;
                border: 1px solid #5c5c5c; /* Adiciona uma borda padrão */
                background-color: white; /* Fundo branco padrão */
                }
                QLineEdit:hover {
                background-color: #e0fffb; /* Azul suave ao passar o mouse */
                border: 1px solid #155f8e;
                }
                QLineEdit:pressed {
                background-color: #e0fffb; /* Azul um pouco mais forte ao clicar */
                border: 1px solid #155f8e;
                
                }
                """)

                
                
                
                self.lineEdit_valor = QtWidgets.QLineEdit(self.tela_cadastro_widget)
                self.lineEdit_valor.setGeometry(QtCore.QRect(440, 650, 300, 60))  # Ajuste a posição conforme necessário
                self.lineEdit_valor.setObjectName("lineEdit_valor")
                self.lineEdit_valor.setStyleSheet("""
                QLineEdit {
                font: 12pt "Sans Serif Collection";
                color: rgb(51, 51, 51);
                border-radius: 5px;
                border: 1px solid #5c5c5c; /* Adiciona uma borda padrão */
                background-color: white; /* Fundo branco padrão */
                }
                QLineEdit:hover {
                background-color: #e0fffb; /* Azul suave ao passar o mouse */
                border: 1px solid #155f8e;
                }
                QLineEdit:pressed {
                background-color: #e0fffb; /* Azul um pouco mais forte ao clicar */
                border: 1px solid #155f8e;
                
                }
                """)
                self.legenda_valor = QtWidgets.QLabel(self.tela_cadastro_widget)
                self.legenda_valor.setGeometry(QtCore.QRect(440, 620, 60, 30))
                self.legenda_valor.setLayoutDirection(QtCore.Qt.LeftToRight)
                self.legenda_valor.setStyleSheet("background-color: transparent;\n"
        "font: 12pt \"HP Simplified\";\n"
        "color: rgb(51, 51, 51);\n"
        "\n"
        "\n"
        "\n"
        "border:none;\n"
        "")
                self.legenda_valor.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
                self.legenda_valor.setObjectName("legenda_valor")
                
                
                self.textEdit_formaPagamento = QtWidgets.QLineEdit(self.tela_cadastro_widget)
                self.textEdit_formaPagamento.setGeometry(QtCore.QRect(840, 390, 300, 60))
                self.textEdit_formaPagamento.setObjectName("textEdit_formaPagamento")
                self.textEdit_formaPagamento.setStyleSheet("""
                QLineEdit {
                font: 12pt "Sans Serif Collection";
                color: rgb(51, 51, 51);
                border-radius: 5px;
                border: 1px solid #5c5c5c; /* Adiciona uma borda padrão */
                background-color: white; /* Fundo branco padrão */
                }
                QLineEdit:hover {
                background-color: #e0fffb; /* Azul suave ao passar o mouse */
                border: 1px solid #155f8e;
                }
                QLineEdit:pressed {
                background-color: #e0fffb; /* Azul um pouco mais forte ao clicar */
                border: 1px solid #155f8e;
                
                }
                """)
                self.legenda_forma_pagamento = QtWidgets.QLabel(self.tela_cadastro_widget)
                self.legenda_forma_pagamento.setGeometry(QtCore.QRect(840, 360, 220, 30))
                self.legenda_forma_pagamento.setLayoutDirection(QtCore.Qt.LeftToRight)
                self.legenda_forma_pagamento.setStyleSheet("background-color: transparent;\n"
        "font: 12pt \"HP Simplified\";\n"
        "color: rgb(51, 51, 51);\n"
        "\n"
        "\n"
        "\n"
        "border:none;\n"
        "")
        
                self.legenda_forma_pagamento.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
                self.legenda_forma_pagamento.setObjectName("legenda_forma_pagamento")
                self.dateEdit = QtWidgets.QDateEdit(self.tela_cadastro_widget)
                self.dateEdit.setGeometry(QtCore.QRect(840, 520, 300, 60))
                self.dateEdit.setStyleSheet("""
                QDateEdit {
                font: 12pt "Sans Serif Collection";
                color: rgb(51, 51, 51);
                border-radius: 5px;
                border: 1px solid #5c5c5c; /* Adiciona uma borda padrão */
                background-color: white; /* Fundo branco padrão */
                }
                QDateEdit:hover {
                background-color: #e0fffb; /* Azul suave ao passar o mouse */
                border: 1px solid #155f8e;
                }
                QDateEdit:pressed {
                background-color: #e0fffb; /* Azul um pouco mais forte ao clicar */
                border: 1px solid #155f8e;
                
                }
                """)
                font = QtGui.QFont()
                font.setFamily("Sans Serif Collection")
                font.setPointSize(8)
                self.dateEdit.setFont(font)
                self.dateEdit.setLayoutDirection(QtCore.Qt.LeftToRight)
                self.dateEdit.setObjectName("dateEdit")
                self.dateEdit.setDate(QDate.currentDate())  # Define a data atual como valor padrão

                # Define o formato da data para o estilo brasileiro (dia/mês/ano)
                self.dateEdit.setDisplayFormat("dd/MM/yyyy")
                
                self.legenda_data = QtWidgets.QLabel(self.tela_cadastro_widget)
                self.legenda_data.setGeometry(QtCore.QRect(840, 490, 120, 30))
                self.legenda_data.setLayoutDirection(QtCore.Qt.LeftToRight)
                self.legenda_data.setStyleSheet("background-color: transparent;\n"
        "font: 12pt \"HP Simplified\";\n"
        "color: rgb(51, 51, 51);\n"
        "\n"
        "\n"
        "\n"
        "border:none;\n"
        "")
                self.legenda_data.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
                self.legenda_data.setObjectName("legenda_data")
                
                

                
               # Criação do QComboBox para Qnt Dividida
                self.comboBox_qntDividida = QtWidgets.QComboBox(self.tela_cadastro_widget)
                self.comboBox_qntDividida.setGeometry(QtCore.QRect(840, 650, 300, 60))  # Ajuste a posição conforme necessário
                self.comboBox_qntDividida.setObjectName("comboBox_qntDividida")
                self.comboBox_qntDividida.setStyleSheet("""
                QComboBox {
                font: 12pt "Sans Serif Collection";
                color: rgb(51, 51, 51);
                border: 1px solid #333; /* Adiciona uma borda padrão */
                border-radius: 5px;
                padding: 1px 18px 1px 3px; /* Ajusta o preenchimento */
                background-color: white; /* Fundo branco padrão */
                }

                QComboBox:hover {
                background-color: #e0fffb; /* Azul suave ao passar o mouse */
                border: 1px solid #155f8e;
                }

                QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px; /* Largura do botão dropdown */
                border-left-width: 0.5px;
                border-top-right-radius: 4px; /* Arredonda o canto superior direito */
                border-bottom-right-radius: 4px; /* Arredonda o canto inferior direito */
                }

                QComboBox::down-arrow {
                image: url(:/images_home/down_combobox.png); /* Caminho para o ícone da seta */
                width: 16px; /* Largura do ícone da seta */
                height: 16px; /* Altura do ícone da seta */
                }

                QComboBox::down-arrow:on { /* Altera o ícone quando o menu está aberto */
                top: 1px; /* Muda a posição do ícone da seta para cima */
                }
                """)


                # Adicionando opções ao comboBox_qntDividida
                self.comboBox_qntDividida.addItem(" à vista")  # Opção para pagamento à vista
                for i in range(2, 13):  # Adiciona opções de 1x até 12x
                        self.comboBox_qntDividida.addItem(f"{i}x")
                # Depois de adicionar todos os itens ao comboBox_qntDividida
                self.comboBox_qntDividida.setCurrentIndex(0)  # Define "à vista" como o valor padrão

                self.legenda_parcelas = QtWidgets.QLabel(self.tela_cadastro_widget)
                self.legenda_parcelas.setGeometry(QtCore.QRect(840, 620, 200, 30))
                self.legenda_parcelas.setLayoutDirection(QtCore.Qt.LeftToRight)
                self.legenda_parcelas.setStyleSheet("background-color: transparent;\n"
        "font: 12pt \"HP Simplified\";\n"
        "color: rgb(51, 51, 51);\n"
        "\n"
        "\n"
        "\n"
        "border:none;\n"
        "")
                self.legenda_parcelas.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
                self.legenda_parcelas.setObjectName("legenda_parcelas")

                
                
                self.pushButton = QtWidgets.QPushButton(self.tela_cadastro_widget)
                self.pushButton.setGeometry(QtCore.QRect(1250, 650, 300, 60))
                self.pushButton.setStyleSheet("background-color: rgb(0, 210, 135);\n"
        "color: rgb(255, 255, 255);\n"
        "font: 20pt \"Sans Serif Collection\";\n"
        "border-radius:10px;")
                self.pushButton.setObjectName("pushButton")


                # Conectar o evento de clique do botão à função coletar_dados_do_formulario
                self.pushButton.clicked.connect(self.coletar_dados_do_formulario)

                
                self.radioButton_entrada = QtWidgets.QRadioButton(self.tela_cadastro_widget)
                self.radioButton_entrada.setGeometry(QtCore.QRect(1240, 540, 131, 21))
                self.radioButton_entrada.setStyleSheet("font: 16pt \"Sans Serif Collection\";\n"
        "color: rgb(51, 51, 51);")
                self.radioButton_entrada.setObjectName("radioButton_entrada")
                self.radioButton_saida = QtWidgets.QRadioButton(self.tela_cadastro_widget)
                self.radioButton_saida.setGeometry(QtCore.QRect(1400, 540, 111, 21))
                self.radioButton_saida.setStyleSheet("font: 16pt \"Sans Serif Collection\";\n"
        "color:rgb(51, 51, 51);")
                self.radioButton_saida.setObjectName("radioButton_saida")
                self.radioButton_entrada.clicked.connect(self.mostrarDocN)
                self.radioButton_saida.clicked.connect(self.ocultarDocN)

                self.menu_opcoes = QtWidgets.QMenuBar(MainWindow)
                self.menu_opcoes.setGeometry(QtCore.QRect(0, 0, 1930, 21))
                self.menu_opcoes.setObjectName("menu_opcoes")
                self.statusbar = QtWidgets.QStatusBar(MainWindow)
                self.statusbar.setObjectName("statusbar")
                
                # Adiciona o widget de cadastro ao QStackedWidget
                self.contentStack.addWidget(self.tela_cadastro_widget)

        # Muda o widget atual para o formulário de cadastro
        self.contentStack.setCurrentWidget(self.tela_cadastro_widget)

        
        self.retranslateUiFormCadastro(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
    def showTelaVerMeses(self):
        # Este método deve preparar e exibir o formulário de cadastro
        # Primeiro, verifique se o formulário já foi criado. Se não, crie e adicione ao self.contentStack
        # Depois, mude o widget atual do self.contentStack para o formulário de cadastro
        
        #INICIALIZA TELA Ver Meses (INICIALIZA O CONTENT Ver Meses)
   
        self.pushButton_voltar.show()
 
         # Verifica se o widget de Ver Meses já foi criado
        if not hasattr(self, 'tela_ver_meses_widget'):
                self.tela_ver_meses_widget = QtWidgets.QWidget()
                self.tela_ver_meses_widget.setObjectName("tela_ver_meses_widget") 
                
                self.radioButton_entrada_2 = QtWidgets.QRadioButton(self.tela_ver_meses_widget)
                self.radioButton_entrada_2.setGeometry(QtCore.QRect(440, 320, 60, 31))
                self.radioButton_entrada_2.setStyleSheet("background-color: transparent;\n"
        "font: 14pt \"Sans Serif Collection\";\n"
        "color: rgb(51, 51, 51);\n"
        "")
                self.radioButton_entrada_2.setObjectName("radioButton_entrada_2")
                self.radioButton_entrada_2.clicked.connect(lambda: self.selecionarAno(2024))
                self.radioButton_entrada_3 = QtWidgets.QRadioButton(self.tela_ver_meses_widget)
                self.radioButton_entrada_3.setGeometry(QtCore.QRect(600, 320, 60, 31))
                self.radioButton_entrada_3.setStyleSheet("background-color: transparent;\n"
        "font: 14pt \"Sans Serif Collection\";\n"
        "color: rgb(51, 51, 51);\n"
        "")
                self.radioButton_entrada_3.setObjectName("radioButton_entrada_3")
                self.radioButton_entrada_3.clicked.connect(lambda: self.selecionarAno(2025))
                self.radioButton_entrada_4 = QtWidgets.QRadioButton(self.tela_ver_meses_widget)
                self.radioButton_entrada_4.setGeometry(QtCore.QRect(760, 320, 60, 31))
                self.radioButton_entrada_4.setStyleSheet("background-color: transparent;\n"
        "font: 14pt \"Sans Serif Collection\";\n"
        "color: rgb(51, 51, 51);\n"
        "")
                self.radioButton_entrada_4.setObjectName("radioButton_entrada_4")
                self.radioButton_entrada_4.clicked.connect(lambda: self.selecionarAno(2026))
                self.radioButton_entrada_5 = QtWidgets.QRadioButton(self.tela_ver_meses_widget)
                self.radioButton_entrada_5.setGeometry(QtCore.QRect(920, 320, 60, 31))
                self.radioButton_entrada_5.setStyleSheet("background-color: transparent;\n"
        "font: 14pt \"Sans Serif Collection\";\n"
        "color: rgb(51, 51, 51);\n"
        "")
                self.radioButton_entrada_5.setObjectName("radioButton_entrada_5")
                self.radioButton_entrada_5.clicked.connect(lambda: self.selecionarAno(2027))
                self.radioButton_entrada_6 = QtWidgets.QRadioButton(self.tela_ver_meses_widget)
                self.radioButton_entrada_6.setGeometry(QtCore.QRect(1080, 320, 60, 31))
                self.radioButton_entrada_6.setStyleSheet("background-color: transparent;\n"
        "font: 14pt \"Sans Serif Collection\";\n"
        "color: rgb(51, 51, 51);\n"
        "")
                self.radioButton_entrada_6.setObjectName("radioButton_entrada_6")
                self.radioButton_entrada_6.clicked.connect(lambda: self.selecionarAno(2028))
                self.radioButton_entrada_7 = QtWidgets.QRadioButton(self.tela_ver_meses_widget)
                self.radioButton_entrada_7.setGeometry(QtCore.QRect(1240, 320, 60, 31))
                self.radioButton_entrada_7.setStyleSheet("background-color: transparent;\n"
        "font: 14pt \"Sans Serif Collection\";\n"
        "color: rgb(51, 51, 51);\n"
        "")
                self.radioButton_entrada_7.setObjectName("radioButton_entrada_7")
                self.radioButton_entrada_7.clicked.connect(lambda: self.selecionarAno(2029))
                self.radioButton_entrada_8 = QtWidgets.QRadioButton(self.tela_ver_meses_widget)
                self.radioButton_entrada_8.setGeometry(QtCore.QRect(1400, 320, 60, 31))
                self.radioButton_entrada_8.setStyleSheet("background-color: transparent;\n"
        "font: 14pt \"Sans Serif Collection\";\n"
        "color: rgb(51, 51, 51);\n"
        "")
                self.radioButton_entrada_8.setObjectName("radioButton_entrada_8")
                self.radioButton_entrada_8.clicked.connect(lambda: self.selecionarAno(2030))
                
                self.pushButton = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton.setGeometry(QtCore.QRect(440, 430, 330, 70))
   
  
                self.pushButton.setObjectName("pushButton")
                self.pushButton.clicked.connect(lambda: self.selecionarMes("January"))
                self.pushButton.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)


                
                self.pushButton_2 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_2.setGeometry(QtCore.QRect(440, 510, 330, 70))
                self.pushButton_2.setObjectName("pushButton_2")
                self.pushButton_2.clicked.connect(lambda: self.selecionarMes("February"))
                self.pushButton_2.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                
                self.pushButton_3 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_3.setGeometry(QtCore.QRect(440, 590, 330, 70))
                self.pushButton_3.setObjectName("pushButton_3")
                self.pushButton_3.clicked.connect(lambda: self.selecionarMes("March"))
                self.pushButton_3.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                
                self.pushButton_4 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_4.setGeometry(QtCore.QRect(440, 670, 330, 70))
                self.pushButton_4.setObjectName("pushButton_4")
                self.pushButton_4.clicked.connect(lambda: self.selecionarMes("April"))
                self.pushButton_4.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                

                self.pushButton_5 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_5.setGeometry(QtCore.QRect(790, 430, 330, 70))
                self.pushButton_5.setObjectName("pushButton_5")
                self.pushButton_5.clicked.connect(lambda: self.selecionarMes("May"))
                self.pushButton_5.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                
                self.pushButton_6 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_6.setGeometry(QtCore.QRect(790, 510, 330, 70))
                self.pushButton_6.setObjectName("pushButton_6")
                self.pushButton_6.clicked.connect(lambda: self.selecionarMes("June"))
                self.pushButton_6.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                

                self.pushButton_7 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_7.setGeometry(QtCore.QRect(790, 590, 330, 70))
                self.pushButton_7.setObjectName("pushButton_7")
                self.pushButton_7.clicked.connect(lambda: self.selecionarMes("July"))
                self.pushButton_7.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                
                self.pushButton_8 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_8.setGeometry(QtCore.QRect(790, 670, 330, 70))
                self.pushButton_8.setObjectName("pushButton_8")
                self.pushButton_8.clicked.connect(lambda: self.selecionarMes("August"))
                self.pushButton_8.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                

                self.pushButton_9 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_9.setGeometry(QtCore.QRect(1140, 430, 330, 70))
                self.pushButton_9.setObjectName("pushButton_9")
                self.pushButton_9.clicked.connect(lambda: self.selecionarMes("September"))
                self.pushButton_9.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                
                
                self.pushButton_10 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_10.setGeometry(QtCore.QRect(1140, 510, 330, 70))
                self.pushButton_10.setObjectName("pushButton_10")
                self.pushButton_10.clicked.connect(lambda: self.selecionarMes("October"))
                self.pushButton_10.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                
                
                self.pushButton_11 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_11.setGeometry(QtCore.QRect(1140, 590, 330, 70))
                self.pushButton_11.setObjectName("pushButton_11")
                self.pushButton_11.clicked.connect(lambda: self.selecionarMes("November"))
                self.pushButton_11.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                

                self.pushButton_12 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_12.setGeometry(QtCore.QRect(1140, 670, 330, 70))
                self.pushButton_12.setObjectName("pushButton_12")
                self.pushButton_12.clicked.connect(lambda: self.selecionarMes("December"))
                self.pushButton_12.setStyleSheet("""
                QPushButton {
                        font: 14pt "Sans Serif Collection";
                        color: rgb(51, 51, 51);
                        border-radius: 5px;
                        border: none; /* Mantém uma borda padrão */
                        background-color: white; /* Fundo branco padrão */
                }
                QPushButton:hover {
                        background-color: #a0ebdd; /* Azul suave ao passar o mouse */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                QPushButton:pressed {
                        background-color: #a0ebdd; /* Azul um pouco mais forte ao clicar */
                        border: 1px solid #5c5c5c; /* Mantém a borda sólida */
                }
                """)
                
                self.label = QtWidgets.QLabel(self.tela_ver_meses_widget)
                self.label.setGeometry(QtCore.QRect(440, 360, 1020, 8))
                self.label.setStyleSheet("background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba(2,0,36,1), stop:1 rgba(9,121,35,1), stop:2 rgba(0,212,255,1));")
                self.label.setText("")
                self.label.setObjectName("label")
                self.pushButton_13 = QtWidgets.QPushButton(self.tela_ver_meses_widget)
                self.pushButton_13.setGeometry(QtCore.QRect(790, 760, 330, 70))
                self.pushButton_13.setStyleSheet("font: 14pt \"Sans Serif Collection\";\n"
        "\n"
        "background-color: rgb(0, 210, 135);\n"
        "color: rgb(255, 255, 255);\n"
        "\n"
        "border-radius:10px;\n"
        "")
                self.pushButton_13.setObjectName("pushButton_13")
                self.pushButton_13.clicked.connect(lambda: self.selecionarAnoResumo(self.anoSelecionado))
         
                
                
                
                
                # Adiciona o widget de cadastro ao QStackedWidget
                self.contentStack.addWidget(self.tela_ver_meses_widget)

        # Muda o widget atual para o formulário de cadastro
        self.contentStack.setCurrentWidget(self.tela_ver_meses_widget)
        
        self.retranslateUiTelaVerMeses(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)  
        


    def retranslateUiFixedTop(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label_header_home.setText(_translate("MainWindow", "HERMANN.FINANCE  "))
        self.label_entradas.setText(_translate("MainWindow", "Entradas"))
        self.label_saidas.setText(_translate("MainWindow", "Saidas"))
        self.label_total.setText(_translate("MainWindow", "Total"))
        
    def retranslateUiContentInitial(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        
        
        self.tableWidget.setColumnCount(7)  # Ajuste conforme necessário para incluir a coluna de ação
        self.tableWidget.setHorizontalHeaderLabels(['DOC Nº', 'Cliente', 'Forma Pagamento', 'Data', 'Valor', 'Qtd Parcelas', 'Ação'])  # Inclui o cabeçalho da coluna de ação
       
            # Define a alinhação dos textos dos cabeçalhos à esquerda
        self.tableWidget.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tableWidget.horizontalHeader().setStyleSheet("""
        QHeaderView::section {
            background-color: #E0E0E0;

            border: 1px solid #D3D3D3;
            font-size: 12pt;
            color: rgb(51, 51, 51);
            border-bottom: 1px solid #333;
            padding: 0 3px;
      
        }
    """)
        self.loadTableData()  # Chamada para carregar os dados na tabela
        self.tableWidget.itemChanged.connect(self.handleItemChanged)
        
    def retranslateUiMenuSetup(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        
        self.menu_opcoes_item0.setTitle(_translate("MainWindow", "Opções"))
        self.actionProcurar.setText(_translate("MainWindow", "Procurar"))
        self.actionCadastrar.setText(_translate("MainWindow", "Cadastrar"))
        self.actionAtualizar.setText(_translate("MainWindow", "Atualizar"))
        self.actionVer_Meses.setText(_translate("MainWindow", "Ver Meses"))
        self.actionVerCaixa.setText(_translate("MainWindow", "Ver Caixa"))
        self.actionDetalhes_do_Saldo.setText(_translate("MainWindow", "Detalhes do Saldo"))
        self.actionFechamento_do_Dia.setText(_translate("MainWindow", "Fechamento do Dia"))  
        self.actionAlterar_senha.setText(_translate("MainWindow", "Alterar Senha")) 
        
        
        
        
        #TELA CADASTRO:
        
    def retranslateUiFormCadastro(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.legenda_docN.setText(_translate("MainWindow", "DOC N°"))
        self.legenda_cliente.setText(_translate("MainWindow", "CLIENTE"))
        self.legenda_valor.setText(_translate("MainWindow", "VALOR"))
        self.legenda_forma_pagamento.setText(_translate("MainWindow", "FORMA PAGAMENTO"))
        self.legenda_data.setText(_translate("MainWindow", "DATA"))
        self.legenda_parcelas.setText(_translate("MainWindow", "QTD PARCELAS"))
        self.pushButton.setText(_translate("MainWindow", "Confirmar"))
        self.radioButton_entrada.setText(_translate("MainWindow", "ENTRADA"))
        self.radioButton_saida.setText(_translate("MainWindow", "SAIDA"))
        
    
    def retranslateUiTelaVerMeses(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.radioButton_entrada_2.setText(_translate("MainWindow", "2024"))
        self.radioButton_entrada_3.setText(_translate("MainWindow", "2025"))
        self.radioButton_entrada_4.setText(_translate("MainWindow", "2026"))
        self.radioButton_entrada_5.setText(_translate("MainWindow", "2027"))
        self.radioButton_entrada_6.setText(_translate("MainWindow", "2028"))
        self.radioButton_entrada_7.setText(_translate("MainWindow", "2029"))
        self.radioButton_entrada_8.setText(_translate("MainWindow", "2030"))
        self.pushButton.setText(_translate("MainWindow", "JANEIRO"))
        self.pushButton_2.setText(_translate("MainWindow", "FEVEREIRO"))
        self.pushButton_3.setText(_translate("MainWindow", "MARÇO"))
        self.pushButton_4.setText(_translate("MainWindow", "ABRIL"))
        self.pushButton_5.setText(_translate("MainWindow", "MAIO"))
        self.pushButton_6.setText(_translate("MainWindow", "JUNHO"))
        self.pushButton_7.setText(_translate("MainWindow", "JULHO"))
        self.pushButton_8.setText(_translate("MainWindow", "AGOSTO"))
        self.pushButton_9.setText(_translate("MainWindow", "SETEMBRO"))
        self.pushButton_10.setText(_translate("MainWindow", "OUTUBRO"))
        self.pushButton_11.setText(_translate("MainWindow", "NOVEMBRO"))
        self.pushButton_12.setText(_translate("MainWindow", "DEZEMBRO"))
        self.pushButton_13.setText(_translate("MainWindow", "VER RESUMO ANUAL"))
        
        
        self.actionProcurar.setText(_translate("MainWindow", "Procurar"))
        self.actionCadastrar.setText(_translate("MainWindow", "Cadastrar"))
        self.actionAtualizar.setText(_translate("MainWindow", "Atualizar"))
        self.actionVer_Meses.setText(_translate("MainWindow", "Ver Meses"))
        self.actionDetalhes_do_Saldo.setText(_translate("MainWindow", "Detalhes do Saldo"))
        self.actionFechamento_do_Dia.setText(_translate("MainWindow", "Fechamento do Dia"))
        
        self.pushButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_2.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_3.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_4.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_5.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_6.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_7.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_8.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_9.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_10.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_11.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_12.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_13.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        # Para os RadioButtons
        self.radioButton_entrada_2.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.radioButton_entrada_3.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.radioButton_entrada_4.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.radioButton_entrada_5.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.radioButton_entrada_6.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.radioButton_entrada_7.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.radioButton_entrada_8.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def ocultarDocN(self):
    # Se o QLineEdit para DocN não existir, cria um
     if not hasattr(self, 'lineEdit_DocN'):
        self.lineEdit_DocN = QtWidgets.QLineEdit(self.tela_cadastro_widget)
        self.lineEdit_DocN.setGeometry(self.comboBox_DocN.geometry())  # Assume a mesma geometria do comboBox_DocN
        self.lineEdit_DocN.setObjectName("lineEdit_DocN")
        self.lineEdit_DocN.setStyleSheet("""
                QLineEdit {
                font: 8pt "Sans Serif Collection";
                color: rgb(51, 51, 51);
                border-radius: 5px;
                border: 1px solid #5c5c5c; /* Adiciona uma borda padrão */
                background-color: white; /* Fundo branco padrão */
                }
                QLineEdit:hover {
                background-color: #e0fffb; /* Azul suave ao passar o mouse */
                border: 1px solid #155f8e;
                }
                QLineEdit:pressed {
                background-color: #e0fffb; /* Azul um pouco mais forte ao clicar */
                border: 1px solid #155f8e;
                
                }
                """)
     self.comboBox_DocN.hide()
     self.legenda_docN.show()
     self.lineEdit_DocN.show()  # Mostra o QLineEdit

    def mostrarDocN(self):
    # Garante que o QLineEdit será ocultado e o QComboBox mostrado
     if hasattr(self, 'lineEdit_DocN'):
        self.lineEdit_DocN.hide()
     self.comboBox_DocN.show()
     self.legenda_docN.show()

    
    def coletar_dados_do_formulario(self):
        try:
                # Conectar ao banco de dados
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password',
                use_pure=True,
                client_flags=[mysql.connector.ClientFlag.LOCAL_FILES]
                )

                # Coletar dados dos campos de entrada
                # Altere esta linha para coletar o valor do QLineEdit quando radioButton_saida estiver ativo
                doc = self.lineEdit_DocN.text() if self.radioButton_saida.isChecked() else self.comboBox_DocN.currentText()
                cliente = self.textEdit_Cliente.text()
                forma_pagamento = self.textEdit_formaPagamento.text()
                valor_text = self.lineEdit_valor.text().replace(',', '.')
                valor = float(valor_text) if valor_text else 0
                qnt_dividida = self.comboBox_qntDividida.currentText() if self.comboBox_qntDividida.currentText() else 0
                data_text = self.dateEdit.date().toString("yyyy-MM-dd")  # Formatação correta da data
                tipo = "SAIDA" if self.radioButton_saida.isChecked() else "ENTRADA"
                
                ano_id, mes_id = obter_id_ano_mes_atual(conn)  # Certifique-se de que esta função retorna os IDs corretos
                
                mes_inserido_MM = data_text.split('-')[1]
                print("Mes inserido MM:",mes_inserido_MM)
                
                mes_inserido_nome = meses_mapping_ingles.get(mes_inserido_MM, "Mês desconhecido")
                


                cursor = conn.cursor()
                
                # Busca as datas de itens fechados
                cursor.execute("SELECT * FROM item WHERE DATE(DATA) = %s AND FECHADO = 1 ", (data_text,))

                busca_data = cursor.fetchall()
                
                if busca_data:
                        QtWidgets.QMessageBox.warning(self.central_widget, "Aviso", "O dia selecionado já foi fechado !")
                        return
                
                # Verifica se o mês atual já existe na tabela Meses
                cursor.execute("SELECT idMes FROM Meses WHERE mes = %s AND idAno = %s", (mes_inserido_nome, ano_id))
                mes_id_inserido = cursor.fetchone()

                # Se não existir, insira o mês na tabela Meses
                if not mes_id_inserido:
                        cursor.execute("INSERT INTO Meses (mes, idAno) VALUES (%s, %s)", (mes_inserido_nome, ano_id))
                        mes_id_inserido = cursor.lastrowid
                        insert_query = """INSERT INTO Item (DOC, CLIENTE, FORMA_PAGAMENTO, DATA, TIPO, ID_MES, VALOR, QNT_DIVIDIDA) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                        values = (doc, cliente, forma_pagamento, data_text, tipo, mes_id_inserido, valor, qnt_dividida)
                else:
                        insert_query = """INSERT INTO Item (DOC, CLIENTE, FORMA_PAGAMENTO, DATA, TIPO, ID_MES, VALOR, QNT_DIVIDIDA) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                        
                        values = (doc, cliente, forma_pagamento, data_text, tipo, mes_id, valor, qnt_dividida)
                        
                        
                        

                cursor.execute(insert_query, values)
                conn.commit()
                QtWidgets.QMessageBox.information(self.central_widget, "Sucesso", "Registro realizado !")
                
                self.atualizarInterfaceFinanceira()

                print("Dados inseridos com sucesso.")
        except mysql.connector.Error as e:
                print(f"Erro ao conectar ao MySQL: {e}")
        finally:
                if conn:
                 conn.close()
                if cursor:
                 cursor.close()

                 
                 
        # Limpe os campos do formulário após a inserção
        # Limpe os campos do formulário após a inserção
        self.comboBox_DocN.setCurrentIndex(0)  # Seleciona o primeiro item
        self.textEdit_Cliente.clear()
        self.textEdit_formaPagamento.clear()
        self.lineEdit_valor.clear()  # Limpar campo de VALOR
        self.comboBox_qntDividida.setCurrentIndex(0)  # Correção para resetar QLineEdit de QUANTIDADE DIVIDIDA
        self.dateEdit.setDate(QtCore.QDate.currentDate())  # Resetar para a data atual
        self.radioButton_entrada.setChecked(False)
        self.radioButton_saida.setChecked(False)  


    def loadTableData(self):
                try:
                # Tenta definir a localidade para pt_BR.UTF-8
                 locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
                except locale.Error:
                 try:
                        # Tenta uma alternativa comum no Windows
                        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
                 except locale.Error:
                        # Usa a localidade padrão do sistema se as específicas falharem
                        locale.setlocale(locale.LC_ALL, '')

                conn = None
                try:
                        conn = mysql.connector.connect(
                        host='localhost',
                        user='root',
                        password='bd.hermannmarmoraria@32231009',
                        database='sistema_financas',
                        auth_plugin='mysql_native_password',
                        use_pure=True
                        )
                        
                        
                                # Obter o ID do mês atual
                        ano_id, mes_id = obter_id_ano_mes_atual(conn)

                        if mes_id is None:
                        # Se não houver ID_MES, limpa a tabela e retorna sem buscar registros
                          self.tableWidget.setRowCount(0)
                          print("Nenhum registro para o mês atual.")
                          return
                 
                        cursor = conn.cursor()
                        query = "SELECT idItem, DOC, CLIENTE, FORMA_PAGAMENTO, DATA, VALOR, QNT_DIVIDIDA, TIPO, FECHADO FROM item WHERE ID_MES = %s ORDER BY DATA DESC"
                        cursor.execute(query, (mes_id,))  # Passa mes_id como parâmetro para a query
                        rows = cursor.fetchall()

                        self.tableWidget.setRowCount(0)
                        self.nomeClientes.clear()  # Limpa o dicionário antes de preenchê-lo novamente

                        for row_number, row_data in enumerate(rows):
                                cliente = row_data[2]  # Supondo que CLIENTE esteja na terceira posição
                                fechado = row_data[8]
                                tipo = row_data[7]
                                
                                self.nomeClientes[row_data[0]] = cliente  # Usa o idItem como chave e CLIENTE como valor
                                self.tableWidget.insertRow(row_number)
                                for column_number, data in enumerate(row_data[1:-1]):

                                        if column_number == 4:  # Específico para a coluna VALOR
                                                valor = row_data[column_number]
                                                try:
                                                        valor = float(data)  # Tenta converter para float
                                                except ValueError:
                                                        valor = 0.0  # Caso a conversão falhe, assume 0.0
                                                if column_number == 4 and tipo == 'ENTRADA':  
                                                        valor_formatted = locale.format_string('+ R$ %.2f', valor, grouping=True)
                                                        item = QtWidgets.QTableWidgetItem(valor_formatted)
                                                        
                                                        

                                                elif column_number == 4 and tipo == 'SAIDA':
                                                        valor_formatted = locale.format_string('- R$ %.2f', valor, grouping=True)
                                                        item = QtWidgets.QTableWidgetItem(valor_formatted)
                                                        # Verifica se o item está fechado para definir a editabilidade e a cor do fundo
                                                        
                                                if fechado == 1:
                                                    # Item não editável, mas selecionável e habilitado
                                                   item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                                                   # Define o fundo como cinza suave para indicar que está fechado
                                                   item.setBackground(QtGui.QColor(240, 240, 240))
                                                else:
                                                   # Item editável (adiciona Qt.ItemIsEditable se necessário)
                                                  item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                                                  
                                        elif column_number == 3:  # Específico para a coluna DATA
                                                        data_formatada = data.strftime('%d/%m/%Y') if isinstance(data, dtTeste.date) else ""
                                                        item = QtWidgets.QTableWidgetItem(data_formatada)
                                                        item.setFont(QFont('Sans Serif Collection', 10))
                                                     
                                                        
                                                        
                                                        if fechado == 1:
                                                            # Item não editável, mas selecionável e habilitado
                                                            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                                                            # Define o fundo como cinza suave para indicar que está fechado
                                                            item.setBackground(QtGui.QColor(240, 240, 240))
                                                        else:
                                                            # Item editável (adiciona Qt.ItemIsEditable se necessário)
                                                            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

                          

                                        else:
                                          item = QtWidgets.QTableWidgetItem(str(data))
                                          item.setFont(QFont('Sans Serif Collection', 10))
                                          
                                          if fechado == 1:
                                                    # Item não editável, mas selecionável e habilitado
                                                   item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                                                   # Define o fundo como cinza suave para indicar que está fechado
                                                   item.setBackground(QtGui.QColor(240, 240, 240))
                                          else:
                                                   # Item editável (adiciona Qt.ItemIsEditable se necessário)
                                                  item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

                                          
                                        
                                        # Aplica a formatação condicional baseada no campo TIPO
                                        if column_number == 4 and tipo == 'ENTRADA':  # Aplica cor verde para ENTRADA na coluna VALOR
                                         item.setForeground(QtGui.QBrush(QtGui.QColor(0, 128, 0)))
                                         
                                         item.setFont(QFont('Arial Rounded MT Bold', 12))
                                        elif column_number == 4 and tipo == 'SAIDA':  # Aplica cor vermelha para SAÍDA na coluna VALOR
                                         item.setForeground(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
                                         item.setFont(QFont('Arial Rounded MT Bold', 12))
                                         
                                        
                                         
                                        
                                     
                                        item.setData(Qt.UserRole, row_data[0])  # Armazenando o ID do item
                                        self.tableWidget.setItem(row_number, column_number, item)  # Ajuste para -1 porque pulamos o ID
                           
                                        

                        # Adiciona o botão de excluir na última coluna
                        # Verifica se o item está fechado para adicionar o botão apropriado
                                if fechado == 1:
                                # Botão indicando que o item está fechado e não pode ser editado
                                  btn_fechado = QtWidgets.QPushButton()
                                  btn_fechado.setIcon(QtGui.QIcon(":/images_home/fechado.png"))
                                  btn_fechado.clicked.connect(lambda: QMessageBox.information(self.central_widget, "Item Fechado", "Impossível editar este item pois o dia já foi fechado."))
                                  self.tableWidget.setCellWidget(row_number, self.tableWidget.columnCount() - 1, btn_fechado)
                                else:

                                 btn_excluir = QtWidgets.QPushButton("Excluir")
                                 btn_excluir.setIcon(QtGui.QIcon(":/images_home/lixeira_table.png"))
                                 btn_excluir.setStyleSheet("color: rgb(246, 68, 68);font: 55 8pt \"Arial Black\";")
                                 btn_excluir.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                                 btn_excluir.clicked.connect(lambda checked, id=row_data[0]: self.excluirItem(id))
                                 self.tableWidget.setCellWidget(row_number, 6, btn_excluir)
                                


                except mysql.connector.Error as e:
                        print(f"Error connecting to MySQL: {e}")
                finally:
                        if conn is not None and conn.is_connected():
                         conn.close()

    def handleItemChanged(self, item):
        row = item.row()
        column = item.column()
        newValue = item.text()
        idItem = item.data(Qt.UserRole)  # Recupera o ID do item usando UserRole
        columnName = self.getColumnNameByIndex(column)
        tipo = None  # Variável para armazenar o tipo baseado no valor
        
        # Atualiza o nome do cliente no dicionário nomeClientes se a coluna editada for 'CLIENTE'
        if columnName == 'CLIENTE':
                self.nomeClientes[idItem] = newValue

        # Converte newValue para o formato correto antes de enviar ao banco

        if columnName == 'VALOR':
                
                # Verificação para definir o tipo baseado no prefixo do valor
                if newValue.startswith(('- R$', ' -R$', ' - R$', '- ', ' -', ' - ', '-')):
                        tipo = 'SAIDA'
                elif newValue.startswith(('+ R$', ' +R$', ' + R$', '+ ', ' +', ' + ', '+',' ','',' R$','R$ ')):
                        tipo = 'ENTRADA'
                        
                # Remove caracteres de moeda e converte para o formato decimal        
                newValue = newValue.replace('- R$', '').replace('.', '').replace(',', '.').replace('+ R$', '').replace('+ ', '').replace(' + ', '').replace(' +', '').replace('+', '').replace('- ', '').replace(' -', '').replace(' - ', '').replace('-', '').replace('R$', '').replace(' R$', '').strip()
                valor_item_float = float(newValue)
                valor_item = self.tableWidget.item(row, 4) #Coluna 4
                
                # Atualização da cor na tabela e reformatação depois de editar
                if tipo == 'ENTRADA':
                        
                        cor = QtGui.QColor(0, 128, 0)  # Verde
                        valor_formatted = locale.format_string('+ R$ %.2f', valor_item_float, grouping=True)
                
                        
                elif tipo == 'SAIDA':
                        
                        
                        cor = QtGui.QColor(255, 0, 0)  # Vermelho
                        valor_formatted = locale.format_string('- R$ %.2f', valor_item_float, grouping=True)
                        
                else:
                        cor = QtGui.QColor(51, 51, 51)  # Cor padrão
                        valor_formatted = valor_item # Não faz nada quando não identifica
                        # Aplicar a cor ao item da coluna "VALOR"
        
                if valor_item:
                  valor_item.setForeground(QtGui.QBrush(cor))
                  valor_item.setText(valor_formatted)

        if columnName == 'DATA':
                # Converte a data do formato brasileiro para o formato aceito pelo MySQL (AAAA-MM-DD)
                try:
                 newValue = dt.strptime(newValue, '%d/%m/%Y').strftime('%Y-%m-%d')
     
                except ValueError:
                 print("Data inválida inserida.")
                 return  # Para a execução se a data não puder ser convertida

        # Aqui você escreve o código para atualizar o banco de dados
        conn = None
        try:
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password'
                )
                cursor = conn.cursor()
                
                query = f"UPDATE item SET {columnName} = %s WHERE idItem = %s"
                cursor.execute(query, (newValue, idItem))
                
                # Se um tipo foi definido, atualiza o "TIPO" no banco de dados
                if tipo:
                   tipo_query = "UPDATE item SET TIPO = %s WHERE idItem = %s"
                   cursor.execute(tipo_query, (tipo, idItem))
                   
                conn.commit()
                self.atualizarInterfaceFinanceira()
                
                
                
        except mysql.connector.Error as e:
                print(f"Error: {e}")
        finally:
                if conn is not None and conn.is_connected():
                 
                 conn.close()
                

    def getColumnNameByIndex(self, index):
        # Retorna o nome da coluna no banco de dados baseado no índice da coluna na tabela
        columns = ['DOC', 'CLIENTE', 'FORMA_PAGAMENTO', 'DATA', 'VALOR', 'QNT_DIVIDIDA','AÇÃO']
        return columns[index]  # Ajuste conforme a estrutura real da sua tabela

    def fechamentoDoDia(self):
        try:
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password'
                )
                cursor = conn.cursor()

                # Busca as datas de itens não fechados
                cursor.execute("SELECT DISTINCT DATE_FORMAT(DATA, '%d/%m/%Y') FROM item WHERE FECHADO = 0 ORDER BY DATE_FORMAT(DATA, '%d/%m/%Y') DESC")
                datas = cursor.fetchall()

                if not datas:
                 QMessageBox.information(self.central_widget, "Fechamento do Dia", "Não há dias para fechar.")
                 return

         
                
                
                # Cria o QMessageBox com QComboBox
                msgBox = QMessageBox()
                msgBox.setFont(QtGui.QFont("HP Simplified", 10))
                msgBox.setWindowTitle("Fechamento do Dia")
                
                
                # Criar QLabel para o título
                titulo = QtWidgets.QLabel("Fechar dia:")
                titulo.setFont(QtGui.QFont("HP Simplified", 10))
                # Define o alinhamento vertical do título para ficar no topo
                titulo.setAlignment(QtCore.Qt.AlignTop)
                
                
                
                comboBox = QtWidgets.QComboBox()
                for data in datas:
                   comboBox.addItem(data[0])
                   
                comboBox.setCurrentIndex(0)
                msgBox.setIcon(QMessageBox.Question)
                
                # Adiciona o QComboBox acima dos botões de confirmação e cancelamento
                layout = msgBox.layout()
                layout.addWidget(titulo, 0, 1, 1, layout.columnCount())
                layout.addWidget(comboBox, 1, 1, 1, layout.columnCount())
                msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                
                ret = msgBox.exec_()

                if ret == QMessageBox.Ok:
                # Solicita login
                 login, okPressedLogin = QInputDialog.getText(self.central_widget, "Login", "Usuário:", QLineEdit.Normal, "")
                 
                 if okPressedLogin and login:
                           # Solicita senha
                           senha, okPressedSenha = QInputDialog.getText(self.central_widget, "Senha", "Senha:", QLineEdit.Password, "")
                      
                           if okPressedSenha and senha:
                               # Verifica login e senha
                              cursor.execute("SELECT * FROM Users WHERE user = %s AND senha = %s", (login, senha))
                              user = cursor.fetchone()
                              if user:
                                  # Fechamento do dia após autenticação bem-sucedida
                                  data_selecionada = dt.strptime(comboBox.currentText(), "%d/%m/%Y").strftime("%Y-%m-%d")
                                  cursor.execute("UPDATE item SET FECHADO = 1 WHERE DATE(DATA) = %s", (data_selecionada,))
                                  conn.commit()
                                  self.setupInitialContent()
                                 
                                  QMessageBox.information(self.central_widget, "Fechamento do Dia", "Dia fechado com sucesso.")
                                  return
                              else:
                                 QMessageBox.warning(self.central_widget, "Erro", "Usuário ou Senha incorretos!")
                                 return
                           else:
                             QMessageBox.warning(self.central_widget, "Cancelado", "Fechamento do dia cancelado.")
                             return
                elif ret == QMessageBox.Cancel:
                        QMessageBox.warning(self.central_widget, "Cancelado", "Fechamento do dia cancelado.")
                        return
                   
                       






                
        except mysql.connector.Error as e:
                QMessageBox.critical(self.central_widget, "Erro", f"Erro ao acessar o banco de dados: {e}")
        finally:
                if conn.is_connected():
                 cursor.close()
                 conn.close()

 



    def atualizarInterfaceFinanceira(self):
        entradas, saidas, total, mes_atual_portugues = buscarDadosFinanceiros()
        
        
        valor_saidas = float(saidas)
        valor_entradas = float(entradas)
        valor_total = float(total)
        
        try:
        # Tenta definir a localidade para pt_BR.UTF-8
                     locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
                  try:
                # Tenta uma alternativa comum no Windows
                          locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
                  except locale.Error:
                # Usa a localidade padrão do sistema se as específicas falharem
                          locale.setlocale(locale.LC_ALL, '')
        
        
        valor_formatted_saida = locale.format_string('- R$ %.2f', valor_saidas, grouping=True)
        valor_formatted_entrada = locale.format_string('+ R$ %.2f', valor_entradas, grouping=True)

        
        self.lineEdit_entradas_valor.setText(valor_formatted_entrada)
        self.lineEdit_saidas_valor.setText(valor_formatted_saida)
        
       
        self.lineEdit_mes_header.setText(mes_atual_portugues.upper())
        # Verifica se o total é maior que zero para ajustar a cor do label_total
        if total > 0:
                self.label_total.setStyleSheet("""
                font: 16pt "Sans Serif Collection";
                color: rgb(255, 255, 255); /* Texto preto para melhor contraste */
                border-radius: 10px;
                background-color: #00D287; /* Verde */
                padding: 0 15px;
                """)
                valor_formatted_total = locale.format_string('+ R$ %.2f', valor_total, grouping=True)
                self.lineEdit_total_valor.setText(valor_formatted_total)
        else:
                self.label_total.setStyleSheet("""
                font: 16pt "Sans Serif Collection";
                color: white;
                border-radius: 10px;
                background-color: rgb(246, 68, 68); /* Mantém o vermelho para valores negativos ou zero */
                padding: 0 15px;
                """)
                # Para valores negativos, formate manualmente para obter o formato "-R$ valor"
                if valor_total < 0:
                  valor_formatted_totalN = '{:.2f}'.format(abs(valor_total))
                  valor_totalCerto = float(valor_formatted_totalN)
                  
                  valor_formatted_total = locale.format_string('- R$ %.2f', valor_totalCerto, grouping=True)
     
                else:
                  valor_formatted_total = '- R$ {:.2f}'.format(valor_total)
    
        self.lineEdit_total_valor.setText(valor_formatted_total)


    def excluirItem(self, itemId):
    # Primeiro, obtemos o nome do cliente a ser excluído para usar na caixa de mensagem
        nome_cliente = self.nomeClientes.get(itemId, "Este cliente")  # Fallback para "Este cliente" se o ID não estiver no dicionário

        # Criar QMessageBox para confirmar a exclusão
        reply = QMessageBox.question(
                self.central_widget,  # Você pode precisar ajustar este argumento dependendo de onde está sua referência de widget central
                "Confirmar Exclusão",
                f"Deseja realmente excluir {nome_cliente}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
        )

        if reply == QMessageBox.Yes:
                conn = None
                try:
                 conn = mysql.connector.connect(
                        host='localhost',
                        user='root',
                        password='bd.hermannmarmoraria@32231009',
                        database='sistema_financas',
                        auth_plugin='mysql_native_password',
                        use_pure=True
                 )
                 cursor = conn.cursor()
                 delete_query = "DELETE FROM item WHERE idItem = %s"
                 cursor.execute(delete_query, (itemId,))
                 conn.commit()

                # Remover o cliente excluído do dicionário nomeClientes
                 if itemId in self.nomeClientes:
                        del self.nomeClientes[itemId]



                # Recarrega os dados na tabela para refletir a exclusão
               
                 self.atualizarInterfaceFinanceira()
                 self.filterTableData()
                 
                # Exibe mensagem de sucesso
                 QMessageBox.information(
                        self.central_widget,  # Ajuste este argumento conforme necessário
                        "Sucesso",
                        "Item excluído com sucesso!"
                 )
                 
                except mysql.connector.Error as e:
                 QMessageBox.warning(
                        self.central_widget,  # Ajuste este argumento conforme necessário
                        "Erro",
                        f"Erro ao excluir item do MySQL: {e}"
                )
                finally:
                 if conn is not None and conn.is_connected():
                        conn.close()
        else:
                # Se o usuário decidir não excluir, simplesmente não faz nada
                pass




    def toggleSearchInput(self):
        isVisible = self.searchInput.isHidden()
        self.searchInput.setHidden(not isVisible)
        if isVisible:
                self.searchInput.setFocus()  # Dá foco à input se ela estiver sendo mostrada

    def filterTableData(self):
         filterText = self.searchInput.text().lower()
         if filterText:
                # Filtra os dados baseado no texto de entrada, comparando com os nomes dos clientes
                filteredRows = {idCliente: nome for idCliente, nome in self.nomeClientes.items() if filterText in nome.lower()}
         else:
                # Se não houver texto de filtro, usa todos os dados
                filteredRows = self.nomeClientes

         self.updateTable(filteredRows)


    def updateTable(self, filteredRows):
        # Itera sobre todas as linhas da tabela
        for row in range(self.tableWidget.rowCount()):
                item = self.tableWidget.item(row, 0)  # Supondo que o ID esteja na primeira coluna
                if item:
                # Decide se a linha deve ser ocultada ou mostrada
                 shouldBeVisible = item.data(Qt.UserRole) in filteredRows
                 self.tableWidget.setRowHidden(row, not shouldBeVisible)





 

        # Execute a consulta e atualize a tabela como antes

    def alterarSenha(self):
        user, ok = QtWidgets.QInputDialog.getText(None, "Alterar Senha", "Usuário:", QtWidgets.QLineEdit.Normal, "")
        if ok and user:
            senha_atual, ok = QtWidgets.QInputDialog.getText(None, "Alterar Senha", "Senha Atual:", QtWidgets.QLineEdit.Password, "")
            if ok and senha_atual:
                try:
                    conn = mysql.connector.connect(host='localhost', user='root', password='bd.hermannmarmoraria@32231009', database='sistema_financas')
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM Users WHERE user = %s AND senha = %s", (user, senha_atual))
                    user_id = cursor.fetchone()
                    if user_id:
                        nova_senha, ok = QtWidgets.QInputDialog.getText(None, "Alterar Senha", f"Nova Senha para {user}:", QtWidgets.QLineEdit.Password, "")
                        if ok and nova_senha:
                            cursor.execute("UPDATE Users SET senha = %s WHERE id = %s", (nova_senha, user_id[0]))
                            conn.commit()
                            QtWidgets.QMessageBox.information(None, "Sucesso", "Senha alterada com sucesso.")
                        else:
                            QtWidgets.QMessageBox.warning(None, "Cancelado", "Alteração de senha cancelada.")
                    else:
                        QtWidgets.QMessageBox.warning(None, "Erro", "Usuário ou Senha incorretos!")
                except mysql.connector.Error as e:
                    QtWidgets.QMessageBox.critical(None, "Erro", f"Erro ao acessar o banco de dados: {e}")
                finally:
                    if conn.is_connected():
                        cursor.close()
                        conn.close()
            else:
                QtWidgets.QMessageBox.warning(None, "Cancelado", "Alteração de senha cancelada.")

    def selecionarAno(self, ano):
        self.anoSelecionado = ano
        print(f"Ano selecionado: {self.anoSelecionado}")  # Log para verificação
        
    def selecionarAnoResumo(self, ano):
        self.anoSelecionado = ano
        print(f"Ano selecionado: {self.anoSelecionado}")  # Log para verificação
        self.verificarRegistroAnoExistente()

    def selecionarMes(self, mes):
        if not self.anoSelecionado:
            QtWidgets.QMessageBox.warning(None, "Aviso", "Por favor, selecione um ano antes de selecionar um mês.")
            return
        self.mesSelecionado = mes
        print(f"Mês selecionado: {self.mesSelecionado}")  # Log para verificação
        self.verificarRegistroExistente()

    def verificarRegistroExistente(self):
        try:
            conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='bd.hermannmarmoraria@32231009',
            database='sistema_financas'
            )
            cursor = conn.cursor()
                
            ano_id_selecionado, mes_id_selecionado = obter_id_ano_mes_selecionado(conn, self.anoSelecionado, self.mesSelecionado)

            if ano_id_selecionado is None and mes_id_selecionado is None:
                QtWidgets.QMessageBox.warning(None, "Aviso", "Não há registros para o ano e mês selecionados !")
            elif ano_id_selecionado is None:
                QtWidgets.QMessageBox.warning(None, "Aviso", "Não há registros para o ano selecionado !")
            elif mes_id_selecionado is None:
                QtWidgets.QMessageBox.information(None, "Aviso", "Não há registros para o mês selecionado !")
            elif mes_id_selecionado and ano_id_selecionado:
                    rows, soma_entradas_mes, soma_saidas_mes, soma_total_mes = obter_dados_para_relatorio(conn, ano_id_selecionado, mes_id_selecionado)
                    # Obtém os nomes do ano e mês selecionados para usar no título do PDF
                
                    mesSelecionado_traduzido = meses_mapa.get(self.mesSelecionado, "Mês desconhecido")
                    anoSelecionado = self.anoSelecionado

                    gerar_relatorio_pdf(self.central_widget,rows, anoSelecionado, mesSelecionado_traduzido, soma_entradas_mes, soma_saidas_mes, soma_total_mes)

            else:
                print(f"ID do Ano: {ano_id_selecionado}, ID do Mês: {mes_id_selecionado}")  # Log para verificação
        except mysql.connector.Error as e:
            QtWidgets.QMessageBox.critical(None, "Erro", f"Erro ao acessar o banco de dados: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
                
    def verificarRegistroAnoExistente(self):
        try:
            conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='bd.hermannmarmoraria@32231009',
            database='sistema_financas'
            )
            cursor = conn.cursor()
                
            ano_id_selecionado,mes_id_selecionado = obter_id_ano_mes_selecionado(conn, self.anoSelecionado, self.mesSelecionado)

            if ano_id_selecionado is None and mes_id_selecionado is None:
                QtWidgets.QMessageBox.warning(None, "Aviso", "Não há registros. Verifique se selecionou um ano!")
 
            elif ano_id_selecionado:
                    rows, soma_entradas_ano, soma_saidas_ano, soma_total_ano = obter_dados_para_relatorio_anual(conn, ano_id_selecionado)
                    # Obtém os nomes do ano e mês selecionados para usar no título do PDF
                
                    
                    anoSelecionado = self.anoSelecionado

                    gerar_relatorio_anual_pdf(self.central_widget,rows, anoSelecionado, soma_entradas_ano, soma_saidas_ano, soma_total_ano)

            else:
                print(f"ID do Ano: {ano_id_selecionado}")  # Log para verificação
        except mysql.connector.Error as e:
            QtWidgets.QMessageBox.critical(None, "Erro", f"Erro ao acessar o banco de dados: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
                
    def setupDetalhesSaldoContent(self):
        # Aqui você configura o conteúdo inicial, como a tabela que você mencionou
        # Este widget é adicionado ao self.contentStack   
        # AQUI SERIA O NOSSO CONTENT (QUE SEMPRE PODE SER REENDERIZADO) ESTE É O MAIN
        
        # Criação do widget que será o conteúdo inicial


        self.pushButton_voltar.setVisible(True)  # Oculta o botão ao retornar ao conteúdo inicial
        self.detalhesSaldoContentWidget = QtWidgets.QWidget()
        self.detalhesSaldoContentWidget.setObjectName("detalhesSaldoContentWidget")
        
        
        
        # Cria uma QScrollArea
        self.scrollArea = QtWidgets.QScrollArea(self.detalhesSaldoContentWidget)
        self.scrollArea.setGeometry(QtCore.QRect(440, 390, 600, 450))
        self.scrollArea.setWidgetResizable(True)  # Permite que o widget interno se expanda
        # Após criar e configurar a QScrollArea
        self.scrollArea.setStyleSheet("""
        QScrollArea {
                border: transparent  /* Define a espessura e a cor da borda */
                
        }
        QScrollBar:vertical {
                width: 12px;  /* Largura da barra de rolagem vertical */
        }
        QScrollBar:horizontal {
                height: 12px;  /* Altura da barra de rolagem horizontal */
        }
        """)

        
        self.contentStack.setCurrentWidget(self.detalhesSaldoContentWidget)
        self.tableWidgetSaldo = QtWidgets.QTableWidget(self.detalhesSaldoContentWidget)
        self.tableWidgetSaldo.setGeometry(QtCore.QRect(440, 390, 600, 450))
        self.tableWidgetSaldo.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.tableWidgetSaldo.setToolTip("")
        self.tableWidgetSaldo.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tableWidgetSaldo.setAutoFillBackground(False)
        self.tableWidgetSaldo.verticalHeader().setVisible(False)

       
        
        # Adiciona a QTableWidget como widget da QScrollArea
        self.scrollArea.setWidget(self.tableWidgetSaldo)
        

        self.tableWidgetSaldo.setStyleSheet("font: 12pt \"Sans Serif Collection\";\n"
"color: rgb(51, 51, 51);")
        self.tableWidgetSaldo.setLineWidth(0)
        self.tableWidgetSaldo.setMidLineWidth(0)
        self.tableWidgetSaldo.setAutoScroll(True)
        self.tableWidgetSaldo.setAutoScrollMargin(16)
        self.tableWidgetSaldo.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
         

        self.tableWidgetSaldo.setObjectName("tableWidgetSaldo")
        

        # Cria uma QScrollArea
        self.scrollAreaDetalhesSaldo = QtWidgets.QScrollArea(self.detalhesSaldoContentWidget)
        self.scrollAreaDetalhesSaldo.setGeometry(QtCore.QRect(1140, 390, 350, 450))
        self.scrollAreaDetalhesSaldo.setWidgetResizable(True)  # Permite que o widget interno se expanda
        # Após criar e configurar a QScrollArea
        self.scrollAreaDetalhesSaldo.setStyleSheet("""
        QScrollArea {
                border: transparent  /* Define a espessura e a cor da borda */
                
        }
        QScrollBar:vertical {
                width: 12px;  /* Largura da barra de rolagem vertical */
        }
        QScrollBar:horizontal {
                height: 12px;  /* Altura da barra de rolagem horizontal */
        }
        """)

  
        self.tableWidgetDetalhesSaldo = QtWidgets.QTableWidget(self.detalhesSaldoContentWidget)
        self.tableWidgetDetalhesSaldo.setGeometry(QtCore.QRect(1140, 390, 350, 450))
        self.tableWidgetDetalhesSaldo.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.tableWidgetDetalhesSaldo.setToolTip("")
        self.tableWidgetDetalhesSaldo.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tableWidgetDetalhesSaldo.setAutoFillBackground(False)
        self.tableWidgetDetalhesSaldo.verticalHeader().setVisible(False)

       
        
        # Adiciona a QTableWidgetDetalhesSaldo como widget da QScrollArea
        self.scrollAreaDetalhesSaldo.setWidget(self.tableWidgetDetalhesSaldo)
        

        self.tableWidgetDetalhesSaldo.setStyleSheet("font: 12pt \"Sans Serif Collection\";\n"
"color: rgb(51, 51, 51);")
        self.tableWidgetDetalhesSaldo.setLineWidth(0)
        self.tableWidgetDetalhesSaldo.setMidLineWidth(0)
        self.tableWidgetDetalhesSaldo.setAutoScroll(True)
        self.tableWidgetDetalhesSaldo.setAutoScrollMargin(16)
        self.tableWidgetDetalhesSaldo.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
         

        self.tableWidgetDetalhesSaldo.setObjectName("tableWidgetDetalhesSaldo")
        
        

        # Adiciona o widget ao QStackedWidget
        self.contentStack.addWidget(self.detalhesSaldoContentWidget)
        self.contentStack.setCurrentWidget(self.detalhesSaldoContentWidget)
        
        self.retranslateUiContentDetalhesSaldo(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        # Ajuste automático ou fixo para larguras de coluna
     
        self.tableWidgetSaldo.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetSaldo.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetSaldo.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetSaldo.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.tableWidgetSaldo.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)

        self.tableWidgetSaldo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidgetDetalhesSaldo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        

        
        
        self.tableWidgetDetalhesSaldo.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetDetalhesSaldo.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
       


    def retranslateUiContentDetalhesSaldo(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        
        
        self.tableWidgetSaldo.setColumnCount(5)  # Ajuste conforme necessário para incluir a coluna de ação
        self.tableWidgetSaldo.setHorizontalHeaderLabels(['Entradas', 'Saidas', 'Data', 'Saldo do Dia','Ação'])  # Inclui o cabeçalho da coluna de ação
       
            # Define a alinhação dos textos dos cabeçalhos à esquerda
        self.tableWidgetSaldo.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tableWidgetSaldo.horizontalHeader().setStyleSheet("""
        QHeaderView::section {
            background-color: #E0E0E0;

            border: 1px solid #D3D3D3;
            font-size: 12pt;
            color: rgb(51, 51, 51);
            border-bottom: 1px solid #333;
            padding: 0 3px;
      
        }
    """)
        self.loadTableDataDetalhesSaldo()
      
        
        
        
        
        
        self.tableWidgetDetalhesSaldo.setColumnCount(2)  # Ajuste conforme necessário para incluir a coluna de ação
        self.tableWidgetDetalhesSaldo.setHorizontalHeaderLabels(['Forma de Pagamento', 'Valor Total'])  # Inclui o cabeçalho da coluna de ação
       
            # Define a alinhação dos textos dos cabeçalhos à esquerda
        self.tableWidgetDetalhesSaldo.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tableWidgetDetalhesSaldo.horizontalHeader().setStyleSheet("""
        QHeaderView::section {
            background-color: #E0E0E0;

            border: 1px solid #D3D3D3;
            font-size: 12pt;
            color: rgb(51, 51, 51);
            border-bottom: 1px solid #333;
            padding: 0 3px;
      
        }
    """)
        
   


    def detalhesSaldoAbrir(self):
        try:
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password'
                )
                cursor = conn.cursor()


                # Solicita login
                login, okPressedLogin = QInputDialog.getText(self.central_widget, "Área restrita", "Usuário:", QLineEdit.Normal, "")
                 
                if okPressedLogin and login:
                           # Solicita senha
                           senha, okPressedSenha = QInputDialog.getText(self.central_widget, "Área restrita", "Senha:", QLineEdit.Password, "")
                      
                           if okPressedSenha and senha:
                               # Verifica login e senha
                              cursor.execute("SELECT * FROM Users WHERE user = %s AND senha = %s", (login, senha))
                              user = cursor.fetchone()
                              if user:
                                  # Fechamento do dia após autenticação bem-sucedida

                                  self.setupDetalhesSaldoContent()
                                 

                              else:
                                 QMessageBox.warning(self.central_widget, "Erro", "Usuário ou Senha incorretos!")
                                 return
                           else:
                             QMessageBox.warning(self.central_widget, "Cancelado", "Abrir Detalhes de saldo cancelado.")
                             return
                else:
                        QMessageBox.warning(self.central_widget, "Cancelado", "Abrir Detalhes de saldo cancelado.")
                        return
                   
                       
        except mysql.connector.Error as e:
                QMessageBox.critical(self.central_widget, "Erro", f"Erro ao acessar o banco de dados: {e}")
        finally:
                if conn.is_connected():
                 cursor.close()
                 conn.close()

    def loadTableDataDetalhesSaldo(self):
                try:
        # Tenta definir a localidade para pt_BR.UTF-8
                     locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
                except locale.Error:
                  try:
                # Tenta uma alternativa comum no Windows
                          locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
                  except locale.Error:
                # Usa a localidade padrão do sistema se as específicas falharem
                          locale.setlocale(locale.LC_ALL, '')
                
                conn = None
                try:
                        conn = mysql.connector.connect(
                        host='localhost',
                        user='root',
                        password='bd.hermannmarmoraria@32231009',
                        database='sistema_financas',
                        auth_plugin='mysql_native_password',
                        use_pure=True
                        )
                        
                        atualizar_saldo_diario(conn)
                        
                        
                       
                        
                        
                        
                        # Obter o ID do mês atual
                        ano_id, mes_id = obter_id_ano_mes_atual(conn)

                        if mes_id is None:
                        # Se não houver ID_MES, limpa a tabela e retorna sem buscar registros
                          self.tableWidgetSaldo.setRowCount(0)
                          print("Nenhum registro para o mês atual.")
                          return
                 
                        cursor = conn.cursor()
                        query = "SELECT idSaldo, entradas, saidas, data, saldo_atual, SELECIONADO FROM saldoDiario WHERE ID_MES = %s ORDER BY data DESC"
                        cursor.execute(query, (mes_id,))  # Passa mes_id como parâmetro para a query
                        rows = cursor.fetchall()

                        self.tableWidgetSaldo.setRowCount(0)
                

                        for row_number, row_data in enumerate(rows):
                     
                                selecionado = row_data[5]
                            
                                data_text = row_data[3]
                                saldo_atual = row_data[4]
                                
                            
                                self.tableWidgetSaldo.insertRow(row_number)
                                for column_number, data in enumerate(row_data[1:-1]):

                                        if column_number == 3 or column_number == 0 or column_number == 1 :  #Todas outras colunas (exceto data e ação) da tabela renderizada
                                                valor = row_data[column_number]
                                                try:
                                                        valor = float(data)  # Tenta converter para float
                                                except ValueError:
                                                        valor = 0.0  # Caso a conversão falhe, assume 0.0
                                                if column_number == 0 or column_number == 1:  
                                                        valor_formatted = locale.format_string('R$ %.2f', valor, grouping=True)
                                                        item = QtWidgets.QTableWidgetItem(valor_formatted)
                                                        
                                                        


                                                
                                                elif column_number == 3:#Coluna saldo atual da tabela renderizada
       
                                                        if valor > 0:
                                                                valor_formatted = locale.format_string('+ R$ %.2f', valor, grouping=True)
                                                                item = QtWidgets.QTableWidgetItem(valor_formatted)
                                                                item.setForeground(QtGui.QBrush(QtGui.QColor(0, 128, 0)))
                                                        else:
                                                                valor_formatted_totalN = '{:.2f}'.format(abs(valor))
                                                                valor_totalCerto = float(valor_formatted_totalN)
                                                                valor_formatted = locale.format_string('- R$ %.2f', valor_totalCerto, grouping=True)
                                                                item = QtWidgets.QTableWidgetItem(valor_formatted)
                                                                item.setForeground(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
                                                                
                                                        item.setFont(QFont('Arial Rounded MT Bold', 12))
                            
                                                        
                                                if selecionado == 1:
                                                    # Item não editável, mas selecionável e habilitado
                                                   item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                                                   # Define o fundo como cinza suave para indicar que está fechado
                                                   item.setBackground(QtGui.QColor(240, 240, 240))
                                                else:
                                                   # Item editável (adiciona Qt.ItemIsEditable se necessário)
                                                  item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                                                  
                                        elif column_number == 2:  # Específico para a coluna DATA
                                                        data_formatada = data.strftime('%d/%m/%Y') if isinstance(data, dtTeste.date) else ""
                                                        item = QtWidgets.QTableWidgetItem(data_formatada)
                                                        item.setFont(QFont('Sans Serif Collection', 10))
                                                     
                                                        
                                                        
                                                        if selecionado == 1:
                                                            # Item não editável, mas selecionável e habilitado
                                                            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                                                            # Define o fundo como cinza suave para indicar que está fechado
                                                            item.setBackground(QtGui.QColor(240, 240, 240))
                                                        else:
                                                            # Item editável (adiciona Qt.ItemIsEditable se necessário)
                                                            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

                          

                                        else:
                                          item = QtWidgets.QTableWidgetItem(str(data))
                                          item.setFont(QFont('Sans Serif Collection', 10))
                                          
                                          if selecionado == 1:
                                                    # Item não editável, mas selecionável e habilitado
                                                   item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                                                   # Define o fundo como cinza suave para indicar que está fechado
                                                   item.setBackground(QtGui.QColor(240, 240, 240))
                                                   

                                          else:
                                                   # Item editável (adiciona Qt.ItemIsEditable se necessário)
                                                  item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)  
                                                  
                                     
                                         
                                        
                                     
                                        item.setData(Qt.UserRole, row_data[0])  # Armazenando o ID do item
                                        self.tableWidgetSaldo.setItem(row_number, column_number, item)  # Ajuste para -1 porque pulamos o ID
                           
                                        

                        # Adiciona o botão de excluir na última coluna
                        # Verifica se o item está fechado para adicionar o botão apropriado
                                if selecionado == 1:
                                # Botão indicando que o item está fechado e não pode ser editado
                                  btn_pesquisado = QtWidgets.QPushButton()
                                  btn_pesquisado.setIcon(QtGui.QIcon(":/images_home/procurar.png"))
                                  btn_pesquisado.clicked.connect(lambda checked, idSaldo=row_data[0] , data_text=data_text: self.marcar_como_selecionado(idSaldo, data_text))


              
                                  self.tableWidgetSaldo.setCellWidget(row_number, self.tableWidgetSaldo.columnCount() - 1, btn_pesquisado)
                                else:

                                  btn_pesquisado = QtWidgets.QPushButton()
                                  btn_pesquisado.setIcon(QtGui.QIcon(":/images_home/procurar.png"))
                                  btn_pesquisado.clicked.connect(lambda checked,idSaldo=row_data[0], data_text=data_text: self.marcar_como_selecionado(idSaldo, data_text))

                                  


                                  self.tableWidgetSaldo.setCellWidget(row_number, self.tableWidgetSaldo.columnCount() - 1, btn_pesquisado)
                                


                except mysql.connector.Error as e:
                        print(f"Error connecting to MySQL: {e}")
                finally:
                        if conn is not None and conn.is_connected():
                         conn.close()


   
    def marcar_como_selecionado(self, idSaldo, data_text):
        conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password',
                use_pure=True
        )
        cursor = conn.cursor()
        # Define todos como não selecionados
        cursor.execute("UPDATE SaldoDiario SET SELECIONADO = 0")
        # Marca o item especificado como selecionado
        cursor.execute("UPDATE SaldoDiario SET SELECIONADO = 1 WHERE idSaldo = %s", (idSaldo,))

        print("ESSE É O ID SELECIONADO:", idSaldo)
       
        conn.commit()
        self.setupDetalhesSaldoContent()

        # Busca detalhes da tabela Item para a data especificada e preenche tableWidgetDetalhesSaldo
        self.preencherDetalhesSaldo(data_text)
        QMessageBox.information(self.central_widget, "Item Buscado", "Verifique os detalhes na tabela ao lado!")

        cursor.close()
        if conn.is_connected():
                conn.close()
                

    def preencherDetalhesSaldo(self, data_text):
        conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password',
                use_pure=True
        )
        cursor = conn.cursor()

        # Limpa a tabela
        self.tableWidgetDetalhesSaldo.setRowCount(0)

        # Executa o select para buscar formas de pagamento distintas, soma dos valores para a data, e o tipo (ENTRADA ou SAÍDA)
        query = """
        SELECT FORMA_PAGAMENTO, SUM(VALOR), TIPO
        FROM Item
        WHERE DATA = %s
        GROUP BY FORMA_PAGAMENTO, TIPO
        """
        cursor.execute(query, (data_text,))
        rows = cursor.fetchall()

        for row in rows:
                row_number = self.tableWidgetDetalhesSaldo.rowCount()
                self.tableWidgetDetalhesSaldo.insertRow(row_number)
                forma_pagamento_item = QtWidgets.QTableWidgetItem(str(row[0]))
                forma_pagamento_item.setFont(QFont('Arial Rounded MT Bold', 12))
                self.tableWidgetDetalhesSaldo.setItem(row_number, 0, forma_pagamento_item)

                valor = float(row[1])
                valor_formatted = locale.format_string('R$ %.2f', valor, grouping=True)
                valor_item = QtWidgets.QTableWidgetItem(valor_formatted)
                valor_item.setFont(QFont('Arial Rounded MT Bold', 12))

                # Verificação baseada na coluna TIPO
                if row[2] == "ENTRADA":
                        valor_item.setForeground(QtGui.QBrush(QtGui.QColor(0, 128, 0))) # Verde
                elif row[2] == "SAIDA":
                        valor_item.setForeground(QtGui.QBrush(QtGui.QColor(255, 0, 0))) # Vermelho
                
                self.tableWidgetDetalhesSaldo.setItem(row_number, 1, valor_item)

        cursor.close()
        
        if conn.is_connected():
                conn.close()



    def setupCaixaContent(self):
        # Aqui você configura o conteúdo inicial, como a tabela que você mencionou
        # Este widget é adicionado ao self.contentStack   
        # AQUI SERIA O NOSSO CONTENT (QUE SEMPRE PODE SER REENDERIZADO) ESTE É O MAIN
        
        # Criação do widget que será o conteúdo inicial


        self.pushButton_voltar.setVisible(True)  # Oculta o botão ao retornar ao conteúdo inicial
        self.caixaContentWidget = QtWidgets.QWidget()
        self.caixaContentWidget.setObjectName("caixaContentWidget")
        
        
        
        # Cria uma QScrollArea
        self.scrollArea = QtWidgets.QScrollArea(self.caixaContentWidget)
        self.scrollArea.setGeometry(QtCore.QRect(750, 390, 400, 300))
        self.scrollArea.setWidgetResizable(True)  # Permite que o widget interno se expanda
        # Após criar e configurar a QScrollArea
        self.scrollArea.setStyleSheet("""
        QScrollArea {
                border: transparent  /* Define a espessura e a cor da borda */
                
        }
        QScrollBar:vertical {
                width: 12px;  /* Largura da barra de rolagem vertical */
        }
        QScrollBar:horizontal {
                height: 12px;  /* Altura da barra de rolagem horizontal */
        }
        """)

        
        self.contentStack.setCurrentWidget(self.caixaContentWidget)
        self.tableWidgetCaixa = QtWidgets.QTableWidget(self.caixaContentWidget)
        self.tableWidgetCaixa.setGeometry(QtCore.QRect(750, 390, 400, 300))
        self.tableWidgetCaixa.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.tableWidgetCaixa.setToolTip("")
        self.tableWidgetCaixa.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tableWidgetCaixa.setAutoFillBackground(False)
        self.tableWidgetCaixa.verticalHeader().setVisible(False)

       
        
        # Adiciona a QTableWidget como widget da QScrollArea
        self.scrollArea.setWidget(self.tableWidgetCaixa)
        

        self.tableWidgetCaixa.setStyleSheet("font: 12pt \"Sans Serif Collection\";\n"
"color: rgb(51, 51, 51);")
        self.tableWidgetCaixa.setLineWidth(0)
        self.tableWidgetCaixa.setMidLineWidth(0)
        self.tableWidgetCaixa.setAutoScroll(True)
        self.tableWidgetCaixa.setAutoScrollMargin(16)
        self.tableWidgetCaixa.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
         

        self.tableWidgetCaixa.setObjectName("tableWidgetCaixa")
        
        # Label para "Valor em caixa:"
        self.labelValorEmCaixa = QtWidgets.QLabel(self.caixaContentWidget)
        self.labelValorEmCaixa.setText("Valor em caixa:")
        self.labelValorEmCaixa.setGeometry(QtCore.QRect(750, 760, 400, 50))  # Ajuste conforme necessário
        self.labelValorEmCaixa.setStyleSheet("background-color: transparent; color: #333; font: bold 16pt 'Sans Serif Collection';")
        self.labelValorEmCaixa.setAlignment(Qt.AlignCenter)  # Centraliza o texto horizontalmente

        # Label para mostrar o valor total em caixa
        self.labelValorTotalCaixa = QtWidgets.QLabel(self.caixaContentWidget)
        self.labelValorTotalCaixa.setGeometry(QtCore.QRect(750, 780, 400, 70))  # Ajuste conforme necessário
        self.labelValorTotalCaixa.setStyleSheet("background-color: transparent; color: #333; font: bold 28pt 'Sans Serif Collection';")
        self.labelValorTotalCaixa.setAlignment(Qt.AlignCenter)  # Centraliza o texto horizontalmente e verticalmente

        # Inicializa o valor total em caixa com 0 ou com o valor atual do banco de dados
        self.atualizarValorTotalCaixa()


        # Adiciona o widget ao QStackedWidget
        self.contentStack.addWidget(self.caixaContentWidget)
        self.contentStack.setCurrentWidget(self.caixaContentWidget)
        
        self.retranslateUiContentCaixa(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        # Ajuste automático ou fixo para larguras de coluna
     
        self.tableWidgetCaixa.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.tableWidgetCaixa.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        
        

        
        

    def retranslateUiContentCaixa(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        
        
        self.tableWidgetCaixa.setColumnCount(2)  # Ajuste conforme necessário para incluir a coluna de ação
        self.tableWidgetCaixa.setHorizontalHeaderLabels(['Distribuição', 'Saldo'])  # Inclui o cabeçalho da coluna de ação
       
            # Define a alinhação dos textos dos cabeçalhos à esquerda
        self.tableWidgetCaixa.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tableWidgetCaixa.horizontalHeader().setStyleSheet("""
        QHeaderView::section {
            background-color: #E0E0E0;

            border: 1px solid #D3D3D3;
            font-size: 12pt;
            color: rgb(51, 51, 51);
            border-bottom: 1px solid #333;
            padding: 0 3px;
      
        }
    """)
        
        self.loadTableDataCaixa()
        self.tableWidgetCaixa.itemChanged.connect(self.handleItemChangedCaixa)
        
        
    def telaCaixaAbrir(self):
        try:
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password'
                )
                cursor = conn.cursor()


                # Solicita login
                login, okPressedLogin = QInputDialog.getText(self.central_widget, "Área restrita", "Usuário:", QLineEdit.Normal, "")
                 
                if okPressedLogin and login:
                           # Solicita senha
                           senha, okPressedSenha = QInputDialog.getText(self.central_widget, "Área restrita", "Senha:", QLineEdit.Password, "")
                      
                           if okPressedSenha and senha:
                               # Verifica login e senha
                              cursor.execute("SELECT * FROM Users WHERE user = %s AND senha = %s", (login, senha))
                              user = cursor.fetchone()
                              if user:
                                  # Fechamento do dia após autenticação bem-sucedida

                                  self.setupCaixaContent()
                                 

                              else:
                                 QMessageBox.warning(self.central_widget, "Erro", "Usuário ou Senha incorretos!")
                                 return
                           else:
                             QMessageBox.warning(self.central_widget, "Cancelado", "Abrir Detalhes de saldo cancelado.")
                             return
                else:
                        QMessageBox.warning(self.central_widget, "Cancelado", "Abrir Detalhes de saldo cancelado.")
                        return
                   
                       
        except mysql.connector.Error as e:
                QMessageBox.critical(self.central_widget, "Erro", f"Erro ao acessar o banco de dados: {e}")
        finally:
                if conn.is_connected():
                 cursor.close()
                 conn.close()
        
      
    def loadTableDataCaixa(self):
        try:
    # Tenta definir a localidade para pt_BR.UTF-8
                locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
                try:
        # Tenta uma alternativa comum no Windows
                        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
                except locale.Error:
        # Usa a localidade padrão do sistema se as específicas falharem
                        locale.setlocale(locale.LC_ALL, '')
        
        conn = None
        try:
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password',
                use_pure=True
                )
                
                verificar_e_inserir_valores_distribuicao_com_saldo(conn)
                
                cursor = conn.cursor()
                # Certifique-se de selecionar também o idCaixa
                query = "SELECT idCaixa, distribuicao, saldo FROM caixa"
                cursor.execute(query)
                rows = cursor.fetchall()

                self.tableWidgetCaixa.setRowCount(0)

                for row_number, row_data in enumerate(rows):
                        idCaixa, distribuicao, saldo = row_data  # Desempacotando os valores
                        
                        self.tableWidgetCaixa.insertRow(row_number)
                        
                        # Coluna de Distribuição
                        item_distribuicao = QtWidgets.QTableWidgetItem(distribuicao)
                        item_distribuicao.setFont(QFont('Sans Serif Collection', 10))
                        self.tableWidgetCaixa.setItem(row_number, 0, item_distribuicao)
                        
                        # Coluna de Saldo, formatada
                        valor_formatted = locale.format_string('R$ %.2f', float(saldo), grouping=True)
                        item_saldo = QtWidgets.QTableWidgetItem(valor_formatted)
                        item_saldo.setFont(QFont('Arial Rounded MT Bold', 12))
                        self.tableWidgetCaixa.setItem(row_number, 1, item_saldo)
                        
                        # Armazenando o ID usando setData
                        item_distribuicao.setData(Qt.UserRole, idCaixa)
                        item_saldo.setData(Qt.UserRole, idCaixa)

        except mysql.connector.Error as e:
                print(f"Error connecting to MySQL: {e}")
        finally:
                if conn is not None and conn.is_connected():
                 conn.close()

   
    def handleItemChangedCaixa(self, item):
        row = item.row()
        column = item.column()
        newValue = item.text()
        idCaixa = item.data(Qt.UserRole)  # Recupera o ID do item usando UserRole
        columnName = self.getColumnNameByIndexCaixa(column)

        
     
                
        # Converte newValue para o formato correto antes de enviar ao banco
        if columnName == 'saldo':
                
                        
                # Remove caracteres de moeda e converte para o formato decimal        
                newValue = newValue.replace('R$', '').replace('.', '').replace(',', '.').replace('+ R$', '').replace('+ ', '').replace(' + ', '').replace(' +', '').replace('+', '').replace('- ', '').replace(' -', '').replace(' - ', '').replace('-', '').strip()
                
                



        # Aqui você escreve o código para atualizar o banco de dados
        conn = None
        try:
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password'
                )
                cursor = conn.cursor()
                
                query = f"UPDATE caixa SET {columnName} = %s WHERE idCaixa = %s"
                cursor.execute(query, (newValue, idCaixa))
                

                   
                conn.commit()
                self.setupCaixaContent()
                
                
                
        except mysql.connector.Error as e:
                print(f"Error: {e}")
        finally:
                if conn is not None and conn.is_connected():
                 
                 conn.close()
   
   
    def getColumnNameByIndexCaixa(self, index):
        # Retorna o nome da coluna no banco de dados baseado no índice da coluna na tabela
        columns = ['distribuicao', 'saldo']
        return columns[index]  # Ajuste conforme a estrutura real da sua tabela


    def atualizarValorTotalCaixa(self):
        conn = None
        try:
                conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='bd.hermannmarmoraria@32231009',
                database='sistema_financas',
                auth_plugin='mysql_native_password',
                use_pure=True
                )
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(saldo) FROM caixa")
                total = cursor.fetchone()[0]
                
                if total is None:
                 total = 0.0  # Caso não haja valores, definir como 0
                
                valor_formatado = locale.format_string('R$ %.2f', total, grouping=True)
                self.labelValorTotalCaixa.setText(valor_formatado)

        except mysql.connector.Error as e:
                print(f"Error connecting to MySQL: {e}")
                self.labelValorTotalCaixa.setText("R$ 0,00")
        finally:
                if conn is not None and conn.is_connected():
                 conn.close()


    def atualizarTela(self):
            self.setupInitialContent()
            QMessageBox.information(self.central_widget, "Atualizado", "Tela inicial atualizada!.")
import images_home.resources

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont("HP Simplified", 10)) 
    create_tables()   
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())




