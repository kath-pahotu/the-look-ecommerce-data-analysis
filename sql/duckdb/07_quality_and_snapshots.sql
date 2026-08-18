CREATE SCHEMA IF NOT EXISTS qa;


/* ============================================================
   1. QA TEST RESULTS

   Common output:
   - check_name
   - layer
   - severity
   - failure_count
   - denominator
   - blocking
   - handling_rule
   - status
   - failure_rate
   ============================================================ */

CREATE OR REPLACE TABLE qa.test_results AS

WITH checks AS (

    /* --------------------------------------------------------
       Primary-key uniqueness
       -------------------------------------------------------- */

    SELECT
        'dim_customer_key_unique' AS check_name,
        'core' AS layer,
        'CRITICAL' AS severity,
        COUNT(*) - COUNT(DISTINCT user_id) AS failure_count,
        COUNT(*) AS denominator,
        1 AS blocking,
        'Every customer must have one unique user_id' AS handling_rule
    FROM core.dim_customer

    UNION ALL

    SELECT
        'dim_product_key_unique',
        'core',
        'CRITICAL',
        COUNT(*) - COUNT(DISTINCT product_id),
        COUNT(*),
        1,
        'Every product must have one unique product_id'
    FROM core.dim_product

    UNION ALL

    SELECT
        'dim_date_key_unique',
        'core',
        'CRITICAL',
        COUNT(*) - COUNT(DISTINCT date_key),
        COUNT(*),
        1,
        'Every calendar date must have one unique date_key'
    FROM core.dim_date

    UNION ALL

    SELECT
        'dim_distribution_center_key_unique',
        'core',
        'CRITICAL',
        COUNT(*) - COUNT(DISTINCT distribution_center_id),
        COUNT(*),
        1,
        'Every distribution center must have one unique ID'
    FROM core.dim_distribution_center

    UNION ALL

    SELECT
        'fact_order_key_unique',
        'core',
        'CRITICAL',
        COUNT(*) - COUNT(DISTINCT order_id),
        COUNT(*),
        1,
        'Every order must appear once in fact_order'
    FROM core.fact_order

    UNION ALL

    SELECT
        'fact_order_item_key_unique',
        'core',
        'CRITICAL',
        COUNT(*) - COUNT(DISTINCT order_item_id),
        COUNT(*),
        1,
        'Every order item must appear once in fact_order_item'
    FROM core.fact_order_item

    UNION ALL

    SELECT
        'fact_inventory_key_unique',
        'core',
        'CRITICAL',
        COUNT(*) - COUNT(DISTINCT inventory_item_id),
        COUNT(*),
        1,
        'Every inventory item must appear once in fact_inventory'
    FROM core.fact_inventory

    UNION ALL

    SELECT
        'fact_session_key_unique',
        'core',
        'CRITICAL',
        COUNT(*) - COUNT(DISTINCT session_id),
        COUNT(*),
        1,
        'Every session_id must produce exactly one fact-session row'
    FROM core.fact_session


    /* --------------------------------------------------------
       Session reconciliation
       -------------------------------------------------------- */

    UNION ALL

    SELECT
        'session_count_reconciles',
        'core',
        'CRITICAL',

        ABS(
            (
                SELECT COUNT(DISTINCT session_id)::BIGINT
                FROM stg.events
                WHERE session_id IS NOT NULL
            )
            -
            (
                SELECT COUNT(*)::BIGINT
                FROM core.fact_session
            )
        ),

        (
            SELECT COUNT(DISTINCT session_id)
            FROM stg.events
            WHERE session_id IS NOT NULL
        ),

        1,
        'Every distinct nonblank event session must produce one fact session'

    UNION ALL

    SELECT
        'session_event_count_reconciles',
        'core',
        'CRITICAL',

        ABS(
            (
                SELECT COUNT(*)::BIGINT
                FROM stg.events
                WHERE session_id IS NOT NULL
            )
            -
            (
                SELECT COALESCE(SUM(event_count), 0)::BIGINT
                FROM core.fact_session
            )
        ),

        (
            SELECT COUNT(*)
            FROM stg.events
            WHERE session_id IS NOT NULL
        ),

        1,
        'Summed fact-session event counts must equal sessionizable events'

    UNION ALL

    SELECT
        'blank_event_session_ids',
        'staging',
        'WARNING',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM stg.events) AS denominator,
        0 AS blocking,
        'Events without session_id are excluded from session analysis'
    FROM stg.events
    WHERE session_id IS NULL

    UNION ALL

    SELECT
        'sessions_with_multiple_user_ids',
        'staging',
        'HIGH',
        COUNT(*) AS failure_count,
        (
            SELECT COUNT(DISTINCT session_id)
            FROM stg.events
            WHERE session_id IS NOT NULL
        ) AS denominator,
        1 AS blocking,
        'One session should not be assigned to multiple users'
    FROM (
        SELECT
            session_id
        FROM stg.events
        WHERE session_id IS NOT NULL
        GROUP BY session_id
        HAVING COUNT(DISTINCT user_id) > 1
    ) AS inconsistent_sessions


    /* --------------------------------------------------------
       Referential integrity
       -------------------------------------------------------- */

    UNION ALL

    SELECT
        'orders_without_customer',
        'core',
        'HIGH',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.fact_order) AS denominator,
        1 AS blocking,
        'Every identified order must match a customer dimension row'
    FROM core.fact_order AS f
    LEFT JOIN core.dim_customer AS c
        ON f.customer_id = c.user_id
    WHERE f.customer_id IS NOT NULL
      AND c.user_id IS NULL

    UNION ALL

    SELECT
        'order_items_without_order',
        'core',
        'CRITICAL',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.fact_order_item) AS denominator,
        1 AS blocking,
        'Every order item must match an order'
    FROM core.fact_order_item AS i
    LEFT JOIN core.fact_order AS o
        ON i.order_id = o.order_id
    WHERE o.order_id IS NULL

    UNION ALL

    SELECT
        'order_items_without_product',
        'core',
        'CRITICAL',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.fact_order_item) AS denominator,
        1 AS blocking,
        'Every order item must match a product'
    FROM core.fact_order_item AS i
    LEFT JOIN core.dim_product AS p
        ON i.product_id = p.product_id
    WHERE p.product_id IS NULL

    UNION ALL

    SELECT
        'inventory_without_product',
        'core',
        'HIGH',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.fact_inventory) AS denominator,
        1 AS blocking,
        'Every inventory unit must match a product'
    FROM core.fact_inventory AS i
    LEFT JOIN core.dim_product AS p
        ON i.product_id = p.product_id
    WHERE p.product_id IS NULL

    UNION ALL

    SELECT
        'inventory_without_distribution_center',
        'core',
        'HIGH',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.fact_inventory) AS denominator,
        1 AS blocking,
        'Every inventory unit must match a distribution center'
    FROM core.fact_inventory AS i
    LEFT JOIN core.dim_distribution_center AS dc
        ON i.distribution_center_id = dc.distribution_center_id
    WHERE dc.distribution_center_id IS NULL


    /* --------------------------------------------------------
       Commercial and timeline checks
       -------------------------------------------------------- */

    UNION ALL

    SELECT
        'negative_item_prices_or_costs',
        'core',
        'HIGH',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.fact_order_item) AS denominator,
        1 AS blocking,
        'Negative sale prices and product costs are invalid'
    FROM core.fact_order_item
    WHERE sale_price < 0
       OR unit_cost < 0

    UNION ALL

    SELECT
        'cost_above_sale_price',
        'core',
        'WARNING',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.fact_order_item) AS denominator,
        0 AS blocking,
        'Review potentially loss-making items; do not silently remove them'
    FROM core.fact_order_item
    WHERE unit_cost > sale_price

    UNION ALL

    SELECT
        'invalid_order_item_timeline',
        'core',
        'HIGH',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.fact_order_item) AS denominator,
        0 AS blocking,
        'Exclude invalid timelines from lead-time metrics and investigate them'
    FROM core.fact_order_item
    WHERE valid_timeline_flag = 0


    /* --------------------------------------------------------
       Informational observations
       -------------------------------------------------------- */

    UNION ALL

    SELECT
        'events_without_user_id',
        'staging',
        'INFO',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM stg.events) AS denominator,
        0 AS blocking,
        'Anonymous events remain valid for traffic analysis but not customer analysis'
    FROM stg.events
    WHERE user_id IS NULL

    UNION ALL

    SELECT
        'rows_in_incomplete_maximum_month',
        'core',
        'INFO',
        COUNT(*) AS failure_count,
        (SELECT COUNT(*) FROM core.dim_date) AS denominator,
        0 AS blocking,
        'Exclude the incomplete maximum month from complete-period comparisons'
    FROM core.dim_date
    WHERE is_complete_month = 0
      AND month_start = (
          SELECT MAX(month_start)
          FROM core.dim_date
      )
)

