from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import nbformat as nbf


def analysis_notebook(project_root: Path, connection: duckdb.DuckDBPyConnection):
    metrics = {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT metric_name, metric_value FROM mart.executive_snapshot"
        ).fetchall()
    }
    notebook = nbf.v4.new_notebook()
    notebook["metadata"]["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            f"""# TheLook eCommerce: data quality and core analysis

## tl;dr

- Gross sales: **{metrics['Gross Sales']}**; net sales after cancellations and returns: **{metrics['Net Sales']}**.
- Sessions: **{metrics['Sessions']}**; conversion: **{metrics['Session Conversion Rate']}**; cart abandonment: **{metrics['Cart Abandonment Rate']}**.
- The latest source month is partial and is excluded from default period comparisons.
- Invalid shipment-before-item timestamps are excluded from delivery lead-time measures."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

This notebook is the reproducible companion to the SQL warehouse and Power BI blueprint. It reads generated marts, validates the most decision-relevant checks, and visualizes acquisition, commercial, cohort, and operations evidence.

### Key Assumptions

- Net sales excludes Cancelled and Returned item value.
- Sessions are derived inside SQL from `events.csv` grouped by `session_id`; no source session file is used.
- Funnel conversion uses those derived sessions, not event rows.
- Customer retention means a later month with at least one non-cancelled/non-returned purchase.
- May 2024 is incomplete."""
        ),
        nbf.v4.new_markdown_cell("## Data\n\n### 1. Load generated marts"),
        nbf.v4.new_code_cell(
            """from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

CURRENT_DIR = Path.cwd()
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "notebooks" else CURRENT_DIR
ANALYSIS_DIR = PROJECT_ROOT / "data" / "processed" / "analysis"
QA_DIR = PROJECT_ROOT / "outputs" / "qa"

sales = pd.read_csv(ANALYSIS_DIR / "sales_monthly.csv", parse_dates=["month_start"])
channels = pd.read_csv(ANALYSIS_DIR / "channel_quality.csv")
acquisition = pd.read_csv(ANALYSIS_DIR / "acquisition_source_value.csv")
categories = pd.read_csv(ANALYSIS_DIR / "product_performance_category.csv")
cohorts = pd.read_csv(ANALYSIS_DIR / "cohort_retention.csv", parse_dates=["cohort_month"])
qa = pd.read_csv(QA_DIR / "test_results.csv")

{"sales_rows": len(sales), "channel_rows": len(channels), "acquisition_rows": len(acquisition), "category_rows": len(categories), "qa_status": qa["status"].value_counts().to_dict()}"""
        ),
        nbf.v4.new_markdown_cell("### 2. Check blocking data-quality tests"),
        nbf.v4.new_code_cell(
            """blocking_failures = qa[qa["status"] == "FAIL"]
assert blocking_failures.empty, blocking_failures
qa[qa["status"] != "PASS"][["check_name", "severity", "failure_count", "failure_rate", "notes"]]"""
        ),
        nbf.v4.new_markdown_cell("## Results\n\n### 3. Monthly commercial performance"),
        nbf.v4.new_code_cell(
            """sns.set_theme(style="whitegrid")
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(sales["month_start"], sales["net_sales_value"], label="Net sales", linewidth=2)
ax.plot(sales["month_start"], sales["net_profit_value"], label="Net profit", linewidth=2)
partial = sales[sales["is_complete_month"] == 0]
if not partial.empty:
    ax.axvspan(partial["month_start"].min(), partial["month_start"].max() + pd.offsets.MonthEnd(1), color="#D9DEE7", alpha=.55, label="Partial month")
ax.set(title="Monthly net sales and net profit", xlabel="", ylabel="USD")
ax.legend(frameon=False);"""
        ),
        nbf.v4.new_markdown_cell("### 4. Acquisition-source quality"),
        nbf.v4.new_code_cell(
            """from IPython.display import display
display(
    channels.sort_values("sessions", ascending=False)[
        ["traffic_source", "sessions", "session_conversion_rate", "cart_abandonment_rate"]
    ].style.format({
        "session_conversion_rate": "{:.1%}",
        "cart_abandonment_rate": "{:.1%}",
    })
)
display(
    acquisition.sort_values("net_sales_value", ascending=False)[
        ["acquisition_source", "customers", "orders", "net_sales_value", "net_sales_per_customer"]
    ].style.format({
        "net_sales_value": "${:,.0f}",
        "net_sales_per_customer": "${:,.2f}",
    })
)"""
        ),
        nbf.v4.new_markdown_cell("### 5. Product portfolio"),
        nbf.v4.new_code_cell(
            """fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(categories["net_sales_value"], categories["net_margin_rate"],
           s=categories["items"] / categories["items"].max() * 500 + 30,
           alpha=.55, color="#2457A7")
for _, row in categories.nlargest(8, "net_sales_value").iterrows():
    ax.annotate(row["category"], (row["net_sales_value"], row["net_margin_rate"]), xytext=(4,4), textcoords="offset points", fontsize=8)
ax.set(title="Category net sales and margin", xlabel="Net sales (USD)", ylabel="Net margin rate");"""
        ),
        nbf.v4.new_markdown_cell("### 6. Purchase cohort retention"),
        nbf.v4.new_code_cell(
            """latest = cohorts[cohorts["months_since_first_order"].between(0, 12)].copy()
latest["cohort_label"] = latest["cohort_month"].dt.strftime("%Y-%m")
matrix = latest.pivot(index="cohort_label", columns="months_since_first_order", values="retention_rate").tail(24)
fig, ax = plt.subplots(figsize=(11, 8))
sns.heatmap(matrix, cmap=sns.light_palette("#2457A7", as_cmap=True), vmin=0, vmax=1, ax=ax)
ax.set(title="Purchase cohort retention (latest 24 cohorts)", xlabel="Months since first order", ylabel="First-order cohort");"""
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- Acquisition volume is concentrated, so channel decisions should combine traffic, conversion, abandonment, and attributed net sales.
- Product volume, revenue, and margin are separate decision dimensions.
- Delivery analysis is trustworthy only after filtering invalid timestamp sequences and showing valid-record coverage.
- The generated star schema and DAX measures are the production-facing handoff; this notebook preserves the analytical audit trail."""
        ),
    ]
    return notebook


