# Code map

Every object in the warehouse, and the file and line that builds it. Generated
from the files themselves by `src/build_code_map.py` on every run, so it cannot
drift from the code.

---

## If you are looking for one thing

| Question | Open |
|---|---|
| A number in the dashboard looks wrong | `docs/kpi_dictionary.md`, then the mart below that owns it |
| How is net sales defined | `sql/duckdb/03_core_facts.sql` - `core.fact_order_item` |
| How do you handle the country spellings | `seeds/country_master.csv` + `sql/duckdb/02_core_dimensions.sql` |
| Show me the plan-versus-actual logic | `sql/duckdb/08_commercial_planning.sql` - `mart.plan_vs_actual_monthly` |
| How does the price-volume-mix bridge work | `sql/duckdb/08_commercial_planning.sql` - `mart.price_volume_mix` |
| What stops a bad build | `src/pipeline.py` - `assert_no_blocking_failures()` |
| What exactly do you check | `00_raw_quality.sql`, `07_quality_and_snapshots.sql`, `09_quality_commercial.sql` |
| Which rows got rejected and why | `sql/duckdb/08_commercial_planning.sql` - `qa.plan_rejects` |
| Prove nothing was lost between layers | `sql/duckdb/09_quality_commercial.sql` - `qa.reconciliation_statement` |
| Where does the segmentation come from | `src/advanced_analytics.py` - `rfm_segmentation()` |
| How was the forecast model chosen | `src/forecasting.py` - `backtest()`, and `docs/forecast_review.md` |
| How do I rebuild this | `docs/how_to_run.md`, then `src/run_all.py` |

---

## The SQL build, in run order

`src/pipeline.py` globs `sql/duckdb/*.sql` and runs them in name order. The
numbering is the dependency order, not a filing convention.

| # | File | Builds | Objects |
|---|---|---|---|
| 00 | `00_raw_quality.sql` | Source quality gate - runs before any model exists | 1 |
| 01 | `01_staging.sql` | Typing and renaming only, one view per source table | 8 |
| 02 | `02_core_dimensions.sql` | Conformed dimensions, where the country master is applied | 9 |
| 03 | `03_core_facts.sql` | Transactional grain, where gross/net/profit are defined | 4 |
| 04 | `04_mart_acquisition_funnel.sql` | Acquisition, funnel and channel marts | 5 |
| 05 | `05_mart_revenue_customer.sql` | Revenue, product, geography and customer marts | 6 |
| 06 | `06_mart_operations_inventory.sql` | Operations, delivery and inventory marts | 4 |
| 07 | `07_quality_and_snapshots.sql` | Warehouse quality gate + the executive snapshot | 3 |
| 08 | `08_commercial_planning.sql` | The second source: harmonisation, FX, plan vs actual, PVM | 8 |
| 09 | `09_quality_commercial.sql` | Commercial quality gate + the reconciliation statement | 2 |

---

## Every warehouse object

`lines` is the length of the statement, so you can see at a glance which objects
carry real logic and which are a straight projection.

### `stg` - 9 objects

| Object | File | Line | Lines |
|---|---|---|---|
| `stg.distribution_centers` | `sql/duckdb/01_staging.sql` | 118 | 7 |
| `stg.events` | `sql/duckdb/01_staging.sql` | 59 | 15 |
| `stg.inventory_events` | `sql/duckdb/01_staging.sql` | 102 | 15 |
| `stg.order_items` | `sql/duckdb/01_staging.sql` | 44 | 14 |
| `stg.orders` | `sql/duckdb/01_staging.sql` | 31 | 12 |
| `stg.plan_submissions` | `sql/duckdb/08_commercial_planning.sql` | 33 | 45 |
| `stg.products` | `sql/duckdb/01_staging.sql` | 18 | 12 |
| `stg.sessions` | `sql/duckdb/01_staging.sql` | 76 | 25 |
| `stg.users` | `sql/duckdb/01_staging.sql` | 3 | 14 |

### `core` - 14 objects

