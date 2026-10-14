"""Figures for the commercial planning layer.

Kept separate from render_outputs.py so the original reporting figures and the
commercial ones can be regenerated independently.
"""

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
}


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close()


def price_volume_mix_waterfall(connection, figure_dir: Path) -> None:
    bridge = (
        connection.execute(
            """
            SELECT SUM(revenue_prior)   AS prior_revenue,
                   SUM(volume_effect)   AS volume,
                   SUM(mix_effect)      AS mix,
                   SUM(price_effect)    AS price,
                   SUM(revenue_current) AS current_revenue
            FROM mart.price_volume_mix
            WHERE comparison_label LIKE 'YTD%'
            """
        )
        .fetchdf()
        .iloc[0]
    )

    prior = float(bridge["prior_revenue"])
    volume = float(bridge["volume"])
    mix = float(bridge["mix"])
    price = float(bridge["price"])
    current = float(bridge["current_revenue"])

    labels = ["Jan-Apr" + chr(10) + "2023", "Volume", "Mix", "Price",
              "Jan-Apr" + chr(10) + "2024"]
    heights = [prior, volume, mix, price, current]
    bottoms = [0.0, prior, prior + volume, prior + volume + mix, 0.0]
    colors = [
        COLORS["ink"],
        COLORS["blue"] if volume >= 0 else COLORS["pink"],
        COLORS["olive"] if mix >= 0 else COLORS["pink"],
        COLORS["gold"] if price >= 0 else COLORS["pink"],
        COLORS["ink"],
    ]

    # Two panels. Mix and price are real but two orders of magnitude smaller
    # than volume, so on a single axis they vanish into the gridline. The
    # right-hand panel shows them at their own scale rather than letting the
    # chart imply they are zero.
    fig, (ax, ax_zoom) = plt.subplots(
        1, 2, figsize=(13, 5.5), gridspec_kw={"width_ratios": [2.4, 1]}
    )

    ax.bar(labels, heights, bottom=bottoms, color=colors, width=0.6)
    offset = max(abs(h) for h in heights) * 0.02
    for index, (bottom, height) in enumerate(zip(bottoms, heights)):
        text = f"{height:+,.0f}" if 0 < index < 4 else f"{height:,.0f}"
        ax.text(index, bottom + height + offset, text, ha="center", va="bottom",
                fontsize=10, color=COLORS["ink"])
    ax.set_title(
        "Net sales bridge, YTD Jan-Apr 2024 vs 2023"
        + chr(10)
        + "Growth is almost entirely volume",
        loc="left",
    )
    ax.set_ylabel("Net sales (USD)")
    ax.grid(axis="x", visible=False)

    zoom_values = [mix, price]
    zoom_colors = [
        COLORS["pink"] if mix < 0 else COLORS["olive"],
        COLORS["gold"] if price >= 0 else COLORS["pink"],
    ]
    ax_zoom.bar(["Mix", "Price"], zoom_values, color=zoom_colors, width=0.5)
    ax_zoom.axhline(0, color=COLORS["ink"], linewidth=1)
    zoom_offset = max(abs(v) for v in zoom_values) * 0.06
    for index, value in enumerate(zoom_values):
        ax_zoom.text(
            index,
            value + (zoom_offset if value >= 0 else -zoom_offset),
            f"{value:+,.0f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=10,
            color=COLORS["ink"],
        )
    # Headroom so the value labels clear the title and the axis floor.
    span = max(abs(v) for v in zoom_values)
    ax_zoom.set_ylim(min(0, min(zoom_values)) - span * 0.35, max(zoom_values) + span * 0.25)

    share = (abs(mix) + abs(price)) / abs(current - prior)
    ax_zoom.set_title(
        "Mix and price at their own scale"
        + chr(10)
        + f"Together {share:.1%} of the total movement",
        loc="left",
    )
    ax_zoom.grid(axis="x", visible=False)
    save_figure(figure_dir / "price_volume_mix_bridge.png")


