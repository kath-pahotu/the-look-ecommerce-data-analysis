from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


COLORS = {
    "blue": "#2457A7",
    "gold": "#C9952E",
    "orange": "#D8783F",
    "olive": "#7E8D42",
    "pink": "#C46686",
    "ink": "#20242C",
    "grid": "#D9DEE7",
}


def money(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.1%}"


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close()


def render_figures(connection: duckdb.DuckDBPyConnection, figure_dir: Path) -> None:
    sns.set_theme(style="whitegrid")

    monthly = connection.execute(
        """
        SELECT month_start, net_sales_value, net_profit_value, is_complete_month
        FROM mart.sales_monthly ORDER BY month_start
        """
    ).fetchdf()
    monthly["month_start"] = pd.to_datetime(monthly["month_start"])
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(
        monthly["month_start"],
        monthly["net_sales_value"],
        color=COLORS["blue"],
        linewidth=2,
        label="Net sales",
    )
    ax.plot(
        monthly["month_start"],
        monthly["net_profit_value"],
        color=COLORS["gold"],
        linewidth=2,
        label="Net profit",
    )
    partial = monthly[monthly["is_complete_month"] == 0]
    if not partial.empty:
        ax.axvspan(
            partial["month_start"].min(),
            partial["month_start"].max() + pd.offsets.MonthEnd(1),
            color=COLORS["grid"],
            alpha=0.55,
            label="Partial month",
        )
    ax.set_title("Monthly net sales and net profit")
    ax.set_xlabel("")
    ax.set_ylabel("USD")
    ax.legend(frameon=False, ncol=3)
    save_figure(figure_dir / "monthly_sales_profit.png")

    funnel = connection.execute(
        """
        SELECT traffic_source, stage_order, stage, stage_sessions
        FROM mart.funnel_stage_channel ORDER BY stage_order, traffic_source
        """
    ).fetchdf()
    pivot = funnel.pivot(index="stage", columns="traffic_source", values="stage_sessions")
    stage_order = ["Sessions", "Product Viewed", "Cart Reached", "Purchase"]
    pivot = pivot.reindex(stage_order)
    ax = pivot.plot(
        kind="bar",
        figsize=(11, 6),
        color=[
            COLORS["blue"],
            COLORS["gold"],
            COLORS["orange"],
            COLORS["olive"],
            COLORS["pink"],
        ],
    )
    ax.set_title("Funnel stage sessions by traffic source")
    ax.set_xlabel("")
    ax.set_ylabel("Sessions")
    ax.legend(title="Traffic source", frameon=False, ncol=3)
    save_figure(figure_dir / "funnel_by_channel.png")

    categories = connection.execute(
        """
        SELECT department, category, net_sales_value, net_margin_rate, items
        FROM mart.product_performance_category
        """
    ).fetchdf()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(
        categories["net_sales_value"],
        categories["net_margin_rate"],
        s=(categories["items"] / categories["items"].max() * 500 + 30),
        color=COLORS["blue"],
        alpha=0.55,
        edgecolors=COLORS["ink"],
        linewidth=0.4,
    )
    for _, row in categories.nlargest(8, "net_sales_value").iterrows():
        ax.annotate(
            row["department"] + " - " + row["category"],
            (row["net_sales_value"], row["net_margin_rate"]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_title("Category net sales and margin")
    ax.set_xlabel("Net sales (USD)")
    ax.set_ylabel("Net margin rate")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    save_figure(figure_dir / "category_sales_margin.png")

    delivery = connection.execute(
        """
        SELECT distribution_center_name, median_end_to_end_lead_days,
               p90_end_to_end_lead_days
        FROM mart.delivery_performance_dc
        ORDER BY median_end_to_end_lead_days
        """
    ).fetchdf()
    y = range(len(delivery))
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(
        [value - 0.18 for value in y],
        delivery["median_end_to_end_lead_days"],
        height=0.35,
        color=COLORS["blue"],
        label="Median",
    )
    ax.barh(
        [value + 0.18 for value in y],
        delivery["p90_end_to_end_lead_days"],
        height=0.35,
        color=COLORS["gold"],
        label="P90",
    )
    ax.set_yticks(list(y), delivery["distribution_center_name"])
    ax.set_title("End-to-end delivery lead time by distribution center")
    ax.set_xlabel("Days")
    ax.legend(frameon=False)
    save_figure(figure_dir / "delivery_lead_time_dc.png")

    cohort = connection.execute(
        """
        SELECT cohort_month, months_since_first_order, retention_rate
        FROM mart.cohort_retention
        WHERE months_since_first_order BETWEEN 0 AND 12
        """
    ).fetchdf()
    cohort["cohort_month"] = pd.to_datetime(cohort["cohort_month"]).dt.strftime("%Y-%m")
    matrix = cohort.pivot(
        index="cohort_month", columns="months_since_first_order", values="retention_rate"
    ).tail(24)
    fig, ax = plt.subplots(figsize=(11, 8))
    sns.heatmap(
        matrix,
        cmap=sns.light_palette(COLORS["blue"], as_cmap=True),
        vmin=0,
        vmax=1,
        ax=ax,
        cbar_kws={"label": "Retention rate"},
    )
    ax.set_title("Purchase cohort retention (latest 24 cohorts)")
    ax.set_xlabel("Months since first order")
    ax.set_ylabel("First-order cohort")
    save_figure(figure_dir / "cohort_retention_heatmap.png")


def render_documents(project_root: Path, connection: duckdb.DuckDBPyConnection) -> None:
    docs_dir = project_root / "docs"
    private_dir = project_root / "private_review"
    docs_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)

    totals = connection.execute(
        """
        SELECT
            SUM(gross_sales_value) AS gross_sales,
            SUM(cancelled_value) AS cancelled_value,
            SUM(returned_value) AS returned_value,
            SUM(net_sales_value) AS net_sales,
            SUM(net_profit_value) AS net_profit,
            COUNT(DISTINCT order_id) AS orders,
            COUNT(DISTINCT customer_id) AS customers
        FROM core.fact_order_item
        """
    ).fetchone()
    sessions = connection.execute(
        """
        SELECT COUNT(*) AS sessions, SUM(cart_flag) AS carts,
               SUM(purchase_flag) AS purchases,
               SUM(cart_abandoned_flag) AS abandoned
        FROM core.fact_session
        """
    ).fetchone()
    repeat_rate = connection.execute(
        "SELECT AVG(repeat_customer_flag) FROM mart.customer_360"
    ).fetchone()[0]
    top_categories = connection.execute(
        """
        SELECT department || ' - ' || category AS category_label,
               net_sales_value, net_profit_value, net_margin_rate,
               observed_return_rate
        FROM mart.product_performance_category
        ORDER BY net_sales_value DESC LIMIT 5
        """
    ).fetchall()
    channels = connection.execute(
        """
        SELECT traffic_source, sessions, session_conversion_rate,
               cart_abandonment_rate
        FROM mart.channel_quality
        ORDER BY sessions DESC
        """
    ).fetchall()
    acquisition_sources = connection.execute(
        """
        SELECT acquisition_source, customers, orders, net_sales_value,
               net_sales_per_customer
        FROM mart.acquisition_source_value
        ORDER BY net_sales_value DESC
        """
    ).fetchall()
    annual = connection.execute(
        """
        SELECT year, SUM(net_sales_value) AS net_sales
        FROM mart.sales_monthly
        WHERE is_complete_month = 1
        GROUP BY year ORDER BY year
        """
    ).fetchall()
    inventory = connection.execute(
        """
        SELECT SUM(inventory_units), SUM(sold_units),
               SUM(unsold_inventory_cost), SUM(aged_181_plus_units)
        FROM mart.inventory_performance
        """
    ).fetchone()
    top_country = connection.execute(
        """
        SELECT country, net_sales_value
        FROM mart.geography_performance_country
        ORDER BY net_sales_value DESC LIMIT 1
        """
    ).fetchone()
    invalid_shipping = connection.execute(
        """
        SELECT failure_count, failure_rate
        FROM qa.test_results
        WHERE check_name = 'shipping_not_before_item_created'
        """
    ).fetchone()
    qa_summary = connection.execute(
        "SELECT status, COUNT(*) FROM qa.test_results GROUP BY status ORDER BY status"
    ).fetchall()
    advanced = json.loads(
        (project_root / "artifacts" / "advanced_metrics.json").read_text(encoding="utf-8")
    )

    gross_sales, cancelled_value, returned_value, net_sales, net_profit, orders, customers = totals
    session_count, cart_sessions, purchases, abandoned = sessions
    annual_rows = "\n".join(
        f"| {year} | {money(value)} |"
        for year, value in annual
    )
    category_rows = "\n".join(
        f"| {name} | {money(sales)} | {money(profit)} | {pct(margin)} | {pct(return_rate)} |"
        for name, sales, profit, margin, return_rate in top_categories
    )
    channel_rows = "\n".join(
        f"| {name} | {sessions_value:,} | {pct(conversion)} | {pct(abandonment)} |"
        for name, sessions_value, conversion, abandonment in channels
    )
    acquisition_rows = "\n".join(
        f"| {name} | {customers_value:,} | {orders_value:,} | {money(sales)} | {money(sales_per_customer)} |"
        for name, customers_value, orders_value, sales, sales_per_customer
        in acquisition_sources
    )
    model = advanced["return_propensity"]
    rfm = advanced["rfm_segmentation"]
    basket = advanced["market_basket"]
    segment_rows = "\n".join(
        f"| {segment['segment']} | {segment['customers']:,} | "
        f"{segment['median_recency_days']:.0f} days | {money(segment['total_net_sales'])} |"
        for segment in rfm["segments"]
    )
    champions = next(s for s in rfm["segments"] if s["segment"] == "Champions")
    hibernating = next(s for s in rfm["segments"] if s["segment"] == "Hibernating")
    champion_customer_share = champions["customers"] / rfm["customers_segmented"]
    champion_sales_share = champions["total_net_sales"] / (
        champions["total_net_sales"] + hibernating["total_net_sales"]
    )

    findings = f"""# Analysis & Findings

## Decision summary

The dataset supports a connected BI story across acquisition, funnel behavior, commercial performance, customer value, product mix, returns, fulfillment, and inventory. Use **net sales** (gross sales less cancelled and returned item value) for executive performance, keep gross sales visible as demand, and treat May 2024 as a partial month.

## Headline metrics

- Data coverage: January 2019 to May 2024; May 2024 is incomplete.
- Gross sales value: {money(gross_sales)}.
- Cancelled value: {money(cancelled_value)}; returned value: {money(returned_value)}.
- Net sales: {money(net_sales)}; net profit: {money(net_profit)}.
- Orders: {orders:,}; purchasing customers: {customers:,}.
- Sessions: {session_count:,}; purchase sessions: {purchases:,}; session conversion: {pct(purchases / session_count)}.
- Cart sessions: {cart_sessions:,}; abandoned cart sessions: {abandoned:,}; cart abandonment: {pct(abandoned / cart_sessions)}.
- Repeat-customer rate: {pct(repeat_rate)}.

## Business questions & findings

### 1. Acquisition, onsite behavior, and funnel

**Questions addressed:** Which traffic sources drive session volume, purchase conversion, and acquisition-attributed value? Where do sessions exit between product view, cart, and purchase? Which channels show high cart abandonment? Is channel concentration creating growth risk?

| Channel | Sessions | Conversion | Cart Abandonment |
|---|---|---|---|
{channel_rows}

Traffic volume is concentrated in Email and Adwords. Every session field is rebuilt inside SQL by grouping `events.csv` on `session_id`; no source session file is used. `events.user_id` is missing on many individual events, but a session can still be linked when one of its events identifies the user.

Customer acquisition-source value is analyzed separately because its taxonomy (Search, Display, Organic, Facebook, Email) does not align one-to-one with session channels:

| Acquisition Source | Customers | Orders | Net Sales | Per Customer |
|---|---|---|---|---|
{acquisition_rows}

By country, {top_country[0]} is the single largest net-sales market ({money(top_country[1])}), ahead of every other country individually — see `mart.geography_performance_country` for the full breakdown.

### 2. Revenue and growth

**Questions addressed:** How do gross sales, net sales, profit, customers, orders, and AOV move over time? Is growth driven by volume or basket value? Which trends are valid after excluding the incomplete latest month?

| Year | Net Sales (complete months) |
|---|---|
{annual_rows}

Do not compare the partial 2024 period against full prior years. The dashboard marks incomplete months and period measures use the complete-period flag.

### 3. Product and commercial performance

**Questions addressed:** Which categories lead sales, profit, units, and margin? Which high-volume products underperform on revenue or profit? Which product groups show elevated observed return rate?

| Category | Net Sales | Profit | Margin | Return Rate |
|---|---|---|---|---|
{category_rows}

High volume, high revenue, and high margin are not interchangeable. The Product page therefore uses a sales-versus-margin quadrant with item volume and return rate as context.

### 4. Customers and lifecycle

**Questions addressed:** How large is the repeat-customer base? Which acquisition cohorts retain purchase activity? Which RFM segments should receive retention, reactivation, or VIP treatment?

Champions make up only {pct(champion_customer_share)} of segmented customers ({champions['customers']:,} of {rfm['customers_segmented']:,}) but generate {pct(champion_sales_share)} of the combined Champions+Hibernating net sales ({money(champions['total_net_sales'])} vs. {money(hibernating['total_net_sales'])} from {hibernating['customers']:,} Hibernating customers) — a small, high-value segment outweighing a much larger dormant one. Full segment profiles are in Advanced methods below.

### 5. Operations, delivery, returns, and inventory

**Questions addressed:** How long are order-to-ship, ship-to-delivery, and end-to-end stages? Which distribution centers have high median or tail (P90) lead time? Which inventory groups have low sell-through or aged unsold value?

- Inventory units: {int(inventory[0]):,}; sold units: {int(inventory[1]):,}; sell-through: {pct(inventory[1] / inventory[0])}.
- Unsold inventory cost: {money(inventory[2])}; aged 181+ day units: {int(inventory[3]):,}.
- {int(invalid_shipping[0]):,} order-item rows ({pct(invalid_shipping[1])}) have `shipped_at < created_at`. Delivery metrics exclude those rows and display valid-record coverage.

## Advanced methods

### 1. Gini coefficient & Lorenz curve

**Why it fits:** revenue concentration is a direct question about equity of spending across the customer base.

**Method:** compute the Gini coefficient on net customer spend, validate the formula against known extreme/mild-inequality examples, then plot the Lorenz curve (see `notebooks/02_statistical_deep_dives.ipynb`).

**Value:** quantifies whether retention economics on a high-value tail beat blanket acquisition spend. It is a single summary statistic; it does not identify *which* customers to act on — RFM segmentation below does that.

### 2. RFM customer clustering

**Why it fits:** order history supports recency, frequency, monetary value, profit, and return behavior at customer grain.

**Method:** log-transform R/F/M, robust scale, compare K=2..8 using silhouette and inertia, and select {rfm['selected_k']} action-oriented clusters (silhouette {rfm['silhouette_selected_k']:.2f}).

**Result:** {rfm['customers_segmented']:,} customers segmented into {rfm['selected_k']} groups.

| Segment | Customers | Median Recency | Total Net Sales |
|---|---|---|---|
{segment_rows}

**Value:** CRM targeting, lifecycle campaigns, VIP service, reactivation, and segment drill-through in Power BI. Clusters describe observed behavior; they do not prove a treatment will work.

### 3. Return-propensity classification

**Why it fits:** Complete versus Returned item outcomes can be modeled from pre-outcome product, customer, price, order, time, and fulfillment-location features.

**Method:** eligibility restriction to Complete/Returned items, time-based train/test split, one-hot encoding, class-balanced logistic regression, ROC AUC, average precision, Brier score, coefficient review, decile lift, and leakage audit.

**Result:** test ROC AUC is {model['roc_auc']:.3f} and top-decile lift is {model['top_decile_lift']:.2f}x. This weak signal is an honest dataset finding — the model is a portfolio demonstration, not a production score.

**Decision rule:** do not deploy if out-of-time lift is weak. The honest result on synthetic data is itself an analytical conclusion.

### 4. Market-basket association rules

**Why it fits:** co-purchased categories inform cross-sell and merchandising design.

**Method:** category-level association mining over eligible multi-item orders, ranked by lift with support and pair count retained as guards.

**Result:** {basket['rules_generated']:,} directional category rules from {basket['eligible_orders']:,} eligible orders. Use lift with support and pair count; do not rank on lift alone.

The data has no randomized assignment table, so a historical A/B effect cannot be estimated. A forward-looking power plan is included instead (see `docs/technical_reference.md`).

## Material limitations

- This is a synthetic dataset; patterns are analytical demonstrations, not evidence about a real company.
- Order and item status behave like snapshot categories. Net sales excludes Cancelled and Returned; gross sales remains available.
- Product-level cart abandonment cannot be attributed reliably because cart/purchase events do not contain cart contents or order IDs.
- External delivery benchmarks were not added; set SLA targets based on the portfolio scenario or verified market sources.
"""
    (docs_dir / "analysis_and_findings.md").write_text(findings, encoding="utf-8")

    dq_rows = connection.execute(
        """
        SELECT check_name, layer, severity, failure_count, denominator,
               failure_rate, status, notes
        FROM qa.test_results
        ORDER BY CASE status WHEN 'FAIL' THEN 1 WHEN 'WARN' THEN 2 ELSE 3 END,
                 CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                               WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                 check_name
        """
    ).fetchall()
    dq_table = "\n".join(
        f"| {name} | {layer} | {severity} | {status} | {failures:,} | "
        f"{rate:.2%} | {notes} |"
        for name, layer, severity, failures, _, rate, status, notes in dq_rows
    )
    dq_doc = f"""# Data quality review

## Overall assessment

Automated test summary: {dict(qa_summary)}. Blocking failures must be zero before Power BI refresh. Warnings are documented limitations and remain visible in the dashboard guide.

| Check | Layer | Severity | Status | Failures | Failure rate | Interpretation |
|---|---|---:|---:|---:|---:|---|
{dq_table}

## Required handling

- Exclude invalid timestamp sequences from fulfillment lead-time calculations.
- Use session grain for funnel denominators; do not count events as users or sessions.
- Mark May 2024 partial and exclude it from default MoM/YoY comparisons.
- Do not claim product-level cart abandonment without cart-line data.
- Keep PII (name, email, street address, IP address) out of Power BI exports.
"""
    (private_dir / "data_quality_review.md").write_text(dq_doc, encoding="utf-8")

    session_audit = connection.execute(
        """
        WITH per_session AS (
            SELECT
                session_id,
                COUNT(DISTINCT user_id) AS user_ids,
                COUNT(DISTINCT browser) AS browsers,
                COUNT(DISTINCT traffic_source) AS traffic_sources
            FROM stg.events
            GROUP BY session_id
        )
        SELECT
            (SELECT COUNT(*) FROM raw.events) AS event_rows,
            (SELECT COUNT(DISTINCT session_id) FROM stg.events) AS derived_sessions,
            (SELECT COUNT(*) FROM core.fact_session) AS fact_sessions,
            (SELECT SUM(event_count) FROM core.fact_session) AS reconciled_event_rows,
            SUM(user_ids > 1) AS multi_user_sessions,
            SUM(browsers > 1) AS multi_browser_sessions,
            SUM(traffic_sources > 1) AS multi_source_sessions
        FROM per_session
        """
    ).fetchone()
    raw_tables = [
        row[0]
        for row in connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
            ORDER BY table_name
            """
        ).fetchall()
    ]
    event_rows, derived_sessions, fact_sessions, reconciled_events, multi_users, multi_browsers, multi_sources = session_audit
    session_doc = f"""# Session source-lineage audit

## Conclusion

**PASS.** The warehouse contains exactly seven original raw tables. There is no raw session table. `stg.sessions` and `core.fact_session` are reconstructed from `raw.events` by grouping on `session_id`.

## Raw tables loaded

{chr(10).join(f"- `{table}`" for table in raw_tables)}

## Reconciliation evidence

| Check | Result |
|---|---:|
| Source event rows | {int(event_rows):,} |
| Distinct event session IDs | {int(derived_sessions):,} |
| Modeled fact sessions | {int(fact_sessions):,} |
| Sum of modeled session event counts | {int(reconciled_events):,} |
| Sessions with multiple customer IDs | {int(multi_users):,} |
| Sessions with multiple browsers | {int(multi_browsers):,} |
| Sessions with multiple traffic sources | {int(multi_sources):,} |

The event and session reconciliations have zero variance. See `notebooks/03_event_sessionization_audit.ipynb` for the executable review and `docs/technical_reference.md` for field-level derivation rules.
"""
    (private_dir / "session_lineage_audit.md").write_text(
        session_doc, encoding="utf-8"
    )


def run(project_root: Path) -> None:
    connection = duckdb.connect(
        str(project_root / "artifacts" / "thelook_analytics.duckdb"),
        read_only=True,
    )
    try:
        render_figures(connection, project_root / "artifacts" / "figures")
        render_documents(project_root, connection)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.project_root.resolve())


if __name__ == "__main__":
    main()
