CREATE OR REPLACE TABLE core.fact_order AS
SELECT
    o.order_id,
    o.user_id AS customer_id,
    o.order_status,
    o.created_at AS order_created_at,
    o.shipped_at,
    o.delivered_at,
    o.returned_at,
    CAST(strftime(o.created_at, '%Y%m%d') AS INTEGER) AS order_date_key,
    o.item_count,
    c.acquisition_source AS acquisition_source,
    CASE WHEN o.shipped_at >= o.created_at THEN datediff('minute', o.created_at, o.shipped_at) / 1440.0 END AS ship_lead_days,
    CASE WHEN o.delivered_at >= o.shipped_at THEN datediff('minute', o.shipped_at, o.delivered_at) / 1440.0 END AS delivery_lead_days,
    CASE WHEN o.delivered_at >= o.created_at THEN datediff('minute', o.created_at, o.delivered_at) / 1440.0 END AS end_to_end_lead_days,
    CASE WHEN o.returned_at >= o.delivered_at THEN datediff('minute', o.delivered_at, o.returned_at) / 1440.0 END AS return_cycle_days,
    CASE
        WHEN o.shipped_at IS NOT NULL AND o.shipped_at < o.created_at THEN 0
        WHEN o.delivered_at IS NOT NULL AND (o.shipped_at IS NULL OR o.delivered_at < o.shipped_at) THEN 0
        WHEN o.returned_at IS NOT NULL AND (o.delivered_at IS NULL OR o.returned_at < o.delivered_at) THEN 0
        ELSE 1
    END AS valid_timeline_flag,
    CASE WHEN o.order_status = 'Cancelled' THEN 1 ELSE 0 END AS cancelled_order_flag,
    CASE WHEN o.order_status = 'Returned' THEN 1 ELSE 0 END AS returned_order_flag,
    CASE WHEN o.order_status = 'Complete' THEN 1 ELSE 0 END AS completed_order_flag
FROM stg.orders o
JOIN core.dim_customer c ON o.user_id = c.user_id;

CREATE OR REPLACE TABLE core.fact_order_item AS
SELECT
    i.order_item_id,
    i.order_id,
    i.user_id AS customer_id,
    i.product_id,
    i.inventory_item_id,
    p.distribution_center_id,
    c.acquisition_source AS acquisition_source,
    i.item_status,
    i.created_at AS order_item_created_at,
    i.shipped_at,
    i.delivered_at,
    i.returned_at,
    CAST(strftime(i.created_at, '%Y%m%d') AS INTEGER) AS order_date_key,
    i.sale_price,
    p.unit_cost,
    i.sale_price - p.unit_cost AS gross_margin_value,
    CASE WHEN i.sale_price > 0 THEN (i.sale_price - p.unit_cost) / i.sale_price END AS gross_margin_rate,
    i.sale_price AS gross_sales_value,
    CASE WHEN i.item_status = 'Cancelled' THEN i.sale_price ELSE 0 END AS cancelled_value,
    CASE WHEN i.item_status = 'Returned' THEN i.sale_price ELSE 0 END AS returned_value,
    CASE WHEN i.item_status NOT IN ('Cancelled', 'Returned') THEN i.sale_price ELSE 0 END AS net_sales_value,
    CASE WHEN i.item_status NOT IN ('Cancelled', 'Returned') THEN i.sale_price - p.unit_cost ELSE 0 END AS net_profit_value,
    CASE WHEN i.item_status = 'Cancelled' THEN 1 ELSE 0 END AS cancelled_item_flag,
    CASE WHEN i.item_status = 'Returned' THEN 1 ELSE 0 END AS returned_item_flag,
    CASE WHEN i.item_status IN ('Complete', 'Returned') THEN 1 ELSE 0 END AS return_observation_eligible_flag,
    CASE WHEN i.shipped_at >= i.created_at THEN datediff('minute', i.created_at, i.shipped_at) / 1440.0 END AS ship_lead_days,
    CASE WHEN i.delivered_at >= i.shipped_at THEN datediff('minute', i.shipped_at, i.delivered_at) / 1440.0 END AS delivery_lead_days,
    CASE WHEN i.delivered_at >= i.created_at THEN datediff('minute', i.created_at, i.delivered_at) / 1440.0 END AS end_to_end_lead_days,
    CASE WHEN i.returned_at >= i.delivered_at THEN datediff('minute', i.delivered_at, i.returned_at) / 1440.0 END AS return_cycle_days,
    CASE
        WHEN i.shipped_at IS NOT NULL AND i.shipped_at < i.created_at THEN 0
        WHEN i.delivered_at IS NOT NULL AND (i.shipped_at IS NULL OR i.delivered_at < i.shipped_at) THEN 0
        WHEN i.returned_at IS NOT NULL AND (i.delivered_at IS NULL OR i.returned_at < i.delivered_at) THEN 0
        ELSE 1
    END AS valid_timeline_flag