| Object | File | Line | Lines |
|---|---|---|---|
| `core.dim_acquisition_source` | `sql/duckdb/02_core_dimensions.sql` | 116 | 4 |
| `core.dim_country` | `sql/duckdb/02_core_dimensions.sql` | 130 | 10 |
| `core.dim_customer` | `sql/duckdb/02_core_dimensions.sql` | 61 | 24 |
| `core.dim_date` | `sql/duckdb/02_core_dimensions.sql` | 3 | 57 |
| `core.dim_distribution_center` | `sql/duckdb/02_core_dimensions.sql` | 108 | 2 |
| `core.dim_market` | `sql/duckdb/02_core_dimensions.sql` | 149 | 10 |
| `core.dim_month` | `sql/duckdb/02_core_dimensions.sql` | 160 | 15 |
| `core.dim_product` | `sql/duckdb/02_core_dimensions.sql` | 86 | 21 |
| `core.dim_session_traffic_source` | `sql/duckdb/02_core_dimensions.sql` | 111 | 4 |
| `core.fact_inventory` | `sql/duckdb/03_core_facts.sql` | 107 | 24 |
| `core.fact_order` | `sql/duckdb/03_core_facts.sql` | 1 | 27 |
| `core.fact_order_item` | `sql/duckdb/03_core_facts.sql` | 29 | 40 |
| `core.fact_plan` | `sql/duckdb/08_commercial_planning.sql` | 113 | 19 |
| `core.fact_session` | `sql/duckdb/03_core_facts.sql` | 70 | 36 |

### `mart` - 21 objects

| Object | File | Line | Lines |
|---|---|---|---|
| `mart.acquisition_source_value` | `sql/duckdb/04_mart_acquisition_funnel.sql` | 86 | 11 |
| `mart.actual_country_month` | `sql/duckdb/08_commercial_planning.sql` | 136 | 23 |
| `mart.cart_abandonment_segments` | `sql/duckdb/04_mart_acquisition_funnel.sql` | 51 | 19 |
| `mart.channel_quality` | `sql/duckdb/04_mart_acquisition_funnel.sql` | 71 | 14 |
| `mart.cohort_retention` | `sql/duckdb/05_mart_revenue_customer.sql` | 132 | 30 |
| `mart.commercial_scorecard` | `sql/duckdb/08_commercial_planning.sql` | 335 | 120 |
| `mart.customer_360` | `sql/duckdb/05_mart_revenue_customer.sql` | 86 | 45 |
| `mart.delivery_performance_dc` | `sql/duckdb/06_mart_operations_inventory.sql` | 21 | 20 |
| `mart.executive_snapshot` | `sql/duckdb/07_quality_and_snapshots.sql` | 117 | 16 |
| `mart.funnel_monthly_channel` | `sql/duckdb/04_mart_acquisition_funnel.sql` | 33 | 17 |
| `mart.funnel_stage_channel` | `sql/duckdb/04_mart_acquisition_funnel.sql` | 3 | 29 |
| `mart.geography_performance_country` | `sql/duckdb/05_mart_revenue_customer.sql` | 65 | 20 |
| `mart.inventory_performance` | `sql/duckdb/06_mart_operations_inventory.sql` | 71 | 19 |
| `mart.operations_monthly` | `sql/duckdb/06_mart_operations_inventory.sql` | 1 | 19 |
| `mart.plan_vs_actual_monthly` | `sql/duckdb/08_commercial_planning.sql` | 168 | 30 |
| `mart.plan_vs_actual_region` | `sql/duckdb/08_commercial_planning.sql` | 202 | 16 |
| `mart.price_volume_mix` | `sql/duckdb/08_commercial_planning.sql` | 235 | 93 |
| `mart.product_performance_brand` | `sql/duckdb/05_mart_revenue_customer.sql` | 43 | 14 |
| `mart.product_performance_category` | `sql/duckdb/05_mart_revenue_customer.sql` | 24 | 18 |
| `mart.return_risk_segments` | `sql/duckdb/06_mart_operations_inventory.sql` | 42 | 28 |
| `mart.sales_monthly` | `sql/duckdb/05_mart_revenue_customer.sql` | 1 | 22 |

### `qa` - 6 objects

