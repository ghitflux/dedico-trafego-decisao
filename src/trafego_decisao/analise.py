"""Orquestra a análise. Cada função devolve uma tabela usada no notebook e no README.

Tudo que sai daqui está na escala publicada: valores em moeda viram índice com a meta de CAC
valendo 100 (`Parametros.indice`), e o que não é moeda aparece como fração, razão ou contagem.
"""

from __future__ import annotations

from functools import partial

import numpy as np
import pandas as pd

from trafego_decisao import consultas, economia, regras, simulador
from trafego_decisao.parametros import RAIZ, Parametros

DADOS = RAIZ / "data"
# CAC real dos criativos e das operações simuladas, na escala em que a meta vale 100.
INDICES_CORTE = [50, 60, 70, 80, 90, 100, 110, 125, 150, 175, 200, 250, 300, 400]
INDICES_ESCALA = list(range(60, 155, 5))
EIXO_CAC = "CAC real (meta = 100)"

# Grades da análise de sensibilidade das regras.
GRADE_K_SEM_VENDA = (1.5, 2.0, 3.0, 4.0)
GRADE_K_CAC = (1.25, 1.5, 2.0, 3.0)
GRADE_K_PISO = (0.0, 2.0, 3.0, 4.0, 6.0, 8.0)
GRADE_N_DIAS = (2, 3, 4, 5, 6, 7)


def _cacs(p: Parametros, indices) -> np.ndarray:
    """Converte a grade em índice para a moeda dos parâmetros (arredondada, para não carregar erro de ponto flutuante)."""
    return np.round(np.asarray(indices, dtype=float) / 100.0 * p.meta_cac, 9)


def carregar_cambio() -> pd.Series:
    return pd.read_csv(DADOS / "cambio_ptax.csv")["dolar_venda"]


# --------------------------------------------------------------------------- economia


def conferir_modelo(p: Parametros) -> pd.DataFrame:
    """A função de margem reproduz contas de referência feitas à parte? Devolve só o desvio relativo."""
    linhas = []
    for item in p.conferencia:
        extra = {k: item[k] for k in ("custo_demo_perdida_usd",) if k in item}
        modelo = economia.sobra_para_midia(p, **item["entradas"], **extra)
        linhas.append({"conta": item["conta"], "desvio do modelo": modelo / item["esperado"] - 1})
    return pd.DataFrame(linhas).set_index("conta")


def cenarios_de_referencia(p: Parametros, sobra: float) -> pd.DataFrame:
    """Os cenários de mídia de referência, do melhor ao pior, em termos relativos."""
    cpc, conv = p.entradas["cpc"], p.entradas["conv_clique"]
    linhas = []
    for nome, (custo_clique, conversao) in p.cenarios.items():
        cac = custo_clique / conversao
        linhas.append(
            {
                "cenário": nome,
                "CAC (meta = 100)": p.indice(cac),
                "CAC ÷ CAC de empate": cac / sobra,
                "lucro por venda (meta = 100)": p.indice(sobra - cac),
                "custo por clique (piso da faixa = 100)": 100 * custo_clique / cpc.baixo,
                "conversão (teto da faixa = 100)": 100 * conversao / conv.alto,
            }
        )
    return pd.DataFrame(linhas).set_index("cenário")


def fronteira(p: Parametros, sobra: float, sorteio: pd.DataFrame) -> dict[str, float]:
    """Geometria da fronteira de empate em eixos relativos.

    Eixo x: conversão de clique em compra, com o teto da faixa valendo 100.
    Eixo y: custo por clique, com o piso da faixa valendo 100.
    Nessa escala a fronteira é a reta y = inclinação * x; abaixo dela a primeira compra paga a mídia.
    """
    cpc, conv = p.entradas["cpc"], p.entradas["conv_clique"]
    fator = conv.alto / cpc.baixo
    return {
        "conversao_minima": 100 * conv.baixo / conv.alto,
        "cpc_maximo": 100 * cpc.alto / cpc.baixo,
        "inclinacao_margem_de_referencia": sobra * fator,
        "inclinacao_margem_mediana": float(sorteio["sobra"].median()) * fator,
    }


def resumo_dos_cenarios(p: Parametros, sorteio: pd.DataFrame) -> dict[str, float]:
    """Leitura do sorteio de cenários: quanto do espaço plausível se paga na primeira compra."""
    return {
        "cenarios": int(len(sorteio)),
        "fracao_que_se_paga": float((sorteio["lucro"] > 0).mean()),
        "fracao_com_cac_na_meta": float((sorteio["cac"] <= p.meta_cac).mean()),
        "cac_mediano": float(p.indice(sorteio["cac"].median())),
        "sobra_mediana": float(p.indice(sorteio["sobra"].median())),
        "sobra_p5": float(p.indice(sorteio["sobra"].quantile(0.05))),
        "sobra_p95": float(p.indice(sorteio["sobra"].quantile(0.95))),
        "lucro_mediano": float(p.indice(sorteio["lucro"].median())),
    }


