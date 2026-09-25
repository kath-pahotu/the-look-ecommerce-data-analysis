# Power BI build guide

## Before opening Power BI

1. Read `../README.md`.
2. Confirm `../artifacts/validation_report.json` says `PASS` and review `qa.test_results` for warnings.
3. Review session lineage in `../docs/technical_reference.md` and the reconciliation checks in `../sql/duckdb/07_quality_and_snapshots.sql`.

`fact_session` is already reconstructed from `events.csv` by the backend SQL. Do not import a separate session source file.

## Recommended import path

Use Parquet for speed when your Power BI version supports local Parquet; use CSV for widest compatibility.

1. Run the backend pipeline.
2. In Power BI Desktop, select **Get Data**:
   - Parquet: import each file in `data/processed/power_bi/parquet/`.
   - CSV: import each file in `data/processed/power_bi/csv/`.
   - SQL Server: select the deployed `model` tables and `mart` views.
3. Load core dimensions and facts first.
4. Load selected marts/advanced outputs only for pages that need them.
5. Keep session traffic source and customer acquisition source as separate dimensions; do not merge their labels.

## Core tables to load first

- `dim_date`
- `dim_customer`
- `dim_product`
- `dim_distribution_center`
- `dim_session_traffic_source`
- `dim_acquisition_source`
- `fact_order`
- `fact_order_item`
- `fact_session`
- `fact_inventory`

The remaining 15 exports are page-level marts that simplify specific visuals.

## Data-type setup

- Keys: Whole number, except `session_id`, which is text.
- Dates: Date.
- Timestamps: Date/Time.
- Currency: Fixed decimal number.
- Rates: Decimal number, formatted as percentage.
- Flags: Whole number or True/False.

## Relationships

Create the relationships in `data_model.md`. Use **one-to-many**, dimension-to-fact, **single direction**. Do not connect facts to facts.

Mark `dim_date[calendar_date]` as the date table.

## Measures

1. Create a blank table named `Measures`.
2. Add the definitions from `measures.dax`.
3. Organize display folders: Commercial, Growth, Funnel, Customer, Operations, Inventory, Data Quality.
4. Hide raw numeric columns when a measure exists.

## Theme and layout

Import `theme.json`. Build pages from `dashboard_blueprint.md`. Keep page canvas 16:9, white/near-white background, quiet grid lines, and restrained blue/gold/orange/olive/pink accents.

## Partial-period handling

May 2024 is incomplete. Use `dim_date[is_complete_month] = 1` for default period-comparison visuals or display a visible partial-period badge when the partial month is included.

## Required source-lineage tooltip

On the Acquisition & Funnel page, add a small information tooltip:

> Sessions are derived from event rows grouped by session ID. Anonymous sessions remain included in funnel denominators; customer analysis uses identified sessions only.

## SQL Server option

The local environment could not create/restore a database under the current Windows login. The SQL Server scripts are deployment-ready but require a login with `CREATE DATABASE`, `BULK INSERT`, and schema/table permissions. The executed DuckDB/CSV/Parquet path is the verified fallback.

## Refresh

- CSV/Parquet: rerun `src/run_all.py`, then Refresh in Power BI.
- SQL Server: rerun bulk load/model refresh scripts, then Refresh.
- Advanced tables: rerun Python methods before the Power BI refresh.

Finish with `../private_review/power_bi_build_checklist.md`.
