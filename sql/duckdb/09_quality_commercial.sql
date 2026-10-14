-- =====================================================================
-- 09_quality_commercial.sql
-- Quality gates for the commercial planning layer, plus an end-to-end
-- reconciliation statement that can be handed to a reviewer as-is.
--
-- Same convention as 07: `severity` is the label, `blocking` decides
-- whether a non-zero failure count stops the build. Submission defects are
-- deliberately NON-blocking - an imperfect regional submission is a normal
-- condition to report back, not a reason to refuse to publish the numbers.
-- Structural defects (unmapped country, broken grain, FX that does not tie)
-- are blocking, because they would make the consolidated figure wrong.
-- =====================================================================

CREATE OR REPLACE TABLE qa.plan_validation AS
WITH plan_month_bounds AS (
    SELECT canonical_country, MIN(plan_month) AS first_month, MAX(plan_month) AS last_month
    FROM core.fact_plan
    GROUP BY 1
),
expected_months AS (
    SELECT b.canonical_country, CAST(m.value AS DATE) AS plan_month
    FROM plan_month_bounds b,
         generate_series(b.first_month, b.last_month, INTERVAL 1 MONTH) AS m(value)
),
month_gaps AS (
    SELECT COUNT(*) AS gap_count
    FROM expected_months e
    LEFT JOIN core.fact_plan p
      ON e.canonical_country = p.canonical_country AND e.plan_month = p.plan_month
    WHERE p.canonical_country IS NULL
),
pvm_residual AS (
    SELECT COUNT(*) AS broken_comparisons
    FROM (
        SELECT comparison_label,
               ABS(SUM(volume_effect) + SUM(mix_effect) + SUM(price_effect)
                   - SUM(total_variance)) AS residual
        FROM mart.price_volume_mix
        GROUP BY 1
    )
    WHERE residual > 0.01
),
checks AS (
    SELECT 'plan_country_resolves_to_master' AS check_name, 'stg' AS layer,
           'CRITICAL' AS severity, 1 AS blocking,
           (SELECT COUNT(*) FROM stg.plan_submissions WHERE flag_unmapped_country = 1) AS failure_count,
           (SELECT COUNT(*) FROM stg.plan_submissions) AS denominator,
           'Every submitted country spelling maps to a canonical country' AS notes
    UNION ALL
    SELECT 'plan_currency_has_budget_rate', 'stg', 'CRITICAL', 1,
           (SELECT COUNT(*) FROM stg.plan_submissions WHERE flag_missing_fx_rate = 1),
           (SELECT COUNT(*) FROM stg.plan_submissions),
           'Every submitted currency has a budget FX rate'
    UNION ALL
    SELECT 'plan_grain_unique_country_month', 'core', 'CRITICAL', 1,
           (SELECT COUNT(*) FROM core.fact_plan)
           - (SELECT COUNT(*) FROM (SELECT DISTINCT canonical_country, plan_month FROM core.fact_plan)),
           (SELECT COUNT(*) FROM core.fact_plan),
           'fact_plan holds one row per country per month'
    UNION ALL
    SELECT 'plan_consolidation_ties_to_submissions', 'core', 'CRITICAL', 1,
           CASE WHEN ABS(
                (SELECT COALESCE(SUM(plan_net_sales_usd), 0) FROM core.fact_plan)
              - (SELECT COALESCE(SUM(plan_net_sales_usd), 0) FROM stg.plan_submissions
                 WHERE flag_unmapped_country = 0 AND flag_missing_fx_rate = 0
                   AND flag_blank_target = 0 AND flag_negative_target = 0)
           ) > 0.01 THEN 1 ELSE 0 END,
           1,
           'Consolidated plan equals the sum of accepted submission rows'
    UNION ALL
    SELECT 'plan_fx_conversion_reconciles', 'stg', 'CRITICAL', 1,
           (SELECT COUNT(*) FROM stg.plan_submissions
            WHERE plan_net_sales_local IS NOT NULL
              AND budget_rate_to_usd IS NOT NULL
              AND ABS(plan_net_sales_usd - plan_net_sales_local * budget_rate_to_usd) > 0.01),
           (SELECT COUNT(*) FROM stg.plan_submissions),
           'Local-to-USD conversion reproduces exactly at the budget rate'
    UNION ALL
    SELECT 'actuals_tie_to_fact_order_item', 'mart', 'CRITICAL', 1,
           CASE WHEN ABS(
                (SELECT COALESCE(SUM(net_sales_value), 0) FROM mart.actual_country_month)
              - (SELECT COALESCE(SUM(net_sales_value), 0) FROM core.fact_order_item)
           ) > 0.01 THEN 1 ELSE 0 END,
           1,
           'Country-grain actuals reconcile to the item fact with no leakage'
    UNION ALL
    SELECT 'pvm_decomposition_is_exact', 'mart', 'CRITICAL', 1,
           (SELECT broken_comparisons FROM pvm_residual),
           (SELECT COUNT(DISTINCT comparison_label) FROM mart.price_volume_mix),
           'Volume + mix + price effects sum back to total variance per comparison'
    UNION ALL
    SELECT 'plan_target_not_blank', 'stg', 'HIGH', 0,
           (SELECT COUNT(*) FROM stg.plan_submissions WHERE flag_blank_target = 1),
           (SELECT COUNT(*) FROM stg.plan_submissions),
           'Blank plan cells are quarantined and returned to the submitting region'
    UNION ALL
    SELECT 'plan_target_not_negative', 'stg', 'HIGH', 0,
           (SELECT COUNT(*) FROM stg.plan_submissions WHERE flag_negative_target = 1),
           (SELECT COUNT(*) FROM stg.plan_submissions),
           'Negative targets indicate a sign error in the submitted file'
    UNION ALL
    SELECT 'plan_month_coverage_contiguous', 'core', 'HIGH', 0,
           (SELECT gap_count FROM month_gaps),
           (SELECT COUNT(*) FROM core.fact_plan),
           'A gap means a region submitted late or skipped a period'
    UNION ALL
    SELECT 'plan_country_key_clean', 'stg', 'MEDIUM', 0,
           (SELECT COUNT(*) FROM stg.plan_submissions WHERE flag_whitespace_in_key = 1),
           (SELECT COUNT(*) FROM stg.plan_submissions),
           'Whitespace in a join key silently creates an unmatched market'
    UNION ALL
    SELECT 'scorecard_has_reporting_month', 'mart', 'HIGH', 0,
           (SELECT COUNT(*) FROM mart.commercial_scorecard WHERE actual_value IS NULL),
           (SELECT COUNT(*) FROM mart.commercial_scorecard),
           'Every scorecard KPI resolved a value for the reporting month'
)
SELECT
    check_name,
    layer,
    severity,
    failure_count,
    denominator,
    failure_count::DOUBLE / NULLIF(denominator, 0) AS failure_rate,
    CASE
        WHEN failure_count = 0 THEN 'PASS'
        WHEN blocking = 1 THEN 'FAIL'
        ELSE 'WARN'
    END AS status,
    notes
