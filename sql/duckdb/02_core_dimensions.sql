CREATE SCHEMA IF NOT EXISTS core;

CREATE OR REPLACE TABLE core.dim_date AS
WITH date_bounds AS (
    SELECT MIN(date_value)::DATE AS min_date, MAX(date_value)::DATE AS max_date
    FROM (
        SELECT MIN(created_at) AS date_value FROM stg.events
        UNION ALL SELECT MAX(created_at) FROM stg.events
        UNION ALL SELECT MIN(created_at) FROM stg.order_items
        UNION ALL SELECT MAX(created_at) FROM stg.order_items
        UNION ALL SELECT MIN(created_at) FROM stg.inventory_events
        UNION ALL SELECT MAX(COALESCE(sold_at, created_at)) FROM stg.inventory_events
    )
),
calendar AS (
    SELECT CAST(value AS DATE) AS calendar_date, max_date
    FROM date_bounds,
         generate_series(min_date, max_date, INTERVAL 1 DAY) AS series(value)
)
SELECT
    CAST(strftime(calendar_date, '%Y%m%d') AS INTEGER) AS date_key,
    calendar_date,
    EXTRACT(year FROM calendar_date)::INTEGER AS year,
    EXTRACT(quarter FROM calendar_date)::INTEGER AS quarter_number,
    'Q' || EXTRACT(quarter FROM calendar_date)::INTEGER AS quarter_label,
    EXTRACT(month FROM calendar_date)::INTEGER AS month_number,
    strftime(calendar_date, '%B') AS month_name,
    strftime(calendar_date, '%b %Y') AS month_year,
    date_trunc('month', calendar_date)::DATE AS month_start,
    date_trunc('quarter', calendar_date)::DATE AS quarter_start,
    date_trunc('year', calendar_date)::DATE AS year_start,
    EXTRACT(week FROM calendar_date)::INTEGER AS iso_week_number,
    EXTRACT(isodow FROM calendar_date)::INTEGER AS iso_day_of_week,
    strftime(calendar_date, '%A') AS day_name,
    CASE WHEN EXTRACT(isodow FROM calendar_date) IN (6, 7) THEN 1 ELSE 0 END AS is_weekend,
    CASE WHEN calendar_date < date_trunc('month', max_date) THEN 1 ELSE 0 END AS is_complete_month,
    -- Fiscal calendar. Group reporting runs on a fiscal year that starts in
    -- October, so FY2024 covers 2023-10-01 .. 2024-09-30. The start month is
    -- the single assumption here; changing 10 below re-bases every fiscal
    -- column consistently. Documented in docs/technical_reference.md.
    CASE
        WHEN EXTRACT(month FROM calendar_date) >= 10
        THEN EXTRACT(year FROM calendar_date)::INTEGER + 1
        ELSE EXTRACT(year FROM calendar_date)::INTEGER
    END AS fiscal_year,
    'FY' || CASE
        WHEN EXTRACT(month FROM calendar_date) >= 10
        THEN EXTRACT(year FROM calendar_date)::INTEGER + 1
        ELSE EXTRACT(year FROM calendar_date)::INTEGER
    END AS fiscal_year_label,
    ((EXTRACT(month FROM calendar_date)::INTEGER + 2) % 12) + 1 AS fiscal_month_number,
    CAST(FLOOR(((EXTRACT(month FROM calendar_date)::INTEGER + 2) % 12) / 3.0) AS INTEGER) + 1 AS fiscal_quarter_number,
    'FQ' || (CAST(FLOOR(((EXTRACT(month FROM calendar_date)::INTEGER + 2) % 12) / 3.0) AS INTEGER) + 1) AS fiscal_quarter_label,
    CASE
        WHEN EXTRACT(month FROM calendar_date) >= 10
        THEN make_date(EXTRACT(year FROM calendar_date)::INTEGER, 10, 1)
        ELSE make_date(EXTRACT(year FROM calendar_date)::INTEGER - 1, 10, 1)
    END AS fiscal_year_start
FROM calendar;

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
    COALESCE(country, 'Unknown') AS country,
    COALESCE(state, 'Unknown') AS state,
    COALESCE(city, 'Unknown') AS city,
    postal_code,
    latitude,
    longitude,
    acquisition_source,
    registered_at,
    CAST(strftime(registered_at, '%Y%m%d') AS INTEGER) AS registered_date_key
FROM stg.users;

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
    retail_price - unit_cost AS unit_margin,
    CASE WHEN retail_price > 0 THEN (retail_price - unit_cost) / retail_price END AS unit_margin_rate,
    CASE
        WHEN retail_price < 25 THEN 'Under $25'
        WHEN retail_price < 50 THEN '$25-$49'
        WHEN retail_price < 100 THEN '$50-$99'
        WHEN retail_price < 200 THEN '$100-$199'
        ELSE '$200+'
    END AS price_band
FROM stg.products;

CREATE OR REPLACE TABLE core.dim_distribution_center AS
SELECT * FROM stg.distribution_centers;

CREATE OR REPLACE TABLE core.dim_session_traffic_source AS
SELECT ROW_NUMBER() OVER (ORDER BY traffic_source)::INTEGER AS session_traffic_source_key,
       traffic_source
FROM (SELECT DISTINCT traffic_source FROM stg.sessions);

CREATE OR REPLACE TABLE core.dim_acquisition_source AS
SELECT ROW_NUMBER() OVER (ORDER BY acquisition_source)::INTEGER AS acquisition_source_key,
       acquisition_source
FROM (SELECT DISTINCT acquisition_source FROM stg.users);

-- ---------------------------------------------------------------------
-- 1. Conformed country dimension
--
-- TheLook's users.csv genuinely contains local-language spellings
-- ("Espana" alongside "Spain", "Deutschland" alongside "Germany") which
-- split a single market into two phantom markets in any country report.
-- The seed maps every observed source value to a canonical country and a
-- region, so regional reporting has one row per market.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE core.dim_country AS
SELECT
    ROW_NUMBER() OVER (ORDER BY canonical_country, source_country_value)::INTEGER AS country_key,
    source_country_value,
    canonical_country,
    region,
    sub_region,
    CAST(is_alias AS INTEGER) AS is_alias,
    alias_reason
FROM raw.country_master;

-- ---------------------------------------------------------------------
-- 1b. Star-schema dimensions for the month and market grains
--
-- core.dim_country is a MAPPING table: it holds one row per observed source
-- spelling, so canonical_country repeats and it cannot serve as the "one"
-- side of a relationship. The two dimensions below are the ones Power BI
-- joins to, each with a genuinely unique key.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE core.dim_market AS
SELECT
    ROW_NUMBER() OVER (ORDER BY canonical_country)::INTEGER AS market_key,
    canonical_country,
    region,
    sub_region,
    COUNT(*) AS source_spellings_mapped
FROM core.dim_country
WHERE canonical_country <> 'Unknown'
GROUP BY canonical_country, region, sub_region;

CREATE OR REPLACE TABLE core.dim_month AS
SELECT DISTINCT
    month_start,
    CAST(strftime(month_start, '%Y%m') AS INTEGER) AS month_key,
    year,
    month_number,
    month_name,
    month_year,
    quarter_label,
    fiscal_year,
    fiscal_year_label,
    fiscal_quarter_label,
    fiscal_month_number,
    is_complete_month
FROM core.dim_date;
