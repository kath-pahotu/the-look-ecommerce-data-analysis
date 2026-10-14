"""Monthly net-sales forecast, backtest, scenarios, and forecast-vs-plan.

WHY THESE METHODS
-----------------
A commercial forecast has to be explainable to a planning committee and
reproducible by whoever inherits it, so the candidate set is deliberately
small and conventional:

  seasonal_naive        same month last year. The benchmark any method must
                        beat before it earns its complexity.
  seasonal_naive_drift  same month last year, scaled by the most recent
                        year-on-year movement. Captures trend without fitting.
  holt_winters_log      additive trend and additive seasonality fitted on the
                        log of net sales, which is equivalent to multiplicative
                        trend and seasonality on the original scale but more
                        numerically stable on a strongly growing series.

Selection is by backtested MAPE, not by in-sample fit.

BACKTEST DESIGN
---------------
Rolling origin over the last BACKTEST_ORIGINS origins, scored across EVERY step
of the forecast horizon the model is actually run at - not one month ahead.
Each origin refits on data available up to that point only, so no future
information reaches the fit.

The horizon matters more than it looks. An earlier version of this module
scored every model ONE month ahead over six origins, and then ran the winner
EIGHT months ahead. Audited in Oct 2026 across all 32 usable origins, that
design did not pick the wrong champion - but it had almost no power to tell
the candidates apart, and it hid a large difference:

    step   seasonal_naive_drift   holt_winters_log
      1                    7.1%              11.8%
      8                   11.4%              62.7%

At one month the two look comparable, and over six origins they split the
folds three-three. Across the whole eight-month horizon one is 8.4% and the
other 36.5%. Scoring on a step you never use tells you very little about the
step you do. See docs/forecast_review.md for the full evidence.

BENCHMARK
---------
seasonal_naive is kept as the floor, but on this series it is a weak floor:
net sales roughly double year on year, so "same month last year" under-predicts
in every single fold (bias -47%, equal in magnitude to its MAPE). It proves the
other models beat a naive rule; it does not prove they are good.

HONEST LIMITATION
-----------------
TheLook is synthetic. Its growth curve is far smoother than real retail
demand, which carries promotional spikes, stockouts and competitive shocks.
The MAPE reported here is therefore optimistic and should be read as a
demonstration of the validation method, not as an accuracy claim that would
transfer to a real business. This is stated in the README alongside the
numbers.

COUNTRY ALLOCATION
------------------
The country split is top-down: the global forecast is allocated using each
market's trailing 6-month share of net sales. Bottom-up per-country models
were not used because the smaller markets (Colombia, Poland) have too few
observations to fit seasonality, and a top-down split that is stated plainly
is more honest than thirteen weak models averaged together.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SEASONAL_PERIODS = 12
FORECAST_END = "2024-12-01"

# How many rolling origins to score. Six (the original setting) was too few to
# separate the candidates: at one month ahead they split the folds three-three.
# Every origin still needs 2*SEASONAL_PERIODS+1 months of history to fit
# Holt-Winters, so the count is capped at run time by what the series allows.
BACKTEST_ORIGINS = 24
MIN_TRAIN_MONTHS = 2 * SEASONAL_PERIODS + 1

SCENARIOS = {
    "Base": {
        "volume_multiplier": 1.00,
        "margin_delta_pp": 0.0,
        "narrative": "Current trend continues; no change to pricing or promotion intensity.",
    },
    "Upside": {
        "volume_multiplier": 1.10,
        "margin_delta_pp": 0.5,
        "narrative": "Peak-season sell-through runs 10% ahead with a modest mix benefit.",
    },
    "Downside": {
        "volume_multiplier": 0.90,
        "margin_delta_pp": -2.0,
        "narrative": "Demand softens 10% and clearing aged stock costs 2 points of margin.",
    },
}


# ---------------------------------------------------------------- models


def seasonal_naive(history: pd.Series, horizon: int) -> np.ndarray:
    last_season = history.iloc[-SEASONAL_PERIODS:].to_numpy()
    return np.array([last_season[i % SEASONAL_PERIODS] for i in range(horizon)])


def seasonal_naive_drift(history: pd.Series, horizon: int) -> np.ndarray:
    base = seasonal_naive(history, horizon)
    if len(history) <= SEASONAL_PERIODS:
        return base
    recent = float(history.iloc[-1])
    year_ago = float(history.iloc[-1 - SEASONAL_PERIODS])
    drift = recent / year_ago if year_ago > 0 else 1.0
    drift = float(np.clip(drift, 0.5, 2.5))
    return base * drift


def holt_winters_log(history: pd.Series, horizon: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    if len(history) < 2 * SEASONAL_PERIODS + 1:
        return seasonal_naive_drift(history, horizon)
    logged = np.log(history.clip(lower=1.0))
    model = ExponentialSmoothing(
        logged,
        trend="add",
        seasonal="add",
        seasonal_periods=SEASONAL_PERIODS,
        initialization_method="estimated",
    ).fit(optimized=True)
    return np.exp(model.forecast(horizon).to_numpy())


MODELS = {
    "seasonal_naive": seasonal_naive,
    "seasonal_naive_drift": seasonal_naive_drift,
    "holt_winters_log": holt_winters_log,
}


# ---------------------------------------------------------------- backtest


def backtest(series: pd.Series, horizon: int = 1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rolling-origin backtest scored across the whole forecast horizon.

    Returns (scores, detail). `scores` is one row per model; `detail` is one row
    per model x origin x step, written to mart.forecast_backtest_detail so the
    horizon decay is inspectable rather than taken on trust.

    For each origin the model is refitted on history up to that origin and asked
    for `horizon` months. Every step is scored, so a model that is sharp next
    month but drifts by month eight is penalised for the drift - which is the
    behaviour that matters when the forecast is used to call the full-year
    landing.
    """
    # offset counts back from the end. It must be >= horizon so every step of
    # the forecast has an actual to compare against, and small enough to leave
    # MIN_TRAIN_MONTHS of history for the fit.
    largest_offset = min(BACKTEST_ORIGINS + horizon - 1, len(series) - MIN_TRAIN_MONTHS)
    offsets = list(range(largest_offset, horizon - 1, -1))
    if not offsets:
        raise ValueError(
            f"series of {len(series)} months cannot support a {horizon}-month "
            f"backtest with {MIN_TRAIN_MONTHS} months of training history"
        )

    detail_rows: list[dict[str, object]] = []
    for name, fn in MODELS.items():
        for offset in offsets:
            history = series.iloc[:-offset]
            predicted = fn(history, horizon)
            for step in range(horizon):
                actual = float(series.iloc[-offset + step])
                point = float(predicted[step])
                detail_rows.append(
                    {
                        "model": name,
                        "origin_month": series.index[-offset].date().isoformat(),
                        "target_month": series.index[-offset + step].date().isoformat(),
                        "step": step + 1,
                        "actual": actual,
                        "predicted": point,
                        "absolute_percentage_error": abs(point - actual) / actual,
                    }
                )
    detail = pd.DataFrame(detail_rows)

    rows = []
    for name, frame in detail.groupby("model", sort=False):
        first = frame[frame["step"] == 1]["absolute_percentage_error"]
        last = frame[frame["step"] == horizon]["absolute_percentage_error"]
        rows.append(
            {
                "model": name,
                "mape": float(frame["absolute_percentage_error"].mean()),
                "mape_first_step": float(first.mean()),
                "mape_final_step": float(last.mean()) if len(last) else float("nan"),
                "worst_month_ape": float(frame["absolute_percentage_error"].max()),
                "bias": float((frame["predicted"] / frame["actual"] - 1).mean()),
                "horizon": horizon,
                "origins": int(frame["origin_month"].nunique()),
                "folds": int(len(frame)),
            }
        )
    scores = pd.DataFrame(rows).sort_values("mape").reset_index(drop=True)
    return scores, detail


