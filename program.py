import re
import time
import gspread

from selenium import webdriver
from selenium.webdriver.common.by import By
from google.oauth2.service_account import Credentials
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException
)
from selenium.webdriver.support import expected_conditions as EC

class RoboEFisco:

    def __init__(self):

        options = Options()
        options.add_experimental_option(
            "debuggerAddress",
            "127.0.0.1:9222"
        )

        self.driver = webdriver.Chrome(options=options)

        self.planilha = None
        self.aba = None

    def aguardar_login_efisco(self):

        while True:

            try:
                self.driver.find_element(
                    By.XPATH,
                    '//*[@id="a_usuario"]'
                )
                return "✅ Usuario Logado no eFisco"

            except NoSuchElementException:
                pass

            try:
                botao = self.driver.find_element(
                    By.XPATH,
                    '//*[@id="btt_gov"]'
                )
                botao.click()
                time.sleep(2)
                continue

            except NoSuchElementException:
                pass

            try:
                WebDriverWait(self.driver, 300).until(
                    EC.presence_of_element_located(
                        (By.ID, "a_usuario")
                    )
                )

                print("✅ Usuário Logado no eFisco")
                return "Usuario Logado no eFisco"

            except:
                return None

    def abrir_efisco(self):

        self.driver.switch_to.new_window("tab")
        self.driver.get("https://efisco.sefaz.pe.gov.br/")

    def lendo_planilha(self):

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        credenciais = Credentials.from_service_account_file(
            "credenciais.json",
            scopes=scopes
        )

        cliente = gspread.authorize(credenciais)

        self.planilha = cliente.open_by_key(
            "1lkM9yOjhu_D2nQjRFl-Wt6lNgWPvzl2wbQiaO633-KM"
        )

        self.aba = self.planilha.worksheet("BMs 2026")

        dados = self.aba.get_all_values()

        # ============================================================
        # REGISTRO QUE SERÁ PROCESSADO
        # ============================================================

        linha = 708
        registro_atual = dados[linha - 1]

        numero_sei = registro_atual[11]
        numero_contrato = registro_atual[4]
        descricao = registro_atual[7]
        fonte = registro_atual[15]
        local_obra = registro_atual[8]

        cidade = ""

        contrato = numero_contrato
        fonte_recurso = fonte

        data_atual = registro_atual[0].split(" ")[0]


        # ============================================================
        # MONTA O HISTÓRICO
        # Contrato + Fonte + Local da obra
        # ============================================================

        historico = []
        anteriores = []

        for indice, linha_atual in enumerate(dados, start=1):

            if (
                len(linha_atual) > 31
                and linha_atual[4] == contrato
                and linha_atual[15] == fonte_recurso
                and linha_atual[8] == local_obra
            ):

                item_historico = {
                    "linha": indice,
                    "resolucao": linha_atual[31].strip(),
                    "valor": linha_atual[14],
                    "data": linha_atual[0].split(" ")[0]
                }

                historico.append(item_historico)

                # Somente registros anteriores ao registro atual
                if indice < linha:
                    anteriores.append(item_historico)


        # ============================================================
        # RESOLUÇÃO DA LINHA ATUAL
        # ============================================================

        resolucao_atual = registro_atual[31].strip()

        resolucao = resolucao_atual
        numero_empenho = ""
        linha_empenho = None

        resultado_atual = re.search(
            r"NE\s*0*(\d+)",
            resolucao_atual,
            re.IGNORECASE
        )


        # ============================================================
        # 1º - VERIFICA SE A PRÓPRIA LINHA POSSUI NE
        # ============================================================

        if resultado_atual:

            numero_empenho = resultado_atual.group(1)
            linha_empenho = linha


        # ============================================================
        # 2º - SE NÃO POSSUI NE, PROCURA NOS REGISTROS ANTERIORES
        # ============================================================

        else:

            for item in reversed(anteriores):

                resolucao_anterior = item["resolucao"]

                resultado_anterior = re.search(
                    r"NE\s*0*(\d+)",
                    resolucao_anterior,
                    re.IGNORECASE
                )

                # Não possui NE?
                # Ignora e continua para o próximo registro anterior.
                if not resultado_anterior:
                    continue

                # Encontrou uma resolução com NE
                numero_empenho = resultado_anterior.group(1)
                resolucao = resolucao_anterior
                linha_empenho = item["linha"]

                print(
                    f"Empenho encontrado no registro anterior "
                    f"{item['linha']}: {resolucao_anterior}"
                )

                # Encontrou o registro anterior que precisamos.
                # Para imediatamente a pesquisa.
                break


        # ============================================================
        # SOMA O HISTÓRICO DA NE ENCONTRADA
        # ============================================================

        valor_ne = 0.0

        if numero_empenho:

            for item in anteriores:

                # Ignora registros da mesma data
                if item["data"] == data_atual:
                    continue

                resultado_item = re.search(
                    r"NE\s*0*(\d+)",
                    item["resolucao"],
                    re.IGNORECASE
                )

                if not resultado_item:
                    continue

                ne_item = resultado_item.group(1)

                # Só soma valores pertencentes à mesma NE
                if ne_item == numero_empenho:

                    valor = item["valor"]

                    if valor:

                        valor_ne += float(
                            valor.replace(".", "").replace(",", ".")
                        )


        # ============================================================
        # IDENTIFICA CIDADE NA DESCRIÇÃO
        # ============================================================

        resultado = re.search(
            r"NO MUNIC[IÍ]PIO DE\s+(.+?),\s+NO ESTADO",
            descricao,
            re.IGNORECASE
        )

        if resultado:
            cidade = resultado.group(1).title()


        # ============================================================
        # RETORNO
        # ============================================================

        return {
            "linha": linha,
            "contrato": numero_contrato,
            "local_obra": local_obra,
            "fonte": fonte,
            "sei": numero_sei,
            "resolucao": resolucao,
            "empenho": numero_empenho,
            "valor_ne": valor_ne
        }

    def consultar_empenho(self, numero_empenho):

        self.driver.get("https://efisco.sefaz.pe.gov.br/sfi_com_sca/PRMontarMenuAcesso")
        time.sleep(5)

        wait = WebDriverWait(self.driver, 20)

        wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="favoritos_carrossel_itens"]/div/ul/li[1]/a'
                )
            )
        ).click()

        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="primeiro_campo"]')
            )
        )

        ug = self.driver.find_element(
            By.XPATH,
            '//*[@id="primeiro_campo"]'
        )

        ug.clear()
        ug.send_keys("651101")

        time.sleep(3)

        campo = self.driver.find_element(
            By.XPATH,
            '//*[@id="nuEmpenho"]'
        )

        campo.clear()
        campo.send_keys(numero_empenho)

        self.driver.find_element(
            By.XPATH,
            '//*[@id="tpOrdenacaoConsultaEmpenho"]'
        ).click()

        time.sleep(3)
        self.driver.find_element(
            By.XPATH,
            '//*[@id="btt_localizar"]'
        ).click()

        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//table//tr[2]")
            )
        )

        time.sleep(3)

        wait.until(
        EC.element_to_be_clickable(
                (By.ID, "rdb_consulta")
            )
        ).click()

        wait.until(
            EC.element_to_be_clickable(
                (By.ID, "btt_Extrato")
            )
        ).click()

        wait.until(
            EC.presence_of_element_located(
                (By.ID, "cdCelulaOrcamentaria")
            )
        )

        return self.extrato_empenho()

    def extrato_empenho(self):

        wait = WebDriverWait(self.driver, 20)

        # ============================================================
        # FUNÇÃO PARA LER CAMPOS EVITANDO STALE ELEMENT
        # ============================================================

        def pegar_valor(by, localizador):

            for tentativa in range(5):

                try:
                    elemento = wait.until(
                        EC.presence_of_element_located(
                            (by, localizador)
                        )
                    )

                    valor = elemento.get_attribute("value")

                    return valor

                except StaleElementReferenceException:

                    time.sleep(1)

            raise Exception(
                f"Não foi possível ler o campo: {localizador}"
            )


        # ============================================================
        # AGUARDA A TELA DO EXTRATO
        # ============================================================

        wait.until(
            EC.presence_of_element_located(
                (By.ID, "cdCelulaOrcamentaria")
            )
        )

        time.sleep(2)


        # ============================================================
        # LÊ OS DADOS
        # ============================================================

        celula = pegar_valor(
            By.ID,
            "cdCelulaOrcamentaria"
        )

        ficha_financeira = pegar_valor(
            By.ID,
            "cdFichaFinanceiraFormatado"
        )

        if " - " in ficha_financeira:
            ficha_financeira = ficha_financeira.split(" - ", 1)[1]


        valor_liquidar = pegar_valor(
            By.XPATH,
            '//*[@id="table_tabeladados"]/tbody/tr[5]/td[2]/input'
        )

        valor_pagar_liquidado = pegar_valor(
            By.XPATH,
            '//*[@id="table_tabeladados"]/tbody/tr[4]/td[2]/input'
        )


        # ============================================================
        # SEPARA CÉLULA ORÇAMENTÁRIA
        # ============================================================

        partes = celula.split(".")

        acao = partes[5]
        subacao = partes[6]
        fonte = partes[7]


        return {
            "celula": celula,
            "ficha_financeira": ficha_financeira,
            "acao": acao,
            "subacao": subacao,
            "fonte": fonte,
            "valor_liquidar": valor_liquidar,
            "valor_pagar_liquidado": valor_pagar_liquidado
        }

