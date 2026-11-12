-- Métricas por dia e criativo: a base de todas as outras consultas.
-- Uma linha por (dia, criativo), mesmo nos dias sem demonstração ou sem venda.
-- Valores na escala do estudo (meta de CAC = 100).
WITH demos_dia AS (
    SELECT criada_em AS dia, criativo, COUNT(*) AS demonstracoes, SUM(custo) AS custo_demonstracoes
    FROM demonstracoes
    GROUP BY ALL
),
vendas_dia AS (
    SELECT
        pago_em AS dia,
        criativo,
        COUNT(*) AS vendas,
        SUM(valor) FILTER (WHERE NOT reembolsado) AS receita,
        COUNT(*) FILTER (WHERE reembolsado) AS reembolsos
    FROM pagamentos
    GROUP BY ALL
)
SELECT
    g.dia,
    g.criativo,
    g.cliques,
    g.valor                                               AS gasto,
    COALESCE(d.demonstracoes, 0)                          AS demonstracoes,
    COALESCE(v.vendas, 0)                                 AS vendas,
    COALESCE(v.reembolsos, 0)                             AS reembolsos,
    COALESCE(v.receita, 0)                                AS receita,
    COALESCE(d.custo_demonstracoes, 0)                    AS custo_demonstracoes,
    COALESCE(d.demonstracoes, 0) / NULLIF(g.cliques, 0)   AS taxa_clique_demo,
    COALESCE(v.vendas, 0) / NULLIF(d.demonstracoes, 0)    AS taxa_demo_venda,
    g.valor / NULLIF(v.vendas, 0)                         AS cac_dia
FROM gasto_midia AS g
LEFT JOIN demos_dia AS d USING (dia, criativo)
LEFT JOIN vendas_dia AS v USING (dia, criativo)
ORDER BY g.dia, g.criativo;
