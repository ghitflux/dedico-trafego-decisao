"""Testes das regras. Valores na escala do estudo: a meta de CAC vale 100."""

from functools import partial

import numpy as np
import pytest
from scipy import stats

from trafego_decisao import analise, parametros, regras

META = 100.0
GASTO_CONTA_DIA = 1250.0  # 12,5 vendas esperadas por dia quando o CAC real é a meta


def test_simular_vendas_tem_a_media_e_a_dispersao_pedidas():
    gerador = np.random.default_rng(0)
    poisson = regras.simular_vendas(META, GASTO_CONTA_DIA, 1, 200_000, gerador)
    irregular = regras.simular_vendas(META, GASTO_CONTA_DIA, 1, 200_000, gerador, dispersao=2.0)
    assert poisson.mean() == pytest.approx(12.5, rel=0.01)
    assert poisson.var() / poisson.mean() == pytest.approx(1.0, rel=0.03)
    assert irregular.mean() == pytest.approx(12.5, rel=0.01)
    assert irregular.var() / irregular.mean() == pytest.approx(2.0, rel=0.03)


def test_corte_por_limiar_nas_duas_clausulas():
    gasto = np.array([[100.0, 200.0, 300.0]])
    corte = partial(regras.corte_por_limiar, meta=META, k_sem_venda=2.0, k_cac=1.5)
    assert corte(gasto, np.array([[0, 0, 0]])).tolist() == [[False, True, True]]  # sem venda ao chegar a 2 metas
    assert corte(gasto, np.array([[1, 1, 1]])).tolist() == [[False, True, True]]  # CAC de 200 e 300, acima de 150
    assert corte(gasto, np.array([[1, 2, 2]])).tolist() == [[False, False, False]]  # CAC de 100, 100 e 150


def test_multiplicadores_mudam_o_ponto_de_corte():
    gasto = np.array([[100.0, 200.0, 300.0]])
    sem_venda = np.array([[0, 0, 0]])
    uma_venda = np.array([[1, 1, 1]])
    assert regras.corte_por_limiar(gasto, sem_venda, META, k_sem_venda=3.0).tolist() == [[False, False, True]]
    assert regras.corte_por_limiar(gasto, uma_venda, META, k_cac=2.5).tolist() == [[False, False, True]]


def test_piso_adia_so_o_teste_de_cac_alto():
    gasto = np.array([[200.0, 400.0]])
    uma_venda = np.array([[1, 1]])
    assert regras.corte_por_limiar(gasto, uma_venda, META).tolist() == [[True, True]]
    assert regras.corte_por_limiar(gasto, uma_venda, META, k_piso=4.0).tolist() == [[False, True]]
    # A cláusula "sem venda" continua valendo antes do piso.
    assert regras.corte_por_limiar(gasto, np.array([[0, 0]]), META, k_piso=4.0).tolist() == [[True, True]]


def test_corte_estatistico_sem_venda_dispara_no_gasto_previsto_pela_formula():
    equilibrio, alfa = 105.0, 0.10
    limite = -equilibrio * np.log(alfa)  # P(0 vendas) = exp(-gasto / equilibrio) < alfa
    gasto = np.array([[limite - 0.5, limite + 0.5]])
    assert regras.corte_estatistico(gasto, np.zeros((1, 2)), equilibrio, alfa).tolist() == [[False, True]]


def test_curva_de_corte_cresce_com_o_cac_real():
    corte = partial(regras.corte_por_limiar, meta=META)
    curva = regras.curva_de_corte(corte, np.array([50.0, 100.0, 200.0, 400.0]), gasto_dia=250 / 3, dias=14, n=4_000)
    assert curva["prob_desligar"].is_monotonic_increasing
    assert curva["gasto_medio"].is_monotonic_decreasing
    assert curva.loc[400.0, "prob_desligar"] > 0.95


def test_sequencia_maxima():
    condicao = np.array(
        [
            [True, True, False, True, True, True, False],
            [False, False, False, False, False, False, False],
            [True, True, True, True, True, True, True],
        ]
    )
    assert regras.sequencia_maxima(condicao).tolist() == [3, 0, 7]


