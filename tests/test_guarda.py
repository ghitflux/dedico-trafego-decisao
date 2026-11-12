"""Guarda permanente: nada do que é publicado pode trazer valor em moeda nem detalhe do negócio.

O estudo é publicado em unidades relativas (meta de CAC = 100). Estes testes varrem todos os
arquivos versionados e falham se aparecer:
- um símbolo de moeda seguido de número;
- o nome do produto mais de uma vez;
- qualquer valor ou termo da lista privada (`data/privado/guarda.json`), quando ela existe.

A lista privada não é versionada, de propósito: escrever aqui os valores proibidos seria publicá-los.
Num clone sem a pasta privada, o teste que depende dela é pulado e os outros continuam valendo.
"""

from __future__ import annotations

import json
import re
import subprocess

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.text import Text

from trafego_decisao import analise, economia, graficos, parametros

RAIZ = parametros.RAIZ
LISTA_PRIVADA = RAIZ / "data" / "privado" / "guarda.json"
TEXTO = {".py", ".md", ".sql", ".json", ".csv", ".toml", ".ipynb", ".txt", ".yml", ".yaml", ".lock", ".cfg", ""}
IGNORADAS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ipynb_checkpoints", "privado", "raw", "exemplo"}
# Arquivos em que número solto não é dado do estudo: cotações públicas e versões de dependências.
SEM_VARREDURA_DE_VALORES = {"data/cambio_ptax.csv", "uv.lock"}
MOEDA_COM_NUMERO = re.compile(r"(?:R|US|U)\$\s*\d|\b\d+(?:[.,]\d+)?\s*(?:reais|centavos|BRL)\b", re.IGNORECASE)
NOME_DO_PRODUTO = "Dedico" + " " + "Songs"
POSICAO_DE_PRECO = re.compile(
    r"mediana do mercado|market median|mediana del mercado|percentil do pre[cç]o|pre[cç]o do produto"
    r"|pre[cç]o no mercado|pre[cç]o entre concorrentes|preco_concorrentes|posi[cç][aã]o (relativa )?(do|de) pre[cç]o"
    r"|cobram (menos|mais)|concorrentes_exemplo|carregar_concorrentes|posicao_de_preco",
    re.IGNORECASE,
)


def _versionados() -> list[str]:
    """Caminhos (relativos à raiz) dos arquivos de texto que vão ao repositório."""
    try:
        saida = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout.splitlines()
        caminhos = [linha.strip().strip('"') for linha in saida if linha.strip()]
    except (OSError, subprocess.CalledProcessError):
        caminhos = [
            c.relative_to(RAIZ).as_posix()
            for c in RAIZ.rglob("*")
            if c.is_file() and not (set(c.relative_to(RAIZ).parts) & IGNORADAS)
        ]
    return sorted(c for c in caminhos if (RAIZ / c).is_file() and (RAIZ / c).suffix.lower() in TEXTO)


def _ler(caminho: str) -> str:
    return (RAIZ / caminho).read_text(encoding="utf-8", errors="replace")


def _trecho(texto: str, posicao: int) -> str:
    return texto[max(0, posicao - 40) : posicao + 40].replace("\n", " ")


def test_ha_arquivos_para_varrer():
    versionados = _versionados()
    for esperado in ("README.md", "analise.ipynb", "reports/resultados.json", "src/trafego_decisao/parametros.py"):
        assert esperado in versionados
    assert not [c for c in versionados if c.startswith("data/privado/")], "a pasta privada não pode ser versionada"


def test_nenhum_arquivo_versionado_tem_valor_em_moeda():
    achados = []
    for caminho in _versionados():
        texto = _ler(caminho)
        achados += [f"{caminho}: ...{_trecho(texto, m.start())}..." for m in MOEDA_COM_NUMERO.finditer(texto)]
    assert not achados, "valor em moeda em arquivo versionado:\n" + "\n".join(achados[:20])


