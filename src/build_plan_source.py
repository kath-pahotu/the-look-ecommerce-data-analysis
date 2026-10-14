"""Generate the regional commercial plan submissions that the pipeline consumes.

WHAT THIS IS
------------
TheLook eCommerce ships no budget or planning data. To demonstrate the
plan-consolidation and plan-validation workflow that commercial analytics
depends on, this script CONSTRUCTS a planning file from a transparent,
deterministic rule and writes it to data/planning/.

The file is a constructed planning scenario, not source data. Every number in
it is reproducible from the rule below. This is stated in the README and in
docs/commercial_analytics.md.

CONSTRUCTION RULE
-----------------
    plan_net_sales_usd(country, month) =
        actual_net_sales(country, same month one year earlier)
        * trailing_growth(country, planning cycle)
        * ambition(country)
        * seasonal_ambition(month)
    rounded to the nearest 100 USD

    trailing_growth   the country's own calendar-year growth rate observed at
                      the time the plan was written. The FY2023 plan is drawn
                      up in late 2022 and can only see CY2022/CY2021; the
                      FY2024 plan sees CY2023/CY2022. Planning off a trailing
                      rate, not off hindsight, is what makes the resulting
                      variance realistic rather than trivially positive.
    ambition(country) fixed per country, drawn once from U(0.90, 1.12) with
                      seed 20240601 so the file is reproducible. This is the
                      stretch or caution each market negotiates on top of
                      trend, and it is what makes some markets land above
                      plan and others below.
    seasonal_ambition 1.00 for all months except Nov/Dec (1.05), which
                      mirrors how planners load peak-season ambition

A first version of this file applied a flat +15% growth assumption. Against a
dataset growing 70-185% a year that produced 140-210% plan achievement in
every market, which made the variance analysis meaningless - nothing was ever
below plan. The trailing-growth rule above replaced it.

Plan horizon: 2023-01 .. 2024-12.
    2023-01 .. 2024-05  overlap actuals  -> variance analysis
    2024-06 .. 2024-12  beyond actuals   -> forecast-vs-plan validation

SUBMISSION DEFECTS DELIBERATELY PRESENT
---------------------------------------
Regional submissions in real planning cycles arrive imperfect. The following
are present in the output so the validation layer has something real to catch,
and each is listed in docs/commercial_analytics.md:

1. Local-language country names (Espana, Deutschland, Brasil). These mirror
   spellings that genuinely exist in TheLook's own users.csv - they were not
   invented here.
2. Poland submits two months late: 2024-04 and 2024-05 rows are absent.
3. Four plan cells are blank, standing in for unfilled spreadsheet cells.
4. Colombia's country name carries trailing whitespace.
5. One Belgium row carries a negative target, standing in for a sign error.

Plans are submitted in local currency and converted with a fixed budget FX
rate set at the open of the planning cycle, which is standard practice.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

SEED = 20240601
PLAN_START = "2023-01-01"
PLAN_END = "2024-12-01"

# Submission spellings used by each regional system, keyed by canonical country.
SUBMISSION_SPELLING = {
    "Brazil": "Brasil",
    "Spain": "España",
    "Germany": "Deutschland",
    "Colombia": "Colombia ",
}


def load_actuals(
    connection: duckdb.DuckDBPyConnection, country_master: pd.DataFrame
) -> pd.DataFrame:
    """Actual net sales by canonical country and month.

    The country master is passed in from the seed file rather than read from
    the warehouse, so this script can run against a warehouse built before the
    commercial layer existed. The plan file it produces is a committed source
    artifact, regenerated only on request - not on every pipeline run.
    """
    connection.register("country_master_seed", country_master)
    return connection.execute(
        """
        SELECT
            m.canonical_country,
            date_trunc('month', f.order_item_created_at)::DATE AS month_start,
            SUM(f.net_sales_value) AS actual_net_sales_usd,
            SUM(CASE WHEN f.item_status NOT IN ('Cancelled', 'Returned')
                     THEN 1 ELSE 0 END) AS actual_units
        FROM core.fact_order_item f
        JOIN core.dim_customer c ON f.customer_id = c.user_id
        JOIN country_master_seed m ON c.country = m.source_country_value
        WHERE m.canonical_country <> 'Unknown'
        GROUP BY 1, 2
        """
    ).fetchdf()


def build_plan(
    actuals: pd.DataFrame, currency: pd.DataFrame, fx: pd.DataFrame
) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    countries = sorted(actuals["canonical_country"].unique())
    ambition = {c: float(rng.uniform(0.90, 1.12)) for c in countries}

    actuals = actuals.copy()
    actuals["month_start"] = pd.to_datetime(actuals["month_start"])
    actuals["calendar_year"] = actuals["month_start"].dt.year
    lookup = actuals.set_index(["canonical_country", "month_start"])

    # Trailing growth each planning cycle could actually observe.
    yearly = actuals.groupby(["canonical_country", "calendar_year"])[
        "actual_net_sales_usd"
    ].sum()

    def trailing_growth(country: str, plan_year: int) -> float:
        """CY(n-1)/CY(n-2) growth, the last full year visible when planning."""
        numerator_year, denominator_year = plan_year - 1, plan_year - 2
        try:
            numerator = float(yearly.loc[(country, numerator_year)])
            denominator = float(yearly.loc[(country, denominator_year)])
        except KeyError:
            return 1.15
        if denominator <= 0:
            return 1.15
        # Clamp: no planner signs off on a target outside this band.
        return float(np.clip(numerator / denominator, 1.0, 2.2))

    months = pd.date_range(PLAN_START, PLAN_END, freq="MS")
    rows = []
    for country in countries:
        for month in months:
            prior = month - pd.DateOffset(years=1)
            try:
                base = lookup.loc[(country, prior)]
            except KeyError:
                continue
            growth = trailing_growth(country, month.year)
            seasonal = 1.05 if month.month in (11, 12) else 1.00
            factor = growth * ambition[country] * seasonal
            usd = float(base["actual_net_sales_usd"]) * factor
            units = float(base["actual_units"]) * factor
            if usd <= 0:
                continue
            rows.append(
                {
                    "canonical_country": country,
                    "plan_month": month.strftime("%Y-%m-%d"),
                    "plan_net_sales_usd": round(usd / 100.0) * 100.0,
                    "plan_units": int(round(units)),
                }
            )

    plan = pd.DataFrame(rows)
    plan = plan.merge(currency, on="canonical_country", how="left")
    plan = plan.merge(
        fx[["currency_code", "budget_rate_to_usd"]], on="currency_code", how="left"
    )
    plan["plan_net_sales_local"] = (
        plan["plan_net_sales_usd"] / plan["budget_rate_to_usd"]
    ).round(2)
    plan["submitted_country"] = plan["canonical_country"].map(
        lambda c: SUBMISSION_SPELLING.get(c, c)
    )
    plan["submission_batch"] = np.where(
        plan["plan_month"] < "2024-01-01", "FY2023-PLAN-V1", "FY2024-PLAN-V1"
    )
    return plan


def apply_submission_defects(plan: pd.DataFrame) -> pd.DataFrame:
    plan = plan.copy()

    # 2. Poland submitted late: its final two overlap months never arrived.
    late = (plan["canonical_country"] == "Poland") & (
        plan["plan_month"].isin(["2024-04-01", "2024-05-01"])
    )
    plan = plan.loc[~late].copy()

    # 3. Four unfilled spreadsheet cells.
    blanks = [
        ("France", "2023-08-01"),
        ("Japan", "2023-11-01"),
        ("Australia", "2024-02-01"),
        ("United Kingdom", "2024-09-01"),
    ]
    for country, month in blanks:
        mask = (plan["canonical_country"] == country) & (plan["plan_month"] == month)
        plan.loc[mask, "plan_net_sales_local"] = np.nan

    # 5. Sign error on one Belgium row.
    sign = (plan["canonical_country"] == "Belgium") & (
        plan["plan_month"] == "2023-05-01"
    )
    plan.loc[sign, "plan_net_sales_local"] = -plan.loc[sign, "plan_net_sales_local"]

    return plan


def run(project_root: Path) -> dict[str, object]:
    country_master = pd.read_csv(
        project_root / "seeds" / "country_master.csv", encoding="utf-8"
    )
    database_path = project_root / "artifacts" / "thelook_analytics.duckdb"
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        actuals = load_actuals(connection, country_master)
    finally:
        connection.close()

    currency = pd.read_csv(
        project_root / "seeds" / "country_currency.csv", encoding="utf-8"
    )
    fx = pd.read_csv(project_root / "seeds" / "fx_budget_rates.csv", encoding="utf-8")

    plan = apply_submission_defects(build_plan(actuals, currency, fx))

    output = plan[
        [
            "submission_batch",
            "submitted_country",
            "plan_month",
            "currency_code",
            "plan_net_sales_local",
            "plan_units",
        ]
    ].sort_values(["submission_batch", "submitted_country", "plan_month"])

    destination = project_root / "data" / "planning" / "regional_plan_submissions.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(
        destination, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL
    )

    summary = {
        "rows": int(len(output)),
        "countries": int(output["submitted_country"].nunique()),
        "months": int(output["plan_month"].nunique()),
        "blank_targets": int(output["plan_net_sales_local"].isna().sum()),
        "negative_targets": int((output["plan_net_sales_local"] < 0).sum()),
        "path": str(destination),
    }
    print(summary)
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
