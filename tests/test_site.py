"""Forma do bloco `para_o_site` publicado em reports/resultados.json."""

import json
import re

import pytest

from trafego_decisao import parametros

IDIOMAS = ("pt", "en", "es")
TIPOS = {"linhas", "barras", "pontos"}
PAPEIS = {"principal", "base", "alternativa", "neutro"}
FORMATOS = {"numero", "percentual", "data"}


@pytest.fixture(scope="module")
def bloco():
    resultados = json.loads((parametros.RAIZ / "reports" / "resultados.json").read_text(encoding="utf-8"))
    return resultados["para_o_site"]


def _tres_idiomas(valor) -> bool:
    return isinstance(valor, dict) and all(isinstance(valor.get(i), str) and valor[i].strip() for i in IDIOMAS)


def _conferir_grafico(g: dict, exige_leitura: bool) -> None:
    assert g["tipo"] in TIPOS
    for campo in ("titulo", "eixo_x", "eixo_y"):
        assert _tres_idiomas(g[campo]), campo
    assert all(len(g["titulo"][i]) <= 90 for i in IDIOMAS), g["titulo"]["pt"]
    if exige_leitura:
        assert _tres_idiomas(g.get("leitura")), "leitura"
    assert g["formato_x"] in FORMATOS and g["formato_y"] in FORMATOS
    assert 1 <= len(g["series"]) <= 4
    limite = 300 if g["tipo"] == "pontos" else 80
    for serie in g["series"]:
        assert _tres_idiomas(serie["nome"])
        assert serie["papel"] in PAPEIS
        assert 1 <= len(serie["pontos"]) <= limite
        for ponto in serie["pontos"]:
            assert len(ponto) == 2 and isinstance(ponto[1], (int, float))
            assert isinstance(ponto[0], str) if g["tipo"] == "barras" else isinstance(ponto[0], (int, float))
        if "rotulos" in serie:
            assert all(len(serie["rotulos"][i]) == len(serie["pontos"]) for i in IDIOMAS)
    if "faixa" in g:
        assert g["tipo"] == "linhas" and 0 <= g["faixa"]["serie"] < len(g["series"])


def test_textos_do_bloco_nos_tres_idiomas(bloco):
    for campo in ("numero_chave", "pergunta", "resultado", "detalhe", "dados"):
        assert _tres_idiomas(bloco[campo]), campo
    assert len(bloco["numero_chave"]["pt"]) <= 14


def test_grafico_principal(bloco):
    _conferir_grafico(bloco["grafico"], exige_leitura=False)


def test_graficos_extras(bloco):
    extras = bloco["graficos_extras"]
    assert 3 <= len(extras) <= 5
    for grafico in extras:
        _conferir_grafico(grafico, exige_leitura=True)


def test_bloco_do_site_nao_traz_a_posicao_de_preco(bloco):
    """Mesmo em índice, a posição de preço permite deduzir o preço do produto: não vai ao site."""
    titulos = " ".join(g["titulo"]["pt"] for g in [bloco["grafico"], *bloco["graficos_extras"]])
    assert not re.search(r"pre[cç]o", titulos, re.IGNORECASE)
    assert "mediana do mercado" not in json.dumps(bloco, ensure_ascii=False)


def test_bloco_do_site_sem_moeda(bloco):
    texto = json.dumps(bloco, ensure_ascii=False)
    assert not re.search(r"(?:R|US|U)\$|\breais\b|\bBRL\b|\bUSD\b", texto)
