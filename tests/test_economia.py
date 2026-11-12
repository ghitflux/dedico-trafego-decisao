"""Testes da conta de margem. Rodam sempre com os parâmetros fictícios de exemplo."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from trafego_decisao import analise, economia, parametros

P = parametros.carregar(parametros.EXEMPLO)
PTAX = pd.Series(np.linspace(5.0, 5.6, 120))
SEM_MIDIA = {k: v for k, v in P.valores_base().items() if k not in economia.MIDIA}


def test_exemplo_e_rotulado_como_ficticio_e_a_meta_vale_100():
    assert P.fonte == "exemplo"
    assert "FICTÍCIOS" in parametros.EXEMPLO.read_text(encoding="utf-8")
    assert "FICTÍCIOS" in parametros.aviso_da_fonte(P)
    assert P.indice(P.meta_cac) == pytest.approx(100.0)


def test_modelo_reproduz_as_contas_de_referencia():
    conferencia = analise.conferir_modelo(P)
    assert len(conferencia) == 2
    assert (conferencia["desvio do modelo"].abs() < 0.01).all()


def test_demonstracao_perdida_e_paga_por_quem_compra():
    comuns = dict(extras=0.0, imposto=0.08, reembolso=0.0, fracao_pix=0.0, cambio=5.5)
    todas_compram = economia.sobra_para_midia(P, conv_demo=1.0, **comuns)
    uma_em_dez = economia.sobra_para_midia(P, conv_demo=0.10, **comuns)
    # Nove demonstrações perdidas por venda.
    assert todas_compram - uma_em_dez == pytest.approx(9 * P.custo_demo_perdida_usd * 5.5)


def test_pix_e_extras_aumentam_a_sobra_e_imposto_diminui():
    sobra = economia.sobra_para_midia(P, **SEM_MIDIA)
    assert economia.sobra_para_midia(P, **{**SEM_MIDIA, "fracao_pix": 0.6}) > sobra
    assert economia.sobra_para_midia(P, **{**SEM_MIDIA, "extras": 0.0}) < sobra
    assert economia.sobra_para_midia(P, **{**SEM_MIDIA, "imposto": 0.16}) < sobra


def test_lucro_e_sobra_menos_cac():
    valores = P.valores_base()
    sobra = economia.sobra_para_midia(P, **SEM_MIDIA)
    assert economia.lucro_por_venda(P, **valores) == pytest.approx(sobra - valores["cpc"] / valores["conv_clique"])


def test_sorteio_respeita_as_faixas_e_e_reprodutivel():
    a = economia.sortear_cenarios(P, PTAX, n=5_000, semente=1)
    b = economia.sortear_cenarios(P, PTAX, n=5_000, semente=1)
    pd.testing.assert_frame_equal(a, b)
    for nome, entrada in P.entradas.items():
        if nome == "cambio":
            continue
        assert a[nome].between(entrada.baixo, entrada.alto).all()
    assert a["cambio"].between(5.0 * P.fator_cambio, 5.6 * P.fator_cambio).all()
    assert (a["lucro"] == a["sobra"] - a["cac"]).all()


def test_sensibilidade_ordena_pela_amplitude_e_contem_o_valor_base():
    tabela = analise.sensibilidade(P, PTAX)
    assert tabela["amplitude"].is_monotonic_decreasing
    assert tabela["amplitude ÷ maior amplitude"].iloc[0] == pytest.approx(1.0)
    base = tabela.attrs["lucro_base"]
    # O valor-base está dentro da faixa de toda entrada, então o lucro-base fica entre os extremos.
    assert ((tabela["lucro no pior extremo"] <= base + 1e-9) & (base <= tabela["lucro no melhor extremo"] + 1e-9)).all()


def test_precisao_do_cac_estreita_com_mais_dias():
    tabela = analise.precisao_do_cac(P, [3, 7, 14])
    largura = tabela["CAC observado máximo"] - tabela["CAC observado mínimo"]
    assert largura.is_monotonic_decreasing
    # A operação simulada está na meta: a faixa observada precisa conter 100.
    assert (tabela["CAC observado mínimo"] < 100).all() and (tabela["CAC observado máximo"] > 100).all()


def test_trocar_a_moeda_nao_muda_nenhum_resultado_publicado():
    """A escala publicada é relativa: multiplicar todo valor em moeda por um fator não pode mudar nada."""
    fator = 3.7
    em_moeda = ("preco", "taxa_cartao_fixa", "custo_venda_usd", "custo_demo_perdida_usd", "meta_cac", "verba_teste_dia", "verba_criativo_dia")
    entradas = {
        nome: replace(e, base=e.base * fator, baixo=e.baixo * fator, alto=e.alto * fator) if nome in ("cpc", "extras") else e
        for nome, e in P.entradas.items()
    }
    outra = replace(
        P,
        **{campo: getattr(P, campo) * fator for campo in em_moeda},
        entradas=entradas,
        cenarios={nome: (cpc * fator, conv) for nome, (cpc, conv) in P.cenarios.items()},
    )
    sobra, sobra_outra = economia.sobra_de_referencia(P, PTAX), economia.sobra_de_referencia(outra, PTAX)
    assert outra.indice(sobra_outra) == pytest.approx(P.indice(sobra))
    pd.testing.assert_frame_equal(analise.cenarios_de_referencia(outra, sobra_outra), analise.cenarios_de_referencia(P, sobra))
    numericas = ["lucro no pior extremo", "lucro no melhor extremo", "amplitude"]
    pd.testing.assert_frame_equal(analise.sensibilidade(outra, PTAX)[numericas], analise.sensibilidade(P, PTAX)[numericas])
    resumo = analise.resumo_dos_cenarios(P, economia.sortear_cenarios(P, PTAX, n=5_000))
    resumo_outra = analise.resumo_dos_cenarios(outra, economia.sortear_cenarios(outra, PTAX, n=5_000))
    assert resumo_outra == pytest.approx(resumo)
    corte, _ = analise.curvas_de_corte(P, sobra)
    corte_outra, _ = analise.curvas_de_corte(outra, sobra_outra)
    assert np.abs(corte_outra - corte).to_numpy().max() < 0.01