def sessionization_notebook(
    project_root: Path, connection: duckdb.DuckDBPyConnection
):
    metrics = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM raw.events) AS events,
            (SELECT COUNT(DISTINCT session_id) FROM stg.events) AS sessions,
            (SELECT COUNT(*) FROM core.fact_session WHERE customer_id IS NOT NULL) AS identified_sessions,
            (SELECT COUNT(*) FROM core.fact_session WHERE customer_id IS NULL) AS anonymous_sessions,
            (SELECT SUM(event_count) FROM core.fact_session) AS reconciled_events
        """
    ).fetchone()
    events, sessions, identified, anonymous, reconciled = metrics
    notebook = nbf.v4.new_notebook()
    notebook["metadata"]["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            f"""# Event-derived sessionization audit

## tl;dr

- The original dataset has seven input files; sessions are reconstructed only from `events.csv`.
- **{events:,}** events group into **{sessions:,}** unique sessions.
- Session event counts reconcile to **{reconciled:,}** source events with zero variance.
- **{identified:,}** sessions contain a customer ID and **{anonymous:,}** remain anonymous."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

This diagnostic notebook proves the source lineage used by the warehouse and Power BI funnel. The SQL pipeline groups normalized events by `session_id`, orders events by `sequence_number`, and derives timing, channel, browser, identity coverage, and funnel flags.

### Key Assumptions

- `session_id` is the session grain.
- A session may have zero or one nonnull customer ID; multiple IDs are a blocking error.
- Browser and traffic source must be constant inside a session; inconsistency is a blocking error.
- Event timestamps are interpreted as UTC."""
        ),
        nbf.v4.new_markdown_cell("## Data\n\n### 1. Connect to the executed warehouse"),
        nbf.v4.new_code_cell(
            """from pathlib import Path
import duckdb