# ---------------------------------------------------------------- build


def run(project_root: Path) -> dict[str, object]:
    database_path = project_root / "artifacts" / "thelook_analytics.duckdb"
    connection = duckdb.connect(str(database_path))

    monthly = connection.execute(
        """
        SELECT month_start, net_sales_value, net_margin_rate
        FROM mart.sales_monthly
        WHERE is_complete_month = 1
        ORDER BY month_start
        """
    ).fetchdf()
    monthly["month_start"] = pd.to_datetime(monthly["month_start"])
    series = monthly.set_index("month_start")["net_sales_value"].astype(float)
    series.index.freq = "MS"  # silences statsmodels frequency inference warnings
    current_margin = float(monthly["net_margin_rate"].iloc[-1])

    last_actual_month = series.index[-1]
    horizon_index = pd.date_range(
        last_actual_month + pd.DateOffset(months=1), FORECAST_END, freq="MS"
    )
    horizon = len(horizon_index)

    # Score every model at the horizon it will actually be run at, not at one
    # month ahead. The two answers differ on this series - see the module
    # docstring and docs/forecast_review.md.
    scores, backtest_detail = backtest(series, horizon)
    champion = str(scores.iloc[0]["model"])
    point_forecast = MODELS[champion](series, horizon)

    forecast = pd.DataFrame(
        {
            "month_start": horizon_index,
            "forecast_net_sales_usd": point_forecast,
            "model": champion,
        }
    )

    # Scenario layer
    scenario_rows = []
    for name, config in SCENARIOS.items():
        values = point_forecast * config["volume_multiplier"]
        margin = current_margin + config["margin_delta_pp"] / 100.0
        for month, value in zip(horizon_index, values):
            scenario_rows.append(
                {
                    "scenario": name,
                    "month_start": month,
                    "forecast_net_sales_usd": float(value),
                    "assumed_margin_rate": margin,
                    "forecast_net_profit_usd": float(value) * margin,
                    "volume_multiplier": config["volume_multiplier"],
                    "margin_delta_pp": config["margin_delta_pp"],
                    "narrative": config["narrative"],
                }
            )
    scenarios = pd.DataFrame(scenario_rows)

    # Top-down country allocation on the trailing 6-month share.
    shares = connection.execute(
        """
        SELECT canonical_country,
               SUM(net_sales_value) AS trailing_net_sales
        FROM mart.actual_country_month
        WHERE is_complete_month = 1
          AND month_start > (SELECT MAX(month_start) FROM mart.actual_country_month
                             WHERE is_complete_month = 1) - INTERVAL 6 MONTH
        GROUP BY 1
        """
    ).fetchdf()
    shares["allocation_share"] = (
        shares["trailing_net_sales"] / shares["trailing_net_sales"].sum()
    )

    allocation = forecast.merge(shares, how="cross")
    allocation["forecast_net_sales_usd"] = (
        allocation["forecast_net_sales_usd"] * allocation["allocation_share"]
    )
    allocation = allocation[
        ["month_start", "canonical_country", "allocation_share", "forecast_net_sales_usd"]
    ]

    connection.register("forecast_df", forecast)
    connection.register("scenarios_df", scenarios)
    connection.register("scores_df", scores)
    connection.register("allocation_df", allocation)
    connection.register("backtest_detail_df", backtest_detail)

    connection.execute(
        "CREATE OR REPLACE TABLE mart.forecast_backtest_detail AS "
        "SELECT * FROM backtest_detail_df"
    )
    connection.execute(
        "CREATE OR REPLACE TABLE mart.forecast_monthly AS SELECT * FROM forecast_df"
    )
    connection.execute(
        "CREATE OR REPLACE TABLE mart.forecast_scenarios AS SELECT * FROM scenarios_df"
    )
    connection.execute(
        "CREATE OR REPLACE TABLE mart.forecast_accuracy AS SELECT * FROM scores_df"
    )
    connection.execute(
        "CREATE OR REPLACE TABLE mart.forecast_country_month AS SELECT * FROM allocation_df"
    )

    # Forecast vs plan over the remaining plan horizon - the question a
    # planning committee actually asks: are we going to land the number?
    connection.execute(
        """
        CREATE OR REPLACE TABLE mart.forecast_vs_plan AS
        WITH plan_months AS (
            SELECT plan_month, SUM(plan_net_sales_usd) AS plan_net_sales_usd
            FROM core.fact_plan
            GROUP BY 1
        ),
        actual_months AS (
            SELECT month_start, SUM(net_sales_value) AS actual_net_sales_usd
            FROM mart.actual_country_month
            WHERE is_complete_month = 1
            GROUP BY 1
        )
        SELECT
            COALESCE(p.plan_month, f.month_start, a.month_start) AS month_start,
            a.actual_net_sales_usd,
            f.forecast_net_sales_usd,
            COALESCE(a.actual_net_sales_usd, f.forecast_net_sales_usd) AS expected_net_sales_usd,
            p.plan_net_sales_usd,
            CASE WHEN a.actual_net_sales_usd IS NOT NULL THEN 'Actual' ELSE 'Forecast' END AS basis,
            COALESCE(a.actual_net_sales_usd, f.forecast_net_sales_usd) - p.plan_net_sales_usd
                AS gap_to_plan_usd,
            CASE WHEN p.plan_net_sales_usd > 0
                 THEN COALESCE(a.actual_net_sales_usd, f.forecast_net_sales_usd)
                      / p.plan_net_sales_usd END AS expected_achievement_rate
        FROM plan_months p
        FULL OUTER JOIN mart.forecast_monthly f ON p.plan_month = f.month_start
        FULL OUTER JOIN actual_months a ON p.plan_month = a.month_start
        WHERE COALESCE(p.plan_month, f.month_start, a.month_start)
              >= (SELECT MIN(plan_month) FROM core.fact_plan)
        ORDER BY 1
        """
    )

    # Exports
    analysis_dir = project_root / "data" / "processed" / "analysis"
    power_bi_dir = project_root / "data" / "processed" / "power_bi" / "csv"
    for directory in (analysis_dir, power_bi_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for table in (
        "forecast_monthly",
        "forecast_scenarios",
        "forecast_accuracy",
        "forecast_backtest_detail",
        "forecast_country_month",
        "forecast_vs_plan",
    ):
        frame = connection.execute(f"SELECT * FROM mart.{table}").fetchdf()
        frame.to_csv(analysis_dir / f"{table}.csv", index=False, encoding="utf-8")
        frame.to_csv(power_bi_dir / f"{table}.csv", index=False, encoding="utf-8")

    plan_gap = connection.execute(
        """
        SELECT
            SUM(expected_net_sales_usd) AS expected_full_period,
            SUM(plan_net_sales_usd) AS plan_full_period,
            SUM(expected_net_sales_usd) / NULLIF(SUM(plan_net_sales_usd), 0) AS achievement
        FROM mart.forecast_vs_plan
        WHERE plan_net_sales_usd IS NOT NULL
        """
    ).fetchdf().iloc[0]
    connection.close()

    summary = {
        "champion_model": champion,
        "backtest_origins": int(scores["origins"].iloc[0]),
        "backtest_horizon": horizon,
        "backtest_note": (
            f"Models are scored across all {horizon} steps of the forecast "
            "horizon, not one month ahead. At one month the candidates look "
            "comparable; across the horizon they are not. See "
            "docs/forecast_review.md."
        ),
        "model_scores": scores.to_dict(orient="records"),
        "last_actual_month": last_actual_month.date().isoformat(),
        "forecast_months": horizon,
        "expected_vs_plan_achievement": float(plan_gap["achievement"]),
        "scenarios": list(SCENARIOS),
    }
    output = project_root / "artifacts" / "forecast_summary.json"
    output.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    run(args.project_root.resolve())


if __name__ == "__main__":
    main()