FROM stg.order_items i
JOIN core.dim_product p ON i.product_id = p.product_id
JOIN core.dim_customer c ON i.user_id = c.user_id;

CREATE OR REPLACE TABLE core.fact_session AS
SELECT
    s.session_id,
    s.user_id AS customer_id,
    s.session_start_at,
    s.session_end_at,
    CAST(strftime(s.session_start_at, '%Y%m%d') AS INTEGER) AS session_date_key,
    s.browser,
    s.traffic_source,
    COALESCE(c.country, 'Unknown') AS country,
    s.event_count,
    s.events_with_user_id,
    s.event_identity_coverage_rate,
    CASE WHEN s.events_with_user_id > 0 THEN 1 ELSE 0 END AS identified_session_flag,
    CASE WHEN s.session_end_at >= s.session_start_at
         THEN datediff('second', s.session_start_at, s.session_end_at) END AS session_duration_seconds,
    s.first_event_type,
    s.final_event_type,
    s.home_flag,
    s.department_flag,
    s.product_view_flag,
    s.cart_flag,
    s.purchase_flag,
    s.cancel_event_flag,
    CASE WHEN s.cart_flag = 1 AND s.purchase_flag = 0 THEN 1 ELSE 0 END AS cart_abandoned_flag,
    CASE WHEN s.product_view_flag = 1 AND s.cart_flag = 0 AND s.purchase_flag = 0
         THEN 1 ELSE 0 END AS early_product_exit_flag,
    CASE
        WHEN s.purchase_flag = 1 THEN 'Purchase'
        WHEN s.cart_flag = 1 THEN 'Cart'
        WHEN s.product_view_flag = 1 THEN 'Product'
        WHEN s.department_flag = 1 THEN 'Department'
        ELSE 'Home'
    END AS highest_stage
FROM stg.sessions s
LEFT JOIN core.dim_customer c ON s.user_id = c.user_id;

CREATE OR REPLACE TABLE core.fact_inventory AS
WITH as_of AS (SELECT MAX(created_at)::DATE AS as_of_date FROM stg.events)
SELECT
    i.inventory_item_id,
    i.product_id,
    i.distribution_center_id,
    i.created_at AS inventory_created_at,
    i.sold_at,
    CAST(strftime(i.created_at, '%Y%m%d') AS INTEGER) AS inventory_created_date_key,
    i.unit_cost,
    i.retail_price,
    CASE WHEN i.sold_at IS NOT NULL THEN 1 ELSE 0 END AS sold_flag,
    CASE WHEN i.sold_at >= i.created_at THEN datediff('day', i.created_at, i.sold_at) END AS days_to_sell,
    CASE WHEN i.sold_at IS NULL THEN datediff('day', i.created_at::DATE, as_of.as_of_date) END AS unsold_age_days,
    CASE
        WHEN i.sold_at IS NOT NULL THEN 'Sold'
        WHEN datediff('day', i.created_at::DATE, as_of.as_of_date) <= 30 THEN '0-30 days'
        WHEN datediff('day', i.created_at::DATE, as_of.as_of_date) <= 60 THEN '31-60 days'
        WHEN datediff('day', i.created_at::DATE, as_of.as_of_date) <= 90 THEN '61-90 days'
        WHEN datediff('day', i.created_at::DATE, as_of.as_of_date) <= 180 THEN '91-180 days'
        ELSE '181+ days'
    END AS inventory_age_bucket
FROM stg.inventory_events i
CROSS JOIN as_of;
