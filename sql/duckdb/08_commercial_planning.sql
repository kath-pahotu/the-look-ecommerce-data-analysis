-- =====================================================================
-- 08_commercial_planning.sql
-- Commercial planning and performance-management layer.
--
-- Adds a SECOND source system to the warehouse: regional plan submissions
-- arriving as a flat file in local currency with the master-data and
-- completeness defects that real planning cycles produce. Everything here
-- follows the same raw -> stg -> core -> mart discipline as the sales side.
--
-- The conformed country, market and month dimensions this layer depends on
-- live in 02_core_dimensions.sql, because the sales marts need them too.
--
-- Contents
--   2. stg.plan_submissions        harmonised, FX-converted, defect-flagged
--   3. qa.plan_rejects             quarantined rows with a stated reason
--   4. core.fact_plan              clean plan at country x month, USD
--   5. mart.actual_country_month   actuals on the conformed country grain
--   6. mart.plan_vs_actual_monthly country x month variance
--   7. mart.plan_vs_actual_region  region roll-up
--   8. mart.price_volume_mix       three-way revenue bridge
--   9. mart.commercial_scorecard   one-page management scorecard
-- =====================================================================

-- ---------------------------------------------------------------------
-- 2. Staging the plan submissions
--
-- Cleaning applied, in order:
--   trim whitespace from the submitted country name
--   map the submitted spelling to a canonical country via the seed
--   convert local currency to USD at the fixed budget rate
--   raise one flag per validation rule rather than silently dropping rows
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW stg.plan_submissions AS
WITH trimmed AS (
    SELECT
        submission_batch,
        submitted_country,
        TRIM(submitted_country) AS submitted_country_trimmed,
        CAST(plan_month AS DATE) AS plan_month,
        UPPER(TRIM(currency_code)) AS currency_code,
        CAST(plan_net_sales_local AS DOUBLE) AS plan_net_sales_local,
        CAST(plan_units AS BIGINT) AS plan_units
    FROM raw.plan_submissions
),
mapped AS (
    SELECT
        t.*,
        c.canonical_country,
        c.region,
        c.sub_region,
        f.budget_rate_to_usd
    FROM trimmed t
    LEFT JOIN (
        SELECT DISTINCT source_country_value, canonical_country, region, sub_region
        FROM core.dim_country
    ) c ON t.submitted_country_trimmed = c.source_country_value
    LEFT JOIN raw.fx_budget_rates f ON t.currency_code = f.currency_code
)
SELECT
    submission_batch,
    submitted_country,
    submitted_country_trimmed,
    canonical_country,
    region,
    sub_region,
    plan_month,
    currency_code,
    budget_rate_to_usd,
    plan_net_sales_local,
    plan_net_sales_local * budget_rate_to_usd AS plan_net_sales_usd,
    plan_units,
    CASE WHEN canonical_country IS NULL THEN 1 ELSE 0 END AS flag_unmapped_country,
    CASE WHEN budget_rate_to_usd IS NULL THEN 1 ELSE 0 END AS flag_missing_fx_rate,
    CASE WHEN plan_net_sales_local IS NULL THEN 1 ELSE 0 END AS flag_blank_target,
    CASE WHEN plan_net_sales_local < 0 THEN 1 ELSE 0 END AS flag_negative_target,
    CASE WHEN submitted_country <> TRIM(submitted_country) THEN 1 ELSE 0 END AS flag_whitespace_in_key
FROM mapped;

-- ---------------------------------------------------------------------
-- 3. Quarantine
--
-- A row is rejected when it cannot be used for reporting at all: no
-- canonical country, no FX rate, no target, or a negative target. Rejected
-- rows are kept with a reason so they can be sent back to the submitting
-- region, which is what a planning analyst actually does with them. The
-- build is not failed - an imperfect submission is normal, silently
-- dropping it is not.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE qa.plan_rejects AS
SELECT
    submission_batch,
    submitted_country,
    plan_month,
    currency_code,
    plan_net_sales_local,
    CASE
        WHEN flag_unmapped_country = 1 THEN 'Country not present in the country master'
        WHEN flag_missing_fx_rate = 1 THEN 'No budget FX rate for the submitted currency'
        WHEN flag_blank_target = 1 THEN 'Plan value is blank'
        WHEN flag_negative_target = 1 THEN 'Plan value is negative'
    END AS reject_reason
