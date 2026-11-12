"""Roda as consultas de `sql/` no DuckDB, em memória, sobre as tabelas da operação."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from trafego_decisao import regras, simulador

PASTA_SQL = Path(__file__).resolve().parents[2] / "sql"


def _ler(nome: str) -> str:
    return (PASTA_SQL / f"{nome}.sql").read_text(encoding="utf-8").strip().rstrip(";")


def conectar(tabelas: dict[str, pd.DataFrame]) -> duckdb.DuckDBPyConnection:
    """Abre um banco em memória com as tabelas dadas e a visão `metricas_diarias`."""
    conexao = duckdb.connect(":memory:")
    for nome, tabela in tabelas.items():
        conexao.register(f"_{nome}", tabela)
        conexao.execute(f"CREATE TABLE {nome} AS SELECT * FROM _{nome}")
        conexao.unregister(f"_{nome}")
    conexao.execute(f"CREATE VIEW metricas_diarias AS {_ler('metricas_diarias')}")
    return conexao


def metricas_diarias(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conexao.execute("SELECT * FROM metricas_diarias").df()


def corte_criativos(
    conexao: duckdb.DuckDBPyConnection,
    meta: float = simulador.META,
    k_sem_venda: float = regras.K_SEM_VENDA,
    k_cac: float = regras.K_CAC,
    k_piso: float = regras.K_PISO,
) -> pd.DataFrame:
    parametros = {"corte_sem_venda": k_sem_venda * meta, "corte_cac": k_cac * meta, "piso": k_piso * meta}
    return conexao.execute(_ler("corte_criativos"), parametros).df()


def escala_dias_seguidos(
    conexao: duckdb.DuckDBPyConnection, meta: float = simulador.META, n_dias: int = regras.N_DIAS
) -> pd.DataFrame:
    return conexao.execute(_ler("escala_dias_seguidos"), {"meta": meta, "dias_seguidos": n_dias}).df()


def margem_por_criativo(conexao: duckdb.DuckDBPyConnection, custos: dict[str, float] | None = None) -> pd.DataFrame:
    """`custos`: taxa_cartao_pct, taxa_cartao_fixa, taxa_pix_pct, imposto e custo_entrega (por pedido)."""
    return conexao.execute(_ler("margem_por_criativo"), custos or simulador.CUSTOS).df()
