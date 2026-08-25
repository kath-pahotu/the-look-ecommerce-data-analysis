CREATE SCHEMA IF NOT EXISTS mart;

CREATE OR REPLACE TABLE mart.funnel_stage_channel AS
WITH stage_counts AS (
    SELECT traffic_source, 1 AS stage_order, 'Sessions' AS stage, COUNT(*) AS stage_sessions
    FROM core.fact_session GROUP BY traffic_source
    UNION ALL
    SELECT traffic_source, 2, 'Product Viewed', SUM(product_view_flag)
    FROM core.fact_session GROUP BY traffic_source
    UNION ALL
    SELECT traffic_source, 3, 'Cart Reached', SUM(cart_flag)
    FROM core.fact_session GROUP BY traffic_source
    UNION ALL
    SELECT traffic_source, 4, 'Purchase', SUM(purchase_flag)
    FROM core.fact_session GROUP BY traffic_source
),
windowed AS (
    SELECT
        *,
        FIRST_VALUE(stage_sessions) OVER (PARTITION BY traffic_source ORDER BY stage_order) AS initial_sessions,
        LAG(stage_sessions) OVER (PARTITION BY traffic_source ORDER BY stage_order) AS previous_stage_sessions
    FROM stage_counts
)
SELECT
    traffic_source,
    stage_order,
    stage,
    stage_sessions,
    stage_sessions::DOUBLE / NULLIF(initial_sessions, 0) AS conversion_from_session_rate,
    stage_sessions::DOUBLE / NULLIF(previous_stage_sessions, 0) AS conversion_from_previous_stage_rate
FROM windowed;

CREATE OR REPLACE TABLE mart.funnel_monthly_channel AS
SELECT
    date_trunc('month', session_start_at)::DATE AS month_start,
    traffic_source,
    COUNT(*) AS sessions,
    COUNT(DISTINCT customer_id) AS users,
    SUM(product_view_flag) AS product_view_sessions,
    SUM(cart_flag) AS cart_sessions,
    SUM(purchase_flag) AS purchase_sessions,
    SUM(cart_abandoned_flag) AS abandoned_cart_sessions,
    SUM(purchase_flag)::DOUBLE / COUNT(*) AS session_conversion_rate,
    SUM(cart_abandoned_flag)::DOUBLE / NULLIF(SUM(cart_flag), 0) AS cart_abandonment_rate,
    AVG(event_count) AS avg_events_per_session,
    AVG(session_duration_seconds) AS avg_session_duration_seconds,
    AVG(event_identity_coverage_rate) AS avg_event_identity_coverage_rate
FROM core.fact_session
GROUP BY month_start, traffic_source;

CREATE OR REPLACE TABLE mart.cart_abandonment_segments AS
WITH segments AS (
    SELECT 'Traffic Source' AS segment_type, traffic_source AS segment_value,
           COUNT(*) AS sessions, SUM(cart_flag) AS cart_sessions,
           SUM(cart_abandoned_flag) AS abandoned_cart_sessions, SUM(purchase_flag) AS purchase_sessions
    FROM core.fact_session GROUP BY traffic_source
    UNION ALL
    SELECT 'Browser', browser, COUNT(*), SUM(cart_flag), SUM(cart_abandoned_flag), SUM(purchase_flag)
    FROM core.fact_session GROUP BY browser
    UNION ALL
    SELECT 'Country', country, COUNT(*), SUM(cart_flag), SUM(cart_abandoned_flag), SUM(purchase_flag)
    FROM core.fact_session GROUP BY country
)
SELECT
    *,
    abandoned_cart_sessions::DOUBLE / NULLIF(cart_sessions, 0) AS cart_abandonment_rate,
    purchase_sessions::DOUBLE / NULLIF(sessions, 0) AS session_conversion_rate
FROM segments
WHERE sessions >= 500;

CREATE OR REPLACE TABLE mart.channel_quality AS
SELECT
    traffic_source,
    COUNT(*) AS sessions,
    COUNT(DISTINCT customer_id) AS users,
    SUM(cart_flag) AS cart_sessions,
    SUM(purchase_flag) AS purchase_sessions,
    SUM(cart_abandoned_flag) AS abandoned_cart_sessions,
    AVG(event_count) AS avg_events_per_session,
    AVG(event_identity_coverage_rate) AS avg_event_identity_coverage_rate,
    SUM(purchase_flag)::DOUBLE / NULLIF(COUNT(*), 0) AS session_conversion_rate,
    SUM(cart_abandoned_flag)::DOUBLE / NULLIF(SUM(cart_flag), 0) AS cart_abandonment_rate
FROM core.fact_session
GROUP BY traffic_source;

CREATE OR REPLACE TABLE mart.acquisition_source_value AS
SELECT
    acquisition_source,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    SUM(gross_sales_value) AS gross_sales_value,
    SUM(net_sales_value) AS net_sales_value,
    SUM(net_profit_value) AS net_profit_value,
    SUM(net_sales_value) / NULLIF(COUNT(DISTINCT customer_id), 0) AS net_sales_per_customer
FROM core.fact_order_item
GROUP BY acquisition_source;
