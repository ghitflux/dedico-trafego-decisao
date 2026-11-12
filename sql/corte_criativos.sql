-- Regra de corte de criativo por limiar, aplicada ao fim de cada dia sobre o acumulado.
-- Parâmetros, na mesma unidade do gasto: $corte_sem_venda (gasto sem venda que desliga),
-- $corte_cac (CAC acumulado que desliga) e $piso (gasto mínimo antes de julgar o CAC).
-- Devolve, por criativo, o primeiro dia em que cada versão da regra mandaria desligar
-- (NULL = sobreviveu ao teste inteiro).
WITH acumulado AS (
    SELECT
        dia,
        criativo,
        SUM(gasto)  OVER dias_do_criativo AS gasto_acumulado,
        SUM(vendas) OVER dias_do_criativo AS vendas_acumuladas
    FROM metricas_diarias
    WINDOW dias_do_criativo AS (PARTITION BY criativo ORDER BY dia ROWS UNBOUNDED PRECEDING)
),
avaliado AS (
    SELECT
        *,
        gasto_acumulado / NULLIF(vendas_acumuladas, 0) AS cac_acumulado,
        vendas_acumuladas = 0 AND gasto_acumulado >= $corte_sem_venda AS sem_venda,
        vendas_acumuladas > 0 AND gasto_acumulado / vendas_acumuladas > $corte_cac AS cac_alto
    FROM acumulado
)
SELECT
    criativo,
    MIN(dia) FILTER (WHERE sem_venda OR cac_alto)                                    AS corte_limiar_simples,
    MIN(dia) FILTER (WHERE sem_venda OR (cac_alto AND gasto_acumulado >= $piso))     AS corte_limiar_com_piso,
    MAX(gasto_acumulado)                                                             AS gasto_no_teste,
    MAX(vendas_acumuladas)                                                           AS vendas_no_teste,
    MAX(gasto_acumulado) / NULLIF(MAX(vendas_acumuladas), 0)                         AS cac_no_teste
FROM avaliado
GROUP BY criativo
ORDER BY cac_no_teste NULLS LAST;