def test_nenhum_arquivo_publicado_traz_a_posicao_de_preco():
    """Mesmo em índice, a posição do preço entre concorrentes deixa deduzir o preço do produto.

    Vale para todo arquivo versionado (README, notebook, resultados.json, código) e para os PNG:
    a figura de preço não pode voltar. Os próprios arquivos de teste ficam de fora porque contêm o padrão.
    """
    achados = []
    for caminho in _versionados():
        if caminho.startswith("tests/"):
            continue
        texto = _ler(caminho)
        achados += [f"{caminho}: ...{_trecho(texto, m.start())}..." for m in POSICAO_DE_PRECO.finditer(texto)]
    assert not achados, "posição de preço em arquivo versionado:\n" + "\n".join(achados[:20])
    assert not (RAIZ / "reports" / "figuras" / "preco_concorrentes.png").exists()


def test_readme_e_notebook_estao_cobertos_pelo_guarda():
    """README e notebook são os arquivos que mais mudam à mão: confere que entram na varredura e passam limpos."""
    for caminho in ("README.md", "analise.ipynb"):
        assert caminho in _versionados()
        texto = _ler(caminho)
        assert not MOEDA_COM_NUMERO.search(texto), caminho
        assert not POSICAO_DE_PRECO.search(texto), caminho


def test_nome_do_produto_aparece_no_maximo_uma_vez():
    total = sum(_ler(caminho).count(NOME_DO_PRODUTO) for caminho in _versionados())
    assert total <= 1


def test_nenhum_arquivo_versionado_tem_valor_ou_termo_da_lista_privada():
    if not LISTA_PRIVADA.exists():
        pytest.skip("lista privada ausente (clone público): a varredura de valores e termos do negócio só roda na máquina do autor")
    lista = json.loads(LISTA_PRIVADA.read_text(encoding="utf-8"))
    valores = [re.compile(r"(?<![\d.,])" + re.escape(v) + r"(?!\d)") for v in lista["valores"]]
    termos = [re.compile(t, re.IGNORECASE) for t in lista["termos"]]
    achados = []
    for caminho in _versionados():
        texto = _ler(caminho)
        padroes = termos if caminho in SEM_VARREDURA_DE_VALORES else termos + valores
        for padrao in padroes:
            achados += [f"{caminho}: ...{_trecho(texto, m.start())}..." for m in padrao.finditer(texto)]
    assert not achados, "valor ou termo do negócio em arquivo versionado:\n" + "\n".join(achados[:30])


def test_nenhuma_figura_tem_texto_com_moeda():
    """Monta as quatro figuras com os parâmetros de exemplo e lê todo texto desenhado nelas."""
    p = parametros.carregar(parametros.EXEMPLO)
    ptax = analise.carregar_cambio()
    equilibrio = economia.sobra_de_referencia(p, ptax)
    sorteio = economia.sortear_cenarios(p, ptax, n=5_000)
    desenho = analise.desenho_do_teste(p)
    corte, _ = analise.curvas_de_corte(p, equilibrio)
    figuras = [
        graficos.fronteira_de_equilibrio(
            analise.fronteira(p, equilibrio, sorteio),
            analise.cenarios_de_referencia(p, equilibrio),
            analise.resumo_dos_cenarios(p, sorteio)["fracao_que_se_paga"],
        ),
        graficos.sensibilidade(analise.sensibilidade(p, ptax)),
        graficos.curvas_de_corte(corte, p.indice(equilibrio), desenho),
        graficos.curvas_de_escala(analise.curvas_de_escala(p), p.indice(equilibrio), desenho),
    ]
    try:
        for figura in figuras:
            figura.canvas.draw()  # preenche os rótulos dos eixos
            textos = [t.get_text() for t in figura.findobj(Text)]
            assert len(textos) > 5
            com_moeda = [t for t in textos if "$" in t or MOEDA_COM_NUMERO.search(t)]
            assert not com_moeda, com_moeda
            com_preco = [t for t in textos if POSICAO_DE_PRECO.search(t)]
            assert not com_preco, com_preco
    finally:
        for figura in figuras:
            plt.close(figura)
