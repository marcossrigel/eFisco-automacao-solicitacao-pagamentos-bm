import re
import time
import gspread

from selenium import webdriver
from selenium.webdriver.common.by import By
from google.oauth2.service_account import Credentials
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
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

        self.planilha = cliente.open_by_key("1lkM9yOjhu_D2nQjRFl-Wt6lNgWPvzl2wbQiaO633-KM")

        self.aba = self.planilha.worksheet("BMs 2026")

        dados = self.aba.get_all_values()

        linha = 1052
        registro = dados[linha - 1]

        numero_sei = registro[11] 
        numero_contrato = registro[4]   
        descricao = registro[7]          
        fonte = registro[15]
        local_obra = registro[8]

        cidade = ""

        contrato = numero_contrato
        fonte_recurso = fonte

        historico = []
        anteriores = []
        registro = dados[linha - 1]
        data_atual = registro[0].split(" ")[0]

        for indice, linha_atual in enumerate(dados, start=1):

            if (
                len(linha_atual) > 31
                and linha_atual[4] == contrato
                and linha_atual[15] == fonte_recurso
                and linha_atual[8] == local_obra
            ):

                registro = {
                    "linha": indice,
                    "resolucao": linha_atual[31],
                    "valor": linha_atual[14],
                    "data": linha_atual[0].split(" ")[0]
                }

                historico.append(registro)

                # Guarda somente as linhas anteriores à atual
                if indice < linha:
                    anteriores.append(registro)

        if anteriores:

            resolucao = dados[linha - 1][31]

            # Extrai a NE da resolução
            resultado = re.search(r"NE(\d+)", resolucao, re.IGNORECASE)

            if resultado:
                ne_atual = resultado.group(1)
            else:
                ne_atual = ""

            valor_ne = 0.0

            for item in anteriores:

                print(
                    item["linha"],
                    item["data"],
                    item["valor"]
                )
                # Ignora registros com a mesma data e hora
                if item["data"] == data_atual:
                    continue

                resultado_item = re.search(
                    r"NE(\d+)",
                    item["resolucao"],
                    re.IGNORECASE
                )

                if not resultado_item:
                    continue

                ne_item = resultado_item.group(1)

                # Soma apenas quem possui a mesma NE
                if ne_item == ne_atual:

                    valor = item["valor"]

                    if valor:
                        valor_ne += float(
                            valor.replace(".", "").replace(",", ".")
                        )


        else:

            resolucao = ""
            valor_ne = 0.0

        resultado = re.search(r"NE(\d+)", resolucao)

        if resultado:
            numero_empenho = resultado.group(1)
        else:
            numero_empenho = ""

        resultado = re.search(
            r"NO MUNIC[IÍ]PIO DE\s+(.+?),\s+NO ESTADO",
            descricao,
            re.IGNORECASE
        )

        if resultado:
            cidade = resultado.group(1).title()

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

        checkbox = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//tr[td[contains(., 'NE{numero_empenho}')]]//input[@type='checkbox']"
                )
            )
        )

        checkbox.click()
        time.sleep(3)

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

        celula = wait.until(
            EC.presence_of_element_located(
                (By.ID, "cdCelulaOrcamentaria")
            )
        ).get_attribute("value")

        ficha_financeira = wait.until(
            EC.presence_of_element_located(
                (By.ID, "cdFichaFinanceiraFormatado")
            )
        ).get_attribute("value")

        # Remove o código da ficha, mantendo apenas a descrição
        if " - " in ficha_financeira:
            ficha_financeira = ficha_financeira.split(" - ", 1)[1]

        valor_liquidar = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="table_tabeladados"]/tbody/tr[5]/td[2]/input'
                )
            )
        ).get_attribute("value")

        valor_pagar_liquidado = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="table_tabeladados"]/tbody/tr[4]/td[2]/input'
                )
            )
        ).get_attribute("value")

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

    print("=" * 60)
    print(f"Nº do SEI: {dados['sei']}")
    print(f"Contrato : {dados['contrato']}")
    print(f"Local da obra : {dados['local_obra']}")
    print(f"Fonte : {dados['fonte']}")
    print(f"Resolução : {dados['resolucao']}")
    print(f"Empenho : {dados['empenho']}")
    print()

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

    print("\n" + "=" * 60)
    print("CONFERÊNCIA DA NE")
    print("=" * 60)
    print(f"Soma das resoluções.....: {valor_ne:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"Valor a Pagar Liquidado.: {valor_pagar_liquidado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    if abs(valor_ne - valor_pagar_liquidado) < 0.01:
        print("Resultado...............: OK")
        valor_disponivel = valor_liquidar
    else:
        print("Resultado...............: DIVERGENTE")
        valor_disponivel = valor_liquidar - valor_ne

    print("=" * 60)

    print(f"Célula Orçamentária: {extrato['celula']}")
    print(f"Ficha Financeira: {extrato['ficha_financeira']}")
    print(f"Ação: {extrato['acao']}")
    print(f"Subação: {extrato['subacao']}")
    print(f"Fonte: {extrato['fonte']}")
    print(f"Valor a Liquidar: {extrato['valor_liquidar']}")
    valor_disponivel_formatado = (
        f"{valor_disponivel:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    print(f"Valor Disponível de NE: {valor_disponivel_formatado}")
    print("=" * 60)

    print()

    print("\n" + "=" * 60)
    print("SIMULAÇÃO DA ESCRITA NA PLANILHA")
    print("=" * 60)

    # AC - Ação (coluna 29)
    print(
        f"Linha {dados['linha']} | Ação -> {extrato['acao']}"
    )

    # AD - Subação (coluna 30)
    print(
        f"Linha {dados['linha']} | Subação -> {extrato['subacao']}"
    )

    # AE - Fonte (coluna 31)
    print(
        f"Linha {dados['linha']} | Fonte -> {extrato['fonte']}"
    )

    # AG - Ficha Financeira (coluna 33)
    print(
        f"Linha {dados['linha']} | Ficha Financeira -> {extrato['ficha_financeira']}"
    )

    # AK - Valor Disponível de NE (coluna 37)
    print(
        f"Linha {dados['linha']} | Valor Disponível de NE -> "
        f"{valor_disponivel:.2f}".replace(".", ",")
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
