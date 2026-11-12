"""Gera uma operação de teste simulada, no formato das tabelas que a camada SQL lê.

Tudo aqui é FICTÍCIO e já está na escala do estudo, em que a meta de CAC vale 100: os valores
não vêm do arquivo de parâmetros nem de operação real. A camada de métricas é exercitada com
dado simulado em que a verdade é conhecida (o CAC real de cada criativo é escolhido aqui).
São três tabelas: `gasto_midia` (um registro por dia e criativo), `demonstracoes` (uma por
demonstração grátis iniciada) e `pagamentos` (um por pedido pago).
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

META = 100.0
DIAS = 14
# CAC real de cada criativo: três grupos, três criativos por grupo. Vai de ótimo a péssimo.
CAC_REAL = {
    "A1": 70.0,
    "A2": 100.0,
    "A3": 160.0,
    "B1": 90.0,
    "B2": 130.0,
    "B3": 275.0,
    "C1": 110.0,
    "C2": 200.0,
    "C3": 400.0,
}
INICIO = date(2030, 1, 7)  # data fictícia
GASTO_CRIATIVO_DIA = 250.0 / 3
CPC = 6.0
CONV_DEMO = 0.15
CUSTO_DEMO = 5.0
PRECO = 120.0
EXTRA = 70.0
FRACAO_COM_EXTRA = 0.25
# Custos da venda usados na consulta de margem (também fictícios).
CUSTOS = {"taxa_cartao_pct": 0.04, "taxa_cartao_fixa": 2.0, "taxa_pix_pct": 0.01, "imposto": 0.08, "custo_entrega": 4.0}


def simular_operacao(dias: int = DIAS, semente: int = 7) -> dict[str, pd.DataFrame]:
    """Devolve as três tabelas (gasto_midia, demonstracoes, pagamentos) de um teste de `dias` dias."""
    gerador = np.random.default_rng(semente)
    gasto, demonstracoes, pagamentos = [], [], []
    for criativo, cac_real in CAC_REAL.items():
        conv_clique = CPC / cac_real
        prob_demo = conv_clique / CONV_DEMO  # fração dos cliques que chega a iniciar a demonstração
        for d in range(dias):
            dia = INICIO + timedelta(days=d)
            cliques = int(gerador.poisson(GASTO_CRIATIVO_DIA / CPC))
            gasto.append(
                {"dia": dia, "canal": "midia_paga", "criativo": criativo, "cliques": cliques, "valor": GASTO_CRIATIVO_DIA}
            )
            iniciaram = int(gerador.binomial(cliques, min(prob_demo, 1.0)))
            compraram = gerador.random(iniciaram) < CONV_DEMO
            for comprou in compraram:
                demo_id = len(demonstracoes) + 1
                demonstracoes.append({"demo_id": demo_id, "criativo": criativo, "criada_em": dia, "custo": CUSTO_DEMO})
                if comprou:
                    com_extra = gerador.random() < FRACAO_COM_EXTRA
                    pagamentos.append(
                        {
                            "pagamento_id": len(pagamentos) + 1,
                            "demo_id": demo_id,
                            "criativo": criativo,
                            "pago_em": dia,
                            "valor": PRECO + (EXTRA if com_extra else 0.0),
                            "metodo": "pix" if gerador.random() < 0.5 else "cartao",
                            "reembolsado": bool(gerador.random() < 0.03),
                        }
                    )
    return {
        "gasto_midia": pd.DataFrame(gasto),
        "demonstracoes": pd.DataFrame(demonstracoes),
        "pagamentos": pd.DataFrame(pagamentos),
    }