SELECT
    check_name,
    layer,
    severity,
    failure_count,
    denominator,
    blocking,
    handling_rule,

    CASE
        WHEN failure_count = 0 THEN 'PASS'
        WHEN severity = 'INFO' THEN 'INFO'
        WHEN blocking = 1 THEN 'FAIL'
        ELSE 'WARN'
    END AS status,

    failure_count::DOUBLE
        / NULLIF(denominator, 0)
        AS failure_rate

FROM checks;


/* ============================================================
   2. METRIC RECONCILIATION

   Variance must equal zero, except for tiny permitted
   floating-point differences in monetary values.
   ============================================================ */

CREATE OR REPLACE TABLE qa.metric_reconciliation AS

WITH metrics AS (

    SELECT
        'orders_rows' AS metric_name,
        'stg.orders' AS source_layer,
        'core.fact_order' AS modeled_layer,
        (SELECT COUNT(*)::DOUBLE FROM stg.orders) AS source_value,
        (SELECT COUNT(*)::DOUBLE FROM core.fact_order) AS modeled_value,
        0.0 AS tolerance

    UNION ALL

    SELECT
        'order_items_rows',
        'stg.order_items',
        'core.fact_order_item',
        (SELECT COUNT(*)::DOUBLE FROM stg.order_items),
        (SELECT COUNT(*)::DOUBLE FROM core.fact_order_item),
        0.0

    UNION ALL

    SELECT
        'inventory_rows',
        'stg.inventory_events',
        'core.fact_inventory',
        (SELECT COUNT(*)::DOUBLE FROM stg.inventory_events),
        (SELECT COUNT(*)::DOUBLE FROM core.fact_inventory),
        0.0

    UNION ALL

    SELECT
        'sessions_from_events',
        'stg.events',
        'core.fact_session',

        (
            SELECT COUNT(DISTINCT session_id)::DOUBLE
            FROM stg.events
            WHERE session_id IS NOT NULL
        ),

        (
            SELECT COUNT(*)::DOUBLE
            FROM core.fact_session
        ),

        0.0

    UNION ALL

    SELECT
        'events_into_sessions',
        'stg.events',
        'core.fact_session',

        (
            SELECT COUNT(*)::DOUBLE
            FROM stg.events
            WHERE session_id IS NOT NULL
        ),

        (
            SELECT COALESCE(SUM(event_count), 0)::DOUBLE
            FROM core.fact_session
        ),

        0.0

    UNION ALL

    SELECT
        'gross_sales_value',
        'stg.order_items',
        'core.fact_order_item',

        (
            SELECT COALESCE(SUM(sale_price), 0)::DOUBLE
            FROM stg.order_items
        ),

        (
            SELECT COALESCE(SUM(gross_sales_value), 0)::DOUBLE
            FROM core.fact_order_item
        ),

        0.01

    UNION ALL

    SELECT
        'gross_sales_fact_to_monthly_mart',
        'core.fact_order_item',
        'mart.sales_monthly',

        (
            SELECT COALESCE(SUM(gross_sales_value), 0)::DOUBLE
            FROM core.fact_order_item
        ),

        (
            SELECT COALESCE(SUM(gross_sales_value), 0)::DOUBLE
            FROM mart.sales_monthly
        ),

        0.01

    UNION ALL

    SELECT
        'net_sales_fact_to_monthly_mart',
        'core.fact_order_item',
        'mart.sales_monthly',

        (
            SELECT COALESCE(SUM(net_sales_value), 0)::DOUBLE
            FROM core.fact_order_item
        ),

        (
            SELECT COALESCE(SUM(net_sales_value), 0)::DOUBLE
            FROM mart.sales_monthly
        ),

        0.01

    UNION ALL

    SELECT
        'net_profit_fact_to_monthly_mart',
        'core.fact_order_item',
        'mart.sales_monthly',

        (
            SELECT COALESCE(SUM(net_profit_value), 0)::DOUBLE
            FROM core.fact_order_item
        ),

        (
            SELECT COALESCE(SUM(net_profit_value), 0)::DOUBLE
            FROM mart.sales_monthly
        ),

        0.01
)