def main():

    robo = RoboEFisco()
    robo.abrir_efisco()
    robo.aguardar_login_efisco()
    dados = robo.lendo_planilha()

    print("\n" + "=" * 60)
    print(f"REGISTRO {dados['linha']}")
    print("=" * 60)

    print(f"SEI ..............: {dados['sei']}")
    print(f"Contrato .........: {dados['contrato']}")
    print(f"Local da obra ....: {dados['local_obra']}")
    print(f"Fonte ............: {dados['fonte']}")
    print(f"Resolução ........: {dados['resolucao']}")
    print(f"Empenho ..........: {dados['empenho']}")
    print()

    # Verifica se possui empenho
    if not dados["empenho"] or not str(dados["empenho"]).strip():
        print("⚠️ Registro sem empenho!")
        print("=" * 60)
        input("\nPressione ENTER para encerrar...")
        return

    extrato = robo.consultar_empenho(dados["empenho"])

    valor_liquidar = float(
        extrato["valor_liquidar"]
        .replace(".", "")
        .replace(",", ".")
    )

    valor_pagar_liquidado = float(
        extrato["valor_pagar_liquidado"]
        .replace(".", "")
        .replace(",", ".")
    )

    valor_ne = dados["valor_ne"]


    # ============================================================
    # CONFERÊNCIA
    # ============================================================

    print("CONFERÊNCIA DA NE")

    print(
        f"Soma resoluções ..: R$ "
        f"{valor_ne:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    print(
        f"Pago/Liquidado ...: R$ "
        f"{valor_pagar_liquidado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    if abs(valor_ne - valor_pagar_liquidado) < 0.01:
        print("Resultado ........: ✅ OK")
        valor_disponivel = valor_liquidar
    else:
        print("Resultado ........: ❌ DIVERGENTE")
        valor_disponivel = valor_liquidar - valor_ne


    # ============================================================
    # DADOS ORÇAMENTÁRIOS
    # ============================================================

    print()
    print("DADOS ORÇAMENTÁRIOS")

    print(f"Ficha Financeira .: {extrato['ficha_financeira']}")
    print(f"Ação .............: {extrato['acao']}")
    print(f"Subação ..........: {extrato['subacao']}")
    print(f"Fonte ............: {extrato['fonte']}")
    print(f"Valor a Liquidar .: R$ {extrato['valor_liquidar']}")

    print("=" * 60)


if __name__ == "__main__":
    main()
