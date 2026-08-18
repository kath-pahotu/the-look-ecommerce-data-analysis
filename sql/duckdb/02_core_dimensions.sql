/* ============================================================
   02_core_dimensions.sql

   Purpose:
   Create reusable descriptive dimensions from staging views.

   Inputs:
   - stg.events
   - stg.order_items
   - stg.inventory_events
   - stg.users
   - stg.products
   - stg.distribution_centers
   - stg.sessions

   Outputs:
   - core.dim_date
   - core.dim_customer
   - core.dim_product
   - core.dim_distribution_center
   - core.dim_session_traffic_source
   - core.dim_acquisition_source
   ============================================================ */


CREATE SCHEMA IF NOT EXISTS core;


/* ============================================================
   1. DATE DIMENSION

   Grain:
   One row per calendar date.

   Purpose:
   Provide reusable year, quarter, month, week and weekday
   attributes for Power BI.
   ============================================================ */

CREATE OR REPLACE TABLE core.dim_date AS

WITH date_bounds AS (
    SELECT
        MIN(date_value)::DATE AS min_date,
        MAX(date_value)::DATE AS max_date

    FROM (
        SELECT
            MIN(created_at) AS date_value
        FROM stg.events

        UNION ALL

        SELECT
            MAX(created_at)
        FROM stg.events

        UNION ALL

        SELECT
            MIN(created_at)
        FROM stg.order_items

        UNION ALL

        SELECT
            MAX(created_at)
        FROM stg.order_items

        UNION ALL

        SELECT
            MIN(created_at)
        FROM stg.inventory_events

        UNION ALL

        SELECT
            MAX(
                COALESCE(sold_at, created_at)
            )
        FROM stg.inventory_events
    )
),

calendar AS (
    SELECT
        CAST(value AS DATE) AS calendar_date,
        max_date

    FROM date_bounds,

    generate_series(
        min_date,
        max_date,
        INTERVAL 1 DAY
    ) AS series(value)
)

SELECT
    CAST(
        strftime(calendar_date, '%Y%m%d')
        AS INTEGER
    ) AS date_key,

    calendar_date,

    EXTRACT(
        year FROM calendar_date
    )::INTEGER AS year,

    EXTRACT(
        quarter FROM calendar_date
    )::INTEGER AS quarter_number,

    'Q'
        || EXTRACT(
            quarter FROM calendar_date
        )::INTEGER
        AS quarter_label,

    EXTRACT(
        month FROM calendar_date
    )::INTEGER AS month_number,

    strftime(
        calendar_date,
        '%B'
    ) AS month_name,

    strftime(
        calendar_date,
        '%b %Y'
    ) AS month_year,

    date_trunc(
        'month',
        calendar_date
    )::DATE AS month_start,

    date_trunc(
        'quarter',
        calendar_date
    )::DATE AS quarter_start,

    date_trunc(
        'year',
        calendar_date
    )::DATE AS year_start,

    EXTRACT(
        week FROM calendar_date
    )::INTEGER AS iso_week_number,

    EXTRACT(
        isodow FROM calendar_date
    )::INTEGER AS iso_day_of_week,

    strftime(
        calendar_date,
        '%A'
    ) AS day_name,

    CASE
        WHEN EXTRACT(
            isodow FROM calendar_date
        ) IN (6, 7)
        THEN 1
        ELSE 0
    END AS is_weekend,

    CASE
        WHEN calendar_date
             < date_trunc('month', max_date)
        THEN 1
        ELSE 0
    END AS is_complete_month

FROM calendar;


/* ============================================================
   2. CUSTOMER DIMENSION

   Grain:
   One row per customer.

   Source:
   stg.users
   ============================================================ */

CREATE OR REPLACE TABLE core.dim_customer AS

SELECT
    user_id,

    age,

    CASE
        WHEN age IS NULL THEN 'Unknown'
        WHEN age < 25 THEN '18-24'
        WHEN age < 35 THEN '25-34'
        WHEN age < 45 THEN '35-44'
        WHEN age < 55 THEN '45-54'
        WHEN age < 65 THEN '55-64'
        ELSE '65+'
    END AS age_band,

    gender,

    COALESCE(
        country,
        'Unknown'
    ) AS country,

    COALESCE(
        state,
        'Unknown'
    ) AS state,

    COALESCE(
        city,
        'Unknown'
    ) AS city,

    postal_code,

    latitude,

    longitude,

    acquisition_source,

    registered_at,

    CAST(
        strftime(
            registered_at,
            '%Y%m%d'
        )
        AS INTEGER
    ) AS registered_date_key

FROM stg.users;


/* ============================================================
   3. PRODUCT DIMENSION

   Grain:
   One row per product.

   Source:
   stg.products
   ============================================================ */

CREATE OR REPLACE TABLE core.dim_product AS

SELECT
    product_id,

    category,

    product_name,

    brand,

    department,

    sku,

    distribution_center_id,

    unit_cost,

    retail_price,

    retail_price - unit_cost
        AS unit_margin,

    CASE
        WHEN retail_price > 0
        THEN
            (retail_price - unit_cost)
            / retail_price
    END AS unit_margin_rate,

    CASE
        WHEN retail_price < 25
            THEN 'Under $25'

        WHEN retail_price < 50
            THEN '$25-$49'

        WHEN retail_price < 100
            THEN '$50-$99'

        WHEN retail_price < 200
            THEN '$100-$199'

        ELSE '$200+'
    END AS price_band

FROM stg.products;


/* ============================================================
   4. DISTRIBUTION CENTER DIMENSION

   Grain:
   One row per distribution center.
   ============================================================ */

CREATE OR REPLACE TABLE
    core.dim_distribution_center AS

SELECT
    distribution_center_id,
    distribution_center_name,
    latitude,
    longitude

FROM stg.distribution_centers;


/* ============================================================
   5. SESSION TRAFFIC SOURCE DIMENSION

   Grain:
   One row per distinct session traffic source.

   This describes the source recorded during a website session.
   ============================================================ */

CREATE OR REPLACE TABLE
    core.dim_session_traffic_source AS

SELECT
    ROW_NUMBER() OVER (
        ORDER BY traffic_source
    )::INTEGER AS session_traffic_source_key,

    traffic_source

FROM (
    SELECT DISTINCT
        traffic_source

    FROM stg.sessions
);


/* ============================================================
   6. ACQUISITION SOURCE DIMENSION

   Grain:
   One row per distinct customer acquisition source.

   This describes the source that originally acquired a user.
   ============================================================ */

CREATE OR REPLACE TABLE
    core.dim_acquisition_source AS

SELECT
    ROW_NUMBER() OVER (
        ORDER BY acquisition_source
    )::INTEGER AS acquisition_source_key,

    acquisition_source

FROM (
    SELECT DISTINCT
        acquisition_source

    FROM stg.users
);








