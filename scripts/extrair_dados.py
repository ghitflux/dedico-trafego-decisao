"""Atualiza o único dado externo do projeto: a cotação diária do dólar (PTAX venda) dos últimos
12 meses, do Banco Central, em data/cambio_ptax.csv. É dado público e é versionado.

Uso:
    python scripts/extrair_dados.py
"""

from __future__ import annotations

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
    n = baixar_cambio()
    print(f"cambio_ptax.csv: {n} cotações")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
