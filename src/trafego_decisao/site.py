"""Bloco `para_o_site`: textos e gráficos do estudo como dados, para o site desenhar nativamente.

Tudo sai do dicionário de resultados já normalizado (meta de CAC = 100): nenhum valor em moeda entra
aqui. O gráfico principal é o do corte de criativo (o número-chave); `graficos_extras` traz o
equivalente das outras figuras do README, do achado mais importante para o menos.
"""

from __future__ import annotations

IDIOMAS = ("pt", "en", "es")
LIMIAR, PISO, TESTE = "Limiar simples", "Limiar com piso de gasto", "Teste estatístico"
SEGUIDOS, JANELA, PERIODO = (
    "Dias seguidos na meta (n = 5)",
    "Qualquer janela de n dias na meta (n = 5)",
    "Período inteiro na meta",
)
EIXO_CAC = {"pt": "CAC real (meta = 100)", "en": "True CAC (target = 100)", "es": "CAC real (meta = 100)"}


def _n(valor: float, casas: int = 0) -> dict[str, str]:
    """O mesmo número nos três idiomas (pt e es com vírgula decimal)."""
    texto = f"{valor:.{casas}f}"
    return {"pt": texto.replace(".", ","), "en": texto, "es": texto.replace(".", ",")}


def _p(valor: float, casas: int = 0) -> dict[str, str]:
    return {i: f"{t}%" for i, t in _n(valor * 100, casas).items()}


def _curva(tabela: dict, coluna: str, ate: float | None = None) -> list[list[float]]:
    pontos = sorted((float(x), float(linha[coluna])) for x, linha in tabela.items())
    return [[round(x, 1), round(y, 4)] for x, y in pontos if ate is None or x <= ate]


# --------------------------------------------------------------------------- gráfico principal


def corte(r: dict) -> dict:
    """Linhas: chance de um criativo ser desligado no teste, por CAC real, nas três regras de corte."""
    tabela = r["corte_prob_desligar"]
    na_meta = tabela["100"]
    a, b, c = _p(na_meta[LIMIAR]), _p(na_meta[PISO]), _p(na_meta[TESTE])
    dias = r["desenho_do_teste"]["dias de teste"]
    return {
        "tipo": "linhas",
        "titulo": {
            "pt": f"Um corte por limiar desliga {a['pt']} dos criativos que estão exatamente na meta",
            "en": f"A threshold kill rule switches off {a['en']} of creatives that are exactly on target",
            "es": f"Un corte por umbral apaga el {a['es']} de las creatividades que están justo en la meta",
        },
        "leitura": {
            "pt": f"Chance de um criativo ser desligado em {dias} dias de teste, conforme o CAC real dele. Com piso de gasto antes de julgar o CAC, o erro na meta cai para {b['pt']}; com um teste estatístico, para {c['pt']}.",
            "en": f"Chance that a creative is switched off within a {dias}-day test, by its true CAC. With a minimum spend before judging CAC, the on-target error drops to {b['en']}; with a statistical test, to {c['en']}.",
            "es": f"Probabilidad de que una creatividad se apague en {dias} días de prueba, según su CAC real. Con un gasto mínimo antes de juzgar el CAC, el error en la meta baja al {b['es']}; con una prueba estadística, al {c['es']}.",
        },
        "eixo_x": EIXO_CAC,
        "eixo_y": {"pt": "Chance de ser desligado", "en": "Chance of being switched off", "es": "Probabilidad de apagarse"},
        "formato_x": "numero",
        "formato_y": "percentual",
        "series": [
            {"nome": {"pt": "Limiar simples", "en": "Simple threshold", "es": "Umbral simple"}, "papel": "base", "pontos": _curva(tabela, LIMIAR, 300)},
            {"nome": {"pt": "Limiar com piso de gasto", "en": "Threshold with minimum spend", "es": "Umbral con gasto mínimo"}, "papel": "alternativa", "pontos": _curva(tabela, PISO, 300)},
            {"nome": {"pt": "Teste estatístico", "en": "Statistical test", "es": "Prueba estadística"}, "papel": "principal", "pontos": _curva(tabela, TESTE, 300)},
        ],
    }


# --------------------------------------------------------------------------- gráficos extras