SELECT
    metric_name,
    source_layer,
    modeled_layer,
    source_value,
    modeled_value,
    source_value - modeled_value AS variance,
    tolerance,

    CASE
        WHEN ABS(source_value - modeled_value) <= tolerance
        THEN 'PASS'
        ELSE 'FAIL'
    END AS status

FROM metrics;


/* ============================================================
   3. CURRENT METRIC SNAPSHOT

   This is a summary of the current warehouse run.
   CREATE OR REPLACE stores the latest snapshot only.
   ============================================================ */

CREATE OR REPLACE TABLE qa.metric_snapshot AS

SELECT
    CURRENT_TIMESTAMP AS snapshot_at,

    (SELECT COUNT(*) FROM core.dim_customer) AS customers,
    (SELECT COUNT(*) FROM core.dim_product) AS products,
    (SELECT COUNT(*) FROM core.fact_order) AS orders,
    (SELECT COUNT(*) FROM core.fact_order_item) AS order_items,
    (SELECT COUNT(*) FROM core.fact_session) AS sessions,
    (SELECT COUNT(*) FROM core.fact_inventory) AS inventory_units,

    (
        SELECT COALESCE(SUM(gross_sales_value), 0)
        FROM core.fact_order_item
    ) AS gross_sales_value,

    (
        SELECT COALESCE(SUM(net_sales_value), 0)
        FROM core.fact_order_item
    ) AS net_sales_value,

    (
        SELECT COALESCE(SUM(net_profit_value), 0)
        FROM core.fact_order_item
    ) AS net_profit_value,

    (
        SELECT COALESCE(SUM(returned_item_flag), 0)
        FROM core.fact_order_item
    ) AS returned_items,

    (
        SELECT COALESCE(SUM(cancelled_item_flag), 0)
        FROM core.fact_order_item
    ) AS cancelled_items;