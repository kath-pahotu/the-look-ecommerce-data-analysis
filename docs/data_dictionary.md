# Modeled data dictionary

## Dimensions

### `dim_date`

Date key, calendar fields, month/quarter/year anchors, weekday, weekend, and `is_complete_month`.

### `dim_customer`

Privacy-safe customer attributes: numeric ID, age/age band, gender, country/state/city, coordinates, acquisition source, and registration timestamp. Names, email, street address, and IP are excluded.

### `dim_product`

Product ID, category, name, brand, department, SKU, distribution center, unit cost, retail price, unit margin, margin rate, and price band.

### `dim_distribution_center`

Distribution center ID, name, latitude, and longitude.

### `dim_session_traffic_source`

Distinct session-channel values derived from `events.csv` and used only with `fact_session`.

### `dim_acquisition_source`

Customer acquisition-source values used with order and order-item facts. The two source taxonomies are intentionally not conformed.

## Facts

### `fact_order`

One row per order with customer, status, dates, item count, acquisition source, lifecycle lead times, timeline-validity flag, and status flags.

### `fact_order_item`

One row per item with order/customer/product/inventory/DC keys, status, lifecycle dates, price, cost, gross/net sales, leakage, profit, return eligibility, lead times, and timeline-validity flag.

### `fact_session`

One row per distinct `events.session_id`, derived entirely from event records, with customer, date, browser, source, country, event and identity coverage, duration, funnel-stage flags, cart abandonment, early exit, and highest stage.

### `fact_inventory`

One row per inventory item with product/DC, created/sold dates, cost/retail, sold flag, days to sell, unsold age, and age bucket.

## Marts

`funnel_stage_channel`, `funnel_monthly_channel`, `channel_quality`, `cart_abandonment_segments`, `sales_monthly`, `product_performance_category`, `product_performance_brand`, `geography_performance_country`, `customer_360`, `cohort_retention`, `operations_monthly`, `delivery_performance_dc`, `return_risk_segments`, and `inventory_performance`.