CURRENT_DIR = Path.cwd()
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "notebooks" else CURRENT_DIR
connection = duckdb.connect(
    str(PROJECT_ROOT / "artifacts" / "thelook_analytics.duckdb"),
    read_only=True,
)
raw_tables = {
    row[0]
    for row in connection.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'"
    ).fetchall()
}
expected_raw_tables = {
    "users", "products", "orders", "order_items", "events",
    "inventory_events", "distribution_centers",
}
assert raw_tables == expected_raw_tables, (raw_tables, expected_raw_tables)
sorted(raw_tables)"""
        ),
        nbf.v4.new_markdown_cell("## Results\n\n### 2. Validate the event-to-session grain"),
        nbf.v4.new_code_cell(
            """session_profile = connection.execute(
    "WITH per_session AS ("
    " SELECT session_id, COUNT(*) AS event_count,"
    " COUNT(DISTINCT user_id) AS user_ids,"
    " COUNT(DISTINCT browser) AS browsers,"
    " COUNT(DISTINCT traffic_source) AS traffic_sources"
    " FROM stg.events GROUP BY session_id"
    ") SELECT COUNT(*) AS derived_sessions,"
    " SUM(session_id IS NULL OR session_id = '') AS invalid_session_ids,"
    " SUM(user_ids > 1) AS sessions_with_multiple_users,"
    " SUM(browsers > 1) AS sessions_with_multiple_browsers,"
    " SUM(traffic_sources > 1) AS sessions_with_multiple_sources"
    " FROM per_session"
).fetchdf()
session_profile"""
        ),
        nbf.v4.new_markdown_cell("### 3. Reconcile source events to modeled sessions"),
        nbf.v4.new_code_cell(
            """reconciliation = connection.execute(
    "SELECT"
    " (SELECT COUNT(*) FROM stg.events) AS source_events,"
    " (SELECT SUM(event_count) FROM core.fact_session) AS modeled_session_events,"
    " (SELECT COUNT(DISTINCT session_id) FROM stg.events) AS source_sessions,"
    " (SELECT COUNT(*) FROM core.fact_session) AS modeled_sessions"
).fetchdf()
assert reconciliation.loc[0, "source_events"] == reconciliation.loc[0, "modeled_session_events"]
assert reconciliation.loc[0, "source_sessions"] == reconciliation.loc[0, "modeled_sessions"]
reconciliation"""
        ),
        nbf.v4.new_markdown_cell("### 4. Review identity coverage and funnel fields"),
        nbf.v4.new_code_cell(
            """coverage = connection.execute(
    "SELECT COUNT(*) AS sessions,"
    " SUM(identified_session_flag) AS identified_sessions,"
    " AVG(event_identity_coverage_rate) AS average_session_event_identity_coverage,"
    " SUM(product_view_flag) AS product_sessions,"
    " SUM(cart_flag) AS cart_sessions,"
    " SUM(purchase_flag) AS purchase_sessions"
    " FROM core.fact_session"
).fetchdf()
coverage"""
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- `core.fact_session` is a modeled fact built from event records, not an original dataset file.
- The source and model reconcile at both event and session grain.
- Anonymous sessions remain valid for channel and funnel analysis, but customer-level segmentation must use identified sessions only.
- The executable transformation is in `sql/duckdb/01_staging.sql`; Power BI imports the resulting `fact_session` table."""
        ),
    ]
    return notebook


def run(project_root: Path) -> None:
    notebooks_dir = project_root / "notebooks"
    notebooks_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(
        str(project_root / "artifacts" / "thelook_analytics.duckdb"), read_only=True
    )
    try:
        nbf.write(
            analysis_notebook(project_root, connection),
            notebooks_dir / "01_data_quality_and_core_analysis.ipynb",
        )
        nbf.write(
            sessionization_notebook(project_root, connection),
            notebooks_dir / "03_event_sessionization_audit.ipynb",
        )
    finally:
        connection.close()
    # NOTE: 02_statistical_deep_dives.ipynb is hand-authored (the analytical-reasoning
    # walkthrough of Gini, RFM, and Return Propensity) and is intentionally NOT regenerated
    # here. run_all.py re-executes it in place so its outputs stay reproducible.


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.project_root.resolve())


if __name__ == "__main__":
    main()