def escala(r: dict) -> dict:
    """Linhas: chance de cada regra liberar a escala, por CAC real da operação."""
    tabela = r["escala_prob_liberar"]
    boa = tabela["90"]
    a, b = _p(boa[SEGUIDOS]), _p(boa[PERIODO])
    dias = r["desenho_do_teste"]["dias de teste"]
    return {
        "tipo": "linhas",
        "titulo": {
            "pt": f"Com CAC 10% abaixo da meta, dias seguidos liberam a escala {a['pt']} das vezes; somar tudo, {b['pt']}",
            "en": f"With CAC 10% under target, “days in a row” scales up {a['en']} of the time; pooling, {b['en']}",
            "es": f"Con el CAC 10% bajo la meta, días seguidos liberan la escala el {a['es']}; sumarlo todo, el {b['es']}",
        },
        "leitura": {
            "pt": f"Chance de cada regra liberar a escala ao fim de {dias} dias de teste, conforme o CAC real da operação. Exigir dias seguidos perde operação boa; qualquer janela libera a ruim; somar o período inteiro separa melhor as duas.",
            "en": f"Chance that each rule allows scaling up at the end of a {dias}-day test, by the operation's true CAC. Requiring consecutive days misses good operations; any window lets bad ones through; pooling the whole period separates them best.",
            "es": f"Probabilidad de que cada regla libere la escala al final de {dias} días de prueba, según el CAC real de la operación. Exigir días seguidos pierde operaciones buenas; cualquier ventana deja pasar las malas; sumar el período entero las separa mejor.",
        },
        "eixo_x": EIXO_CAC,
        "eixo_y": {"pt": "Chance de liberar a escala", "en": "Chance of scaling up", "es": "Probabilidad de liberar la escala"},
        "formato_x": "numero",
        "formato_y": "percentual",
        "series": [
            {"nome": {"pt": "n dias seguidos na meta (n = 5)", "en": "n days in a row on target (n = 5)", "es": "n días seguidos en la meta (n = 5)"}, "papel": "base", "pontos": _curva(tabela, SEGUIDOS)},
            {"nome": {"pt": "Qualquer janela de n dias (n = 5)", "en": "Any n-day window (n = 5)", "es": "Cualquier ventana de n días (n = 5)"}, "papel": "alternativa", "pontos": _curva(tabela, JANELA)},
            {"nome": {"pt": "Período inteiro", "en": "Whole period", "es": "Período completo"}, "papel": "principal", "pontos": _curva(tabela, PERIODO)},
        ],
    }


ENTRADAS = {
    "Custo por clique": ("Custo por clique", "Cost per click", "Costo por clic"),
    "Conversão de clique em compra": ("Conversão de clique em compra", "Click-to-purchase conversion", "Conversión de clic en compra"),
    "Demonstrações que viram compra": ("Demonstrações que viram compra", "Free trials that convert", "Demostraciones que se convierten"),
    "Receita de extras por pedido": ("Receita de extras por pedido", "Add-on revenue per order", "Ingreso por extras por pedido"),
    "Imposto sobre a receita": ("Imposto sobre a receita", "Tax on revenue", "Impuesto sobre el ingreso"),
    "Pedidos reembolsados": ("Pedidos reembolsados", "Refunded orders", "Pedidos reembolsados"),
    "Dólar efetivo": ("Dólar efetivo", "Effective dollar rate", "Dólar efectivo"),
    "Pedidos pagos por Pix": ("Pedidos pagos por Pix", "Orders paid via Pix", "Pedidos pagados por Pix"),
}


