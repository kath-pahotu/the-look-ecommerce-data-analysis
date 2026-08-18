/* ============================================================
   04_mart_acquisition_funnel.sql

   Purpose:
   Create acquisition, channel, funnel and abandonment marts.

   Inputs:
   - core.fact_session
   - core.fact_order_item

   Outputs:
   - mart.funnel_stage_channel
   - mart.funnel_monthly_channel
   - mart.cart_abandonment_segments
   - mart.channel_quality
   - mart.acquisition_source_value
   ============================================================ */

CREATE SCHEMA IF NOT EXISTS mart;


/* ============================================================
   1. FUNNEL STAGE BY CHANNEL

   Grain:
   One row per traffic source and funnel stage.
   ============================================================ */

CREATE OR REPLACE TABLE mart.funnel_stage_channel AS

WITH stage_counts AS (

    SELECT
        traffic_source,
        1 AS stage_order,
        'Sessions' AS stage,
        COUNT(*) AS stage_sessions
    FROM core.fact_session
    GROUP BY traffic_source

    UNION ALL

    SELECT
        traffic_source,
        2 AS stage_order,
        'Product Viewed' AS stage,
        SUM(product_view_flag) AS stage_sessions
    FROM core.fact_session
    GROUP BY traffic_source

    UNION ALL

    SELECT
        traffic_source,
        3 AS stage_order,
        'Cart Reached' AS stage,
        SUM(cart_flag) AS stage_sessions
    FROM core.fact_session
    GROUP BY traffic_source

    UNION ALL

    SELECT
        traffic_source,
        4 AS stage_order,
        'Purchase' AS stage,
        SUM(purchase_flag) AS stage_sessions
    FROM core.fact_session
    GROUP BY traffic_source
),

windowed AS (

    SELECT
        *,

        FIRST_VALUE(stage_sessions) OVER (
            PARTITION BY traffic_source
            ORDER BY stage_order
        ) AS initial_sessions,

        LAG(stage_sessions) OVER (
            PARTITION BY traffic_source
            ORDER BY stage_order
        ) AS previous_stage_sessions

    FROM stage_counts
)

SELECT
    traffic_source,
    stage_order,
    stage,
    stage_sessions,

    stage_sessions::DOUBLE
        / NULLIF(initial_sessions, 0)
        AS conversion_from_session_rate,

    stage_sessions::DOUBLE
        / NULLIF(previous_stage_sessions, 0)
        AS conversion_from_previous_stage_rate

FROM windowed;


/* ============================================================
   2. MONTHLY FUNNEL BY CHANNEL

   Grain:
   One row per month and traffic source.
   ============================================================ */

CREATE OR REPLACE TABLE mart.funnel_monthly_channel AS

SELECT
    date_trunc(
        'month',
        session_start_at
    )::DATE AS month_start,

    traffic_source,

    COUNT(*) AS sessions,

    COUNT(DISTINCT customer_id) AS users,

    SUM(product_view_flag)
        AS product_view_sessions,

    SUM(cart_flag)
        AS cart_sessions,

    SUM(purchase_flag)
        AS purchase_sessions,

    SUM(cart_abandoned_flag)
        AS abandoned_cart_sessions,

    SUM(purchase_flag)::DOUBLE
        / NULLIF(COUNT(*), 0)
        AS session_conversion_rate,

    SUM(cart_abandoned_flag)::DOUBLE
        / NULLIF(SUM(cart_flag), 0)
        AS cart_abandonment_rate,

    AVG(event_count)
        AS avg_events_per_session,

    AVG(session_duration_seconds)
        AS avg_session_duration_seconds,

    AVG(event_identity_coverage_rate)
        AS avg_event_identity_coverage_rate

FROM core.fact_session

GROUP BY
    month_start,
    traffic_source;


/* ============================================================
   3. CART ABANDONMENT SEGMENTS (mart.cart_abandonment_segments)

   Grain:
   One row per segment type and segment value.

   Minimum sample:
   At least 500 sessions.
   ============================================================ */

CREATE OR REPLACE TABLE mart.cart_abandonment_segments AS

WITH segments AS (

    SELECT
        'Traffic Source' AS segment_type,
        traffic_source AS segment_value,
        COUNT(*) AS sessions,
        SUM(cart_flag) AS cart_sessions,
        SUM(cart_abandoned_flag)
            AS abandoned_cart_sessions,
        SUM(purchase_flag) AS purchase_sessions

    FROM core.fact_session

    GROUP BY traffic_source

    UNION ALL

    SELECT
        'Browser' AS segment_type,
        browser AS segment_value,
        COUNT(*) AS sessions,
        SUM(cart_flag) AS cart_sessions,
        SUM(cart_abandoned_flag)
            AS abandoned_cart_sessions,
        SUM(purchase_flag) AS purchase_sessions

    FROM core.fact_session

    GROUP BY browser

    UNION ALL

    SELECT
        'Country' AS segment_type,
        country AS segment_value,
        COUNT(*) AS sessions,
        SUM(cart_flag) AS cart_sessions,
        SUM(cart_abandoned_flag)
            AS abandoned_cart_sessions,
        SUM(purchase_flag) AS purchase_sessions

    FROM core.fact_session

    GROUP BY country
)

SELECT
    segment_type,
    segment_value,
    sessions,
    cart_sessions,
    abandoned_cart_sessions,
    purchase_sessions,

    abandoned_cart_sessions::DOUBLE
        / NULLIF(cart_sessions, 0)
        AS cart_abandonment_rate,

    purchase_sessions::DOUBLE
        / NULLIF(sessions, 0)
        AS session_conversion_rate

FROM segments

WHERE sessions >= 500;


/* ============================================================
   4. CHANNEL QUALITY

   Grain:
   One row per session traffic source.
   ============================================================ */

CREATE OR REPLACE TABLE mart.channel_quality AS

SELECT
    traffic_source,

    COUNT(*) AS sessions,

    COUNT(DISTINCT customer_id) AS users,

    SUM(cart_flag) AS cart_sessions,

    SUM(purchase_flag) AS purchase_sessions,

    SUM(cart_abandoned_flag)
        AS abandoned_cart_sessions,

    AVG(event_count)
        AS avg_events_per_session,

    AVG(event_identity_coverage_rate)
        AS avg_event_identity_coverage_rate,

    SUM(purchase_flag)::DOUBLE
        / NULLIF(COUNT(*), 0)
        AS session_conversion_rate,

    SUM(cart_abandoned_flag)::DOUBLE
        / NULLIF(SUM(cart_flag), 0)
        AS cart_abandonment_rate

FROM core.fact_session

GROUP BY traffic_source;


/* ============================================================
   5. ACQUISITION-SOURCE VALUE

   Grain:
   One row per customer acquisition source.

   Note:
   Acquisition source describes how the customer was originally
   acquired. It is different from session traffic source.
   ============================================================ */

CREATE OR REPLACE TABLE mart.acquisition_source_value AS

SELECT
    acquisition_source,

    COUNT(DISTINCT order_id) AS orders,

    COUNT(DISTINCT customer_id) AS customers,

    SUM(gross_sales_value)
        AS gross_sales_value,

    SUM(net_sales_value)
        AS net_sales_value,

    SUM(net_profit_value)
        AS net_profit_value,

    SUM(net_sales_value)
        / NULLIF(
            COUNT(DISTINCT customer_id),
            0
        ) AS net_sales_per_customer

FROM core.fact_order_item

GROUP BY acquisition_source;