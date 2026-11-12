"""Regras de verba avaliadas sob ruído: com que frequência cada formato de regra decide errado?

O número de vendas de um dia é uma contagem. Com gasto G e custo de aquisição real C, o número
esperado de vendas é G / C e o observado oscila em torno disso (Poisson; ou binomial negativa
quando o dia a dia é mais irregular que o acaso puro). Uma regra de verba lê o CAC *observado*,
que é ruidoso, para adivinhar o CAC *real*, que ninguém vê. Aqui cada regra é simulada milhares
de vezes para cada CAC real possível, e o resultado é a curva "probabilidade de agir x CAC real".

Os formatos estudados são os de uso comum em gestão de tráfego:
- corte por limiar: desligar quando o gasto chega a k_sem_venda vezes a meta sem nenhuma venda,
  ou quando o CAC acumulado passa de k_cac vezes a meta;
- o mesmo corte com piso de gasto: o teste de CAC alto só vale depois de k_piso vezes a meta;
- escala por dias seguidos: liberar depois de n dias seguidos com o CAC do dia na meta;
- escala por janela agregada: liberar quando o CAC somado de uma janela fica na meta.

Os multiplicadores k e o número de dias n são argumentos: `analise.py` os varre numa grade.
As funções aceitam qualquer unidade de valor, desde que gasto, meta e CAC estejam na mesma.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from scipy import stats

# Ponto de referência dentro da grade: os multiplicadores mais comuns em regras de bolso.
K_SEM_VENDA = 2.0
K_CAC = 1.5
K_PISO = 4.0
N_DIAS = 5


def simular_vendas(
    cac_real: float, gasto_dia: float, dias: int, n: int, gerador: np.random.Generator, dispersao: float = 1.0
) -> np.ndarray:
    """Matriz (n simulações x dias) de vendas diárias.

    `dispersao` é a razão variância/média. 1 = Poisson. Acima de 1, binomial negativa com a
    mesma média: representa leilão, dia da semana e criativo cansando, que o Poisson ignora.
    """
    media = gasto_dia / cac_real
    if dispersao <= 1.0:
        return gerador.poisson(media, size=(n, dias))
    r = media / (dispersao - 1)
    return gerador.negative_binomial(r, 1 / dispersao, size=(n, dias))


# --------------------------------------------------------------------------- corte de criativo


def corte_por_limiar(
    gasto: np.ndarray,
    vendas: np.ndarray,
    meta: float,
    k_sem_venda: float = K_SEM_VENDA,
    k_cac: float = K_CAC,
    k_piso: float = 0.0,
) -> np.ndarray:
    """Corte por limiar, conferido ao fim de cada dia sobre o acumulado.

    Desliga quando gastou k_sem_venda vezes a meta sem vender, ou quando o CAC acumulado passa
    de k_cac vezes a meta. Com k_piso acima de zero, a segunda cláusula só vale depois de o
    gasto chegar a k_piso vezes a meta.
    """
    sem_venda = (vendas == 0) & (gasto >= k_sem_venda * meta)
    cac_alto = (vendas > 0) & (gasto >= k_piso * meta) & (gasto / np.maximum(vendas, 1) > k_cac * meta)
    return sem_venda | cac_alto


def corte_estatistico(gasto: np.ndarray, vendas: np.ndarray, equilibrio: float, alfa: float = 0.10) -> np.ndarray:
    """Desliga quando as vendas seriam improváveis se o criativo estivesse no ponto de equilíbrio.

    Teste exato de Poisson: P(vender tão pouco ou menos | CAC real = equilíbrio) < alfa.
    """
    return stats.poisson.cdf(vendas, gasto / equilibrio) < alfa


def curva_de_corte(
    regra: Callable[[np.ndarray, np.ndarray], np.ndarray],
    cacs: np.ndarray,
    gasto_dia: float,
    dias: int,
    n: int = 20_000,
    dispersao: float = 1.0,
    semente: int = 42,
) -> pd.DataFrame:
    """Para cada CAC real: probabilidade de o criativo ser desligado no teste e gasto médio até lá."""
    gerador = np.random.default_rng(semente)
    gasto_acumulado = gasto_dia * np.arange(1, dias + 1)
    linhas = []
    for cac_real in cacs:
        vendas_acumuladas = simular_vendas(cac_real, gasto_dia, dias, n, gerador, dispersao).cumsum(axis=1)
        desligado = regra(gasto_acumulado[None, :], vendas_acumuladas)
        algum_dia = desligado.any(axis=1)
        primeiro_dia = np.where(algum_dia, desligado.argmax(axis=1) + 1, dias)
        linhas.append(
            {
                "cac_real": cac_real,
                "prob_desligar": algum_dia.mean(),
                "gasto_medio": (primeiro_dia * gasto_dia).mean(),
            }
        )
    return pd.DataFrame(linhas).set_index("cac_real")


# --------------------------------------------------------------------------- escala da verba


def sequencia_maxima(condicao: np.ndarray) -> np.ndarray:
    """Maior número de dias seguidos em que a condição vale, por simulação (linha)."""
    maior = np.zeros(condicao.shape[0], dtype=int)
    atual = np.zeros(condicao.shape[0], dtype=int)
    for dia in range(condicao.shape[1]):
        atual = np.where(condicao[:, dia], atual + 1, 0)
        maior = np.maximum(maior, atual)
    return maior


def escala_dias_seguidos(vendas: np.ndarray, gasto_dia: float, meta: float, n_dias: int = N_DIAS) -> np.ndarray:
    """Libera quando o CAC do dia fica na meta por n_dias seguidos. Dia sem venda não está na meta."""
    na_meta = vendas >= gasto_dia / meta
    return sequencia_maxima(na_meta) >= n_dias


def escala_acumulada(vendas: np.ndarray, gasto_dia: float, limite: float, janela: int) -> np.ndarray:
    """Libera quando o CAC somado de alguma janela de `janela` dias corridos fica dentro do limite."""
    soma = np.cumsum(vendas, axis=1)
    soma_janela = soma[:, janela - 1 :] - np.concatenate(
        [np.zeros((vendas.shape[0], 1), dtype=soma.dtype), soma[:, : -janela]], axis=1
    )
    return (soma_janela >= janela * gasto_dia / limite).any(axis=1)


def limite_estatistico(gasto_total: float, equilibrio: float, alfa: float = 0.10) -> float:
    """CAC acumulado máximo que ainda dá evidência de estar abaixo do ponto de equilíbrio.

    Menor número de vendas V tal que P(vender V ou mais | CAC real = equilíbrio) < alfa;
    o limite é gasto_total / V. Traduz um teste estatístico numa regra de uma linha.
    """
    vendas_minimas = stats.poisson.isf(alfa, gasto_total / equilibrio) + 1
    return float(gasto_total / vendas_minimas)


def escala_estatistica(vendas: np.ndarray, gasto_dia: float, equilibrio: float, dias: int = 7) -> np.ndarray:
    """Escala se o CAC acumulado dos primeiros `dias` der evidência de lucro (teste de Poisson a 10%)."""
    gasto_total = gasto_dia * dias
    return gasto_total / np.maximum(vendas[:, :dias].sum(axis=1), 1e-9) <= limite_estatistico(gasto_total, equilibrio)


def curva_de_escala(
    regra: Callable[[np.ndarray, float], np.ndarray],
    cacs: np.ndarray,
    gasto_dia: float,
    dias: int,
    n: int = 20_000,
    dispersao: float = 1.0,
    semente: int = 42,
) -> pd.Series:
    """Para cada CAC real: probabilidade de a regra liberar a escala dentro do período de teste."""
    gerador = np.random.default_rng(semente)
    probabilidades = [
        regra(simular_vendas(cac_real, gasto_dia, dias, n, gerador, dispersao), gasto_dia).mean() for cac_real in cacs
    ]
    return pd.Series(probabilidades, index=pd.Index(cacs, name="cac_real"))


def retorno_da_escala(cac_real: np.ndarray, sobra: float) -> np.ndarray:
    """Retorno sobre a verba ao escalar com um dado CAC real: lucro dividido pelo gasto em mídia.

    Cada venda custa cac_real e deixa `sobra`; por unidade de verba, o resultado é sobra / cac_real - 1.
    Positivo abaixo do ponto de equilíbrio, negativo acima.
    """
    return sobra / np.asarray(cac_real, dtype=float) - 1.0
