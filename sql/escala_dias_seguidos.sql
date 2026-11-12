-- Regra de escala: "CAC na meta por N dias seguidos", sobre o total da conta.
-- Parâmetros: $meta (meta de CAC, na unidade do gasto) e $dias_seguidos (N).
-- Padrão "ilhas e lacunas": dias consecutivos que cumprem a condição recebem o mesmo rótulo de
-- ilha, porque a diferença entre a numeração de todos os dias e a numeração só dos dias na meta
-- fica constante dentro de uma sequência.
WITH total_dia AS (
    SELECT dia, SUM(gasto) AS gasto, SUM(vendas) AS vendas
    FROM metricas_diarias
    GROUP BY dia
),
marcado AS (
    SELECT
        *,
        gasto / NULLIF(vendas, 0)                                   AS cac_dia,
        COALESCE(gasto / NULLIF(vendas, 0) <= $meta, FALSE)         AS na_meta,
        ROW_NUMBER() OVER (ORDER BY dia)                            AS ordem
    FROM total_dia
),
ilhas AS (
    SELECT
        *,
        ordem - ROW_NUMBER() OVER (PARTITION BY na_meta ORDER BY dia) AS ilha
    FROM marcado
),
sequencias AS (
    SELECT
        *,
        CASE WHEN na_meta THEN ROW_NUMBER() OVER (PARTITION BY na_meta, ilha ORDER BY dia) ELSE 0 END AS dias_seguidos_na_meta
    FROM ilhas
)
SELECT
    dia,
    gasto,
    vendas,
    cac_dia,
    na_meta,
    dias_seguidos_na_meta,
    dias_seguidos_na_meta >= $dias_seguidos                              AS libera_escala,
    SUM(gasto) OVER ate_hoje / NULLIF(SUM(vendas) OVER ate_hoje, 0)      AS cac_acumulado
FROM sequencias
WINDOW ate_hoje AS (ORDER BY dia ROWS UNBOUNDED PRECEDING)
ORDER BY dia;
