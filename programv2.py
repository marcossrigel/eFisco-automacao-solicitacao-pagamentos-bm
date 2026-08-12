import os
import pandas as pd

from datetime import datetime

PASTA_DOWNLOADS = r"C:\Users\marcos.rigel.CEHABPE\Downloads"

class RoboEFisco:

    def __init__(self):

        self.planilhas = {
            "CONSULTA EMPENHO": None,
            "LIQUIDAÇÃO DE EMPENHO": None,
            "ORDEM BANCÁRIA": None
        }

        self.dados = {
            "CONSULTA EMPENHO": None,
            "LIQUIDAÇÃO DE EMPENHO": None,
            "ORDEM BANCÁRIA": None
        }


    # ============================================================
    # IDENTIFICA QUAL É A PLANILHA
    # ============================================================

    def identificar_planilha(self, nome_arquivo):

        nome = nome_arquivo.lower()

        if "extracaoob" in nome:
            return "ORDEM BANCÁRIA"

        elif "extracaole" in nome:
            return "LIQUIDAÇÃO DE EMPENHO"

        elif "extracaone" in nome:
            return "CONSULTA EMPENHO"

        return None


    # ============================================================
    # LOCALIZA AS PLANILHAS BAIXADAS HOJE
    # ============================================================

    def verificar_planilhas(self):

        hoje = datetime.now().date()

        for nome_arquivo in os.listdir(PASTA_DOWNLOADS):

            tipo = self.identificar_planilha(nome_arquivo)

            if not tipo:
                continue

            caminho = os.path.join(
                PASTA_DOWNLOADS,
                nome_arquivo
            )

            if not os.path.isfile(caminho):
                continue

            # Ignora downloads ainda em andamento
            if nome_arquivo.lower().endswith(".crdownload"):
                continue

            timestamp = os.path.getmtime(caminho)

            data_arquivo = datetime.fromtimestamp(
                timestamp
            ).date()

            # Só considera arquivos de hoje
            if data_arquivo != hoje:
                continue

            caminho_atual = self.planilhas[tipo]

            # Se ainda não encontrou esse tipo
            if caminho_atual is None:

                self.planilhas[tipo] = caminho

            # Se encontrou mais de um, pega o mais recente
            elif (
                os.path.getmtime(caminho)
                > os.path.getmtime(caminho_atual)
            ):

                self.planilhas[tipo] = caminho


    # ============================================================
    # LÊ UMA PLANILHA
    # ============================================================

    def ler_planilha(self, caminho):

        extensao = os.path.splitext(caminho)[1].lower()

        if extensao == ".xlsx":

            return pd.read_excel(
                caminho,
                engine="openpyxl"
            )

        elif extensao == ".xls":

            return pd.read_excel(
                caminho,
                engine="xlrd"
            )

        else:

            raise ValueError(
                f"Formato não suportado: {extensao}"
            )


    # ============================================================
    # CARREGA AS PLANILHAS
    # ============================================================

    def carregar_planilhas(self):

        for tipo, caminho in self.planilhas.items():

            if caminho is None:
                continue

            try:

                self.dados[tipo] = self.ler_planilha(
                    caminho
                )

            except Exception as erro:

                self.dados[tipo] = None

                print(
                    f"❌ Erro ao carregar "
                    f"{os.path.basename(caminho)}"
                )

                print(f"   {erro}")

    # ============================================================
    # MOSTRA RESULTADO
    # ============================================================

    def mostrar_status(self):

        os.system(
            "cls" if os.name == "nt" else "clear"
        )

        print("🤖 Iniciando")
        print()

        for tipo, caminho in self.planilhas.items():

            # Arquivo não encontrado
            if caminho is None:

                print(f"❌ Não encontrado: {tipo}")
                continue

            nome_arquivo = os.path.basename(caminho)

            # Arquivo realmente carregado
            if self.dados[tipo] is not None:

                print(
                    f"✅ Carregado {nome_arquivo}"
                )

            else:

                print(
                    f"❌ Falha ao carregar {nome_arquivo}"
                )

def main():

    robo = RoboEFisco()
    # 1. Procura as planilhas
    robo.verificar_planilhas()
    # 2. Lê o conteúdo
    robo.carregar_planilhas()
    # 3. Mostra resultado
    robo.mostrar_status()

if __name__ == "__main__":
    main()
