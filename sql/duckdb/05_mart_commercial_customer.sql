CREATE OR REPLACE TABLE mart.sales_monthly AS
SELECT
    d.month_start,
    d.year,
    d.month_number,
    MAX(d.is_complete_month) AS is_complete_month,
    COUNT(DISTINCT f.order_id) AS orders,
    COUNT(DISTINCT f.customer_id) AS customers,
    COUNT(*) AS items,
    SUM(f.gross_sales_value) AS gross_sales_value,
    SUM(f.cancelled_value) AS cancelled_value,
    SUM(f.returned_value) AS returned_value,
    SUM(f.net_sales_value) AS net_sales_value,
    SUM(f.net_profit_value) AS net_profit_value,
    SUM(f.net_profit_value) / NULLIF(SUM(f.net_sales_value), 0) AS net_margin_rate,
    SUM(f.net_sales_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    COUNT(*)::DOUBLE / NULLIF(COUNT(DISTINCT f.order_id), 0) AS items_per_order,
    SUM(f.cancelled_item_flag)::DOUBLE / COUNT(*) AS item_cancellation_rate,
    SUM(f.returned_item_flag)::DOUBLE / COUNT(*) AS item_return_rate
FROM core.fact_order_item f
JOIN core.dim_date d ON f.order_date_key = d.date_key
GROUP BY d.month_start, d.year, d.month_number;

CREATE OR REPLACE TABLE mart.product_performance_category AS
SELECT
    p.department,
    p.category,
    COUNT(DISTINCT f.product_id) AS products,
    COUNT(DISTINCT f.order_id) AS orders,
    COUNT(DISTINCT f.customer_id) AS customers,
    COUNT(*) AS items,
    SUM(f.gross_sales_value) AS gross_sales_value,
    SUM(f.net_sales_value) AS net_sales_value,
    SUM(f.net_profit_value) AS net_profit_value,
    SUM(f.net_profit_value) / NULLIF(SUM(f.net_sales_value), 0) AS net_margin_rate,
    SUM(f.returned_item_flag) AS returned_items,
    SUM(f.returned_item_flag)::DOUBLE / NULLIF(SUM(f.return_observation_eligible_flag), 0) AS observed_return_rate,
    SUM(f.cancelled_item_flag)::DOUBLE / COUNT(*) AS cancellation_rate
FROM core.fact_order_item f
JOIN core.dim_product p ON f.product_id = p.product_id
GROUP BY p.department, p.category;

CREATE OR REPLACE TABLE mart.product_performance_brand AS
SELECT
    p.brand,
    COUNT(DISTINCT p.category) AS categories,
    COUNT(DISTINCT f.product_id) AS products,
    COUNT(DISTINCT f.order_id) AS orders,
    COUNT(*) AS items,
    SUM(f.net_sales_value) AS net_sales_value,
    SUM(f.net_profit_value) AS net_profit_value,
    SUM(f.net_profit_value) / NULLIF(SUM(f.net_sales_value), 0) AS net_margin_rate,
    SUM(f.returned_item_flag)::DOUBLE / NULLIF(SUM(f.return_observation_eligible_flag), 0) AS observed_return_rate
FROM core.fact_order_item f
JOIN core.dim_product p ON f.product_id = p.product_id
GROUP BY p.brand;

CREATE OR REPLACE TABLE mart.geography_performance_country AS
SELECT
    c.country,
    COUNT(DISTINCT f.order_id) AS orders,
    COUNT(DISTINCT f.customer_id) AS customers,
    COUNT(*) AS items,
    SUM(f.net_sales_value) AS net_sales_value,
    SUM(f.net_profit_value) AS net_profit_value,
    SUM(f.net_sales_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    SUM(f.returned_item_flag)::DOUBLE / NULLIF(SUM(f.return_observation_eligible_flag), 0) AS observed_return_rate
FROM core.fact_order_item f
JOIN core.dim_customer c ON f.customer_id = c.user_id
GROUP BY c.country;

CREATE OR REPLACE TABLE mart.customer_360 AS
WITH as_of AS (SELECT MAX(order_item_created_at)::DATE AS as_of_date FROM core.fact_order_item),
customer_sales AS (
    SELECT
        customer_id,
        MIN(order_item_created_at)::DATE AS first_order_date,
        MAX(order_item_created_at)::DATE AS last_order_date,
        COUNT(DISTINCT order_id) AS order_count,
        COUNT(*) AS item_count,
        SUM(gross_sales_value) AS gross_sales_value,
        SUM(net_sales_value) AS net_sales_value,
        SUM(net_profit_value) AS net_profit_value,
        SUM(returned_item_flag) AS returned_items,
        SUM(cancelled_item_flag) AS cancelled_items,
        SUM(return_observation_eligible_flag) AS return_eligible_items
    FROM core.fact_order_item
    GROUP BY customer_id
)
SELECT
    c.user_id AS customer_id,
    c.age,
    c.age_band,
    c.gender,
    c.country,
    c.state,
    c.city,
    c.acquisition_source,
    c.registered_at,
    s.first_order_date,
    s.last_order_date,
    date_trunc('month', s.first_order_date)::DATE AS first_order_cohort_month,
    datediff('day', s.last_order_date, as_of.as_of_date) AS recency_days,
    s.order_count,
    s.item_count,
    s.gross_sales_value,
    s.net_sales_value,
    s.net_profit_value,
    s.net_sales_value / NULLIF(s.order_count, 0) AS average_order_value,
    s.returned_items,
    s.cancelled_items,
    s.returned_items::DOUBLE / NULLIF(s.return_eligible_items, 0) AS observed_return_rate,
    CASE WHEN s.order_count >= 2 THEN 1 ELSE 0 END AS repeat_customer_flag
FROM core.dim_customer c
JOIN customer_sales s ON c.user_id = s.customer_id
CROSS JOIN as_of;

CREATE OR REPLACE TABLE mart.cohort_retention AS
WITH eligible_activity AS (
    SELECT DISTINCT
        customer_id,
        date_trunc('month', order_item_created_at)::DATE AS activity_month
    FROM core.fact_order_item
    WHERE net_sales_value > 0
),
cohorted AS (
    SELECT
        customer_id,
        MIN(activity_month) OVER (PARTITION BY customer_id) AS cohort_month,
        activity_month
    FROM eligible_activity
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM cohorted
    WHERE activity_month = cohort_month
    GROUP BY cohort_month
)
SELECT
    c.cohort_month,
    datediff('month', c.cohort_month, c.activity_month) AS months_since_first_order,
    s.cohort_size,
    COUNT(DISTINCT c.customer_id) AS active_customers,
    COUNT(DISTINCT c.customer_id)::DOUBLE / s.cohort_size AS retention_rate
FROM cohorted c
JOIN cohort_sizes s USING (cohort_month)
GROUP BY c.cohort_month, months_since_first_order, s.cohort_size;
