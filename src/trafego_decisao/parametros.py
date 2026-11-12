"""Parâmetros do modelo, lidos de um arquivo JSON. Nenhum valor do negócio fica no código.

Ordem de busca:
1. `data/privado/parametros.json`: os valores reais. A pasta está no `.gitignore` e não é publicada.
2. `data/parametros_exemplo.json`: valores FICTÍCIOS, versionados, só para o código rodar.

Os dois arquivos estão em moeda. Nada sai do pacote em moeda: toda tabela e toda figura passam
por `Parametros.indice`, que divide pela meta de CAC e multiplica por 100. Na escala publicada,
a meta de CAC vale 100 e o resto (CAC de empate, lucro por venda, gasto) é lido contra ela.

Origem possível de cada entrada incerta:
- "medido": observado diretamente.
- "publicado": número de tabela pública, ainda a confirmar.
- "premissa": não há dado; a faixa vai do pior ao melhor caso considerado plausível.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PRIVADO = RAIZ / "data" / "privado" / "parametros.json"
EXEMPLO = RAIZ / "data" / "parametros_exemplo.json"

ROTULOS = {
    "cpc": "Custo por clique",
    "conv_clique": "Conversão de clique em compra",
    "conv_demo": "Demonstrações que viram compra",
    "extras": "Receita de extras por pedido",
    "imposto": "Imposto sobre a receita",
    "reembolso": "Pedidos reembolsados",
    "fracao_pix": "Pedidos pagos por Pix",
    "cambio": "Dólar efetivo",
}


@dataclass(frozen=True)
class Entrada:
    """Uma entrada incerta: valor-base e faixa plausível."""

    rotulo: str
    base: float
    baixo: float
    alto: float
    origem: str


@dataclass(frozen=True)
class Parametros:
    fonte: str  # "privado" ou "exemplo"
    preco: float
    taxa_cartao_pct: float
    taxa_cartao_fixa: float
    taxa_pix_pct: float
    custo_venda_usd: float  # custo variável de entregar um pedido, cobrado em dólar
    custo_demo_perdida_usd: float  # custo de uma demonstração grátis que não virou compra
    fator_cambio: float  # acréscimo sobre a cotação oficial (imposto e spread da compra em dólar)
    meta_cac: float
    verba_teste_dia: float  # gasto diário da conta no período de teste
    verba_criativo_dia: float  # gasto diário de um criativo no período de teste
    dias_teste: int
    entradas: dict[str, Entrada]
    cenarios: dict[str, tuple[float, float]]  # nome -> (custo por clique, conversão de clique em compra)
    conferencia: tuple[dict, ...]

    def indice(self, valor):
        """Converte um valor em moeda para a escala publicada, em que a meta de CAC vale 100."""
        return valor * 100.0 / self.meta_cac

    def valores_base(self) -> dict[str, float]:
        return {nome: entrada.base for nome, entrada in self.entradas.items()}


def carregar(caminho: Path | str | None = None) -> Parametros:
    """Lê os parâmetros. Sem caminho, usa o arquivo privado se existir e o de exemplo se não existir."""
    if caminho is None:
        caminho = PRIVADO if PRIVADO.exists() else EXEMPLO
    caminho = Path(caminho)
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    fonte = "exemplo" if caminho.resolve() == EXEMPLO.resolve() else "privado"
    entradas = {
        nome: Entrada(ROTULOS[nome], float(e["base"]), float(e["baixo"]), float(e["alto"]), e["origem"])
        for nome, e in bruto["entradas"].items()
    }
    return Parametros(
        fonte=fonte,
        preco=float(bruto["preco"]),
        taxa_cartao_pct=float(bruto["taxa_cartao_pct"]),
        taxa_cartao_fixa=float(bruto["taxa_cartao_fixa"]),
        taxa_pix_pct=float(bruto["taxa_pix_pct"]),
        custo_venda_usd=float(bruto["custo_venda_usd"]),
        custo_demo_perdida_usd=float(bruto["custo_demo_perdida_usd"]),
        fator_cambio=float(bruto["fator_cambio"]),
        meta_cac=float(bruto["meta_cac"]),
        verba_teste_dia=float(bruto["verba_teste_dia"]),
        verba_criativo_dia=float(bruto["verba_canal_dia"]) / int(bruto["criativos_no_teste"]),
        dias_teste=int(bruto["dias_teste"]),
        entradas=entradas,
        cenarios={nome: (float(cpc), float(conv)) for nome, (cpc, conv) in bruto["cenarios"].items()},
        conferencia=tuple(bruto.get("conferencia", [])),
    )


def aviso_da_fonte(p: Parametros) -> str:
    """Uma linha dizendo com que parâmetros a análise rodou."""
    if p.fonte == "privado":
        return "Parâmetros: arquivo privado (valores reais). Tudo abaixo está na escala em que a meta de CAC vale 100."
    return (
        "AVISO: rodando com data/parametros_exemplo.json, que tem valores FICTÍCIOS (o arquivo privado não "
        "existe ou não foi pedido). Os resultados servem para conferir o código, não reproduzem os publicados."
    )