FROM stg.plan_submissions
WHERE flag_unmapped_country = 1
   OR flag_missing_fx_rate = 1
   OR flag_blank_target = 1
   OR flag_negative_target = 1;

-- ---------------------------------------------------------------------
-- 4. core.fact_plan
-- Grain: one row per canonical country per plan month.
-- Rows that survived quarantine only.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE core.fact_plan AS
SELECT
    canonical_country,
    region,
    sub_region,
    plan_month,
    CAST(strftime(plan_month, '%Y%m%d') AS INTEGER) AS plan_date_key,
    currency_code,
    budget_rate_to_usd,
    SUM(plan_net_sales_local) AS plan_net_sales_local,
    SUM(plan_net_sales_usd) AS plan_net_sales_usd,
    SUM(plan_units) AS plan_units,
    MAX(submission_batch) AS submission_batch
FROM stg.plan_submissions
WHERE flag_unmapped_country = 0
  AND flag_missing_fx_rate = 0
  AND flag_blank_target = 0
  AND flag_negative_target = 0
GROUP BY 1, 2, 3, 4, 5, 6, 7;

-- ---------------------------------------------------------------------
-- 5. Actuals on the conformed country grain
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE mart.actual_country_month AS
SELECT
    co.canonical_country,
    co.region,
    co.sub_region,
    date_trunc('month', f.order_item_created_at)::DATE AS month_start,
    d.fiscal_year,
    d.fiscal_quarter_label,
    d.is_complete_month,
    SUM(f.gross_sales_value) AS gross_sales_value,
    SUM(f.net_sales_value) AS net_sales_value,
    SUM(f.net_profit_value) AS net_profit_value,
    SUM(CASE WHEN f.item_status NOT IN ('Cancelled', 'Returned') THEN 1 ELSE 0 END) AS net_units,
    COUNT(DISTINCT f.order_id) AS orders,
    COUNT(DISTINCT f.customer_id) AS customers
FROM core.fact_order_item f
JOIN core.dim_customer cu ON f.customer_id = cu.user_id
JOIN (
    SELECT DISTINCT source_country_value, canonical_country, region, sub_region
    FROM core.dim_country
) co ON cu.country = co.source_country_value
JOIN core.dim_date d ON f.order_date_key = d.date_key
GROUP BY 1, 2, 3, 4, 5, 6, 7;

-- ---------------------------------------------------------------------
-- 6. Plan vs actual, country x month
--
-- FULL OUTER JOIN on purpose: a month present in the plan but absent from
-- actuals (a future month) and a month present in actuals but absent from
-- the plan (a region that never submitted) are both real conditions that a
-- consolidation report has to surface rather than hide.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE mart.plan_vs_actual_monthly AS
SELECT
    COALESCE(a.canonical_country, p.canonical_country) AS canonical_country,
    COALESCE(a.region, p.region) AS region,
    COALESCE(a.month_start, p.plan_month) AS month_start,
    a.net_sales_value AS actual_net_sales_usd,
    a.net_units AS actual_units,
    p.plan_net_sales_usd,
    p.plan_units,
    a.net_sales_value - p.plan_net_sales_usd AS variance_usd,
    CASE WHEN p.plan_net_sales_usd > 0
         THEN (a.net_sales_value - p.plan_net_sales_usd) / p.plan_net_sales_usd END AS variance_rate,
    CASE WHEN p.plan_net_sales_usd > 0
         THEN a.net_sales_value / p.plan_net_sales_usd END AS achievement_rate,
    COALESCE(a.is_complete_month, 0) AS is_complete_month,
    CASE WHEN COALESCE(a.month_start, p.plan_month)
              BETWEEN (SELECT MIN(plan_month) FROM core.fact_plan)
                  AND (SELECT MAX(plan_month) FROM core.fact_plan)
         THEN 1 ELSE 0 END AS in_plan_horizon,
    CASE
        WHEN p.plan_net_sales_usd IS NULL THEN 'Actual with no plan'
        WHEN a.net_sales_value IS NULL THEN 'Plan with no actual yet'
        WHEN a.net_sales_value >= p.plan_net_sales_usd THEN 'On or above plan'
        WHEN a.net_sales_value >= p.plan_net_sales_usd * 0.95 THEN 'Within 5% of plan'
        ELSE 'Below plan'
    END AS plan_status
