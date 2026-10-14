# Warehouse catalogue

Every object in the warehouse: **66 tables and views, 685 columns**. Generated from the live warehouse by
`src/build_data_catalogue.py` on every build, so it cannot drift from the data.

## How to read a column row

| Column | Means |
|---|---|
| **Nulls** | how many rows have no value. A LEFT JOIN onto a column with nulls produces nulls downstream that were never planned for. |
| **Distinct** | how many different values. Equal to the row count means the column is a candidate key; very low means it is a category worth grouping by. |
| **Example** | a real value from the table, so the format is visible - `2024-01-27 22:36:43` versus `20240127` matters when writing a join. |

For a live version of this on any single table, the workbench has `w.cols("core.fact_plan")`.

## Contents

### [`raw`](#raw) - 10 objects

| Object | Rows | Grain |
|---|---|---|
| [`raw.country_master`](#rawcountry_master) | 16 | - |
| [`raw.distribution_centers`](#rawdistribution_centers) | 10 | - |
| [`raw.events`](#rawevents) | 2,420,661 | - |
| [`raw.fx_budget_rates`](#rawfx_budget_rates) | 10 | - |
| [`raw.inventory_events`](#rawinventory_events) | 488,146 | - |
| [`raw.order_items`](#raworder_items) | 180,862 | - |
| [`raw.orders`](#raworders) | 124,814 | - |
| [`raw.plan_submissions`](#rawplan_submissions) | 292 | - |
| [`raw.products`](#rawproducts) | 29,120 | - |
| [`raw.users`](#rawusers) | 100,000 | - |

### [`stg`](#stg) - 9 objects

| Object | Rows | Grain |
|---|---|---|
| [`stg.distribution_centers`](#stgdistribution_centers) | 10 | - |
| [`stg.events`](#stgevents) | 2,420,661 | - |
| [`stg.inventory_events`](#stginventory_events) | 488,146 | - |
| [`stg.order_items`](#stgorder_items) | 180,862 | - |
| [`stg.orders`](#stgorders) | 124,814 | - |
| [`stg.plan_submissions`](#stgplan_submissions) | 292 | - |
| [`stg.products`](#stgproducts) | 29,120 | - |
| [`stg.sessions`](#stgsessions) | 680,862 | one row per session_id |
| [`stg.users`](#stgusers) | 100,000 | - |

### [`core`](#core) - 14 objects

| Object | Rows | Grain |
|---|---|---|
| [`core.dim_acquisition_source`](#coredim_acquisition_source) | 5 | - |
| [`core.dim_country`](#coredim_country) | 16 | one row per observed source spelling (a mapping table - canonical_country repeats) |
| [`core.dim_customer`](#coredim_customer) | 100,000 | one row per customer |
| [`core.dim_date`](#coredim_date) | 1,994 | one row per calendar day |
| [`core.dim_distribution_center`](#coredim_distribution_center) | 10 | - |
| [`core.dim_market`](#coredim_market) | 13 | one row per canonical market |
| [`core.dim_month`](#coredim_month) | 67 | one row per month |
| [`core.dim_product`](#coredim_product) | 29,120 | one row per product |
| [`core.dim_session_traffic_source`](#coredim_session_traffic_source) | 5 | - |
| [`core.fact_inventory`](#corefact_inventory) | 488,146 | one row per inventory item |
| [`core.fact_order`](#corefact_order) | 124,814 | one row per order |
| [`core.fact_order_item`](#corefact_order_item) | 180,862 | one row per order line item |
| [`core.fact_plan`](#corefact_plan) | 287 | one row per canonical_country x plan_month (accepted rows only) |
| [`core.fact_session`](#corefact_session) | 680,862 | one row per session |

### [`mart`](#mart) - 27 objects

| Object | Rows | Grain |
|---|---|---|
| [`mart.acquisition_source_value`](#martacquisition_source_value) | 5 | - |
| [`mart.actual_country_month`](#martactual_country_month) | 770 | one row per canonical_country x month |
| [`mart.cart_abandonment_segments`](#martcart_abandonment_segments) | 22 | - |
| [`mart.channel_quality`](#martchannel_quality) | 5 | - |
| [`mart.cohort_retention`](#martcohort_retention) | 1,936 | one row per acquisition cohort x months-since |
| [`mart.commercial_scorecard`](#martcommercial_scorecard) | 9 | one row per KPI |
| [`mart.customer_360`](#martcustomer_360) | 80,095 | one row per customer |
| [`mart.delivery_performance_dc`](#martdelivery_performance_dc) | 10 | - |
| [`mart.executive_snapshot`](#martexecutive_snapshot) | 12 | - |
| [`mart.forecast_accuracy`](#martforecast_accuracy) | 3 | - |
| [`mart.forecast_backtest_detail`](#martforecast_backtest_detail) | 576 | - |
| [`mart.forecast_country_month`](#martforecast_country_month) | 104 | - |
| [`mart.forecast_monthly`](#martforecast_monthly) | 8 | - |
| [`mart.forecast_scenarios`](#martforecast_scenarios) | 24 | - |
| [`mart.forecast_vs_plan`](#martforecast_vs_plan) | 24 | - |
| [`mart.funnel_monthly_channel`](#martfunnel_monthly_channel) | 325 | - |
| [`mart.funnel_stage_channel`](#martfunnel_stage_channel) | 20 | - |
| [`mart.geography_performance_country`](#martgeography_performance_country) | 13 | one row per canonical market |
| [`mart.inventory_performance`](#martinventory_performance) | 356 | - |
| [`mart.operations_monthly`](#martoperations_monthly) | 65 | one row per month |
| [`mart.plan_vs_actual_monthly`](#martplan_vs_actual_monthly) | 860 | one row per canonical_country x month |
| [`mart.plan_vs_actual_region`](#martplan_vs_actual_region) | 6 | one row per region |
| [`mart.price_volume_mix`](#martprice_volume_mix) | 108 | one row per comparison x category |
| [`mart.product_performance_brand`](#martproduct_performance_brand) | 2,755 | - |
| [`mart.product_performance_category`](#martproduct_performance_category) | 36 | - |
| [`mart.return_risk_segments`](#martreturn_risk_segments) | 48 | - |
| [`mart.sales_monthly`](#martsales_monthly) | 65 | one row per month |

### [`qa`](#qa) - 6 objects

| Object | Rows | Grain |
|---|---|---|
| [`qa.metric_reconciliation`](#qametric_reconciliation) | 5 | - |
| [`qa.plan_rejects`](#qaplan_rejects) | 5 | one row per quarantined submission |
| [`qa.plan_validation`](#qaplan_validation) | 12 | one row per commercial check |
| [`qa.raw_test_results`](#qaraw_test_results) | 9 | one row per source check |
| [`qa.reconciliation_statement`](#qareconciliation_statement) | 8 | one row per stream x step |
| [`qa.test_results`](#qatest_results) | 14 | one row per warehouse check |

---

## raw

The source files, landed exactly as delivered. Nothing is typed, renamed or cleaned here - this layer exists so that every later number can be traced back to the row it came from.

### `raw.country_master`

**16 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `source_country_value` | VARCHAR | - | 16 | `Australia` |
| `canonical_country` | VARCHAR | - | 14 | `Australia` |
| `region` | VARCHAR | - | 4 | `AMER` |
| `sub_region` | VARCHAR | - | 11 | `Benelux` |
| `is_alias` | BIGINT | - | 2 | `0` |
| `alias_reason` | VARCHAR | 12 | 4 | `Customers with no country recorded` |

### `raw.distribution_centers`

**10 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `id` | BIGINT | - | 10 | `1` |
| `name` | VARCHAR | - | 10 | `Charleston SC` |
| `latitude` | DOUBLE | - | 10 | `29.7604` |
| `longitude` | DOUBLE | - | 10 | `-118.25` |

### `raw.events`

**2,420,661 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `id` | BIGINT | - | 2,420,661 | `1` |
| `user_id` | BIGINT | 1,124,527 | 80,095 | `1` |
| `sequence_number` | BIGINT | - | 13 | `1` |
| `session_id` | VARCHAR | - | 680,862 | `000033df-8326-4121-817b-591468a...` |
| `created_at` | TIMESTAMP | - | 2,145,707 | `2019-01-02 00:15:00` |
| `ip_address` | VARCHAR | - | 680,806 | `1.0.106.52` |
| `city` | VARCHAR | - | 8,778 | `A Ramallosa` |
| `state` | VARCHAR | - | 231 | `Acre` |
| `postal_code` | VARCHAR | - | 17,327 | `002-8054` |
| `browser` | VARCHAR | - | 5 | `Chrome` |
| `traffic_source` | VARCHAR | - | 5 | `Adwords` |
| `uri` | VARCHAR | - | 35,530 | `/cancel` |
| `event_type` | VARCHAR | - | 6 | `cancel` |

### `raw.fx_budget_rates`

**10 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `currency_code` | VARCHAR | - | 10 | `AUD` |
| `currency_name` | VARCHAR | - | 10 | `Australian Dollar` |
| `budget_rate_to_usd` | DOUBLE | - | 10 | `0.00025` |
| `rate_basis` | VARCHAR | - | 2 | `Budget rate fixed at planning c...` |

### `raw.inventory_events`

**488,146 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `id` | BIGINT | - | 488,146 | `1` |
| `product_id` | BIGINT | - | 29,045 | `1` |
| `created_at` | TIMESTAMP | - | 462,705 | `2018-11-28 00:54:28` |
| `sold_at` | TIMESTAMP | 307,284 | 180,640 | `2019-01-09 03:58:22` |
| `cost` | DOUBLE | - | 26,312 | `0.0082999997779726` |
| `product_category` | VARCHAR | - | 26 | `Accessories` |
| `product_name` | VARCHAR | 20 | 27,242 | `!iT Jeans Junior's Billy Shorts` |
| `product_brand` | VARCHAR | 374 | 2,754 | `!it Jeans` |
| `product_retail_price` | DOUBLE | - | 4,185 | `0.0199999995529651` |
| `product_department` | VARCHAR | - | 2 | `Men` |
| `product_sku` | VARCHAR | - | 29,045 | `00003E3B9E5336685200AE85D21B4F5E` |
| `product_distribution_center_id` | BIGINT | - | 10 | `1` |

### `raw.order_items`

**180,862 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `id` | BIGINT | - | 180,862 | `1` |
| `order_id` | BIGINT | - | 124,814 | `1` |
| `user_id` | BIGINT | - | 80,095 | `1` |
| `product_id` | BIGINT | - | 29,045 | `1` |
| `inventory_item_id` | BIGINT | - | 180,862 | `100001` |
| `status` | VARCHAR | - | 5 | `Cancelled` |
| `created_at` | TIMESTAMP | - | 180,640 | `2019-01-09 03:58:22` |
| `shipped_at` | TIMESTAMP | 62,943 | 79,322 | `2019-01-10 14:39:00` |
| `delivered_at` | TIMESTAMP | 117,399 | 43,224 | `2019-02-08 09:59:00` |
| `returned_at` | TIMESTAMP | 162,821 | 12,390 | `2019-02-18 06:19:00` |
| `sale_price` | DOUBLE | - | 4,185 | `0.0199999995529651` |

### `raw.orders`

**124,814 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `order_id` | BIGINT | - | 124,814 | `1` |
| `user_id` | BIGINT | - | 80,095 | `1` |
| `status` | VARCHAR | - | 5 | `Cancelled` |
| `gender` | VARCHAR | - | 2 | `F` |
| `created_at` | TIMESTAMP | - | 117,491 | `2019-01-09 05:08:00` |
| `returned_at` | TIMESTAMP | 112,375 | 12,390 | `2019-02-18 06:19:00` |
| `shipped_at` | TIMESTAMP | 43,360 | 79,322 | `2019-01-10 14:39:00` |
| `delivered_at` | TIMESTAMP | 80,947 | 43,224 | `2019-02-08 09:59:00` |
| `num_of_item` | BIGINT | - | 4 | `1` |

### `raw.plan_submissions`

**292 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `submission_batch` | VARCHAR | - | 2 | `FY2023-PLAN-V1` |
| `submitted_country` | VARCHAR | - | 13 | `Australia` |
| `plan_month` | DATE | - | 24 | `2023-01-01` |
| `currency_code` | VARCHAR | - | 10 | `AUD` |
| `plan_net_sales_local` | DOUBLE | 4 | 251 | `-2685.19` |
| `plan_units` | BIGINT | - | 234 | `1` |

### `raw.products`

**29,120 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `id` | BIGINT | - | 29,120 | `1` |
| `cost` | DOUBLE | - | 26,375 | `0.0082999997779726` |
| `category` | VARCHAR | - | 26 | `Accessories` |
| `name` | VARCHAR | 2 | 27,309 | `!iT Jeans Junior's Billy Shorts` |
| `brand` | VARCHAR | 24 | 2,756 | `!it Jeans` |
| `retail_price` | DOUBLE | - | 4,194 | `0.0199999995529651` |
| `department` | VARCHAR | - | 2 | `Men` |
| `sku` | VARCHAR | - | 29,120 | `00003E3B9E5336685200AE85D21B4F5E` |
| `distribution_center_id` | BIGINT | - | 10 | `1` |

### `raw.users`

**100,000 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `id` | BIGINT | - | 100,000 | `1` |
| `first_name` | VARCHAR | - | 690 | `Aaron` |
| `last_name` | VARCHAR | - | 1,000 | `Abbott` |
| `email` | VARCHAR | - | 83,678 | `aaronadams@example.com` |
| `age` | BIGINT | - | 59 | `12` |
| `gender` | VARCHAR | - | 2 | `F` |
| `state` | VARCHAR | - | 227 | `Acre` |
| `street_address` | VARCHAR | - | 100,000 | `000 Fowler Point Suite 412` |
| `postal_code` | VARCHAR | - | 15,639 | `002-8054` |
| `city` | VARCHAR | - | 7,880 | `Aachen` |
| `country` | VARCHAR | - | 15 | `Australia` |
| `latitude` | DOUBLE | - | 16,365 | `-0.1713982778` |
| `longitude` | DOUBLE | - | 16,321 | `-0.004981921591` |
| `traffic_source` | VARCHAR | - | 5 | `Display` |
| `created_at` | TIMESTAMP | - | 97,903 | `2019-01-02 00:22:00` |

---

## stg

One view per source table. Types cast, columns renamed to a consistent convention, and nothing else: no joins, no filtering, no business logic. Row counts must equal the source exactly.

### `stg.distribution_centers`

**10 rows** · `view`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `distribution_center_id` | INTEGER | - | 10 | `1` |
| `distribution_center_name` | VARCHAR | - | 10 | `Charleston SC` |
| `latitude` | DOUBLE | - | 10 | `29.7604` |
| `longitude` | DOUBLE | - | 10 | `-118.25` |

### `stg.events`

**2,420,661 rows** · `view`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `event_id` | BIGINT | - | 2,420,661 | `1` |
| `user_id` | BIGINT | 1,124,527 | 80,095 | `1` |
| `sequence_number` | INTEGER | - | 13 | `1` |
| `session_id` | VARCHAR | - | 680,862 | `000033df-8326-4121-817b-591468a...` |
| `created_at` | TIMESTAMP | - | 2,145,707 | `2019-01-02 00:15:00` |
| `city` | VARCHAR | - | 8,778 | `A Ramallosa` |
| `state` | VARCHAR | - | 231 | `Acre` |
| `postal_code` | VARCHAR | - | 17,327 | `002-8054` |
| `browser` | VARCHAR | - | 5 | `Chrome` |
| `traffic_source` | VARCHAR | - | 5 | `Adwords` |
| `uri` | VARCHAR | - | 35,530 | `/cancel` |
| `event_type` | VARCHAR | - | 6 | `cancel` |

### `stg.inventory_events`

**488,146 rows** · `view`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `inventory_item_id` | BIGINT | - | 488,146 | `1` |
| `product_id` | BIGINT | - | 29,045 | `1` |
| `created_at` | TIMESTAMP | - | 462,705 | `2018-11-28 00:54:28` |
| `sold_at` | TIMESTAMP | 307,284 | 180,640 | `2019-01-09 03:58:22` |
| `unit_cost` | DOUBLE | - | 26,312 | `0.0082999997779726` |
| `category` | VARCHAR | - | 26 | `Accessories` |
| `product_name` | VARCHAR | - | 27,243 | `!iT Jeans Junior's Billy Shorts` |
| `brand` | VARCHAR | - | 2,755 | `!it Jeans` |
| `retail_price` | DOUBLE | - | 4,185 | `0.0199999995529651` |
| `department` | VARCHAR | - | 2 | `Men` |
| `sku` | VARCHAR | - | 29,045 | `00003E3B9E5336685200AE85D21B4F5E` |
| `distribution_center_id` | INTEGER | - | 10 | `1` |

### `stg.order_items`

**180,862 rows** · `view`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `order_item_id` | BIGINT | - | 180,862 | `1` |
| `order_id` | BIGINT | - | 124,814 | `1` |
| `user_id` | BIGINT | - | 80,095 | `1` |
| `product_id` | BIGINT | - | 29,045 | `1` |
| `inventory_item_id` | BIGINT | - | 180,862 | `100001` |
| `item_status` | VARCHAR | - | 5 | `Cancelled` |
| `created_at` | TIMESTAMP | - | 180,640 | `2019-01-09 03:58:22` |
| `shipped_at` | TIMESTAMP | 62,943 | 79,322 | `2019-01-10 14:39:00` |
| `delivered_at` | TIMESTAMP | 117,399 | 43,224 | `2019-02-08 09:59:00` |
| `returned_at` | TIMESTAMP | 162,821 | 12,390 | `2019-02-18 06:19:00` |
| `sale_price` | DOUBLE | - | 4,185 | `0.0199999995529651` |

### `stg.orders`

**124,814 rows** · `view`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `order_id` | BIGINT | - | 124,814 | `1` |
| `user_id` | BIGINT | - | 80,095 | `1` |
| `order_status` | VARCHAR | - | 5 | `Cancelled` |
| `gender` | VARCHAR | - | 2 | `F` |
| `created_at` | TIMESTAMP | - | 117,491 | `2019-01-09 05:08:00` |
| `returned_at` | TIMESTAMP | 112,375 | 12,390 | `2019-02-18 06:19:00` |
| `shipped_at` | TIMESTAMP | 43,360 | 79,322 | `2019-01-10 14:39:00` |
| `delivered_at` | TIMESTAMP | 80,947 | 43,224 | `2019-02-08 09:59:00` |
| `item_count` | INTEGER | - | 4 | `1` |

### `stg.plan_submissions`

**292 rows** · `view`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `submission_batch` | VARCHAR | - | 2 | `FY2023-PLAN-V1` |
| `submitted_country` | VARCHAR | - | 13 | `Australia` |
| `submitted_country_trimmed` | VARCHAR | - | 13 | `Australia` |
| `canonical_country` | VARCHAR | - | 13 | `Australia` |
| `region` | VARCHAR | - | 3 | `AMER` |
| `sub_region` | VARCHAR | - | 10 | `Benelux` |
| `plan_month` | DATE | - | 24 | `2023-01-01` |
| `currency_code` | VARCHAR | - | 10 | `AUD` |
| `budget_rate_to_usd` | DOUBLE | - | 10 | `0.00025` |
| `plan_net_sales_local` | DOUBLE | 4 | 251 | `-2685.19` |
| `plan_net_sales_usd` | DOUBLE | 4 | 252 | `-2900.0052` |
| `plan_units` | BIGINT | - | 234 | `1` |
| `flag_unmapped_country` | INTEGER | - | 1 | `0` |
| `flag_missing_fx_rate` | INTEGER | - | 1 | `0` |
| `flag_blank_target` | INTEGER | - | 2 | `0` |
| `flag_negative_target` | INTEGER | - | 2 | `0` |
| `flag_whitespace_in_key` | INTEGER | - | 2 | `0` |

### `stg.products`

**29,120 rows** · `view`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `product_id` | BIGINT | - | 29,120 | `1` |
| `unit_cost` | DOUBLE | - | 26,375 | `0.0082999997779726` |
| `category` | VARCHAR | - | 26 | `Accessories` |
| `product_name` | VARCHAR | - | 27,310 | `!iT Jeans Junior's Billy Shorts` |
| `brand` | VARCHAR | - | 2,757 | `!it Jeans` |
| `retail_price` | DOUBLE | - | 4,194 | `0.0199999995529651` |
| `department` | VARCHAR | - | 2 | `Men` |
| `sku` | VARCHAR | - | 29,120 | `00003E3B9E5336685200AE85D21B4F5E` |
| `distribution_center_id` | INTEGER | - | 10 | `1` |

### `stg.sessions`

**680,862 rows** · `view` · grain: one row per session_id

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `session_id` | VARCHAR | - | 680,862 | `000033df-8326-4121-817b-591468a...` |
| `user_id` | BIGINT | 500,000 | 80,095 | `1` |
| `event_count` | INTEGER | - | 7 | `1` |
| `events_with_user_id` | INTEGER | - | 5 | `0` |
| `event_identity_coverage_rate` | DOUBLE | - | 2 | `0.0` |
| `session_start_at` | TIMESTAMP | - | 628,366 | `2019-01-02 00:15:00` |
| `session_end_at` | TIMESTAMP | - | 628,819 | `2019-01-02 00:29:00` |
| `city` | VARCHAR | - | 8,778 | `A Ramallosa` |
| `state` | VARCHAR | - | 231 | `Acre` |
| `postal_code` | VARCHAR | - | 17,327 | `002-8054` |
| `browser` | VARCHAR | - | 5 | `Chrome` |
| `traffic_source` | VARCHAR | - | 5 | `Adwords` |
| `first_event_type` | VARCHAR | - | 3 | `department` |
| `final_event_type` | VARCHAR | - | 4 | `cancel` |
| `home_flag` | INTEGER | - | 2 | `0` |
| `department_flag` | INTEGER | - | 2 | `0` |
| `product_view_flag` | INTEGER | - | 1 | `1` |
| `cart_flag` | INTEGER | - | 2 | `0` |
| `purchase_flag` | INTEGER | - | 2 | `0` |
| `cancel_event_flag` | INTEGER | - | 2 | `0` |

### `stg.users`

**100,000 rows** · `view`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `user_id` | BIGINT | - | 100,000 | `1` |
| `age` | INTEGER | - | 59 | `12` |
| `gender` | VARCHAR | - | 2 | `F` |
| `state` | VARCHAR | - | 227 | `Acre` |
| `postal_code` | VARCHAR | - | 15,639 | `002-8054` |
| `city` | VARCHAR | - | 7,880 | `Aachen` |
| `country` | VARCHAR | - | 15 | `Australia` |
| `latitude` | DOUBLE | - | 16,365 | `-0.1713982778` |
| `longitude` | DOUBLE | - | 16,321 | `-0.004981921591` |
| `acquisition_source` | VARCHAR | - | 5 | `Display` |
| `registered_at` | TIMESTAMP | - | 97,903 | `2019-01-02 00:22:00` |

---

## core

The conformed model. Dimensions every fact joins to, and facts at the transactional grain carrying the derived measures. This is where gross, net and profit are defined, and where the country master is applied.

### `core.dim_acquisition_source`

**5 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `acquisition_source_key` | INTEGER | - | 5 | `1` |
| `acquisition_source` | VARCHAR | - | 5 | `Display` |

### `core.dim_country`

**16 rows** · `table` · grain: one row per observed source spelling (a mapping table - canonical_country repeats)

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `country_key` | INTEGER | - | 16 | `1` |
| `source_country_value` | VARCHAR | - | 16 | `Australia` |
| `canonical_country` | VARCHAR | - | 14 | `Australia` |
| `region` | VARCHAR | - | 4 | `AMER` |
| `sub_region` | VARCHAR | - | 11 | `Benelux` |
| `is_alias` | INTEGER | - | 2 | `0` |
| `alias_reason` | VARCHAR | 12 | 4 | `Customers with no country recorded` |

### `core.dim_customer`

**100,000 rows** · `table` · grain: one row per customer

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `user_id` | BIGINT | - | 100,000 | `1` |
| `age` | INTEGER | - | 59 | `12` |
| `age_band` | VARCHAR | - | 6 | `18-24` |
| `gender` | VARCHAR | - | 2 | `F` |
| `country` | VARCHAR | - | 15 | `Australia` |
| `state` | VARCHAR | - | 227 | `Acre` |
| `city` | VARCHAR | - | 7,880 | `Aachen` |
| `postal_code` | VARCHAR | - | 15,639 | `002-8054` |
| `latitude` | DOUBLE | - | 16,365 | `-0.1713982778` |
| `longitude` | DOUBLE | - | 16,321 | `-0.004981921591` |
| `acquisition_source` | VARCHAR | - | 5 | `Display` |
| `registered_at` | TIMESTAMP | - | 97,903 | `2019-01-02 00:22:00` |
| `registered_date_key` | INTEGER | - | 1,954 | `20190102` |

### `core.dim_date`

**1,994 rows** · `table` · grain: one row per calendar day

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `date_key` | INTEGER | - | 1,994 | `20181128` |
| `calendar_date` | DATE | - | 1,994 | `2018-11-28` |
| `year` | INTEGER | - | 7 | `2018` |
| `quarter_number` | INTEGER | - | 4 | `1` |
| `quarter_label` | VARCHAR | - | 4 | `Q1` |
| `month_number` | INTEGER | - | 12 | `1` |
| `month_name` | VARCHAR | - | 12 | `April` |
| `month_year` | VARCHAR | - | 67 | `Apr 2019` |
| `month_start` | DATE | - | 67 | `2018-11-01` |
| `quarter_start` | DATE | - | 23 | `2018-10-01` |
| `year_start` | DATE | - | 7 | `2018-01-01` |
| `iso_week_number` | INTEGER | - | 53 | `1` |
| `iso_day_of_week` | INTEGER | - | 7 | `1` |
| `day_name` | VARCHAR | - | 7 | `Friday` |
| `is_weekend` | INTEGER | - | 2 | `0` |
| `is_complete_month` | INTEGER | - | 2 | `0` |
| `fiscal_year` | INTEGER | - | 6 | `2019` |
| `fiscal_year_label` | VARCHAR | - | 6 | `FY2019` |
| `fiscal_month_number` | INTEGER | - | 12 | `1` |
| `fiscal_quarter_number` | INTEGER | - | 4 | `1` |
| `fiscal_quarter_label` | VARCHAR | - | 4 | `FQ1` |
| `fiscal_year_start` | DATE | - | 6 | `2018-10-01` |

### `core.dim_distribution_center`

**10 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `distribution_center_id` | INTEGER | - | 10 | `1` |
| `distribution_center_name` | VARCHAR | - | 10 | `Charleston SC` |
| `latitude` | DOUBLE | - | 10 | `29.7604` |
| `longitude` | DOUBLE | - | 10 | `-118.25` |

### `core.dim_market`

**13 rows** · `table` · grain: one row per canonical market

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `market_key` | INTEGER | - | 13 | `1` |
| `canonical_country` | VARCHAR | - | 13 | `Australia` |
| `region` | VARCHAR | - | 3 | `AMER` |
| `sub_region` | VARCHAR | - | 10 | `Benelux` |
| `source_spellings_mapped` | BIGINT | - | 2 | `1` |

### `core.dim_month`

**67 rows** · `table` · grain: one row per month

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `month_start` | DATE | - | 67 | `2018-11-01` |
| `month_key` | INTEGER | - | 67 | `201811` |
| `year` | INTEGER | - | 7 | `2018` |
| `month_number` | INTEGER | - | 12 | `1` |
| `month_name` | VARCHAR | - | 12 | `April` |
| `month_year` | VARCHAR | - | 67 | `Apr 2019` |
| `quarter_label` | VARCHAR | - | 4 | `Q1` |
| `fiscal_year` | INTEGER | - | 6 | `2019` |
| `fiscal_year_label` | VARCHAR | - | 6 | `FY2019` |
| `fiscal_quarter_label` | VARCHAR | - | 4 | `FQ1` |
| `fiscal_month_number` | INTEGER | - | 12 | `1` |
| `is_complete_month` | INTEGER | - | 2 | `0` |

### `core.dim_product`

**29,120 rows** · `table` · grain: one row per product

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `product_id` | BIGINT | - | 29,120 | `1` |
| `category` | VARCHAR | - | 26 | `Accessories` |
| `product_name` | VARCHAR | - | 27,310 | `!iT Jeans Junior's Billy Shorts` |
| `brand` | VARCHAR | - | 2,757 | `!it Jeans` |
| `department` | VARCHAR | - | 2 | `Men` |
| `sku` | VARCHAR | - | 29,120 | `00003E3B9E5336685200AE85D21B4F5E` |
| `distribution_center_id` | INTEGER | - | 10 | `1` |
| `unit_cost` | DOUBLE | - | 26,375 | `0.0082999997779726` |
| `retail_price` | DOUBLE | - | 4,194 | `0.0199999995529651` |
| `unit_margin` | DOUBLE | - | 26,396 | `0.011699999774992502` |
| `unit_margin_rate` | DOUBLE | - | 3,191 | `0.33000000193715084` |
| `price_band` | VARCHAR | - | 5 | `$100-$199` |

### `core.dim_session_traffic_source`

**5 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `session_traffic_source_key` | INTEGER | - | 5 | `1` |
| `traffic_source` | VARCHAR | - | 5 | `Adwords` |

### `core.fact_inventory`

**488,146 rows** · `table` · grain: one row per inventory item

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `inventory_item_id` | BIGINT | - | 488,146 | `1` |
| `product_id` | BIGINT | - | 29,045 | `1` |
| `distribution_center_id` | INTEGER | - | 10 | `1` |
| `inventory_created_at` | TIMESTAMP | - | 462,705 | `2018-11-28 00:54:28` |
| `sold_at` | TIMESTAMP | 307,284 | 180,640 | `2019-01-09 03:58:22` |
| `inventory_created_date_key` | INTEGER | - | 1,967 | `20181128` |
| `unit_cost` | DOUBLE | - | 26,312 | `0.0082999997779726` |
| `retail_price` | DOUBLE | - | 4,185 | `0.0199999995529651` |
| `sold_flag` | INTEGER | - | 2 | `0` |
| `days_to_sell` | BIGINT | 307,284 | 61 | `0` |
| `unsold_age_days` | BIGINT | 180,862 | 1,589 | `10` |
| `inventory_age_bucket` | VARCHAR | - | 6 | `0-30 days` |

### `core.fact_order`

**124,814 rows** · `table` · grain: one row per order

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `order_id` | BIGINT | - | 124,814 | `1` |
| `customer_id` | BIGINT | - | 80,095 | `1` |
| `order_status` | VARCHAR | - | 5 | `Cancelled` |
| `order_created_at` | TIMESTAMP | - | 117,491 | `2019-01-09 05:08:00` |
| `shipped_at` | TIMESTAMP | 43,360 | 79,322 | `2019-01-10 14:39:00` |
| `delivered_at` | TIMESTAMP | 80,947 | 43,224 | `2019-02-08 09:59:00` |
| `returned_at` | TIMESTAMP | 112,375 | 12,390 | `2019-02-18 06:19:00` |
| `order_date_key` | INTEGER | - | 1,924 | `20190109` |
| `item_count` | INTEGER | - | 4 | `1` |
| `acquisition_source` | VARCHAR | - | 5 | `Display` |
| `ship_lead_days` | DOUBLE | 43,360 | 4,320 | `0.0` |
| `delivery_lead_days` | DOUBLE | 80,947 | 7,192 | `0.0` |
| `end_to_end_lead_days` | DOUBLE | 80,947 | 10,139 | `0.005555555555555556` |
| `return_cycle_days` | DOUBLE | 112,375 | 4,072 | `0.0` |
| `valid_timeline_flag` | INTEGER | - | 1 | `1` |
| `cancelled_order_flag` | INTEGER | - | 2 | `0` |
| `returned_order_flag` | INTEGER | - | 2 | `0` |
| `completed_order_flag` | INTEGER | - | 2 | `0` |

### `core.fact_order_item`

**180,862 rows** · `table` · grain: one row per order line item

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `order_item_id` | BIGINT | - | 180,862 | `1` |
| `order_id` | BIGINT | - | 124,814 | `1` |
| `customer_id` | BIGINT | - | 80,095 | `1` |
| `product_id` | BIGINT | - | 29,045 | `1` |
| `inventory_item_id` | BIGINT | - | 180,862 | `100001` |
| `distribution_center_id` | INTEGER | - | 10 | `1` |
| `acquisition_source` | VARCHAR | - | 5 | `Display` |
| `item_status` | VARCHAR | - | 5 | `Cancelled` |
| `order_item_created_at` | TIMESTAMP | - | 180,640 | `2019-01-09 03:58:22` |
| `shipped_at` | TIMESTAMP | 62,943 | 79,322 | `2019-01-10 14:39:00` |
| `delivered_at` | TIMESTAMP | 117,399 | 43,224 | `2019-02-08 09:59:00` |
| `returned_at` | TIMESTAMP | 162,821 | 12,390 | `2019-02-18 06:19:00` |
| `order_date_key` | INTEGER | - | 1,933 | `20190109` |
| `sale_price` | DOUBLE | - | 4,185 | `0.0199999995529651` |
| `unit_cost` | DOUBLE | - | 26,312 | `0.0082999997779726` |
| `gross_margin_value` | DOUBLE | - | 26,332 | `0.011699999774992502` |
| `gross_margin_rate` | DOUBLE | - | 3,190 | `0.33000000193715084` |
| `gross_sales_value` | DOUBLE | - | 4,185 | `0.0199999995529651` |
| `cancelled_value` | DOUBLE | - | 3,194 | `0.0` |
| `returned_value` | DOUBLE | - | 2,760 | `0.0` |
| `net_sales_value` | DOUBLE | - | 4,177 | `0.0` |
| `net_profit_value` | DOUBLE | - | 26,150 | `0.0` |
| `cancelled_item_flag` | INTEGER | - | 2 | `0` |
| `returned_item_flag` | INTEGER | - | 2 | `0` |
| `return_observation_eligible_flag` | INTEGER | - | 2 | `0` |
| `ship_lead_days` | DOUBLE | 98,383 | 4,529 | `0.0006944444444444445` |
| `delivery_lead_days` | DOUBLE | 117,399 | 7,192 | `0.0` |
| `end_to_end_lead_days` | DOUBLE | 123,517 | 10,772 | `0.001388888888888889` |
| `return_cycle_days` | DOUBLE | 162,821 | 4,072 | `0.0` |
| `valid_timeline_flag` | INTEGER | - | 2 | `0` |

### `core.fact_plan`

**287 rows** · `table` · grain: one row per canonical_country x plan_month (accepted rows only)

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `canonical_country` | VARCHAR | - | 13 | `Australia` |
| `region` | VARCHAR | - | 3 | `AMER` |
| `sub_region` | VARCHAR | - | 10 | `Benelux` |
| `plan_month` | DATE | - | 24 | `2023-01-01` |
| `plan_date_key` | INTEGER | - | 24 | `20230101` |
| `currency_code` | VARCHAR | - | 10 | `AUD` |
| `budget_rate_to_usd` | DOUBLE | - | 10 | `0.00025` |
| `plan_net_sales_local` | DOUBLE | - | 250 | `0.0` |
| `plan_net_sales_usd` | DOUBLE | - | 251 | `0.0` |
| `plan_units` | HUGEINT | - | 231 | `1` |
| `submission_batch` | VARCHAR | - | 2 | `FY2023-PLAN-V1` |

### `core.fact_session`

**680,862 rows** · `table` · grain: one row per session

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `session_id` | VARCHAR | - | 680,862 | `000033df-8326-4121-817b-591468a...` |
| `customer_id` | BIGINT | 500,000 | 80,095 | `1` |
| `session_start_at` | TIMESTAMP | - | 628,366 | `2019-01-02 00:15:00` |
| `session_end_at` | TIMESTAMP | - | 628,819 | `2019-01-02 00:29:00` |
| `session_date_key` | INTEGER | - | 1,955 | `20190102` |
| `browser` | VARCHAR | - | 5 | `Chrome` |
| `traffic_source` | VARCHAR | - | 5 | `Adwords` |
| `country` | VARCHAR | - | 16 | `Australia` |
| `event_count` | INTEGER | - | 7 | `1` |
| `events_with_user_id` | INTEGER | - | 5 | `0` |
| `event_identity_coverage_rate` | DOUBLE | - | 2 | `0.0` |
| `identified_session_flag` | INTEGER | - | 2 | `0` |
| `session_duration_seconds` | BIGINT | - | 6,765 | `0` |
| `first_event_type` | VARCHAR | - | 3 | `department` |
| `final_event_type` | VARCHAR | - | 4 | `cancel` |
| `home_flag` | INTEGER | - | 2 | `0` |
| `department_flag` | INTEGER | - | 2 | `0` |
| `product_view_flag` | INTEGER | - | 1 | `1` |
| `cart_flag` | INTEGER | - | 2 | `0` |
| `purchase_flag` | INTEGER | - | 2 | `0` |
| `cancel_event_flag` | INTEGER | - | 2 | `0` |
| `cart_abandoned_flag` | INTEGER | - | 2 | `0` |
| `early_product_exit_flag` | INTEGER | - | 2 | `0` |
| `highest_stage` | VARCHAR | - | 3 | `Cart` |

---

## mart

One table per business question, aggregated to the grain that question needs. Nothing here may introduce a number that cannot be derived from `core`.

### `mart.acquisition_source_value`

**5 rows** · `table`

Lifetime value by acquisition source

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `acquisition_source` | VARCHAR | - | 5 | `Display` |
| `orders` | BIGINT | - | 5 | `18599` |
| `customers` | BIGINT | - | 5 | `11949` |
| `gross_sales_value` | DOUBLE | - | 5 | `1605251.9117976613` |
| `net_sales_value` | DOUBLE | - | 5 | `1199981.9912325144` |
| `net_profit_value` | DOUBLE | - | 5 | `165810.8379796539` |
| `net_sales_per_customer` | DOUBLE | - | 5 | `100.42530682337555` |

### `mart.actual_country_month`

**770 rows** · `table` · grain: one row per canonical_country x month

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `canonical_country` | VARCHAR | - | 13 | `Australia` |
| `region` | VARCHAR | - | 3 | `AMER` |
| `sub_region` | VARCHAR | - | 10 | `Benelux` |
| `month_start` | DATE | - | 65 | `2019-01-01` |
| `fiscal_year` | INTEGER | - | 6 | `2019` |
| `fiscal_quarter_label` | VARCHAR | - | 4 | `FQ1` |
| `is_complete_month` | INTEGER | - | 2 | `0` |
| `gross_sales_value` | DOUBLE | - | 768 | `1000.14000415802` |
| `net_sales_value` | DOUBLE | - | 760 | `0.0` |
| `net_profit_value` | DOUBLE | - | 762 | `0.0` |
| `net_units` | HUGEINT | - | 317 | `0` |
| `orders` | BIGINT | - | 295 | `1` |
| `customers` | BIGINT | - | 301 | `1` |

### `mart.cart_abandonment_segments`

**22 rows** · `table`

Where carts are abandoned, and by whom

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `segment_type` | VARCHAR | - | 3 | `Browser` |
| `segment_value` | VARCHAR | - | 22 | `Adwords` |
| `sessions` | BIGINT | - | 22 | `136518` |
| `cart_sessions` | HUGEINT | - | 22 | `128650` |
| `abandoned_cart_sessions` | HUGEINT | - | 12 | `0` |
| `purchase_sessions` | HUGEINT | - | 22 | `0` |
| `cart_abandonment_rate` | DOUBLE | - | 12 | `0.0` |
| `session_conversion_rate` | DOUBLE | - | 12 | `0.0` |

### `mart.channel_quality`

**5 rows** · `table`

Channel-level conversion and value

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `traffic_source` | VARCHAR | - | 5 | `Adwords` |
| `sessions` | BIGINT | - | 5 | `203690` |
| `users` | BIGINT | - | 5 | `16189` |
| `cart_sessions` | HUGEINT | - | 5 | `128650` |
| `purchase_sessions` | HUGEINT | - | 5 | `18172` |
| `abandoned_cart_sessions` | HUGEINT | - | 5 | `112338` |
| `avg_events_per_session` | DOUBLE | - | 5 | `3.5436257517850267` |
| `avg_event_identity_coverage_rate` | DOUBLE | - | 5 | `0.2640061624151927` |
| `session_conversion_rate` | DOUBLE | - | 5 | `0.2640061624151927` |
| `cart_abandonment_rate` | DOUBLE | - | 5 | `0.5788156414318845` |

### `mart.cohort_retention`

**1,936 rows** · `table` · grain: one row per acquisition cohort x months-since

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `cohort_month` | DATE | - | 65 | `2019-01-01` |
| `months_since_first_order` | BIGINT | - | 63 | `0` |
| `cohort_size` | BIGINT | - | 65 | `10` |
| `active_customers` | BIGINT | - | 161 | `1` |
| `retention_rate` | DOUBLE | - | 649 | `0.00145985401459854` |

### `mart.commercial_scorecard`

**9 rows** · `table` · grain: one row per KPI

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `kpi_order` | INTEGER | - | 9 | `1` |
| `kpi_name` | VARCHAR | - | 9 | `Active Customers` |
| `kpi_format` | VARCHAR | - | 4 | `currency` |
| `reporting_month` | DATE | - | 1 | `2024-04-01` |
| `actual_value` | DOUBLE | - | 9 | `0.10671647851863884` |
| `prior_month_value` | DOUBLE | - | 9 | `0.09800796812749003` |
| `last_year_value` | DOUBLE | - | 9 | `0.09176632934682613` |
| `plan_value` | DOUBLE | 7 | 2 | `359799.983182` |
| `mom_variance` | DOUBLE | - | 9 | `-0.0006123306087267855` |
| `mom_variance_rate` | DOUBLE | - | 9 | `-0.0011795955802836877` |
| `yoy_variance` | DOUBLE | - | 9 | `-0.008823293620679434` |
| `yoy_variance_rate` | DOUBLE | - | 9 | `-0.05449386457771899` |
| `plan_variance` | DOUBLE | 7 | 2 | `190357.89733488671` |
| `plan_achievement_rate` | DOUBLE | 7 | 2 | `1.5290658872504637` |
| `plan_rag_status` | VARCHAR | - | 2 | `Green` |

### `mart.customer_360`

**80,095 rows** · `table` · grain: one row per customer

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `customer_id` | BIGINT | - | 80,095 | `1` |
| `age` | INTEGER | - | 59 | `12` |
| `age_band` | VARCHAR | - | 6 | `18-24` |
| `gender` | VARCHAR | - | 2 | `F` |
| `country` | VARCHAR | - | 15 | `Australia` |
| `state` | VARCHAR | - | 226 | `Acre` |
| `city` | VARCHAR | - | 7,609 | `Aachen` |
| `acquisition_source` | VARCHAR | - | 5 | `Display` |
| `registered_at` | TIMESTAMP | - | 78,759 | `2019-01-02 00:22:00` |
| `first_order_date` | DATE | - | 1,927 | `2019-01-09` |
| `last_order_date` | DATE | - | 1,886 | `2019-01-09` |
| `first_order_cohort_month` | DATE | - | 65 | `2019-01-01` |
| `recency_days` | BIGINT | - | 1,886 | `0` |
| `order_count` | BIGINT | - | 4 | `1` |
| `item_count` | BIGINT | - | 14 | `1` |
| `gross_sales_value` | DOUBLE | - | 32,284 | `0.0199999995529651` |
| `net_sales_value` | DOUBLE | - | 25,301 | `0.0` |
| `net_profit_value` | DOUBLE | - | 52,090 | `0.0` |
| `average_order_value` | DOUBLE | - | 28,925 | `0.0` |
| `returned_items` | HUGEINT | - | 10 | `0` |
| `cancelled_items` | HUGEINT | - | 10 | `0` |
| `observed_return_rate` | DOUBLE | 43,082 | 27 | `0.0` |
| `repeat_customer_flag` | INTEGER | - | 2 | `0` |

### `mart.delivery_performance_dc`

**10 rows** · `table`

Delivery lead time by distribution centre

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `distribution_center_id` | INTEGER | - | 10 | `1` |
| `distribution_center_name` | VARCHAR | - | 10 | `Charleston SC` |
| `items` | BIGINT | - | 10 | `11929` |
| `valid_timeline_items` | HUGEINT | - | 10 | `10474` |
| `avg_ship_lead_days` | DOUBLE | - | 10 | `1.4433856685400608` |
| `median_ship_lead_days` | DOUBLE | - | 10 | `1.3916666666666666` |
| `p90_ship_lead_days` | DOUBLE | - | 9 | `2.688888888888889` |
| `avg_delivery_lead_days` | DOUBLE | - | 10 | `2.458527252304366` |
| `median_delivery_lead_days` | DOUBLE | - | 10 | `2.4319444444444445` |
| `p90_delivery_lead_days` | DOUBLE | - | 10 | `4.486111111111111` |
| `avg_end_to_end_lead_days` | DOUBLE | - | 10 | `3.440038836356617` |
| `median_end_to_end_lead_days` | DOUBLE | - | 9 | `3.3201388888888888` |
| `p90_end_to_end_lead_days` | DOUBLE | - | 10 | `5.913055555555557` |
| `observed_return_rate` | DOUBLE | - | 10 | `0.27541176470588236` |

### `mart.executive_snapshot`

**12 rows** · `table`

The headline numbers, formatted for display

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `metric_name` | VARCHAR | - | 12 | `Cart Abandonment Rate` |
| `metric_value` | VARCHAR | - | 12 | `$10,796,335.70` |
| `numeric_value` | DOUBLE | 1 | 11 | `0.14968318386394047` |

### `mart.forecast_accuracy`

**3 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `model` | VARCHAR | - | 3 | `holt_winters_log` |
| `mape` | DOUBLE | - | 3 | `0.0800244783988406` |
| `mape_first_step` | DOUBLE | - | 3 | `0.06457007576607551` |
| `mape_final_step` | DOUBLE | - | 3 | `0.11529421225514007` |
| `worst_month_ape` | DOUBLE | - | 3 | `0.39408325588782117` |
| `bias` | DOUBLE | - | 3 | `-0.007107227671329379` |
| `horizon` | BIGINT | - | 1 | `8` |
| `origins` | BIGINT | - | 1 | `24` |
| `folds` | BIGINT | - | 1 | `192` |

### `mart.forecast_backtest_detail`

**576 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `model` | VARCHAR | - | 3 | `holt_winters_log` |
| `origin_month` | VARCHAR | - | 24 | `2021-10-01` |
| `target_month` | VARCHAR | - | 31 | `2021-10-01` |
| `step` | BIGINT | - | 8 | `1` |
| `actual` | DOUBLE | - | 31 | `113637.62017774582` |
| `predicted` | DOUBLE | - | 415 | `100215.44840494271` |
| `absolute_percentage_error` | DOUBLE | - | 415 | `0.0014986500353625473` |

### `mart.forecast_country_month`

**104 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `month_start` | TIMESTAMP | - | 8 | `2024-05-01 00:00:00` |
| `canonical_country` | VARCHAR | - | 13 | `Australia` |
| `allocation_share` | DOUBLE | - | 13 | `0.0003653814708909956` |
| `forecast_net_sales_usd` | DOUBLE | - | 104 | `10184.150957787571` |

### `mart.forecast_monthly`

**8 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `month_start` | TIMESTAMP | - | 8 | `2024-05-01 00:00:00` |
| `forecast_net_sales_usd` | DOUBLE | - | 8 | `513758.1005126238` |
| `model` | VARCHAR | - | 1 | `seasonal_naive_drift` |

### `mart.forecast_scenarios`

**24 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `scenario` | VARCHAR | - | 3 | `Base` |
| `month_start` | TIMESTAMP | - | 8 | `2024-05-01 00:00:00` |
| `forecast_net_sales_usd` | DOUBLE | - | 24 | `462382.2904613614` |
| `assumed_margin_rate` | DOUBLE | - | 3 | `0.4984898252161537` |
| `forecast_net_profit_usd` | DOUBLE | - | 24 | `230492.86715512886` |
| `volume_multiplier` | DOUBLE | - | 3 | `0.9` |
| `margin_delta_pp` | DOUBLE | - | 3 | `-2.0` |
| `narrative` | VARCHAR | - | 3 | `Current trend continues; no cha...` |

### `mart.forecast_vs_plan`

**24 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `month_start` | TIMESTAMP | - | 24 | `2023-01-01 00:00:00` |
| `actual_net_sales_usd` | DOUBLE | 8 | 16 | `167409.8501970768` |
| `forecast_net_sales_usd` | DOUBLE | 16 | 8 | `513758.1005126238` |
| `expected_net_sales_usd` | DOUBLE | - | 24 | `167409.8501970768` |
| `plan_net_sales_usd` | DOUBLE | - | 24 | `176999.99879299998` |
| `basis` | VARCHAR | - | 2 | `Actual` |
| `gap_to_plan_usd` | DOUBLE | - | 24 | `-11750.034155744186` |
| `expected_achievement_rate` | DOUBLE | - | 24 | `0.8562635036158227` |

### `mart.funnel_monthly_channel`

**325 rows** · `table`

The same funnel, by month

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `month_start` | DATE | - | 65 | `2019-01-01` |
| `traffic_source` | VARCHAR | - | 5 | `Adwords` |
| `sessions` | BIGINT | - | 302 | `1001` |
| `users` | BIGINT | - | 266 | `1` |
| `product_view_sessions` | HUGEINT | - | 302 | `1001` |
| `cart_sessions` | HUGEINT | - | 299 | `1017` |
| `purchase_sessions` | HUGEINT | - | 279 | `1` |
| `abandoned_cart_sessions` | HUGEINT | - | 217 | `100` |
| `session_conversion_rate` | DOUBLE | - | 324 | `0.0008731082654249127` |
| `cart_abandonment_rate` | DOUBLE | - | 324 | `0.09765625` |
| `avg_events_per_session` | DOUBLE | - | 325 | `2.2148541114058355` |
| `avg_session_duration_seconds` | DOUBLE | - | 325 | `10021.96029776675` |
| `avg_event_identity_coverage_rate` | DOUBLE | - | 324 | `0.0008731082654249127` |

### `mart.funnel_stage_channel`

**20 rows** · `table`

Funnel counts by stage and channel

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `traffic_source` | VARCHAR | - | 5 | `Adwords` |
| `stage_order` | INTEGER | - | 4 | `1` |
| `stage` | VARCHAR | - | 4 | `Cart Reached` |
| `stage_sessions` | HUGEINT | - | 15 | `128650` |
| `conversion_from_session_rate` | DOUBLE | - | 11 | `0.2640061624151927` |
| `conversion_from_previous_stage_rate` | DOUBLE | 5 | 11 | `0.4178467598236894` |

### `mart.geography_performance_country`

**13 rows** · `table` · grain: one row per canonical market

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `country` | VARCHAR | - | 13 | `Australia` |
| `region` | VARCHAR | - | 3 | `AMER` |
| `sub_region` | VARCHAR | - | 10 | `Benelux` |
| `orders` | BIGINT | - | 13 | `1560` |
| `customers` | BIGINT | - | 13 | `10` |
| `items` | BIGINT | - | 13 | `2268` |
| `net_sales_value` | DOUBLE | - | 13 | `1170130.541231431` |
| `net_profit_value` | DOUBLE | - | 13 | `103546.38685930346` |
| `average_order_value` | DOUBLE | - | 13 | `63.234397531167055` |
| `observed_return_rate` | DOUBLE | - | 13 | `0.15384615384615385` |
| `source_spellings` | VARCHAR | - | 13 | `Australia` |

### `mart.inventory_performance`

**356 rows** · `table`

Stock age and cover

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `department` | VARCHAR | - | 2 | `Men` |
| `category` | VARCHAR | - | 26 | `Accessories` |
| `distribution_center_name` | VARCHAR | - | 10 | `Charleston SC` |
| `inventory_units` | BIGINT | - | 333 | `1011` |
| `sold_units` | HUGEINT | - | 313 | `100` |
| `unsold_units` | HUGEINT | - | 324 | `100` |
| `sell_through_rate` | DOUBLE | - | 342 | `0.33984375` |
| `median_days_to_sell` | DOUBLE | - | 27 | `12.0` |
| `p90_days_to_sell` | DOUBLE | - | 63 | `44.80000000000001` |
| `aged_181_plus_units` | HUGEINT | - | 320 | `1004` |
| `unsold_inventory_cost` | DOUBLE | - | 356 | `10030.061221432044` |
| `unsold_inventory_retail_value` | DOUBLE | - | 356 | `100025.81072044373` |

### `mart.operations_monthly`

**65 rows** · `table` · grain: one row per month

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `month_start` | DATE | - | 65 | `2019-01-01` |
| `items` | BIGINT | - | 65 | `10040` |
| `valid_timeline_items` | HUGEINT | - | 65 | `1001` |
| `avg_ship_lead_days` | DOUBLE | - | 65 | `1.1134548611111112` |
| `median_ship_lead_days` | DOUBLE | - | 60 | `1.0743055555555556` |
| `p90_ship_lead_days` | DOUBLE | - | 62 | `1.9521527777777776` |
| `avg_delivery_lead_days` | DOUBLE | 1 | 64 | `2.296846299297677` |
| `median_delivery_lead_days` | DOUBLE | 1 | 63 | `2.16875` |
| `p90_delivery_lead_days` | DOUBLE | 1 | 64 | `4.198611111111111` |
| `avg_end_to_end_lead_days` | DOUBLE | 1 | 64 | `3.2912404214559383` |
| `median_end_to_end_lead_days` | DOUBLE | 1 | 64 | `2.9770833333333333` |
| `p90_end_to_end_lead_days` | DOUBLE | 1 | 63 | `5.678194444444444` |
| `observed_return_rate` | DOUBLE | 1 | 63 | `0.1810344827586207` |
| `cancellation_rate` | DOUBLE | - | 65 | `0.08695652173913043` |

### `mart.plan_vs_actual_monthly`

**860 rows** · `table` · grain: one row per canonical_country x month

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `canonical_country` | VARCHAR | - | 13 | `Australia` |
| `region` | VARCHAR | - | 3 | `AMER` |
| `month_start` | DATE | - | 72 | `2019-01-01` |
| `actual_net_sales_usd` | DOUBLE | 90 | 760 | `0.0` |
| `actual_units` | HUGEINT | 90 | 317 | `0` |
| `plan_net_sales_usd` | DOUBLE | 573 | 251 | `0.0` |
| `plan_units` | HUGEINT | 573 | 231 | `1` |
| `variance_usd` | DOUBLE | 663 | 197 | `-0.8580025177002426` |
| `variance_rate` | DOUBLE | 663 | 197 | `-0.00042900168785180913` |
| `achievement_rate` | DOUBLE | 663 | 197 | `0.0794631586576763` |
| `is_complete_month` | INTEGER | - | 2 | `0` |
| `in_plan_horizon` | INTEGER | - | 2 | `0` |
| `plan_status` | VARCHAR | - | 5 | `Actual with no plan` |

### `mart.plan_vs_actual_region`

**6 rows** · `table` · grain: one row per region

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `region` | VARCHAR | - | 3 | `AMER` |
| `plan_year` | DATE | - | 2 | `2023-01-01` |
| `actual_net_sales_usd` | DOUBLE | - | 6 | `1024573.540946126` |
| `plan_net_sales_usd` | DOUBLE | - | 6 | `1046200.0` |
| `variance_usd` | DOUBLE | - | 6 | `-21626.459053874016` |
| `achievement_rate` | DOUBLE | - | 6 | `0.9423430333845452` |
| `month_rows` | BIGINT | - | 6 | `10` |
| `months_without_plan` | HUGEINT | - | 3 | `1` |

### `mart.price_volume_mix`

**108 rows** · `table` · grain: one row per comparison x category

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `comparison_label` | VARCHAR | - | 3 | `Apr 2024 vs Apr 2023` |
| `comparison_order` | INTEGER | - | 3 | `1` |
| `department` | VARCHAR | - | 2 | `Men` |
| `category` | VARCHAR | - | 26 | `Accessories` |
| `units_prior` | HUGEINT | - | 103 | `106` |
| `units_current` | HUGEINT | - | 105 | `1003` |
| `revenue_prior` | DOUBLE | - | 108 | `10127.480041503906` |
| `revenue_current` | DOUBLE | - | 108 | `10743.59997677803` |
| `asp_prior` | DOUBLE | - | 108 | `110.06308270807136` |
| `asp_current` | DOUBLE | - | 108 | `100.23115728306752` |
| `total_variance` | DOUBLE | - | 108 | `10273.78002357483` |
| `volume_effect` | DOUBLE | - | 108 | `10350.438184669976` |
| `mix_effect` | DOUBLE | - | 108 | `-1036.8722387061707` |
| `price_effect` | DOUBLE | - | 108 | `-1045.041972810881` |

### `mart.product_performance_brand`

**2,755 rows** · `table`

Sales and margin by brand

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `brand` | VARCHAR | - | 2,755 | `!it Jeans` |
| `categories` | BIGINT | - | 21 | `1` |
| `products` | BIGINT | - | 126 | `1` |
| `orders` | BIGINT | - | 333 | `1` |
| `items` | BIGINT | - | 335 | `1` |
| `net_sales_value` | DOUBLE | - | 2,380 | `0.0` |
| `net_profit_value` | DOUBLE | - | 2,748 | `0.0` |
| `net_margin_rate` | DOUBLE | 6 | 2,464 | `0.3310000039637089` |
| `observed_return_rate` | DOUBLE | 97 | 358 | `0.0` |

### `mart.product_performance_category`

**36 rows** · `table`

Sales and margin by category

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `department` | VARCHAR | - | 2 | `Men` |
| `category` | VARCHAR | - | 26 | `Accessories` |
| `products` | BIGINT | - | 35 | `1041` |
| `orders` | BIGINT | - | 36 | `1014` |
| `customers` | BIGINT | - | 36 | `1004` |
| `items` | BIGINT | - | 36 | `1021` |
| `gross_sales_value` | DOUBLE | - | 36 | `107507.1401977539` |
| `net_sales_value` | DOUBLE | - | 36 | `125529.79023993015` |
| `net_profit_value` | DOUBLE | - | 36 | `100135.9358037227` |
| `net_margin_rate` | DOUBLE | - | 36 | `0.37602426690689567` |
| `returned_items` | HUGEINT | - | 36 | `100` |
| `observed_return_rate` | DOUBLE | - | 36 | `0.26130268199233714` |
| `cancellation_rate` | DOUBLE | - | 36 | `0.1288936627282492` |

### `mart.return_risk_segments`

**48 rows** · `table`

Return rate by segment

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `segment_type` | VARCHAR | - | 4 | `Acquisition Source` |
| `segment_value` | VARCHAR | - | 48 | `18-24` |
| `items` | BIGINT | - | 48 | `1021` |
| `eligible_items` | HUGEINT | - | 48 | `10649` |
| `returned_items` | HUGEINT | - | 47 | `100` |
| `returned_value` | DOUBLE | - | 48 | `108741.23016476631` |
| `observed_return_rate` | DOUBLE | - | 48 | `0.26130268199233714` |

### `mart.sales_monthly`

**65 rows** · `table` · grain: one row per month

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `month_start` | DATE | - | 65 | `2019-01-01` |
| `year` | INTEGER | - | 6 | `2019` |
| `month_number` | INTEGER | - | 12 | `1` |
| `is_complete_month` | INTEGER | - | 2 | `0` |
| `orders` | BIGINT | - | 64 | `103` |
| `customers` | BIGINT | - | 64 | `102` |
| `items` | BIGINT | - | 65 | `10040` |
| `gross_sales_value` | DOUBLE | - | 65 | `102529.76008415222` |
| `cancelled_value` | DOUBLE | - | 65 | `10235.640016555786` |
| `returned_value` | DOUBLE | - | 65 | `0.0` |
| `net_sales_value` | DOUBLE | - | 65 | `1035.6399946212769` |
| `net_profit_value` | DOUBLE | - | 65 | `100114.81687565282` |
| `net_margin_rate` | DOUBLE | - | 65 | `0.4939079044268592` |
| `average_order_value` | DOUBLE | - | 65 | `50.729444636238945` |
| `items_per_order` | DOUBLE | - | 65 | `1.2307692307692308` |
| `item_cancellation_rate` | DOUBLE | - | 65 | `0.08695652173913043` |
| `item_return_rate` | DOUBLE | - | 65 | `0.0` |

---

## qa

The evidence layer: check results, the quarantined rows, and the reconciliation statements. Exported to `outputs/qa/` on every build.

### `qa.metric_reconciliation`

**5 rows** · `table`

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `metric_name` | VARCHAR | - | 5 | `events_into_sessions_rows` |
| `source_value` | DOUBLE | - | 5 | `10796335.701331269` |
| `modeled_value` | DOUBLE | - | 5 | `10796335.701331269` |
| `variance` | DOUBLE | - | 1 | `0.0` |

### `qa.plan_rejects`

**5 rows** · `table` · grain: one row per quarantined submission

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `submission_batch` | VARCHAR | - | 2 | `FY2023-PLAN-V1` |
| `submitted_country` | VARCHAR | - | 5 | `Australia` |
| `plan_month` | DATE | - | 5 | `2023-05-01` |
| `currency_code` | VARCHAR | - | 4 | `AUD` |
| `plan_net_sales_local` | DOUBLE | 4 | 1 | `-2685.19` |
| `reject_reason` | VARCHAR | - | 2 | `Plan value is blank` |

### `qa.plan_validation`

**12 rows** · `table` · grain: one row per commercial check

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `check_name` | VARCHAR | - | 12 | `actuals_tie_to_fact_order_item` |
| `layer` | VARCHAR | - | 3 | `core` |
| `severity` | VARCHAR | - | 3 | `CRITICAL` |
| `failure_count` | BIGINT | - | 5 | `0` |
| `denominator` | BIGINT | - | 5 | `1` |
| `failure_rate` | DOUBLE | - | 5 | `0.0` |
| `status` | VARCHAR | - | 2 | `PASS` |
| `notes` | VARCHAR | - | 12 | `A gap means a region submitted ...` |

### `qa.raw_test_results`

**9 rows** · `table` · grain: one row per source check

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `check_name` | VARCHAR | - | 9 | `country_master_covers_source` |
| `layer` | VARCHAR | - | 1 | `raw` |
| `severity` | VARCHAR | - | 2 | `CRITICAL` |
| `failure_count` | BIGINT | - | 2 | `0` |
| `denominator` | BIGINT | - | 7 | `10` |
| `failure_rate` | DOUBLE | - | 2 | `0.0` |
| `status` | VARCHAR | - | 2 | `PASS` |
| `notes` | VARCHAR | - | 9 | `Event user_id is sparse; sessio...` |

### `qa.reconciliation_statement`

**8 rows** · `table` · grain: one row per stream x step

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `step_order` | INTEGER | - | 8 | `1` |
| `stream` | VARCHAR | - | 2 | `Plan` |
| `stage` | VARCHAR | - | 5 | `Source file` |
| `entity` | VARCHAR | - | 8 | `core.fact_order_item` |
| `row_count` | BIGINT | - | 5 | `135749` |
| `value_usd` | DOUBLE | 2 | 3 | `10796335.701331269` |
| `row_delta` | BIGINT | 2 | 4 | `-287` |
| `value_delta` | DOUBLE | 5 | 1 | `0.0` |
| `expectation` | VARCHAR | - | 8 | `Accepted rows only - source row...` |

### `qa.test_results`

**14 rows** · `table` · grain: one row per warehouse check

| Column | Type | Nulls | Distinct | Example |
|---|---|---|---|---|
| `check_name` | VARCHAR | - | 14 | `delivery_not_before_shipping` |
| `layer` | VARCHAR | - | 3 | `core` |
| `severity` | VARCHAR | - | 3 | `CRITICAL` |
| `failure_count` | HUGEINT | - | 3 | `0` |
| `denominator` | BIGINT | - | 6 | `1` |
| `failure_rate` | DOUBLE | - | 3 | `0.0` |
| `status` | VARCHAR | - | 2 | `PASS` |
| `notes` | VARCHAR | - | 14 | `Cost above retail would invalid...` |

