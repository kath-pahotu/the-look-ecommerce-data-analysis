CREATE OR REPLACE TABLE mart.operations_monthly AS
SELECT
    d.month_start,
    COUNT(*) AS items,
    SUM(f.valid_timeline_flag) AS valid_timeline_items,
    AVG(f.ship_lead_days) AS avg_ship_lead_days,
    median(f.ship_lead_days) AS median_ship_lead_days,
    quantile_cont(f.ship_lead_days, 0.90) AS p90_ship_lead_days,
    AVG(f.delivery_lead_days) AS avg_delivery_lead_days,
    median(f.delivery_lead_days) AS median_delivery_lead_days,
    quantile_cont(f.delivery_lead_days, 0.90) AS p90_delivery_lead_days,
    AVG(f.end_to_end_lead_days) AS avg_end_to_end_lead_days,
    median(f.end_to_end_lead_days) AS median_end_to_end_lead_days,
    quantile_cont(f.end_to_end_lead_days, 0.90) AS p90_end_to_end_lead_days,
    SUM(f.returned_item_flag)::DOUBLE / NULLIF(SUM(f.return_observation_eligible_flag), 0) AS observed_return_rate,
    SUM(f.cancelled_item_flag)::DOUBLE / COUNT(*) AS cancellation_rate
FROM core.fact_order_item f
JOIN core.dim_date d ON f.order_date_key = d.date_key
GROUP BY d.month_start;

CREATE OR REPLACE TABLE mart.delivery_performance_dc AS
SELECT
    dc.distribution_center_id,
    dc.distribution_center_name,
    COUNT(*) AS items,
    SUM(f.valid_timeline_flag) AS valid_timeline_items,
    AVG(f.ship_lead_days) AS avg_ship_lead_days,
    median(f.ship_lead_days) AS median_ship_lead_days,
    quantile_cont(f.ship_lead_days, 0.90) AS p90_ship_lead_days,
    AVG(f.delivery_lead_days) AS avg_delivery_lead_days,
    median(f.delivery_lead_days) AS median_delivery_lead_days,
    quantile_cont(f.delivery_lead_days, 0.90) AS p90_delivery_lead_days,
    AVG(f.end_to_end_lead_days) AS avg_end_to_end_lead_days,
    median(f.end_to_end_lead_days) AS median_end_to_end_lead_days,
    quantile_cont(f.end_to_end_lead_days, 0.90) AS p90_end_to_end_lead_days,
    SUM(f.returned_item_flag)::DOUBLE / NULLIF(SUM(f.return_observation_eligible_flag), 0) AS observed_return_rate
FROM core.fact_order_item f
JOIN core.dim_distribution_center dc
  ON f.distribution_center_id = dc.distribution_center_id
GROUP BY dc.distribution_center_id, dc.distribution_center_name;

CREATE OR REPLACE TABLE mart.return_risk_segments AS
WITH segments AS (
    SELECT 'Category' AS segment_type, p.category AS segment_value,
           COUNT(*) AS items, SUM(f.return_observation_eligible_flag) AS eligible_items,
           SUM(f.returned_item_flag) AS returned_items, SUM(f.returned_value) AS returned_value
    FROM core.fact_order_item f JOIN core.dim_product p ON f.product_id = p.product_id
    GROUP BY p.category
    UNION ALL
    SELECT 'Country', c.country, COUNT(*), SUM(f.return_observation_eligible_flag),
           SUM(f.returned_item_flag), SUM(f.returned_value)
    FROM core.fact_order_item f JOIN core.dim_customer c ON f.customer_id = c.user_id
    GROUP BY c.country
    UNION ALL
    SELECT 'Age Band', c.age_band, COUNT(*), SUM(f.return_observation_eligible_flag),
           SUM(f.returned_item_flag), SUM(f.returned_value)
    FROM core.fact_order_item f JOIN core.dim_customer c ON f.customer_id = c.user_id
    GROUP BY c.age_band
    UNION ALL
    SELECT 'Acquisition Source', f.acquisition_source, COUNT(*), SUM(f.return_observation_eligible_flag),
           SUM(f.returned_item_flag), SUM(f.returned_value)
    FROM core.fact_order_item f
    GROUP BY f.acquisition_source
)
SELECT
    *,
    returned_items::DOUBLE / NULLIF(eligible_items, 0) AS observed_return_rate
FROM segments
WHERE eligible_items >= 100;

CREATE OR REPLACE TABLE mart.inventory_performance AS
SELECT
    p.department,
    p.category,
    dc.distribution_center_name,
    COUNT(*) AS inventory_units,
    SUM(i.sold_flag) AS sold_units,
    COUNT(*) - SUM(i.sold_flag) AS unsold_units,
    SUM(i.sold_flag)::DOUBLE / COUNT(*) AS sell_through_rate,
    median(i.days_to_sell) AS median_days_to_sell,
    quantile_cont(i.days_to_sell, 0.90) AS p90_days_to_sell,
    SUM(CASE WHEN i.inventory_age_bucket = '181+ days' THEN 1 ELSE 0 END) AS aged_181_plus_units,
    SUM(CASE WHEN i.sold_flag = 0 THEN i.unit_cost ELSE 0 END) AS unsold_inventory_cost,
    SUM(CASE WHEN i.sold_flag = 0 THEN i.retail_price ELSE 0 END) AS unsold_inventory_retail_value
FROM core.fact_inventory i
JOIN core.dim_product p ON i.product_id = p.product_id
JOIN core.dim_distribution_center dc
  ON i.distribution_center_id = dc.distribution_center_id
GROUP BY p.department, p.category, dc.distribution_center_name;