def plan_achievement(connection, figure_dir: Path) -> None:
    markets = connection.execute(
        """
        SELECT canonical_country,
               SUM(actual_net_sales_usd) / NULLIF(SUM(plan_net_sales_usd), 0) AS achievement
        FROM mart.plan_vs_actual_monthly
        WHERE is_complete_month = 1 AND in_plan_horizon = 1
          AND plan_net_sales_usd IS NOT NULL AND actual_net_sales_usd IS NOT NULL
        GROUP BY 1 ORDER BY 2
        """
    ).fetchdf()

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bar_colors = [
        COLORS["pink"] if v < 0.95 else COLORS["gold"] if v < 1.0 else COLORS["olive"]
        for v in markets["achievement"]
    ]
    ax.barh(markets["canonical_country"], markets["achievement"], color=bar_colors)
    ax.axvline(1.0, color=COLORS["ink"], linestyle="--", linewidth=1)
    for index, value in enumerate(markets["achievement"]):
        ax.text(value + 0.012, index, f"{value:.0%}", va="center", fontsize=9)
    ax.set_title(
        "Plan achievement by market, complete months inside the plan horizon"
        + chr(10)
        + "Dashed line is target; only Poland and Colombia landed below it",
        loc="left",
    )
    ax.set_xlim(0, float(markets["achievement"].max()) * 1.12)
    ax.set_xlabel("Actual / Plan")
    save_figure(figure_dir / "plan_achievement_by_market.png")


def forecast_vs_plan(connection, figure_dir: Path) -> None:
    outlook = connection.execute(
        """
        SELECT month_start, actual_net_sales_usd, forecast_net_sales_usd,
               plan_net_sales_usd
        FROM mart.forecast_vs_plan ORDER BY month_start
        """
    ).fetchdf()
    outlook["month_start"] = pd.to_datetime(outlook["month_start"])

    # Join the forecast line to the last actual point so the series reads as
    # one continuous outlook rather than two disconnected segments.
    last_actual = outlook.loc[outlook["actual_net_sales_usd"].notna()].index.max()
    if last_actual is not None:
        outlook.loc[last_actual, "forecast_net_sales_usd"] = outlook.loc[
            last_actual, "actual_net_sales_usd"
        ]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(outlook["month_start"], outlook["plan_net_sales_usd"],
            color=COLORS["ink"], linestyle="--", linewidth=1.6, label="Plan")
    ax.plot(outlook["month_start"], outlook["actual_net_sales_usd"],
            color=COLORS["blue"], linewidth=2.2, label="Actual")
    ax.plot(outlook["month_start"], outlook["forecast_net_sales_usd"],
            color=COLORS["orange"], linewidth=2.2, linestyle=":", label="Forecast")
    ax.set_title(
        "Actual, forecast and plan across the planning horizon"
        + chr(10)
        + "The forecast line begins where complete actuals end",
        loc="left",
    )
    ax.set_ylabel("Net sales (USD)")
    ax.legend(frameon=False)
    save_figure(figure_dir / "forecast_vs_plan.png")


def backtest_accuracy(connection, figure_dir: Path) -> None:
    accuracy = connection.execute(
        "SELECT model, mape FROM mart.forecast_accuracy ORDER BY mape DESC"
    ).fetchdf()
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.barh(accuracy["model"], accuracy["mape"], color=COLORS["blue"])
    for index, value in enumerate(accuracy["mape"]):
        ax.text(value + 0.008, index, f"{value:.1%}", va="center", fontsize=10)
    ax.set_xlim(0, float(accuracy["mape"].max()) * 1.25)
    ax.set_title(
        "Backtested MAPE across the full 8-month forecast horizon, 24 rolling origins"
        + chr(10)
        + "Seasonal naive is the benchmark the chosen model had to beat",
        loc="left",
    )
    ax.set_xlabel("Mean absolute percentage error")
    save_figure(figure_dir / "forecast_backtest_mape.png")


def run(project_root: Path) -> None:
    sns.set_theme(style="whitegrid")
    connection = duckdb.connect(
        str(project_root / "artifacts" / "thelook_analytics.duckdb"), read_only=True
    )
    figure_dir = project_root / "artifacts" / "figures"
    try:
        price_volume_mix_waterfall(connection, figure_dir)
        plan_achievement(connection, figure_dir)
        forecast_vs_plan(connection, figure_dir)
        backtest_accuracy(connection, figure_dir)
    finally:
        connection.close()
    print({"figures": 4, "directory": str(figure_dir)})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    run(args.project_root.resolve())


if __name__ == "__main__":
    main()
