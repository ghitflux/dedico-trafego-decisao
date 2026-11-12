"""Atualiza os dados de entrada do projeto.

1. data/cambio_ptax.csv: cotação diária do dólar (PTAX venda) dos últimos 12 meses, do Banco
   Central. É dado público e é versionado.
2. data/privado/concorrentes_precos.csv: extrato do levantamento de preços de concorrentes,
   sem nome de marca. Fica na pasta privada, fora do git: o repositório publica só a posição
   relativa do preço (percentil e razão para a mediana), nunca os preços individuais.

Uso:
    python scripts/extrair_dados.py                       # só o câmbio
    python scripts/extrair_dados.py "CAMINHO/levantamento.json"   # câmbio e concorrentes
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

DADOS = Path(__file__).resolve().parents[1] / "data"
URL_PTAX = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarPeriodo(dataInicial=@i,dataFinalCotacao=@f)"
)


def extrair_concorrentes(caminho: Path) -> int:
    """Lê o levantamento (lista `marcas`, cada uma com país, status e preço) e grava o extrato anônimo."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    linhas = []
    for i, marca in enumerate(dados["marcas"], start=1):
        preco = marca.get("preco") or {}
        linhas.append(
            {
                "concorrente": f"Concorrente {i:02d}",
                "pais": "BR" if str(marca.get("pais", "")).startswith("BR") else str(marca.get("pais")),
                "ativo": "sim" if str(marca.get("status", "")).startswith("ativo") else "nao",
                "moeda": str(preco.get("moeda") or "")[:3],
                "preco_principal": (preco.get("principal_centavos") or 0) / 100 or "",
            }
        )
    pasta = DADOS / "privado"
    pasta.mkdir(parents=True, exist_ok=True)
    with (pasta / "concorrentes_precos.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)
    return len(linhas)


def baixar_cambio(dias: int = 365) -> int:
    fim = date.today()
    inicio = fim - timedelta(days=dias)
    parametros = {
        "@i": f"'{inicio:%m-%d-%Y}'",
        "@f": f"'{fim:%m-%d-%Y}'",
        "$top": "500",
        "$format": "json",
        "$select": "cotacaoVenda,dataHoraCotacao",
    }
    url = f"{URL_PTAX}?{urllib.parse.urlencode(parametros, quote_via=urllib.parse.quote)}"
    requisicao = urllib.request.Request(url, headers={"User-Agent": "portfolio-dados/0.1"})
    with urllib.request.urlopen(requisicao, timeout=90) as resposta:
        valores = json.loads(resposta.read())["value"]
    DADOS.mkdir(exist_ok=True)
    with (DADOS / "cambio_ptax.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["data", "dolar_venda"])
        for v in valores:
            escritor.writerow([v["dataHoraCotacao"][:10], v["cotacaoVenda"]])
    return len(valores)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("concorrentes", nargs="?", help="caminho do JSON do levantamento de concorrentes")
    a = parser.parse_args()
    if a.concorrentes:
        n = extrair_concorrentes(Path(a.concorrentes))
        print(f"data/privado/concorrentes_precos.csv: {n} marcas")
    n = baixar_cambio()
    print(f"cambio_ptax.csv: {n} cotações")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