FROM checks;

-- ---------------------------------------------------------------------
-- End-to-end reconciliation statement
--
-- One readable table showing what entered the warehouse, what survived each
-- layer, and where any difference comes from. This is the artifact to open
-- when someone asks "how do I know the dashboard number is right?".
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE qa.reconciliation_statement AS
WITH steps(step_order, stream, stage, entity, row_count, value_usd, expectation) AS (
    VALUES
        (1, 'Sales', 'Source file', 'order_items.csv',
         (SELECT COUNT(*) FROM raw.order_items)::BIGINT,
         (SELECT SUM(sale_price) FROM raw.order_items)::DOUBLE,
         'Baseline: rows and gross value as delivered'),
        (2, 'Sales', 'stg', 'stg.order_items',
         (SELECT COUNT(*) FROM stg.order_items)::BIGINT,
         (SELECT SUM(sale_price) FROM stg.order_items)::DOUBLE,
         'Typing and renaming only - must equal source'),
        (3, 'Sales', 'core', 'core.fact_order_item',
         (SELECT COUNT(*) FROM core.fact_order_item)::BIGINT,
         (SELECT SUM(gross_sales_value) FROM core.fact_order_item)::DOUBLE,
         'Joins to product and customer - must not drop rows'),
        (4, 'Sales', 'mart', 'mart.actual_country_month',
         (SELECT SUM(net_units) FROM mart.actual_country_month)::BIGINT,
         (SELECT SUM(gross_sales_value) FROM mart.actual_country_month)::DOUBLE,
         'Aggregated to country x month - gross value must still tie'),
        (5, 'Plan', 'Source file', 'regional_plan_submissions.csv',
         (SELECT COUNT(*) FROM raw.plan_submissions)::BIGINT,
         NULL::DOUBLE,
         'Submitted in local currency - no USD value yet'),
        (6, 'Plan', 'stg', 'stg.plan_submissions',
         (SELECT COUNT(*) FROM stg.plan_submissions)::BIGINT,
         (SELECT SUM(plan_net_sales_usd) FROM stg.plan_submissions)::DOUBLE,
         'Harmonised and FX-converted - row count must equal source'),
        (7, 'Plan', 'qa', 'qa.plan_rejects',
         (SELECT COUNT(*) FROM qa.plan_rejects)::BIGINT,
         NULL::DOUBLE,
         'Quarantined rows, reported back to the submitting region'),
        (8, 'Plan', 'core', 'core.fact_plan',
         (SELECT COUNT(*) FROM core.fact_plan)::BIGINT,
         (SELECT SUM(plan_net_sales_usd) FROM core.fact_plan)::DOUBLE,
         'Accepted rows only - source rows minus rejects')
)
SELECT
    step_order,
    stream,
    stage,
    entity,
    row_count,
    value_usd,
    row_count - LAG(row_count) OVER (PARTITION BY stream ORDER BY step_order) AS row_delta,
    value_usd - LAG(value_usd) OVER (PARTITION BY stream ORDER BY step_order) AS value_delta,
    expectation
FROM steps
ORDER BY stream, step_order;
