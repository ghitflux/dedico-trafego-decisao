"""Roda a análise completa e grava reports/resultados.json e as figuras do README.

Usa `data/privado/parametros.json` se existir (é assim que os resultados publicados são gerados)
e `data/parametros_exemplo.json`, com valores fictícios, se não existir. Com `--exemplo`, força o
arquivo de exemplo e grava em `reports/exemplo/` (pasta fora do git), sem tocar nos resultados publicados.
Em qualquer caso a saída está na escala relativa: meta de CAC = 100.
"""

from __future__ import annotations

import argparse
import json
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from trafego_decisao import analise, economia, graficos, parametros


def _json(tabela: pd.DataFrame, orient: str = "index") -> dict | list:
    return json.loads(tabela.to_json(orient=orient, force_ascii=False, date_format="iso"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exemplo", action="store_true", help="força os parâmetros fictícios e grava em reports/exemplo/")
    argumentos = parser.parse_args()

    p = parametros.carregar(parametros.EXEMPLO if argumentos.exemplo else None)
    print(parametros.aviso_da_fonte(p))
    # Resultado com parâmetros fictícios nunca sobrescreve o publicado.
    saida = parametros.RAIZ / "reports" / ("exemplo" if p.fonte == "exemplo" else "")
    pasta_figuras = saida / "figuras"
    pasta_figuras.mkdir(parents=True, exist_ok=True)

    ptax = analise.carregar_cambio()
    resumo_precos = analise.posicao_de_preco(analise.carregar_concorrentes(p), p.preco)
    conferencia = analise.conferir_modelo(p)
    equilibrio = economia.sobra_de_referencia(p, ptax)  # em moeda; só sai daqui como índice
    equilibrio_indice = float(p.indice(equilibrio))
    cenarios = analise.cenarios_de_referencia(p, equilibrio)
    sorteio = economia.sortear_cenarios(p, ptax)
    resumo_cenarios = analise.resumo_dos_cenarios(p, sorteio)
    geometria = analise.fronteira(p, equilibrio, sorteio)
    sensibilidade = analise.sensibilidade(p, ptax)
    desenho = analise.desenho_do_teste(p)
    precisao = analise.precisao_do_cac(p, [3, 5, 7, 14])
    corte_prob, corte_gasto = analise.curvas_de_corte(p, equilibrio)
    corte_prob_irregular, _ = analise.curvas_de_corte(p, equilibrio, dispersao=2.0)
    escala = analise.curvas_de_escala(p)
    escala_irregular = analise.curvas_de_escala(p, dispersao=2.0)
    consequencia = analise.consequencia_da_escala(p, escala, equilibrio)
    operacao = analise.operacao_simulada()

    figuras = {
        "preco_concorrentes": graficos.preco_entre_concorrentes(resumo_precos),
        "fronteira": graficos.fronteira_de_equilibrio(geometria, cenarios, resumo_cenarios["fracao_que_se_paga"]),
        "sensibilidade": graficos.sensibilidade(sensibilidade),
        "corte": graficos.curvas_de_corte(corte_prob, equilibrio_indice, desenho),
        "escala": graficos.curvas_de_escala(escala, equilibrio_indice, desenho),
    }
    for nome, figura in figuras.items():
        figura.savefig(pasta_figuras / f"{nome}.png")
        plt.close(figura)

    resultados = {
        "escala": "Valores em moeda divididos pela meta de CAC e multiplicados por 100 (meta de CAC = 100).",
        "parametros": p.fonte,
        "precos": resumo_precos,
        "conferencia_do_modelo": _json(conferencia),
        "cac_de_empate": equilibrio_indice,
        "cenarios_de_referencia": _json(cenarios),
        "sorteio": resumo_cenarios,
        "fronteira": geometria,
        "sensibilidade": {"lucro_base": sensibilidade.attrs["lucro_base"], "tabela": _json(sensibilidade)},
        "desenho_do_teste": desenho,
        "precisao_do_cac": _json(precisao),
        "corte_prob_desligar": _json(corte_prob),
        "corte_gasto_medio": _json(corte_gasto),
        "corte_prob_desligar_dispersao_2": _json(corte_prob_irregular),
        "corte_sensibilidade_k": _json(analise.sensibilidade_do_corte(p)),
        "corte_sensibilidade_piso": _json(analise.sensibilidade_do_piso(p)),
        "escala_prob_liberar": _json(escala),
        "escala_prob_liberar_dispersao_2": _json(escala_irregular),
        "escala_sensibilidade_n": _json(analise.sensibilidade_da_escala(p)),
        "consequencia_da_escala": _json(consequencia),
        "limite_estatistico": analise.limites_estatisticos(p, equilibrio),
        "operacao_simulada": {
            "corte": _json(operacao["corte"], "records"),
            "escala": _json(operacao["escala"], "records"),
            "margem": _json(operacao["margem"], "records"),
        },
    }
    (saida / "resultados.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"CAC de empate: {equilibrio_indice:.1f} (meta = 100) | cenários que se pagam: "
        f"{resumo_cenarios['fracao_que_se_paga']:.2%} | criativos na meta desligados pelo limiar simples: "
        f"{corte_prob.loc[100].iloc[0]:.1%}"
    )
    print(f"Gravado em {saida / 'resultados.json'} e {pasta_figuras}")


if __name__ == "__main__":
    main()