def sensibilidade(p: Parametros, ptax: pd.Series) -> pd.DataFrame:
    """Sensibilidade do lucro por venda a cada entrada, na escala publicada."""
    tabela = economia.sensibilidade(p, ptax)
    for coluna in ("lucro no pior extremo", "lucro no melhor extremo", "amplitude"):
        tabela[coluna] = p.indice(tabela[coluna])
    tabela["amplitude ÷ maior amplitude"] = tabela["amplitude"] / tabela["amplitude"].max()
    tabela.attrs["lucro_base"] = float(p.indice(tabela.attrs["lucro_base"]))
    return tabela


def precisao_do_cac(p: Parametros, dias: list[int]) -> pd.DataFrame:
    """Faixa de 90% do CAC observado para uma operação que está exatamente na meta."""
    tabela = economia.precisao_do_cac(dias, p.meta_cac, p.verba_teste_dia)
    for coluna in ("CAC observado mínimo", "CAC observado máximo"):
        tabela[coluna] = p.indice(tabela[coluna])
    return tabela


def desenho_do_teste(p: Parametros) -> dict[str, float]:
    """O tamanho do teste em vendas esperadas: é o que define quanto ruído as regras enfrentam."""
    return {
        "dias de teste": p.dias_teste,
        "vendas esperadas por dia e por criativo, na meta": p.verba_criativo_dia / p.meta_cac,
        "vendas esperadas por dia na conta, na meta": p.verba_teste_dia / p.meta_cac,
    }


# --------------------------------------------------------------------------- regras de corte


def regras_de_corte(p: Parametros, equilibrio: float) -> dict[str, callable]:
    return {
        "Limiar simples": partial(regras.corte_por_limiar, meta=p.meta_cac),
        "Limiar com piso de gasto": partial(regras.corte_por_limiar, meta=p.meta_cac, k_piso=regras.K_PISO),
        "Teste estatístico": partial(regras.corte_estatistico, equilibrio=equilibrio),
    }


def _curva_de_corte(p: Parametros, regra, dispersao: float = 1.0) -> pd.DataFrame:
    curva = regras.curva_de_corte(
        regra, _cacs(p, INDICES_CORTE), gasto_dia=p.verba_criativo_dia, dias=p.dias_teste, dispersao=dispersao
    )
    curva.index = pd.Index(INDICES_CORTE, name=EIXO_CAC)
    curva["gasto_medio"] = p.indice(curva["gasto_medio"])
    return curva