FROM mart.actual_country_month a
FULL OUTER JOIN core.fact_plan p
  ON a.canonical_country = p.canonical_country
 AND a.month_start = p.plan_month;

-- ---------------------------------------------------------------------
-- 7. Region roll-up over the overlap window only
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE mart.plan_vs_actual_region AS
SELECT
    region,
    date_trunc('year', month_start)::DATE AS plan_year,
    SUM(actual_net_sales_usd) AS actual_net_sales_usd,
    SUM(plan_net_sales_usd) AS plan_net_sales_usd,
    SUM(actual_net_sales_usd) - SUM(plan_net_sales_usd) AS variance_usd,
    CASE WHEN SUM(plan_net_sales_usd) > 0
         THEN SUM(actual_net_sales_usd) / SUM(plan_net_sales_usd) END AS achievement_rate,
    COUNT(*) AS month_rows,
    SUM(CASE WHEN plan_net_sales_usd IS NULL THEN 1 ELSE 0 END) AS months_without_plan
FROM mart.plan_vs_actual_monthly
WHERE actual_net_sales_usd IS NOT NULL
  AND is_complete_month = 1
  AND in_plan_horizon = 1
GROUP BY 1, 2;

-- ---------------------------------------------------------------------
-- 8. Price-Volume-Mix bridge
--
-- Decomposes a net-sales change between two periods into three causes at
-- product-category level. The decomposition is exact: the three effects
-- sum back to the total variance.
--
--   volume = (Q1 - Q0) * s0 * P0     growth held at prior mix and prior price
--   mix    = Q1 * (s1 - s0) * P0     mix shift held at prior price
--   price  = Q1_i * (P1 - P0)        price movement at current volume
--
-- where Q is units, P is average selling price, and s is a category's share
-- of total units in the period.
--
-- Periods excluded: May 2024 is incomplete and never enters a comparison.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE mart.price_volume_mix AS
WITH comparisons(comparison_label, comparison_order,
                 prior_from, prior_to, current_from, current_to) AS (
    VALUES
        ('CY2023 vs CY2022', 1,
         DATE '2022-01-01', DATE '2022-12-31', DATE '2023-01-01', DATE '2023-12-31'),
        ('YTD Jan-Apr 2024 vs 2023', 2,
         DATE '2023-01-01', DATE '2023-04-30', DATE '2024-01-01', DATE '2024-04-30'),
        ('Apr 2024 vs Apr 2023', 3,
         DATE '2023-04-01', DATE '2023-04-30', DATE '2024-04-01', DATE '2024-04-30')
),
items AS (
    SELECT
        f.order_item_created_at::DATE AS activity_date,
        p.department,
        p.category,
        f.net_sales_value
    FROM core.fact_order_item f
    JOIN core.dim_product p ON f.product_id = p.product_id
    WHERE f.item_status NOT IN ('Cancelled', 'Returned')
),
sided AS (
    SELECT
        c.comparison_label,
        c.comparison_order,
        i.department,
        i.category,
        CASE
            WHEN i.activity_date BETWEEN c.prior_from AND c.prior_to THEN 'prior'
            WHEN i.activity_date BETWEEN c.current_from AND c.current_to THEN 'current'
        END AS period_side,
        i.net_sales_value
    FROM comparisons c
    JOIN items i
      ON i.activity_date BETWEEN c.prior_from AND c.prior_to
      OR i.activity_date BETWEEN c.current_from AND c.current_to
),
by_category AS (
    SELECT
        comparison_label,
        comparison_order,
        department,
        category,
        SUM(CASE WHEN period_side = 'prior' THEN net_sales_value ELSE 0 END) AS revenue_prior,
        SUM(CASE WHEN period_side = 'current' THEN net_sales_value ELSE 0 END) AS revenue_current,
        SUM(CASE WHEN period_side = 'prior' THEN 1 ELSE 0 END) AS units_prior,
        SUM(CASE WHEN period_side = 'current' THEN 1 ELSE 0 END) AS units_current
    FROM sided
    GROUP BY 1, 2, 3, 4
),
totals AS (
    SELECT
        comparison_label,
        SUM(units_prior) AS total_units_prior,
        SUM(units_current) AS total_units_current
    FROM by_category
    GROUP BY 1
),
effects AS (
    SELECT
        b.comparison_label,
        b.comparison_order,
        b.department,
        b.category,
        b.units_prior,
        b.units_current,
        b.revenue_prior,
        b.revenue_current,
        CASE WHEN b.units_prior > 0 THEN b.revenue_prior / b.units_prior END AS asp_prior,
        CASE WHEN b.units_current > 0 THEN b.revenue_current / b.units_current END AS asp_current,
        CASE WHEN t.total_units_prior > 0 THEN b.units_prior::DOUBLE / t.total_units_prior END AS share_prior,
        CASE WHEN t.total_units_current > 0 THEN b.units_current::DOUBLE / t.total_units_current END AS share_current,
        t.total_units_prior,
        t.total_units_current
    FROM by_category b
    JOIN totals t ON b.comparison_label = t.comparison_label
)
SELECT
    comparison_label,
    comparison_order,
    department,
    category,
    units_prior,
    units_current,
    revenue_prior,
    revenue_current,
    asp_prior,
    asp_current,
    revenue_current - revenue_prior AS total_variance,
    COALESCE((total_units_current - total_units_prior) * share_prior * asp_prior, 0) AS volume_effect,
    COALESCE(total_units_current * (share_current - share_prior) * asp_prior, 0) AS mix_effect,
    COALESCE(units_current * (asp_current - asp_prior), 0) AS price_effect
