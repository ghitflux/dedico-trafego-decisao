"""Figuras do projeto, todas em unidades relativas (meta de CAC = 100, ou a referência dita no eixo).

A cor segue a entidade: laranja é sempre a regra mais simples, azul a alternativa recomendada.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.ticker import PercentFormatter

from trafego_decisao.estilo import (
    APAGADO,
    AQUA,
    AZUL,
    EIXO,
    ESTILO,
    LARANJA,
    RAMPA_AZUL,
    TINTA,
    TINTA_SECUNDARIA,
    nova_figura,
    numero,
    percentual,
)

META = 100.0


def preco_entre_concorrentes(resumo: dict[str, float]) -> Figure:
    """Faixa do mercado em relação à mediana, com a posição do preço do produto."""
    preco = resumo["preço (mediana do mercado = 100)"]
    lado = "abaixo" if preco < 100 else "acima"
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            f"O preço do produto fica {lado} da mediana do mercado",
            f"Preço de {resumo['concorrentes com preço']} concorrentes, com a mediana valendo 100. "
            "Faixa clara: de p10 a p90. Faixa escura: metade central.",
            altura=2.9,
        )
        fig.subplots_adjust(left=0.04, bottom=0.26, top=0.68)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.plot([resumo["p10 do mercado"], resumo["p90 do mercado"]], [0, 0], color=RAMPA_AZUL[0], linewidth=9, solid_capstyle="butt", zorder=2)
        ax.plot([resumo["p25 do mercado"], resumo["p75 do mercado"]], [0, 0], color=AZUL, linewidth=9, solid_capstyle="butt", zorder=3)
        ax.plot([100, 100], [-0.28, 0.28], color=TINTA_SECUNDARIA, linewidth=1.2, zorder=4)
        ax.annotate("mediana", (100, -0.34), ha="center", va="top", color=TINTA_SECUNDARIA, fontsize=8.5)
        ax.plot([preco, preco], [-0.28, 0.42], color=TINTA, linewidth=2, zorder=5)
        ax.annotate(f"produto: {numero(preco, 0)}", (preco, 0.50), ha="center", va="bottom", color=TINTA, fontsize=9.5)
        ax.set_yticks([])
        ax.set_ylim(-0.8, 1.0)
        ax.set_xlim(0, max(resumo["p90 do mercado"], preco) * 1.08)
        ax.set_xlabel("preço em relação à mediana do mercado (mediana = 100)")
        return fig


def fronteira_de_equilibrio(geometria: dict[str, float], cenarios: pd.DataFrame, fracao_que_se_paga: float) -> Figure:
    """Onde a primeira compra paga a mídia, em eixos relativos às pontas das faixas."""
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            f"Só {percentual(fracao_que_se_paga, 1)} dos cenários sorteados se pagam na primeira compra",
            "Abaixo de cada linha, a primeira compra paga a mídia. O retângulo é a faixa considerada de clique e conversão.",
        )
        ax.grid(axis="x", visible=True)
        x_min, y_max = geometria["conversao_minima"], geometria["cpc_maximo"]
        x_borda = (100 - x_min) * 0.2
        x_lim = (x_min - x_borda, 100 + x_borda)
        y_lim = (100 - (y_max - 100) * 0.22, y_max + (y_max - 100) * 0.10)
        x = np.linspace(*x_lim, 50)
        ax.add_patch(Rectangle((x_min, 100), 100 - x_min, y_max - 100, facecolor="none", edgecolor=EIXO, linewidth=1.2, zorder=1))
        referencia = geometria["inclinacao_margem_de_referencia"]
        series = [
            ("empate com a margem de referência", referencia, AZUL),
            ("empate com a margem mediana dos cenários", geometria["inclinacao_margem_mediana"], RAMPA_AZUL[0]),
        ]
        for nome, inclinacao, cor in series:
            ax.plot(x, inclinacao * x, color=cor, label=nome, zorder=3)
        dentro = np.linspace(x_min, 100, 50)
        ax.fill_between(dentro, 100, np.clip(referencia * dentro, 100, y_max), color=AZUL, alpha=0.10, linewidth=0, zorder=1)
        for nome, linha in cenarios.iterrows():
            ponto = (linha["conversão (teto da faixa = 100)"], linha["custo por clique (piso da faixa = 100)"])
            ax.plot(*ponto, "o", color=TINTA_SECUNDARIA, zorder=4)
            ax.annotate(f"{nome}", ponto, xytext=(8, 0), textcoords="offset points", va="center", color=TINTA_SECUNDARIA, fontsize=9)
        ax.annotate("não se paga", (x_min + (100 - x_min) * 0.28, 100 + (y_max - 100) * 0.80), color=TINTA_SECUNDARIA, fontsize=9.5, ha="center", va="center")
        ax.set_xlim(*x_lim)
        ax.set_ylim(*y_lim)
        ax.set_xlabel("conversão de clique em compra (teto da faixa = 100)")
        ax.set_ylabel("custo por clique (piso da faixa = 100)")
        ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.19), ncol=2, fontsize=9, borderaxespad=0)
        fig.subplots_adjust(bottom=0.25, right=0.97)
        return fig


def sensibilidade(tabela: pd.DataFrame) -> Figure:
    """Faixas horizontais: quanto o lucro por venda muda quando só uma entrada varia."""
    primeira, segunda = tabela.index[:2]
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            f"{primeira} e {segunda.lower()} decidem o lucro por venda",
            "Lucro por venda (meta de CAC = 100) quando só uma entrada percorre a sua faixa e as outras ficam no valor-base.",
        )
        fig.subplots_adjust(left=0.33, right=0.95, bottom=0.16)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ordem = tabela.sort_values("amplitude")
        base = tabela.attrs["lucro_base"]
        for y, (_, linha) in enumerate(ordem.iterrows()):
            ax.plot([linha["lucro no pior extremo"], linha["lucro no melhor extremo"]], [y, y], color=AZUL, linewidth=7, solid_capstyle="round", zorder=3)
            ax.annotate(numero(linha["amplitude"], 0), (linha["lucro no pior extremo"], y), xytext=(-9, 0), textcoords="offset points", ha="right", va="center", color=TINTA_SECUNDARIA, fontsize=9)
        ax.axvline(base, color=EIXO, linewidth=1.2, zorder=2)
        ax.annotate(f"base: {numero(base, 0).replace('-', '−')}", (base, len(ordem) - 0.35), xytext=(-5, 0), textcoords="offset points", ha="right", color=APAGADO, fontsize=8.5)
        ax.axvline(0, color=TINTA_SECUNDARIA, linewidth=1, zorder=2)
        ax.annotate("empate", (0, -0.75), xytext=(4, 0), textcoords="offset points", color=TINTA_SECUNDARIA, fontsize=8.5, va="center")
        ax.set_yticks(range(len(ordem)), list(ordem.index))
        ax.set_ylim(-1.1, len(ordem) - 0.1)
        pior, melhor = tabela["lucro no pior extremo"].min(), max(tabela["lucro no melhor extremo"].max(), 0)
        ax.set_xlim(pior - 0.20 * (melhor - pior), melhor + 0.11 * (melhor - pior))
        ax.set_xlabel("lucro por venda (meta de CAC = 100); o número à esquerda de cada faixa é a amplitude")
        return fig


def _curvas(ax, curvas: pd.DataFrame, cores: dict[str, str], destaque: str) -> None:
    for nome in curvas.columns:
        ax.plot(curvas.index, curvas[nome], color=cores[nome], label=nome, zorder=4 if nome == destaque else 3)


def _marcar_meta(ax, equilibrio: float, topo: float = 1.0) -> None:
    """Linhas verticais na meta (100) e no CAC de empate, com o rótulo do lado de fora de cada uma."""
    empate_a_direita = equilibrio >= META
    ax.axvline(META, color=EIXO, linewidth=1.2, zorder=1)
    ax.annotate("meta\n100", (META, topo), xytext=(-5 if empate_a_direita else 5, -2), textcoords="offset points", ha="right" if empate_a_direita else "left", va="top", color=APAGADO, fontsize=8.5)
    ax.axvline(equilibrio, color=EIXO, linewidth=1.2, zorder=1)
    ax.annotate(f"empate\n{numero(equilibrio, 0)}", (equilibrio, topo), xytext=(5 if empate_a_direita else -5, -2), textcoords="offset points", ha="left" if empate_a_direita else "right", va="top", color=APAGADO, fontsize=8.5)


def curvas_de_corte(curvas: pd.DataFrame, equilibrio: float, desenho: dict[str, float]) -> Figure:
    """Probabilidade de um criativo ser desligado no teste, conforme o CAC real dele."""
    na_meta = curvas.loc[100]
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            f"Um corte por limiar desliga {percentual(na_meta.iloc[0])} dos criativos que estão exatamente na meta",
            f"Chance de um criativo ser desligado em {desenho['dias de teste']} dias de teste, conforme o CAC real dele (meta = 100).",
        )
        fig.subplots_adjust(bottom=0.26)
        cores = dict(zip(curvas.columns, [LARANJA, AQUA, AZUL]))
        _curvas(ax, curvas, cores, curvas.columns[-1])
        _marcar_meta(ax, equilibrio)
        for nome, deslocamento in zip(curvas.columns, [(-8, 6), (-8, 6), (8, -10)]):
            ax.plot(META, na_meta[nome], "o", color=cores[nome], zorder=5)
            ax.annotate(percentual(na_meta[nome]), (META, na_meta[nome]), xytext=deslocamento, textcoords="offset points", ha="right" if deslocamento[0] < 0 else "left", color=TINTA, fontsize=9.5)
        ax.set_xlim(curvas.index.min(), 300)
        ax.set_ylim(0, 1.0)
        ax.set_xlabel("CAC real do criativo (meta = 100): à esquerda os bons, à direita os ruins")
        ax.set_ylabel("chance de ser desligado")
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=3, fontsize=9)
        return fig


def curvas_de_escala(curvas: pd.DataFrame, equilibrio: float, desenho: dict[str, float], destaque: int = 90) -> Figure:
    """Probabilidade de a regra liberar a escala, conforme o CAC real da operação."""
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            "Somar o período inteiro separa operação boa de ruim melhor do que exigir dias seguidos",
            f"Chance de cada regra liberar a escala ao fim de {desenho['dias de teste']} dias de teste, conforme o CAC real da operação (meta = 100).",
        )
        fig.subplots_adjust(bottom=0.26)
        cores = dict(zip(curvas.columns, [LARANJA, AQUA, AZUL]))
        _curvas(ax, curvas, cores, curvas.columns[-1])
        _marcar_meta(ax, equilibrio, topo=0.50)
        ax.axvline(destaque, color=EIXO, linewidth=1.2, zorder=1)
        no_ponto = curvas.loc[destaque]
        for nome in (curvas.columns[0], curvas.columns[-1]):
            ax.plot(destaque, no_ponto[nome], "o", color=cores[nome], zorder=5)
            ax.annotate(percentual(no_ponto[nome]), (destaque, no_ponto[nome]), xytext=(-9, -3), textcoords="offset points", ha="right", va="top", color=TINTA, fontsize=9.5)
        ax.annotate(f"CAC real de {destaque}:\n10% abaixo da meta", (destaque, 0.08), xytext=(-9, 0), textcoords="offset points", ha="right", va="center", color=TINTA_SECUNDARIA, fontsize=8.5)
        ax.set_xlim(curvas.index.min(), curvas.index.max())
        ax.set_ylim(0, 1.02)
        ax.set_xlabel("CAC real da operação (meta = 100)")
        ax.set_ylabel("chance de liberar a escala")
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=3, fontsize=9)
        return fig
