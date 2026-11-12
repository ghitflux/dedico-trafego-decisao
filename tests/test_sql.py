"""A camada SQL e as regras em Python precisam chegar à mesma decisão sobre os mesmos dados."""

from functools import partial

import numpy as np
import pandas as pd
import pytest

from trafego_decisao import consultas, regras, simulador


@pytest.fixture(scope="module")
def operacao():
    tabelas = simulador.simular_operacao()
    conexao = consultas.conectar(tabelas)
    yield tabelas, conexao
    conexao.close()


def test_metricas_diarias_tem_uma_linha_por_dia_e_criativo(operacao):
    tabelas, conexao = operacao
    metricas = consultas.metricas_diarias(conexao)
    assert len(metricas) == simulador.DIAS * len(simulador.CAC_REAL)
    assert metricas["vendas"].sum() == len(tabelas["pagamentos"])
    assert metricas["demonstracoes"].sum() == len(tabelas["demonstracoes"])
    assert metricas["gasto"].sum() == pytest.approx(tabelas["gasto_midia"]["valor"].sum())


def _matriz(metricas: pd.DataFrame, coluna: str) -> pd.DataFrame:
    return metricas.pivot(index="criativo", columns="dia", values=coluna).sort_index(axis=1)


def test_corte_em_sql_bate_com_a_regra_em_python(operacao):
    _, conexao = operacao
    metricas = consultas.metricas_diarias(conexao)
    gasto = _matriz(metricas, "gasto").cumsum(axis=1)
    vendas = _matriz(metricas, "vendas").cumsum(axis=1)
    dias = gasto.columns
    sql = consultas.corte_criativos(conexao).set_index("criativo")
    for coluna, regra in [
        ("corte_limiar_simples", partial(regras.corte_por_limiar, meta=simulador.META)),
        ("corte_limiar_com_piso", partial(regras.corte_por_limiar, meta=simulador.META, k_piso=regras.K_PISO)),
    ]:
        desligado = regra(gasto.to_numpy(), vendas.to_numpy())
        for criativo, linha in zip(gasto.index, desligado):
            esperado = dias[linha.argmax()] if linha.any() else pd.NaT
            obtido = sql.loc[criativo, coluna]
            assert (pd.isna(esperado) and pd.isna(obtido)) or pd.Timestamp(esperado) == pd.Timestamp(obtido), criativo


def test_ilhas_em_sql_batem_com_a_sequencia_em_python(operacao):
    _, conexao = operacao
    escala = consultas.escala_dias_seguidos(conexao)
    na_meta = escala["na_meta"].to_numpy()[None, :]
    assert escala["dias_seguidos_na_meta"].max() == regras.sequencia_maxima(na_meta)[0]
    # Dia sem venda nunca conta como "na meta".
    assert not escala.loc[escala["vendas"] == 0, "na_meta"].any()
    # A contagem zera em todo dia fora da meta e sobe de um em um dentro de uma sequência.
    anterior = 0
    for _, linha in escala.iterrows():
        assert linha["dias_seguidos_na_meta"] == (anterior + 1 if linha["na_meta"] else 0)
        anterior = linha["dias_seguidos_na_meta"]


def test_margem_fecha_com_as_tabelas_de_origem(operacao):
    tabelas, conexao = operacao
    margem = consultas.margem_por_criativo(conexao)
    assert margem["pedidos"].sum() == len(tabelas["pagamentos"])
    pagos = tabelas["pagamentos"][~tabelas["pagamentos"]["reembolsado"]]
    assert margem["receita"].sum() == pytest.approx(pagos["valor"].sum())
    assert np.allclose(margem["resultado"], margem["sobra_antes_da_midia"] - margem["midia"])