FROM effects;

-- ---------------------------------------------------------------------
-- 9. One-page commercial scorecard
--
-- Latest complete month against prior month, same month last year, and
-- plan. This is the artifact a commercial analyst publishes monthly.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE mart.commercial_scorecard AS
WITH anchor AS (
    SELECT MAX(month_start) AS current_month
    FROM mart.sales_monthly
    WHERE is_complete_month = 1
),
periods AS (
    SELECT
        current_month,
        (current_month - INTERVAL 1 MONTH)::DATE AS prior_month,
        (current_month - INTERVAL 1 YEAR)::DATE AS last_year_month
    FROM anchor
),
monthly AS (
    SELECT
        month_start,
        net_sales_value,
        net_profit_value,
        net_margin_rate,
        orders,
        customers,
        items,
        average_order_value,
        item_return_rate,
        item_cancellation_rate
    FROM mart.sales_monthly
),
plan_month AS (
    SELECT plan_month, SUM(plan_net_sales_usd) AS plan_net_sales_usd, SUM(plan_units) AS plan_units
    FROM core.fact_plan
    GROUP BY 1
),
facts AS (
    SELECT
        p.current_month,
        c.net_sales_value   AS cur_net_sales,
        c.net_profit_value  AS cur_net_profit,
        c.net_margin_rate   AS cur_margin_rate,
        c.orders            AS cur_orders,
        c.customers         AS cur_customers,
        c.items             AS cur_units,
        c.average_order_value AS cur_aov,
        c.item_return_rate  AS cur_return_rate,
        c.item_cancellation_rate AS cur_cancel_rate,
        m.net_sales_value   AS pm_net_sales,
        m.net_profit_value  AS pm_net_profit,
        m.net_margin_rate   AS pm_margin_rate,
        m.orders            AS pm_orders,
        m.customers         AS pm_customers,
        m.items             AS pm_units,
        m.average_order_value AS pm_aov,
        m.item_return_rate  AS pm_return_rate,
        m.item_cancellation_rate AS pm_cancel_rate,
        y.net_sales_value   AS ly_net_sales,
        y.net_profit_value  AS ly_net_profit,
        y.net_margin_rate   AS ly_margin_rate,
        y.orders            AS ly_orders,
        y.customers         AS ly_customers,
        y.items             AS ly_units,
        y.average_order_value AS ly_aov,
        y.item_return_rate  AS ly_return_rate,
        y.item_cancellation_rate AS ly_cancel_rate,
        pl.plan_net_sales_usd,
        pl.plan_units
    FROM periods p
    LEFT JOIN monthly c ON c.month_start = p.current_month
    LEFT JOIN monthly m ON m.month_start = p.prior_month
    LEFT JOIN monthly y ON y.month_start = p.last_year_month
    LEFT JOIN plan_month pl ON pl.plan_month = p.current_month
),
unpivoted AS (
    SELECT 1 AS kpi_order, 'Net Sales' AS kpi_name, 'currency' AS kpi_format,
           cur_net_sales AS actual_value, pm_net_sales AS prior_month_value,
           ly_net_sales AS last_year_value, plan_net_sales_usd AS plan_value,
           current_month FROM facts
    UNION ALL SELECT 2, 'Net Profit', 'currency',
           cur_net_profit, pm_net_profit, ly_net_profit, NULL, current_month FROM facts
    UNION ALL SELECT 3, 'Net Margin Rate', 'percent',
           cur_margin_rate, pm_margin_rate, ly_margin_rate, NULL, current_month FROM facts
    UNION ALL SELECT 4, 'Units Sold', 'number',
           cur_units, pm_units, ly_units, plan_units, current_month FROM facts
    UNION ALL SELECT 5, 'Orders', 'number',
           cur_orders, pm_orders, ly_orders, NULL, current_month FROM facts
    UNION ALL SELECT 6, 'Active Customers', 'number',
           cur_customers, pm_customers, ly_customers, NULL, current_month FROM facts
    UNION ALL SELECT 7, 'Average Order Value', 'currency',
           cur_aov, pm_aov, ly_aov, NULL, current_month FROM facts
    UNION ALL SELECT 8, 'Item Return Rate', 'percent_inverse',
           cur_return_rate, pm_return_rate, ly_return_rate, NULL, current_month FROM facts
    UNION ALL SELECT 9, 'Item Cancellation Rate', 'percent_inverse',
           cur_cancel_rate, pm_cancel_rate, ly_cancel_rate, NULL, current_month FROM facts
)
SELECT
    kpi_order,
    kpi_name,
    kpi_format,
    current_month AS reporting_month,
    actual_value,
    prior_month_value,
    last_year_value,
    plan_value,
    actual_value - prior_month_value AS mom_variance,
    CASE WHEN prior_month_value <> 0
         THEN actual_value / prior_month_value - 1 END AS mom_variance_rate,
    actual_value - last_year_value AS yoy_variance,
    CASE WHEN last_year_value <> 0
         THEN actual_value / last_year_value - 1 END AS yoy_variance_rate,
    actual_value - plan_value AS plan_variance,
    CASE WHEN plan_value <> 0 THEN actual_value / plan_value END AS plan_achievement_rate,
    CASE
        WHEN plan_value IS NULL THEN 'No plan'
        WHEN kpi_format = 'percent_inverse' AND actual_value <= plan_value THEN 'Green'
        WHEN kpi_format = 'percent_inverse' AND actual_value <= plan_value * 1.05 THEN 'Amber'
        WHEN kpi_format = 'percent_inverse' THEN 'Red'
        WHEN actual_value >= plan_value THEN 'Green'
        WHEN actual_value >= plan_value * 0.95 THEN 'Amber'
        ELSE 'Red'
    END AS plan_rag_status
FROM unpivoted
ORDER BY kpi_order;