def test_escala_por_dias_seguidos_exige_a_sequencia_inteira():
    # Na meta = 13 vendas ou mais no dia (1250 / 100 = 12,5).
    quase = np.array([[13, 13, 13, 13, 12, 13, 13, 13, 13, 12]])
    exato = np.array([[12, 13, 13, 13, 13, 13, 12, 0, 0, 0]])
    assert not regras.escala_dias_seguidos(quase, GASTO_CONTA_DIA, META, n_dias=5)[0]
    assert regras.escala_dias_seguidos(exato, GASTO_CONTA_DIA, META, n_dias=5)[0]
    assert regras.escala_dias_seguidos(quase, GASTO_CONTA_DIA, META, n_dias=4)[0]
    assert not regras.escala_dias_seguidos(exato, GASTO_CONTA_DIA, META, n_dias=6)[0]


def test_escala_acumulada_bate_com_a_conta_direta():
    gerador = np.random.default_rng(3)
    vendas = gerador.poisson(12.5, size=(500, 14))
    esperado = np.array([any(linha[i : i + 5].sum() >= 5 * 12.5 for i in range(10)) for linha in vendas])
    assert (regras.escala_acumulada(vendas, GASTO_CONTA_DIA, META, janela=5) == esperado).all()
    # Com a janela do tamanho do teste, é só o CAC do período inteiro.
    assert (regras.escala_acumulada(vendas, GASTO_CONTA_DIA, META, janela=14) == (vendas.sum(axis=1) >= 175)).all()


def test_limite_estatistico_controla_o_falso_positivo_no_equilibrio():
    gasto_total, equilibrio, alfa = 17_500.0, 105.0, 0.10
    limite = regras.limite_estatistico(gasto_total, equilibrio, alfa)
    vendas_minimas = round(gasto_total / limite)
    esperadas = gasto_total / equilibrio
    assert stats.poisson.sf(vendas_minimas - 1, esperadas) < alfa  # P(vendas >= mínimo) no equilíbrio
    assert stats.poisson.sf(vendas_minimas - 2, esperadas) >= alfa  # uma venda a menos já não bastaria
    assert limite < equilibrio


def test_periodo_inteiro_e_mais_ingreme_que_dias_seguidos():
    cacs = np.array([80.0, 90.0, 120.0])
    seguidos = regras.curva_de_escala(
        partial(regras.escala_dias_seguidos, meta=META, n_dias=5), cacs, gasto_dia=GASTO_CONTA_DIA, dias=14, n=6_000
    )
    periodo = regras.curva_de_escala(
        partial(regras.escala_acumulada, limite=META, janela=14), cacs, gasto_dia=GASTO_CONTA_DIA, dias=14, n=6_000
    )
    assert periodo[90.0] > seguidos[90.0] + 0.3  # libera muito mais a operação boa
    assert abs(periodo[120.0] - seguidos[120.0]) < 0.03  # sem liberar mais a ruim


def test_retorno_da_escala_troca_de_sinal_no_equilibrio():
    retorno = regras.retorno_da_escala(np.array([90.0, 105.0, 120.0]), sobra=105.0)
    assert retorno[0] > 0 and retorno[1] == pytest.approx(0.0) and retorno[2] < 0


def test_grades_de_sensibilidade_contem_o_ponto_de_referencia():
    """A célula de referência de cada grade precisa repetir a curva principal: mesma regra, mesmo sorteio."""
    p = parametros.carregar(parametros.EXEMPLO)
    corte, _ = analise.curvas_de_corte(p, equilibrio=p.meta_cac * 1.05)
    grade = analise.sensibilidade_do_corte(p)
    assert grade.loc[regras.K_SEM_VENDA, regras.K_CAC] == pytest.approx(corte.loc[100, "Limiar simples"])
    piso = analise.sensibilidade_do_piso(p)
    assert piso.loc[regras.K_PISO, "desliga criativo na meta"] == pytest.approx(corte.loc[100, "Limiar com piso de gasto"])
    # Mais tolerância ao CAC alto desliga menos criativo bom; piso maior também.
    assert grade.loc[regras.K_SEM_VENDA].is_monotonic_decreasing
    assert piso["desliga criativo na meta"].is_monotonic_decreasing
    escala = analise.curvas_de_escala(p)
    por_n = analise.sensibilidade_da_escala(p)
    assert por_n.loc[regras.N_DIAS].iloc[0] == pytest.approx(escala.loc[90, analise.ESCALA_SEGUIDOS])
    assert por_n.iloc[:, 0].is_monotonic_decreasing  # exigir mais dias seguidos libera menos
