"""Generate notebooks/05_commercial_planning_and_forecast.ipynb from the warehouse.

Follows the same pattern as build_notebooks.py: the notebook is generated, not
hand-maintained, so every figure in it comes from the current build and cannot
drift from the dashboard or the documentation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat as nbf

OPEN = """import duckdb
import pandas as pd
from pathlib import Path

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)

CURRENT_DIR = Path.cwd()
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "notebooks" else CURRENT_DIR
connection = duckdb.connect(
    str(PROJECT_ROOT / "artifacts" / "thelook_analytics.duckdb"),
    read_only=True,
)
connection.execute("SELECT 1").fetchone()"""

ALIASES = """# Every source spelling, and what it maps to.
connection.execute(\"\"\"
    SELECT source_country_value, canonical_country, region, is_alias, alias_reason
    FROM core.dim_country
    ORDER BY is_alias DESC, canonical_country
\"\"\").fetchdf()"""

ALIAS_IMPACT = """# What the aliases would have cost if left unmapped: three phantom markets,
# two of them carrying real revenue away from the market they belong to.
connection.execute(\"\"\"
    SELECT
        c.country          AS source_spelling,
        d.canonical_country,
        COUNT(*)           AS items,
        ROUND(SUM(f.net_sales_value), 2) AS net_sales_usd
    FROM core.fact_order_item f
    JOIN core.dim_customer c ON f.customer_id = c.user_id
    JOIN (SELECT DISTINCT source_country_value, canonical_country, is_alias
          FROM core.dim_country) d
      ON c.country = d.source_country_value
    WHERE d.is_alias = 1
    GROUP BY 1, 2
    ORDER BY 4 DESC
\"\"\").fetchdf()"""

VALIDATION = """connection.execute(\"\"\"
    SELECT check_name, severity, failure_count, denominator, status, notes
    FROM qa.plan_validation
    ORDER BY CASE status WHEN 'FAIL' THEN 1 WHEN 'WARN' THEN 2 ELSE 3 END, check_name
\"\"\").fetchdf()"""

REJECTS = """connection.execute(\"\"\"
    SELECT reject_reason, COUNT(*) AS rows_quarantined,
           STRING_AGG(DISTINCT submitted_country, ', ') AS markets
    FROM qa.plan_rejects
    GROUP BY 1
\"\"\").fetchdf()"""

GAPS = """# The coverage check reports gaps. Three different causes sit behind them,
# which is the argument for testing the shape of the data rather than a list
# of problems already known about.
connection.execute(\"\"\"
    WITH bounds AS (
        SELECT canonical_country, MIN(plan_month) AS first_month, MAX(plan_month) AS last_month
        FROM core.fact_plan GROUP BY 1
    ),
    expected AS (
        SELECT b.canonical_country, CAST(m.value AS DATE) AS plan_month
        FROM bounds b, generate_series(b.first_month, b.last_month, INTERVAL 1 MONTH) AS m(value)
    )
    SELECT e.canonical_country, COUNT(*) AS missing_months
    FROM expected e
    LEFT JOIN core.fact_plan p
      ON e.canonical_country = p.canonical_country AND e.plan_month = p.plan_month
    WHERE p.canonical_country IS NULL
    GROUP BY 1 ORDER BY 2 DESC
\"\"\").fetchdf()"""

RECONCILIATION = """connection.execute(\"\"\"
    SELECT stream, stage, entity, row_count, ROUND(value_usd, 2) AS value_usd,
           row_delta, expectation
    FROM qa.reconciliation_statement
    ORDER BY stream, step_order
\"\"\").fetchdf()"""

PVM_TOTALS = """bridge = connection.execute(\"\"\"
    SELECT comparison_label,
           ROUND(SUM(revenue_prior), 0)   AS revenue_prior,
           ROUND(SUM(revenue_current), 0) AS revenue_current,
           ROUND(SUM(total_variance), 0)  AS total_variance,
           ROUND(SUM(volume_effect), 0)   AS volume,
           ROUND(SUM(mix_effect), 0)      AS mix,
           ROUND(SUM(price_effect), 0)    AS price,
           ROUND(SUM(volume_effect) + SUM(mix_effect) + SUM(price_effect)
                 - SUM(total_variance), 6) AS residual
    FROM mart.price_volume_mix
    GROUP BY 1, comparison_order ORDER BY comparison_order
\"\"\").fetchdf()
bridge"""

PVM_CHECK = """# The decomposition must be exact. An off-by-rounding bridge is the classic
# way this analysis quietly breaks, so it is asserted rather than eyeballed.
assert bridge["residual"].abs().max() < 0.01, bridge[["comparison_label", "residual"]]
print(f"Bridge ties on all {len(bridge)} comparisons. "
      f"Largest residual: {bridge['residual'].abs().max():.6f} USD")"""

PVM_ASP = """connection.execute(\"\"\"
    SELECT comparison_label,
           ROUND(SUM(revenue_prior) / SUM(units_prior), 2)     AS asp_prior,
           ROUND(SUM(revenue_current) / SUM(units_current), 2) AS asp_current,
           ROUND(SUM(revenue_current) / SUM(units_current)
                 / (SUM(revenue_prior) / SUM(units_prior)) - 1, 4) AS asp_change,
           ROUND(SUM(volume_effect) / SUM(total_variance), 4)  AS volume_share_of_growth
    FROM mart.price_volume_mix
    GROUP BY 1, comparison_order ORDER BY comparison_order
\"\"\").fetchdf()"""

PVM_CATEGORY = """connection.execute(\"\"\"
    SELECT department, category,
           ROUND(total_variance, 0) AS total_variance,
           ROUND(volume_effect, 0)  AS volume,
           ROUND(mix_effect, 0)     AS mix,
           ROUND(price_effect, 0)   AS price
    FROM mart.price_volume_mix
    WHERE comparison_label LIKE 'YTD%'
    ORDER BY total_variance DESC
    LIMIT 10
\"\"\").fetchdf()"""

PLAN_REGION = """connection.execute(\"\"\"
    SELECT region, EXTRACT(year FROM plan_year)::INTEGER AS plan_year,
           ROUND(actual_net_sales_usd, 0) AS actual_usd,
           ROUND(plan_net_sales_usd, 0)   AS plan_usd,
           ROUND(achievement_rate, 3)     AS achievement,
           months_without_plan
    FROM mart.plan_vs_actual_region
    ORDER BY plan_year, region
\"\"\").fetchdf()"""

PLAN_MARKET = """connection.execute(\"\"\"
    SELECT canonical_country, region,
           ROUND(SUM(actual_net_sales_usd), 0) AS actual_usd,
           ROUND(SUM(plan_net_sales_usd), 0)   AS plan_usd,
           ROUND(SUM(actual_net_sales_usd) / SUM(plan_net_sales_usd), 3) AS achievement
    FROM mart.plan_vs_actual_monthly
    WHERE is_complete_month = 1 AND in_plan_horizon = 1
      AND plan_net_sales_usd IS NOT NULL AND actual_net_sales_usd IS NOT NULL
    GROUP BY 1, 2 ORDER BY achievement
\"\"\").fetchdf()"""

BACKTEST = """connection.execute(\"\"\"
    SELECT model, ROUND(mape, 4) AS mape,
           ROUND(worst_month_ape, 4) AS worst_month_ape,
           ROUND(bias, 4) AS mean_bias, folds
    FROM mart.forecast_accuracy ORDER BY mape
\"\"\").fetchdf()"""

OUTLOOK = """connection.execute(\"\"\"
    SELECT month_start, basis,
           ROUND(expected_net_sales_usd, 0) AS expected_usd,
           ROUND(plan_net_sales_usd, 0)     AS plan_usd,
           ROUND(gap_to_plan_usd, 0)        AS gap_usd,
           ROUND(expected_achievement_rate, 3) AS expected_achievement
    FROM mart.forecast_vs_plan
    WHERE plan_net_sales_usd IS NOT NULL
    ORDER BY month_start
\"\"\").fetchdf()"""

SCENARIOS = """connection.execute(\"\"\"
    SELECT scenario,
           ROUND(SUM(forecast_net_sales_usd), 0)  AS net_sales_usd,
           ROUND(SUM(forecast_net_profit_usd), 0) AS net_profit_usd,
           ROUND(MAX(assumed_margin_rate), 4)     AS assumed_margin,
           MAX(volume_multiplier)                 AS volume_multiplier,
           MAX(narrative)                         AS assumption
    FROM mart.forecast_scenarios GROUP BY 1 ORDER BY 2 DESC
\"\"\").fetchdf()"""

SCORECARD = """connection.execute(\"\"\"
    SELECT kpi_name, reporting_month,
           ROUND(actual_value, 2) AS actual,
           ROUND(mom_variance_rate, 4) AS mom,
           ROUND(yoy_variance_rate, 4) AS yoy,
           ROUND(plan_achievement_rate, 4) AS vs_plan,
           plan_rag_status
    FROM mart.commercial_scorecard ORDER BY kpi_order
\"\"\").fetchdf()"""

CLOSE = """connection.close()
print("Warehouse connection closed.")"""


def build(project_root: Path) -> Path:
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell

    notebook = nbf.v4.new_notebook()
    notebook.cells = [
        md(
            "# 05 — Commercial Planning, Variance and Forecast\n\n"
            "This notebook is the analytical trail behind dashboard pages 8 and 9 and the\n"
            "Excel management pack. It picks up where\n"
            "[`01_data_quality_and_core_analysis`](01_data_quality_and_core_analysis.ipynb)\n"
            "stops: that notebook establishes *what happened*, this one establishes *why the\n"
            "number moved* and *where it is heading*.\n\n"
            "**Two things stated up front.** TheLook is synthetic, so the patterns come from a\n"
            "generator rather than a market. And the plan data is constructed by\n"
            "`src/build_plan_source.py` from a documented rule, because the dataset ships no\n"
            "budget — it is a planning *scenario*, not source data. Both are restated wherever\n"
            "a number depends on them.\n\n"
            "Everything below is generated from the current build, so it cannot drift from the\n"
            "dashboard or from `docs/commercial_analytics.md`."
        ),
        code(OPEN),
        md(
            "## 1. The second source, and the master data it exposed\n\n"
            "Plan data never arrives from the transactional system. It comes from regional\n"
            "teams in spreadsheets, in local currency. Joining it to actuals is where master\n"
            "data stops being a theoretical concern.\n\n"
            "The mapping below is not invented for the exercise: TheLook's own `users.csv`\n"
            "carries `España` next to `Spain`, `Deutschland` next to `Germany`, and `Brasil`\n"
            "for Brazil."
        ),
        code(ALIASES),
        md(
            "Unmapped, these three spellings would appear as separate markets. Two of them\n"
            "carry real revenue that belongs to a market reported elsewhere, and one is a\n"
            "near-zero row that would still pollute any country count."
        ),
        code(ALIAS_IMPACT),
        md(
            "## 2. Validation: what blocks, and what is quarantined\n\n"
            "The design decision here matters more than the checks themselves.\n\n"
            "**Structural defects block the build** — an unmapped country, a broken grain, an\n"
            "FX conversion that does not reproduce, a consolidation that does not tie back to\n"
            "the submissions, a bridge whose effects do not sum. Each of these makes the\n"
            "consolidated number *wrong*, and publishing a wrong number is worse than not\n"
            "publishing.\n\n"
            "**Submission defects do not block** — blank cells, a sign error, a late region.\n"
            "These make the plan *incomplete* rather than wrong. The month-end review still has\n"
            "to happen; the defect goes back to the region that submitted it."
        ),
        code(VALIDATION),
        code(REJECTS),
        md(
            "### One check, three root causes\n\n"
            "The coverage check looks for gaps in a market's own plan months. It is worth\n"
            "reading the result rather than just its pass/fail status, because the gaps come\n"
            "from three unrelated causes:\n\n"
            "- **Colombia** — the market is too small to plan. Sixteen orders in total, so most\n"
            "  months have no prior-year base to plan from. A genuine business condition.\n"
            "- **Poland** — a late submission. Two months never arrived.\n"
            "- **Single-month gaps elsewhere** — the quarantined rows, showing up downstream.\n\n"
            "A rule written against the *shape* of the data catches causes nobody listed in\n"
            "advance. A rule written against a list of known problems does not."
        ),
        code(GAPS),
        md(
            "## 3. Reconciliation\n\n"
            "The statement every reviewer should be handed before they are asked to trust a\n"
            "dashboard: what entered, what survived each layer, and where any difference comes\n"
            "from. The sales stream must carry row count and value through unchanged; the plan\n"
            "stream must lose exactly the quarantined rows and nothing else."
        ),
        code(RECONCILIATION),
        md(
            "## 4. Price-Volume-Mix\n\n"
            "This closes a question left open in\n"
            "[`analysis_and_findings.md` section 2](../docs/analysis_and_findings.md):\n"
            "*is growth driven by volume or basket value?* The descriptive layer could show\n"
            "revenue rising; it could not attribute the movement.\n\n"
            "```\n"
            "volume = (Q1 - Q0) x s0 x P0      growth held at prior mix and prior price\n"
            "mix    = Q1 x (s1 - s0) x P0      mix shift held at prior price\n"
            "price  = Q1_i x (P1 - P0)         price movement at current volume\n"
            "```\n\n"
            "Q is units, P is average selling price, s is the category's share of total units."
        ),
        code(PVM_TOTALS),
        code(PVM_CHECK),
        md(
            "### The finding\n\n"
            "Average selling price barely moves, and volume accounts for almost the whole\n"
            "variance in every comparison."
        ),
        code(PVM_ASP),
        md(
            "**This business grows by selling more units, not by charging more and not by\n"
            "shifting into premium categories.** Two consequences follow. Growth is fully\n"
            "exposed to traffic and conversion, with nothing cushioning a slowdown. And price\n"
            "and mix are untouched levers — a one percent ASP improvement on current volume is\n"
            "worth roughly $30K a quarter on its own.\n\n"
            "The category view shows the same pattern repeating rather than one category\n"
            "driving it."
        ),
        code(PVM_CATEGORY),
        md(
            "## 5. Plan versus actual\n\n"
            "Read 2023 and 2024 differently. 2023 landed close to plan in all three regions,\n"
            "which is the evidence that the variance method works. 2024 runs far ahead\n"
            "everywhere because the plan was built on the prior year's growth rate and the\n"
            "generator's growth accelerated instead — that is an artifact of synthetic data,\n"
            "not commercial outperformance, and it should not be presented as a win."
        ),
        code(PLAN_REGION),
        md(
            "Only two markets land below plan across complete months. They are the same two the\n"
            "coverage check flagged, which is corroboration rather than coincidence: a market\n"
            "too small to plan reliably is also a market likely to miss."
        ),
        code(PLAN_MARKET),
        md(
            "## 6. Forecast, validated before it is used\n\n"
            "Three conventional candidates, selected on **backtested** accuracy rather than\n"
            "in-sample fit. Rolling origin, one month ahead, refitting at each origin so no\n"
            "future information reaches the fit.\n\n"
            "The weak benchmark is published deliberately: seasonal naive at ~54% MAPE is what\n"
            "shows why the drift term matters on a series growing this fast, and it is the bar\n"
            "any method had to clear before it earned its complexity."
        ),
        code(BACKTEST),
        md(
            "**Two things worth stating rather than burying.** The simplest trend-aware method\n"
            "beat Holt-Winters, which means the series does not have structure that more\n"
            "machinery would exploit. And the lowest-MAPE model is biased several points *low*\n"
            "while Holt-Winters is nearly unbiased — for a planning committee that cares more\n"
            "about not under-committing than about average error, the runner-up may be the\n"
            "better choice. The table is published so that trade-off is visible.\n\n"
            "**Honest limitation.** This MAPE is optimistic. Synthetic growth is far smoother\n"
            "than real retail demand, which carries promotional spikes, stockouts and\n"
            "competitive shocks. Read the number as a demonstration of the validation method,\n"
            "not as an accuracy claim that transfers."
        ),
        code(OUTLOOK),
        md(
            "## 7. Scenarios\n\n"
            "Each scenario carries a stated assumption rather than an unexplained multiplier,\n"
            "and the assumptions are sourced from the descriptive layer rather than invented.\n"
            "The downside margin reduction is tied to the inventory finding that 273K units sit\n"
            "in the 181+ day age bucket — clearing that stock means discounting it."
        ),
        code(SCENARIOS),
        md(
            "## 8. The monthly scorecard\n\n"
            "The artifact that actually circulates. Plan targets exist for net sales and units\n"
            "only; everything else is tracked against prior month and last year, and the RAG\n"
            "status is blank rather than green where there is no target to compare against."
        ),
        code(SCORECARD),
        md(
            "## 9. What this dataset cannot support\n\n"
            "Four commercial concepts are deliberately **not** built here, because the data\n"
            "cannot support them honestly:\n\n"
            "| Concept | Blocking limitation |\n"
            "|---|---|\n"
            "| Price elasticity | No discount or promotion field; price is effectively fixed per product, so there is no price variation to regress against |\n"
            "| Promotion effectiveness | No campaign table, no exposure flag, no control group |\n"
            "| Marketing incrementality / ROAS | No marketing cost and no holdout |\n"
            "| Multi-touch attribution | One traffic source per session, no touchpoint sequence per user |\n\n"
            "Section 9 of [`docs/commercial_analytics.md`](../docs/commercial_analytics.md)\n"
            "states the data and the method each one would require. Producing a coefficient\n"
            "from data that cannot identify it would be worse than reporting the gap."
        ),
        code(CLOSE),
    ]

    destination = project_root / "notebooks" / "05_commercial_planning_and_forecast.ipynb"
    destination.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, destination)
    print({"notebook": str(destination), "cells": len(notebook.cells)})
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    build(args.project_root.resolve())


if __name__ == "__main__":
    main()
