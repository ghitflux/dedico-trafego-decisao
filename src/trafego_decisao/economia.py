"""Economia de uma venda: quanto sobra para pagar mídia e quanto custa trazer o comprador.

As funções deste módulo trabalham em moeda, com os parâmetros recebidos. A conversão para a
escala publicada (meta de CAC = 100) é feita em `analise.py`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trafego_decisao.parametros import Parametros

MIDIA = ("cpc", "conv_clique")


def sobra_para_midia(
    p: Parametros,
    *,
    extras,
    imposto,
    reembolso,
    fracao_pix,
    cambio,
    conv_demo,
    custo_demo_perdida_usd=None,
):
    """Margem de contribuição por pedido antes da mídia.

    Receita menos taxa de pagamento, imposto, custo de entrega do pedido e custo das
    demonstrações grátis que não viraram compra. Para cada compra há (1 / conv_demo - 1)
    demonstrações de quem experimentou e foi embora, e quem paga essa conta é quem comprou.
    Aceita números ou vetores (para o sorteio de cenários).
    """
    if custo_demo_perdida_usd is None:
        custo_demo_perdida_usd = p.custo_demo_perdida_usd
    ticket = p.preco + extras
    receita = ticket * (1 - reembolso)
    taxa_cartao = ticket * p.taxa_cartao_pct + p.taxa_cartao_fixa
    taxa_pix = ticket * p.taxa_pix_pct
    taxa_pagamento = fracao_pix * taxa_pix + (1 - fracao_pix) * taxa_cartao
    entrega = cambio * p.custo_venda_usd
    demos_perdidas = cambio * custo_demo_perdida_usd * (1 / conv_demo - 1)
    return receita - taxa_pagamento - imposto * receita - entrega - demos_perdidas


def cac(*, cpc, conv_clique):
    """Custo de aquisição por compra: custo do clique dividido pela conversão do clique."""
    return cpc / conv_clique


def lucro_por_venda(p: Parametros, **entradas):
    """Sobra para mídia menos o custo de aquisição."""
    midia = {k: entradas.pop(k) for k in MIDIA}
    return sobra_para_midia(p, **entradas) - cac(**midia)


def faixa_do_cambio(p: Parametros, ptax: pd.Series) -> tuple[float, float, float]:
    """Mínimo, último valor e máximo do dólar efetivo (cotação oficial com o acréscimo) no período."""
    efetivo = ptax * p.fator_cambio
    return float(efetivo.min()), float(efetivo.iloc[-1]), float(efetivo.max())


def sobra_de_referencia(p: Parametros, ptax: pd.Series | None = None) -> float:
    """Sobra para mídia com os valores-base: é o CAC de empate que as regras devem proteger.

    Com a série de câmbio, usa o dólar efetivo mais recente em vez do valor-base.
    """
    valores = {k: v for k, v in p.valores_base().items() if k not in MIDIA}
    if ptax is not None:
        valores["cambio"] = faixa_do_cambio(p, ptax)[1]
    return float(sobra_para_midia(p, **valores))


def precisao_do_cac(dias: list[int], cac_real: float, verba_dia: float) -> pd.DataFrame:
    """Faixa de 90% do CAC observado depois de alguns dias de teste, para um CAC real dado.

    As vendas somadas seguem Poisson; a faixa do CAC é o gasto dividido pelos quantis das vendas.
    Mostra quanto tempo de teste é preciso para o CAC observado deixar de ser palpite.
    """
    from scipy import stats

    linhas = []
    for d in dias:
        gasto = verba_dia * d
        esperadas = gasto / cac_real
        poucas, muitas = stats.poisson.ppf([0.05, 0.95], esperadas)
        linhas.append(
            {
                "dias": d,
                "vendas esperadas": esperadas,
                "CAC observado mínimo": gasto / muitas,
                "CAC observado máximo": gasto / max(poucas, 1),
            }
        )
    return pd.DataFrame(linhas).set_index("dias")


def sortear_cenarios(p: Parametros, ptax: pd.Series, n: int = 100_000, semente: int = 42) -> pd.DataFrame:
    """Sorteia cenários: uniforme dentro da faixa de cada entrada; câmbio reamostrado da série real.

    Uniforme é a escolha de quem não tem dado: todo valor da faixa é tratado como igualmente
    plausível. O resultado depende das faixas escolhidas.
    """
    gerador = np.random.default_rng(semente)
    cenarios = {
        nome: gerador.uniform(entrada.baixo, entrada.alto, n)
        for nome, entrada in p.entradas.items()
        if nome != "cambio"
    }
    cenarios["cambio"] = gerador.choice(ptax.to_numpy() * p.fator_cambio, size=n, replace=True)
    df = pd.DataFrame(cenarios)
    df["sobra"] = sobra_para_midia(p, **{k: df[k] for k in df.columns if k not in MIDIA})
    df["cac"] = cac(cpc=df["cpc"], conv_clique=df["conv_clique"])
    df["lucro"] = df["sobra"] - df["cac"]
    return df


def sensibilidade(p: Parametros, ptax: pd.Series) -> pd.DataFrame:
    """Efeito de cada entrada, isolada, no lucro por venda (as outras ficam no valor-base).

    Responde "qual número vale a pena medir primeiro": o de maior amplitude.
    """
    base = p.valores_base()
    baixo_cambio, atual, alto_cambio = faixa_do_cambio(p, ptax)
    base["cambio"] = atual
    lucro_base = lucro_por_venda(p, **base)
    linhas = []
    for nome, entrada in p.entradas.items():
        baixo, alto = (baixo_cambio, alto_cambio) if nome == "cambio" else (entrada.baixo, entrada.alto)
        extremos = [lucro_por_venda(p, **{**base, nome: valor}) for valor in (baixo, alto)]
        linhas.append(
            {
                "entrada": entrada.rotulo,
                "origem": entrada.origem,
                "lucro no pior extremo": min(extremos),
                "lucro no melhor extremo": max(extremos),
                "amplitude": max(extremos) - min(extremos),
            }
        )
    tabela = pd.DataFrame(linhas).set_index("entrada").sort_values("amplitude", ascending=False)
    tabela.attrs["lucro_base"] = lucro_base
    return tabela
