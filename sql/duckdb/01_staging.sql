CREATE SCHEMA IF NOT EXISTS stg;

CREATE OR REPLACE VIEW stg.users AS
SELECT
    CAST(id AS BIGINT) AS user_id,
    TRY_CAST(age AS INTEGER) AS age,
    UPPER(TRIM(CAST(gender AS VARCHAR))) AS gender,
    NULLIF(TRIM(CAST(state AS VARCHAR)), '') AS state,
    NULLIF(TRIM(CAST(postal_code AS VARCHAR)), '') AS postal_code,
    NULLIF(TRIM(CAST(city AS VARCHAR)), '') AS city,
    NULLIF(TRIM(CAST(country AS VARCHAR)), '') AS country,
    TRY_CAST(latitude AS DOUBLE) AS latitude,
    TRY_CAST(longitude AS DOUBLE) AS longitude,
    COALESCE(NULLIF(TRIM(CAST(traffic_source AS VARCHAR)), ''), 'Unknown') AS acquisition_source,
    CAST(created_at AS TIMESTAMP) AS registered_at
FROM raw.users;

CREATE OR REPLACE VIEW stg.products AS
SELECT
    CAST(id AS BIGINT) AS product_id,
    TRY_CAST(cost AS DOUBLE) AS unit_cost,
    COALESCE(NULLIF(TRIM(CAST(category AS VARCHAR)), ''), 'Unknown') AS category,
    COALESCE(NULLIF(TRIM(CAST(name AS VARCHAR)), ''), 'Unknown') AS product_name,
    COALESCE(NULLIF(TRIM(CAST(brand AS VARCHAR)), ''), 'Unknown') AS brand,
    TRY_CAST(retail_price AS DOUBLE) AS retail_price,
    COALESCE(NULLIF(TRIM(CAST(department AS VARCHAR)), ''), 'Unknown') AS department,
    CAST(sku AS VARCHAR) AS sku,
    CAST(distribution_center_id AS INTEGER) AS distribution_center_id
FROM raw.products;

CREATE OR REPLACE VIEW stg.orders AS
SELECT
    CAST(order_id AS BIGINT) AS order_id,
    CAST(user_id AS BIGINT) AS user_id,
    TRIM(CAST(status AS VARCHAR)) AS order_status,
    UPPER(TRIM(CAST(gender AS VARCHAR))) AS gender,
    CAST(created_at AS TIMESTAMP) AS created_at,
    CAST(returned_at AS TIMESTAMP) AS returned_at,
    CAST(shipped_at AS TIMESTAMP) AS shipped_at,
    CAST(delivered_at AS TIMESTAMP) AS delivered_at,
    CAST(num_of_item AS INTEGER) AS item_count
FROM raw.orders;

CREATE OR REPLACE VIEW stg.order_items AS
SELECT
    CAST(id AS BIGINT) AS order_item_id,
    CAST(order_id AS BIGINT) AS order_id,
    CAST(user_id AS BIGINT) AS user_id,
    CAST(product_id AS BIGINT) AS product_id,
    CAST(inventory_item_id AS BIGINT) AS inventory_item_id,
    TRIM(CAST(status AS VARCHAR)) AS item_status,
    CAST(created_at AS TIMESTAMP) AS created_at,
    CAST(shipped_at AS TIMESTAMP) AS shipped_at,
    CAST(delivered_at AS TIMESTAMP) AS delivered_at,
    CAST(returned_at AS TIMESTAMP) AS returned_at,
    TRY_CAST(sale_price AS DOUBLE) AS sale_price
FROM raw.order_items;

