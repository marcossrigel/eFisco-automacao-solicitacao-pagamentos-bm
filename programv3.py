import os
import subprocess
import time
import socket

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

PERFIL_EDGE = r"C:\EdgeRobot"

PORTA_EDGE = 9333

URL_EFISCO = (
    "https://efisco.sefaz.pe.gov.br/"
    "sfi_com_sca/PRMontarMenuAcesso"
)


# ============================================================
# VERIFICA SE O EDGE DO ROBÔ JÁ ESTÁ ABERTO
# ============================================================

def porta_aberta():

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)

    resultado = sock.connect_ex(
        ("127.0.0.1", PORTA_EDGE)
    )

    sock.close()

    return resultado == 0


# ============================================================
# ABRIR EDGE
# ============================================================

def abrir_edge():

    if porta_aberta():
        return

    subprocess.Popen([
        EDGE,
        f"--remote-debugging-port={PORTA_EDGE}",
        f"--user-data-dir={PERFIL_EDGE}",
        "--profile-directory=Default"
    ])

    for _ in range(30):

        if porta_aberta():
            return

        time.sleep(1)

    raise Exception(
        "Não foi possível iniciar o Edge na porta de depuração."
    )


# ============================================================
# CONECTAR SELENIUM
# ============================================================

def conectar_selenium():

    options = Options()

    options.add_experimental_option(
        "debuggerAddress",
        f"127.0.0.1:{PORTA_EDGE}"
    )

    driver = webdriver.Edge(options=options)

    return driver


# ============================================================
# ESCOLHER / CRIAR ABA DO EFISCO
# ============================================================

def preparar_aba_efisco(driver):

    aba_efisco = None

    # Procura uma aba do eFisco que já esteja aberta
    for handle in driver.window_handles:

        try:

            driver.switch_to.window(handle)

            url = driver.current_url

            if "efisco.sefaz.pe.gov.br" in url:

                aba_efisco = handle
                break

        except Exception:
            continue

    # --------------------------------------------------------
    # SE JÁ EXISTE UMA ABA DO EFISCO
    # --------------------------------------------------------

    if aba_efisco:

        driver.switch_to.window(aba_efisco)

        driver.get(URL_EFISCO)

    # --------------------------------------------------------
    # SE NÃO EXISTE
    # --------------------------------------------------------

    else:
        driver.switch_to.new_window("tab")
        driver.get(URL_EFISCO)

    # Espera carregamento
    WebDriverWait(driver, 30).until(
        lambda d: d.execute_script(
            "return document.readyState"
        ) == "complete"
    )


# ============================================================
# VERIFICAR LOGIN
# ============================================================

def verificar_login(driver):
    # Se o menu principal existir, já estamos logados
    if driver.find_elements(
        By.ID,
        "favoritos_carrossel_itens"
    ):

        return True

    # Outra forma de identificar usuário logado
    if driver.find_elements(
        By.ID,
        "a_usuario"
    ):

        return True

    return False


# ============================================================
# LOGIN GOV.BR
# ============================================================

def iniciar_login(driver):

    botao_gov = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable(
            (By.ID, "btt_gov")
        )
    )

    botao_gov.click()


# ============================================================
# GARANTIR QUE ESTAMOS NA ABA DO EFISCO
# ============================================================

def localizar_aba_efisco(driver):

    for handle in driver.window_handles:

        try:

            driver.switch_to.window(handle)

            if "efisco.sefaz.pe.gov.br" in driver.current_url:

                return True

        except Exception:
            continue

    return False


# ============================================================
# AGUARDAR MENU
# ============================================================

def aguardar_menu_efisco(driver):

    # Depois do GOV.BR pode ter ocorrido troca de aba
    localizar_aba_efisco(driver)

    menu = WebDriverWait(driver, 60).until(
        EC.visibility_of_element_located(
            (By.ID, "favoritos_carrossel_itens")
        )
    )

    WebDriverWait(driver, 60).until(
        lambda d: len(
            d.find_elements(
                By.XPATH,
                '//*[@id="favoritos_carrossel_itens"]//a'
            )
        ) > 0
    )



# ============================================================
# ACESSAR ORDEM BANCÁRIA
# ============================================================

def acessar_ordem_bancaria(driver):

    xpath = (
        '//*[@id="favoritos_carrossel_itens"]'
        '//a[contains(normalize-space(.), "Ordem Bancária")]'
    )

    wait = WebDriverWait(driver, 30)

    ordem_bancaria = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, xpath)
        )
    )

    driver.execute_script(
        """
        arguments[0].scrollIntoView({
            block: 'center',
            inline: 'center'
        });
        """,
        ordem_bancaria
    )

    time.sleep(1)

    try:

        ordem_bancaria = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, xpath)
            )
        )

        ordem_bancaria.click()

    except Exception:

        ordem_bancaria = driver.find_element(
            By.XPATH,
            xpath
        )

        driver.execute_script(
            "arguments[0].click();",
            ordem_bancaria
        )

# ============================================================
# MAIN
# ============================================================

def main():

    try:

        abrir_edge()

        driver = conectar_selenium()

        preparar_aba_efisco(driver)

        ja_logado = verificar_login(driver)

        if not ja_logado:
            iniciar_login(driver)

        aguardar_menu_efisco(driver)

        acessar_ordem_bancaria(driver)

        print("=" * 60)
        print("🤖 ROBÔ EFISCO")
        print("🤖 ORDEM BANCÁRIA ACESSADA")
        print("=" * 60)

    except Exception as erro:

        print("\n" + "=" * 60)
        print("❌ ERRO NA AUTOMAÇÃO")
        print("=" * 60)
        print(type(erro).__name__)
        print(erro)
        print("=" * 60)


if __name__ == "__main__":
    main()
