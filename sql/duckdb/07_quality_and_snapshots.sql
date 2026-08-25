CREATE SCHEMA IF NOT EXISTS qa;

CREATE OR REPLACE TABLE qa.test_results AS
WITH checks AS (
    SELECT 'users_primary_key_unique' AS check_name, 'raw' AS layer, 'CRITICAL' AS severity,
           COUNT(*)::BIGINT AS failure_count, (SELECT COUNT(*) FROM raw.users)::BIGINT AS denominator,
           1 AS blocking, 'users.id must be unique' AS notes
    FROM (SELECT id FROM raw.users GROUP BY id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'products_primary_key_unique', 'raw', 'CRITICAL', COUNT(*), (SELECT COUNT(*) FROM raw.products), 1,
           'products.id must be unique'
    FROM (SELECT id FROM raw.products GROUP BY id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'orders_primary_key_unique', 'raw', 'CRITICAL', COUNT(*), (SELECT COUNT(*) FROM raw.orders), 1,
           'orders.order_id must be unique'
    FROM (SELECT order_id FROM raw.orders GROUP BY order_id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'order_items_primary_key_unique', 'raw', 'CRITICAL', COUNT(*), (SELECT COUNT(*) FROM raw.order_items), 1,
           'order_items.id must be unique'
    FROM (SELECT id FROM raw.order_items GROUP BY id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'events_primary_key_unique', 'raw', 'CRITICAL', COUNT(*), (SELECT COUNT(*) FROM raw.events), 1,
           'events.id must be unique'
    FROM (SELECT id FROM raw.events GROUP BY id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'events_session_id_present', 'raw', 'CRITICAL', COUNT(*), (SELECT COUNT(*) FROM raw.events), 1,
           'Every event must have a nonblank session_id before sessionization'
    FROM raw.events
    WHERE session_id IS NULL OR TRIM(CAST(session_id AS VARCHAR)) = ''
    UNION ALL
    SELECT 'derived_sessions_primary_key_unique', 'stg', 'CRITICAL', COUNT(*),
           (SELECT COUNT(*) FROM stg.sessions), 1,
           'The event-derived stg.sessions view must have one row per session_id'
    FROM (SELECT session_id FROM stg.sessions GROUP BY session_id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'session_attributes_consistent_within_session', 'stg', 'CRITICAL', COUNT(*),
           (SELECT COUNT(*) FROM stg.sessions), 1,
           'Each session must have at most one user, browser, and traffic source'
    FROM (
        SELECT session_id
        FROM stg.events
        GROUP BY session_id
        HAVING COUNT(DISTINCT user_id) > 1
            OR COUNT(DISTINCT browser) > 1
            OR COUNT(DISTINCT traffic_source) > 1
    )
    UNION ALL
    SELECT 'orders_have_customer', 'stg', 'CRITICAL', COUNT(*), (SELECT COUNT(*) FROM stg.orders), 1,
           'Every order must match a customer'
    FROM stg.orders o LEFT JOIN stg.users u ON o.user_id = u.user_id WHERE u.user_id IS NULL
    UNION ALL
    SELECT 'order_items_have_order', 'stg', 'CRITICAL', COUNT(*), (SELECT COUNT(*) FROM stg.order_items), 1,
           'Every order item must match an order'
    FROM stg.order_items i LEFT JOIN stg.orders o ON i.order_id = o.order_id WHERE o.order_id IS NULL
    UNION ALL
    SELECT 'order_items_have_product', 'stg', 'CRITICAL', COUNT(*), (SELECT COUNT(*) FROM stg.order_items), 1,
           'Every order item must match a product'
    FROM stg.order_items i LEFT JOIN stg.products p ON i.product_id = p.product_id WHERE p.product_id IS NULL
    UNION ALL
    SELECT 'order_item_count_reconciles', 'core', 'CRITICAL',
           ABS((SELECT COUNT(*) FROM stg.order_items) - (SELECT COUNT(*) FROM core.fact_order_item)),
           (SELECT COUNT(*) FROM stg.order_items), 1, 'Fact item rows must equal staged item rows'
    UNION ALL
    SELECT 'session_count_reconciles_to_events', 'core', 'CRITICAL',
           ABS((SELECT COUNT(DISTINCT session_id) FROM stg.events) - (SELECT COUNT(*) FROM core.fact_session)),
           (SELECT COUNT(DISTINCT session_id) FROM stg.events), 1,
           'Fact session rows must equal distinct event session IDs'
    UNION ALL
    SELECT 'session_event_count_reconciles', 'core', 'CRITICAL',
           ABS((SELECT COUNT(*) FROM stg.events) - (SELECT SUM(event_count) FROM core.fact_session)),
           (SELECT COUNT(*) FROM stg.events), 1,
           'Summed event-derived session counts must equal raw event rows'
    UNION ALL
    SELECT 'nonnegative_sale_price', 'stg', 'HIGH', COUNT(*), (SELECT COUNT(*) FROM stg.order_items), 1,
           'Sale prices cannot be negative'
    FROM stg.order_items WHERE sale_price < 0
    UNION ALL
    SELECT 'product_cost_not_above_retail', 'stg', 'HIGH', COUNT(*), (SELECT COUNT(*) FROM stg.products), 1,
           'Cost above retail would invalidate margin'
    FROM stg.products WHERE unit_cost < 0 OR retail_price < 0 OR unit_cost > retail_price
    UNION ALL
    SELECT 'shipping_not_before_item_created', 'core', 'HIGH', COUNT(*), (SELECT COUNT(*) FROM core.fact_order_item), 0,
           'Known source anomaly: exclude invalid rows from delivery lead-time metrics'
    FROM core.fact_order_item WHERE shipped_at < order_item_created_at
    UNION ALL
    SELECT 'delivery_not_before_shipping', 'core', 'HIGH', COUNT(*), (SELECT COUNT(*) FROM core.fact_order_item), 1,
           'Delivery timestamps must follow shipment'
    FROM core.fact_order_item WHERE delivered_at < shipped_at
    UNION ALL
    SELECT 'return_not_before_delivery', 'core', 'HIGH', COUNT(*), (SELECT COUNT(*) FROM core.fact_order_item), 1,
           'Return timestamps must follow delivery'
    FROM core.fact_order_item WHERE returned_at < delivered_at
    UNION ALL
    SELECT 'events_user_id_missing', 'raw', 'INFO', COUNT(*), (SELECT COUNT(*) FROM raw.events), 0,
           'Event user_id is sparse; session customer_id uses the one nonnull ID available within a session'
    FROM raw.events WHERE user_id IS NULL
    UNION ALL
    SELECT 'partial_latest_month', 'mart', 'INFO', COUNT(*), COUNT(*), 0,
           'The maximum source month is partial and excluded from default period comparisons'
    FROM mart.sales_monthly WHERE is_complete_month = 0
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

CREATE OR REPLACE TABLE qa.metric_reconciliation AS
SELECT 'orders_rows' AS metric_name,
       (SELECT COUNT(*) FROM raw.orders)::DOUBLE AS source_value,
       (SELECT COUNT(*) FROM core.fact_order)::DOUBLE AS modeled_value,
       (SELECT COUNT(*) FROM core.fact_order)::DOUBLE - (SELECT COUNT(*) FROM raw.orders)::DOUBLE AS variance
UNION ALL
SELECT 'order_items_rows', (SELECT COUNT(*) FROM raw.order_items),
       (SELECT COUNT(*) FROM core.fact_order_item),
       (SELECT COUNT(*) FROM core.fact_order_item) - (SELECT COUNT(*) FROM raw.order_items)
UNION ALL
SELECT 'sessions_from_events_rows', (SELECT COUNT(DISTINCT session_id) FROM stg.events),
       (SELECT COUNT(*) FROM core.fact_session),
       (SELECT COUNT(*) FROM core.fact_session) - (SELECT COUNT(DISTINCT session_id) FROM stg.events)
UNION ALL
SELECT 'events_into_sessions_rows', (SELECT COUNT(*) FROM stg.events),
       (SELECT SUM(event_count) FROM core.fact_session),
       (SELECT SUM(event_count) FROM core.fact_session) - (SELECT COUNT(*) FROM stg.events)
UNION ALL
SELECT 'gross_sales_value', (SELECT SUM(sale_price) FROM stg.order_items),
       (SELECT SUM(gross_sales_value) FROM core.fact_order_item),
       (SELECT SUM(gross_sales_value) FROM core.fact_order_item) - (SELECT SUM(sale_price) FROM stg.order_items);

CREATE OR REPLACE TABLE mart.executive_snapshot AS
SELECT 'Data as of' AS metric_name, MAX(order_item_created_at)::VARCHAR AS metric_value, NULL::DOUBLE AS numeric_value
FROM core.fact_order_item
UNION ALL SELECT 'Gross Sales', printf('$%,.2f', SUM(gross_sales_value)), SUM(gross_sales_value) FROM core.fact_order_item
UNION ALL SELECT 'Net Sales', printf('$%,.2f', SUM(net_sales_value)), SUM(net_sales_value) FROM core.fact_order_item
UNION ALL SELECT 'Net Profit', printf('$%,.2f', SUM(net_profit_value)), SUM(net_profit_value) FROM core.fact_order_item
UNION ALL SELECT 'Orders', printf('%,d', COUNT(DISTINCT order_id)), COUNT(DISTINCT order_id) FROM core.fact_order_item
UNION ALL SELECT 'Customers', printf('%,d', COUNT(DISTINCT customer_id)), COUNT(DISTINCT customer_id) FROM core.fact_order_item
UNION ALL SELECT 'Sessions', printf('%,d', COUNT(*)), COUNT(*) FROM core.fact_session
UNION ALL SELECT 'Session Conversion Rate', printf('%.2f%%', 100 * AVG(purchase_flag)), AVG(purchase_flag) FROM core.fact_session
UNION ALL SELECT 'Cart Abandonment Rate', printf('%.2f%%', 100 * SUM(cart_abandoned_flag)::DOUBLE / SUM(cart_flag)),
                 SUM(cart_abandoned_flag)::DOUBLE / SUM(cart_flag) FROM core.fact_session
UNION ALL SELECT 'Observed Return Rate', printf('%.2f%%', 100 * SUM(returned_item_flag)::DOUBLE / SUM(return_observation_eligible_flag)),
                 SUM(returned_item_flag)::DOUBLE / SUM(return_observation_eligible_flag) FROM core.fact_order_item
UNION ALL SELECT 'Item Cancellation Rate', printf('%.2f%%', 100 * AVG(cancelled_item_flag)), AVG(cancelled_item_flag) FROM core.fact_order_item
UNION ALL SELECT 'Repeat Customer Rate', printf('%.2f%%', 100 * AVG(repeat_customer_flag)), AVG(repeat_customer_flag) FROM mart.customer_360;