| Object | File | Line | Lines |
|---|---|---|---|
| `qa.metric_reconciliation` | `sql/duckdb/07_quality_and_snapshots.sql` | 95 | 21 |
| `qa.plan_rejects` | `sql/duckdb/08_commercial_planning.sql` | 89 | 18 |
| `qa.plan_validation` | `sql/duckdb/09_quality_commercial.sql` | 14 | 117 |
| `qa.raw_test_results` | `sql/duckdb/00_raw_quality.sql` | 19 | 80 |
| `qa.reconciliation_statement` | `sql/duckdb/09_quality_commercial.sql` | 139 | 48 |
| `qa.test_results` | `sql/duckdb/07_quality_and_snapshots.sql` | 10 | 84 |

---

## The Python modules

| File | Lines | Does |
|---|---|---|
| `src/advanced_analytics.py` | 573 | - |
| `src/build_code_map.py` | 227 | Generate docs/code_map.md - an index of every object to the file that builds it. |
| `src/build_commercial_notebook.py` | 393 | Generate notebooks/05_commercial_planning_and_forecast.ipynb from the warehouse. |
| `src/build_data_catalogue.py` | 236 | Generate docs/warehouse_catalogue.md - every table, every column, from the warehouse. |
| `src/build_excel_pack.py` | 482 | Build the monthly commercial management pack as a formatted Excel workbook. |
| `src/build_notebooks.py` | 301 | - |
| `src/build_plan_source.py` | 273 | Generate the regional commercial plan submissions that the pipeline consumes. |
| `src/build_project_walkthrough.py` | 1129 | Generate notebooks/00_project_walkthrough.ipynb. |
| `src/explore.py` | 343 | Interactive exploration helpers for the DuckDB warehouse. Read-only. |
| `src/forecasting.py` | 427 | Monthly net-sales forecast, backtest, scenarios, and forecast-vs-plan. |
| `src/pipeline.py` | 399 | - |
| `src/render_commercial_figures.py` | 238 | Figures for the commercial planning layer. |
| `src/render_outputs.py` | 201 | - |
| `src/run_all.py` | 88 | - |
| `src/validate_project.py` | 69 | - |

### Public functions worth knowing

| File | Functions |
|---|---|
| `src/advanced_analytics.py` | `save_figure()`, `rfm_segmentation()`, `run()` |
| `src/build_code_map.py` | `scan_sql()`, `scan_python()`, `render()`, `run()` |
| `src/build_commercial_notebook.py` | `build()` |
| `src/build_data_catalogue.py` | `quote()`, `catalogue()`, `run()` |
| `src/build_excel_pack.py` | `write_frame()`, `build_scorecard()`, `build_plan_vs_actual()`, `build_pvm()`, `build_quality()`, `build_definitions()`, `run()` |
| `src/build_notebooks.py` | `analysis_notebook()`, `sessionization_notebook()`, `run()` |
| `src/build_plan_source.py` | `load_actuals()`, `build_plan()`, `apply_submission_defects()`, `run()` |
| `src/build_project_walkthrough.py` | `md()`, `code()`, `figure()`, `conclusion()`, `section()` |
| `src/explore.py` | `open_warehouse()` |
| `src/forecasting.py` | `seasonal_naive()`, `seasonal_naive_drift()`, `holt_winters_log()`, `backtest()`, `run()` |
| `src/pipeline.py` | `configure_logging()`, `sql_literal()`, `check_source_files()`, `ingest_file()`, `ingest_reference()`, `ingest_raw()`, `assert_no_blocking_failures()`, `execute_sql_modules()` |
| `src/render_commercial_figures.py` | `save_figure()`, `price_volume_mix_waterfall()`, `plan_achievement()`, `run()` |
| `src/render_outputs.py` | `save_figure()`, `render_figures()`, `run()` |
| `src/run_all.py` | `run_command()` |
| `src/validate_project.py` | `run()` |

---

## Scoped but not delivered

Present in the repository, listed in the walkthrough under Next steps, and
deliberately absent from the index above, the dashboard and the management pack.
No result from any of it is presented as a finding.

| Where | What |
|---|---|
| `src/advanced_analytics.py` | `return_propensity_model()`, `market_basket()`, `experiment_power_plan()`, `hypothesis_tests()` |

---

## Reading any of it without leaving a notebook

```python
import sys; sys.path.insert(0, "../src")
from explore import open_warehouse

w = open_warehouse()
w.source("mart.price_volume_mix")        # the full statement, from the file
w.source("core.fact_order_item", 40)    # the first 40 lines of it
w.owns("qa.plan_rejects")               # just the file and line
```