def curvas_de_corte(p: Parametros, equilibrio: float, dispersao: float = 1.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Probabilidade de desligar e gasto médio até desligar, por CAC real, para cada regra."""
    curvas = {nome: _curva_de_corte(p, regra, dispersao) for nome, regra in regras_de_corte(p, equilibrio).items()}
    probabilidade = pd.DataFrame({nome: c["prob_desligar"] for nome, c in curvas.items()})
    gasto = pd.DataFrame({nome: c["gasto_medio"] for nome, c in curvas.items()})
    return probabilidade, gasto


def sensibilidade_do_corte(p: Parametros) -> pd.DataFrame:
    """Fração de criativos na meta que o corte por limiar desliga, para cada par de multiplicadores.

    Linhas: k_sem_venda (gasto sem venda que desliga, em múltiplos da meta).
    Colunas: k_cac (CAC acumulado que desliga, em múltiplos da meta).
    """
    tabela = pd.DataFrame(index=pd.Index(GRADE_K_SEM_VENDA, name="k_sem_venda"), columns=pd.Index(GRADE_K_CAC, name="k_cac"), dtype=float)
    for k_sem_venda in GRADE_K_SEM_VENDA:
        for k_cac in GRADE_K_CAC:
            regra = partial(regras.corte_por_limiar, meta=p.meta_cac, k_sem_venda=k_sem_venda, k_cac=k_cac)
            tabela.loc[k_sem_venda, k_cac] = _curva_de_corte(p, regra).loc[100, "prob_desligar"]
    return tabela


def sensibilidade_do_piso(p: Parametros) -> pd.DataFrame:
    """Efeito do piso de gasto (k_piso), com os outros multiplicadores no ponto de referência."""
    linhas = []
    for k_piso in GRADE_K_PISO:
        curva = _curva_de_corte(p, partial(regras.corte_por_limiar, meta=p.meta_cac, k_piso=k_piso))
        linhas.append(
            {
                "k_piso": k_piso,
                "desliga criativo na meta": curva.loc[100, "prob_desligar"],
                "desliga criativo com o dobro da meta": curva.loc[200, "prob_desligar"],
                "gasto médio no criativo com o dobro da meta (meta = 100)": curva.loc[200, "gasto_medio"],
            }
        )
    return pd.DataFrame(linhas).set_index("k_piso")


# --------------------------------------------------------------------------- regras de escala

ESCALA_SEGUIDOS = f"Dias seguidos na meta (n = {regras.N_DIAS})"
ESCALA_JANELA = f"Qualquer janela de n dias na meta (n = {regras.N_DIAS})"
ESCALA_PERIODO = "Período inteiro na meta"


def regras_de_escala(p: Parametros) -> dict[str, callable]:
    return {
        ESCALA_SEGUIDOS: partial(regras.escala_dias_seguidos, meta=p.meta_cac, n_dias=regras.N_DIAS),
        ESCALA_JANELA: partial(regras.escala_acumulada, limite=p.meta_cac, janela=regras.N_DIAS),
        ESCALA_PERIODO: partial(regras.escala_acumulada, limite=p.meta_cac, janela=p.dias_teste),
    }


def _curva_de_escala(p: Parametros, regra, dispersao: float = 1.0) -> pd.Series:
    curva = regras.curva_de_escala(
        regra, _cacs(p, INDICES_ESCALA), gasto_dia=p.verba_teste_dia, dias=p.dias_teste, dispersao=dispersao
    )
    curva.index = pd.Index(INDICES_ESCALA, name=EIXO_CAC)
    return curva


def curvas_de_escala(p: Parametros, dispersao: float = 1.0) -> pd.DataFrame:
    """Probabilidade de liberar a escala no período de teste, por CAC real, para cada regra."""
    return pd.DataFrame({nome: _curva_de_escala(p, regra, dispersao) for nome, regra in regras_de_escala(p).items()})


def sensibilidade_da_escala(p: Parametros, bom: int = 90, ruim: int = 110) -> pd.DataFrame:
    """Chance de liberar uma operação boa e uma ruim, para cada n, nas duas regras que dependem de n."""
    linhas = []
    for n_dias in GRADE_N_DIAS:
        seguidos = _curva_de_escala(p, partial(regras.escala_dias_seguidos, meta=p.meta_cac, n_dias=n_dias))
        janela = _curva_de_escala(p, partial(regras.escala_acumulada, limite=p.meta_cac, janela=n_dias))
        linhas.append(
            {
                "n": n_dias,
                f"dias seguidos: libera a boa (CAC {bom})": seguidos[bom],
                f"dias seguidos: libera a ruim (CAC {ruim})": seguidos[ruim],
                f"qualquer janela: libera a boa (CAC {bom})": janela[bom],
                f"qualquer janela: libera a ruim (CAC {ruim})": janela[ruim],
            }
        )
    return pd.DataFrame(linhas).set_index("n")


def consequencia_da_escala(
    p: Parametros, curvas: pd.DataFrame, equilibrio: float, indices: tuple[int, ...] = (80, 90, 100, 110, 120, 130)
) -> pd.DataFrame:
    """Para alguns CACs reais: o retorno de escalar e a chance de cada regra liberar a escala."""
    tabela = curvas.loc[list(indices)].copy()
    tabela.insert(0, "retorno sobre a verba de escala", regras.retorno_da_escala(_cacs(p, indices), equilibrio))
    return tabela


def limites_estatisticos(p: Parametros, equilibrio: float) -> dict[str, float]:
    """CAC acumulado máximo (meta = 100) que um teste de Poisson a 10% aceita como evidência de lucro."""
    return {
        f"{dias} dias": float(p.indice(regras.limite_estatistico(p.verba_teste_dia * dias, equilibrio)))
        for dias in (p.dias_teste // 2, p.dias_teste)
    }


# --------------------------------------------------------------------------- camada SQL


def operacao_simulada() -> dict[str, pd.DataFrame]:
    """Roda as quatro consultas sobre a operação simulada e junta o CAC real, que só a simulação conhece."""
    conexao = consultas.conectar(simulador.simular_operacao())
    try:
        corte = consultas.corte_criativos(conexao)
        corte.insert(1, "cac_real", corte["criativo"].map(simulador.CAC_REAL))
        margem = consultas.margem_por_criativo(conexao)
        margem.insert(1, "cac_real", margem["criativo"].map(simulador.CAC_REAL))
        return {
            "metricas_diarias": consultas.metricas_diarias(conexao),
            "corte": corte,
            "escala": consultas.escala_dias_seguidos(conexao),
            "margem": margem,
        }
    finally:
        conexao.close()