def sensibilidade(r: dict) -> dict:
    """Barras: amplitude do lucro por venda quando só uma entrada percorre a sua faixa."""
    tabela = r["sensibilidade"]["tabela"]
    ordem = sorted(tabela, key=lambda nome: -tabela[nome]["amplitude"])
    rotulos = {idioma: [ENTRADAS[nome][k] for nome in ordem] for k, idioma in enumerate(IDIOMAS)}
    maior, menor = _n(tabela[ordem[0]]["amplitude"]), _n(tabela[ordem[-1]]["amplitude"])
    return {
        "tipo": "barras",
        "titulo": {
            "pt": "Custo por clique e conversão decidem o lucro por venda; o resto pesa pouco",
            "en": "Cost per click and conversion decide profit per sale; the rest barely matters",
            "es": "El costo por clic y la conversión deciden el beneficio por venta; el resto pesa poco",
        },
        "leitura": {
            "pt": f"Quanto o lucro por venda muda (meta de CAC = 100) quando só uma entrada vai da pior à melhor ponta da sua faixa: {maior['pt']} pontos no custo por clique contra {menor['pt']} na forma de pagamento. É isso que vale medir primeiro.",
            "en": f"How much profit per sale moves (target CAC = 100) when a single input runs from the worst to the best end of its range: {maior['en']} points for cost per click versus {menor['en']} for payment method. That is what to measure first.",
            "es": f"Cuánto cambia el beneficio por venta (meta de CAC = 100) cuando una sola entrada va del peor al mejor extremo de su rango: {maior['es']} puntos en el costo por clic frente a {menor['es']} en la forma de pago. Eso es lo que conviene medir primero.",
        },
        "eixo_x": {"pt": "Entrada", "en": "Input", "es": "Entrada"},
        "eixo_y": {
            "pt": "Amplitude no lucro por venda (meta de CAC = 100)",
            "en": "Swing in profit per sale (target CAC = 100)",
            "es": "Amplitud en el beneficio por venta (meta de CAC = 100)",
        },
        "formato_x": "numero",
        "formato_y": "numero",
        "series": [
            {
                "nome": {"pt": "Amplitude no lucro por venda", "en": "Swing in profit per sale", "es": "Amplitud en el beneficio por venta"},
                "papel": "principal",
                "pontos": [[rotulos["pt"][k], round(tabela[nome]["amplitude"], 1)] for k, nome in enumerate(ordem)],
                "rotulos": rotulos,
            }
        ],
    }


def fronteira(r: dict, passos: int = 25) -> dict:
    """Linhas: custo por clique máximo que ainda empata, por conversão, em eixos relativos às pontas das faixas."""
    g = r["fronteira"]
    x_min = g["conversao_minima"]
    xs = [round(x_min + (100 - x_min) * k / (passos - 1), 2) for k in range(passos)]
    se_paga = _p(r["sorteio"]["fracao_que_se_paga"], 1)

    def reta(inclinacao: float) -> list[list[float]]:
        return [[x, round(inclinacao * x, 2)] for x in xs]

    return {
        "tipo": "linhas",
        "titulo": {
            "pt": f"Só {se_paga['pt']} dos cenários sorteados se pagam na primeira compra",
            "en": f"Only {se_paga['en']} of sampled scenarios pay for themselves on the first purchase",
            "es": f"Solo el {se_paga['es']} de los escenarios sorteados se paga en la primera compra",
        },
        "leitura": {
            "pt": "Abaixo de cada linha, a primeira compra paga a mídia. A conversão está com o teto da faixa valendo 100 e o custo por clique com o piso valendo 100: a linha de empate só passa acima do piso no canto de conversão alta, o único pedaço da faixa que dá lucro.",
            "en": "Below each line, the first purchase pays for the media. Conversion is scaled so the top of its range is 100 and cost per click so the bottom of its range is 100: the break-even line only clears the floor at high conversion, the one corner of the range that turns a profit.",
            "es": "Por debajo de cada línea, la primera compra paga la publicidad. La conversión está con el techo del rango en 100 y el costo por clic con el piso en 100: la línea de equilibrio solo supera el piso con conversión alta, el único rincón del rango que da beneficio.",
        },
        "eixo_x": {
            "pt": "Conversão de clique em compra (teto da faixa = 100)",
            "en": "Click-to-purchase conversion (top of range = 100)",
            "es": "Conversión de clic en compra (techo del rango = 100)",
        },
        "eixo_y": {
            "pt": "Custo por clique que empata (piso da faixa = 100)",
            "en": "Break-even cost per click (bottom of range = 100)",
            "es": "Costo por clic de equilibrio (piso del rango = 100)",
        },
        "formato_x": "numero",
        "formato_y": "numero",
        "series": [
            {"nome": {"pt": "Empate com a margem de referência", "en": "Break-even at the reference margin", "es": "Equilibrio con el margen de referencia"}, "papel": "principal", "pontos": reta(g["inclinacao_margem_de_referencia"])},
            {"nome": {"pt": "Empate com a margem mediana dos cenários", "en": "Break-even at the median scenario margin", "es": "Equilibrio con el margen mediano de los escenarios"}, "papel": "alternativa", "pontos": reta(g["inclinacao_margem_mediana"])},
            {"nome": {"pt": "Piso da faixa de custo por clique", "en": "Bottom of the cost-per-click range", "es": "Piso del rango de costo por clic"}, "papel": "neutro", "pontos": [[x, 100.0] for x in xs]},
        ],
    }


