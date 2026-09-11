from __future__ import annotations

import argparse
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


def run(project_root: Path) -> None:
    connection = duckdb.connect(
        str(project_root / "artifacts" / "thelook_analytics.duckdb"),
        read_only=True,
    )
    try:
        render_figures(connection, project_root / "artifacts" / "figures")
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.project_root.resolve())


if __name__ == "__main__":
    main()
