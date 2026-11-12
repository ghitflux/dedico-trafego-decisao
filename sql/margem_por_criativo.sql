-- Margem de contribuição por criativo no período: o que sobra depois de taxa de pagamento,
-- imposto, custo de entrega, demonstrações grátis (inclusive as que não viraram compra) e mídia.
-- Parâmetros: $taxa_cartao_pct, $taxa_cartao_fixa, $taxa_pix_pct, $imposto, $custo_entrega (por pedido).
WITH pedidos AS (
    SELECT
        criativo,
        COUNT(*)                                             AS pedidos,
        COUNT(*) FILTER (WHERE reembolsado)                  AS reembolsados,
        SUM(valor) FILTER (WHERE NOT reembolsado)            AS receita,
        SUM(
            CASE metodo
                WHEN 'pix' THEN valor * $taxa_pix_pct
                ELSE valor * $taxa_cartao_pct + $taxa_cartao_fixa
            END
        )                                                    AS taxa_pagamento
    FROM pagamentos
    GROUP BY criativo
),
funil AS (
    SELECT
        criativo,
        SUM(gasto)               AS midia,
        SUM(cliques)             AS cliques,
        SUM(demonstracoes)       AS demonstracoes,
        SUM(custo_demonstracoes) AS custo_demonstracoes
    FROM metricas_diarias
    GROUP BY criativo
)
SELECT
    f.criativo,
    f.cliques,
    f.demonstracoes,
    COALESCE(p.pedidos, 0)                                                AS pedidos,
    COALESCE(p.pedidos, 0) / NULLIF(f.demonstracoes, 0)                   AS taxa_demo_venda,
    f.midia,
    f.midia / NULLIF(p.pedidos, 0)                                        AS cac,
    COALESCE(p.receita, 0)                                                AS receita,
    COALESCE(p.receita, 0)
        - COALESCE(p.taxa_pagamento, 0)
        - COALESCE(p.receita, 0) * $imposto
        - f.custo_demonstracoes
        - COALESCE(p.pedidos, 0) * $custo_entrega                         AS sobra_antes_da_midia,
    COALESCE(p.receita, 0)
        - COALESCE(p.taxa_pagamento, 0)
        - COALESCE(p.receita, 0) * $imposto
        - f.custo_demonstracoes
        - COALESCE(p.pedidos, 0) * $custo_entrega
        - f.midia                                                         AS resultado
FROM funil AS f
LEFT JOIN pedidos AS p USING (criativo)
ORDER BY resultado DESC;