def graficos_extras(r: dict) -> list[dict]:
    """As figuras do README que não estão no gráfico principal, do achado mais importante para o menos."""
    return [escala(r), sensibilidade(r), fronteira(r)]


# --------------------------------------------------------------------------- bloco inteiro


def bloco(r: dict) -> dict:
    na_meta = r["corte_prob_desligar"]["100"]
    a, b = _p(na_meta[LIMIAR]), _p(na_meta[PISO])
    boa = r["escala_prob_liberar"]["90"]
    c, d = _p(boa[SEGUIDOS]), _p(boa[PERIODO])
    se_paga = _p(r["sorteio"]["fracao_que_se_paga"], 1)
    empate = _n(r["cac_de_empate"])
    return {
        "numero_chave": {i: a[i] for i in IDIOMAS},
        "pergunta": {
            "pt": "Regras de bolso de verba (cortar criativo, escalar campanha) decidem certo quando as vendas do dia oscilam por acaso?",
            "en": "Do rule-of-thumb budget rules (killing creatives, scaling campaigns) decide correctly when daily sales swing by chance?",
            "es": "¿Las reglas prácticas de presupuesto (apagar creatividades, escalar campañas) deciden bien cuando las ventas del día oscilan por azar?",
        },
        "resultado": {
            "pt": f"Um corte por limiar desliga {a['pt']} dos criativos que estão exatamente na meta; com piso de gasto antes de julgar o CAC, {b['pt']}. Exigir dias seguidos na meta libera só {c['pt']} das vezes uma operação lucrativa; somar o teste inteiro libera {d['pt']}.",
            "en": f"A threshold kill rule switches off {a['en']} of creatives that are exactly on target; with a minimum spend before judging CAC, {b['en']}. Requiring consecutive days on target scales up a profitable operation only {c['en']} of the time; pooling the whole test does it {d['en']} of the time.",
            "es": f"Un corte por umbral apaga el {a['es']} de las creatividades que están justo en la meta; con un gasto mínimo antes de juzgar el CAC, el {b['es']}. Exigir días seguidos en la meta libera solo el {c['es']} de las veces una operación rentable; sumar la prueba completa la libera el {d['es']}.",
        },
        "detalhe": {
            "pt": f"Antes de qualquer regra, a conta: com a meta de CAC em 100, o CAC de empate é {empate['pt']}, e só {se_paga['pt']} dos 100 mil cenários sorteados se pagam na primeira compra. Custo por clique e conversão decidem o resultado; câmbio e forma de pagamento quase não pesam.",
            "en": f"Before any rule, the math: with target CAC at 100, break-even CAC is {empate['en']}, and only {se_paga['en']} of 100,000 sampled scenarios pay for themselves on the first purchase. Cost per click and conversion decide the outcome; exchange rate and payment method barely matter.",
            "es": f"Antes de cualquier regla, la cuenta: con la meta de CAC en 100, el CAC de equilibrio es {empate['es']}, y solo el {se_paga['es']} de los 100.000 escenarios sorteados se paga en la primera compra. El costo por clic y la conversión deciden el resultado; el tipo de cambio y la forma de pago casi no pesan.",
        },
        "dados": {
            "pt": "Lançamento de um produto digital próprio, antes da primeira venda, publicado em unidades relativas (meta de CAC = 100). Custos medidos e câmbio do Banco Central; tráfego como premissa e 20 mil simulações por regra.",
            "en": "Launch of the author's own digital product, before the first sale, published in relative units (target CAC = 100). Measured costs and central bank exchange rates; traffic as assumptions and 20,000 simulations per rule.",
            "es": "Lanzamiento de un producto digital propio, antes de la primera venta, publicado en unidades relativas (meta de CAC = 100). Costos medidos y tipo de cambio del Banco Central; tráfico como supuesto y 20.000 simulaciones por regla.",
        },
        "etiquetas": ["tráfego pago", "Monte Carlo", "Poisson", "curva de operação", "análise de sensibilidade", "SQL (DuckDB)"],
        "grafico": corte(r),
        "graficos_extras": graficos_extras(r),
    }