CREATE OR REPLACE VIEW stg.events AS
SELECT
    CAST(id AS BIGINT) AS event_id,
    TRY_CAST(user_id AS BIGINT) AS user_id,
    CAST(sequence_number AS INTEGER) AS sequence_number,
    NULLIF(TRIM(CAST(session_id AS VARCHAR)), '') AS session_id,
    CAST(created_at AS TIMESTAMP) AS created_at,
    NULLIF(TRIM(CAST(city AS VARCHAR)), '') AS city,
    NULLIF(TRIM(CAST(state AS VARCHAR)), '') AS state,
    NULLIF(TRIM(CAST(postal_code AS VARCHAR)), '') AS postal_code,
    COALESCE(NULLIF(TRIM(CAST(browser AS VARCHAR)), ''), 'Unknown') AS browser,
    COALESCE(NULLIF(TRIM(CAST(traffic_source AS VARCHAR)), ''), 'Unknown') AS traffic_source,
    CAST(uri AS VARCHAR) AS uri,
    LOWER(TRIM(CAST(event_type AS VARCHAR))) AS event_type
FROM raw.events;

-- Derived view, not a source table. One row is produced for each events.session_id.
CREATE OR REPLACE VIEW stg.sessions AS
SELECT
    session_id,
    MAX(user_id) AS user_id,
    COUNT(*)::INTEGER AS event_count,
    COUNT(user_id)::INTEGER AS events_with_user_id,
    COUNT(user_id)::DOUBLE / NULLIF(COUNT(*), 0) AS event_identity_coverage_rate,
    MIN(created_at) AS session_start_at,
    MAX(created_at) AS session_end_at,
    arg_min(city, sequence_number) AS city,
    arg_min(state, sequence_number) AS state,
    arg_min(postal_code, sequence_number) AS postal_code,
    arg_min(browser, sequence_number) AS browser,
    arg_min(traffic_source, sequence_number) AS traffic_source,
    arg_min(event_type, sequence_number) AS first_event_type,
    arg_max(event_type, sequence_number) AS final_event_type,
    MAX(CASE WHEN event_type = 'home' THEN 1 ELSE 0 END) AS home_flag,
    MAX(CASE WHEN event_type = 'department' THEN 1 ELSE 0 END) AS department_flag,
    MAX(CASE WHEN event_type = 'product' THEN 1 ELSE 0 END) AS product_view_flag,
    MAX(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) AS cart_flag,
    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchase_flag,
    MAX(CASE WHEN event_type = 'cancel' THEN 1 ELSE 0 END) AS cancel_event_flag
FROM stg.events
WHERE session_id IS NOT NULL
GROUP BY session_id;

CREATE OR REPLACE VIEW stg.inventory_events AS
SELECT
    CAST(id AS BIGINT) AS inventory_item_id,
    CAST(product_id AS BIGINT) AS product_id,
    CAST(created_at AS TIMESTAMP) AS created_at,
    CAST(sold_at AS TIMESTAMP) AS sold_at,
    TRY_CAST(cost AS DOUBLE) AS unit_cost,
    COALESCE(NULLIF(TRIM(CAST(product_category AS VARCHAR)), ''), 'Unknown') AS category,
    COALESCE(NULLIF(TRIM(CAST(product_name AS VARCHAR)), ''), 'Unknown') AS product_name,
    COALESCE(NULLIF(TRIM(CAST(product_brand AS VARCHAR)), ''), 'Unknown') AS brand,
    TRY_CAST(product_retail_price AS DOUBLE) AS retail_price,
    COALESCE(NULLIF(TRIM(CAST(product_department AS VARCHAR)), ''), 'Unknown') AS department,
    CAST(product_sku AS VARCHAR) AS sku,
    CAST(product_distribution_center_id AS INTEGER) AS distribution_center_id
FROM raw.inventory_events;

CREATE OR REPLACE VIEW stg.distribution_centers AS
SELECT
    CAST(id AS INTEGER) AS distribution_center_id,
    TRIM(CAST(name AS VARCHAR)) AS distribution_center_name,
    TRY_CAST(latitude AS DOUBLE) AS latitude,
    TRY_CAST(longitude AS DOUBLE) AS longitude
FROM raw.distribution_centers;
