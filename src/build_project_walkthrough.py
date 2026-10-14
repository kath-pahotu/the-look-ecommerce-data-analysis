"""Generate notebooks/00_project_walkthrough.ipynb.

WHAT THE NOTEBOOK IS
--------------------
A single readable pass over the whole project, written for someone who has not
seen it before. It does NOT build anything - `src/pipeline.py` does that. The
notebook opens the production warehouse read-only, shows what each layer does,
names the production file that owns it, states where the output is written, and
closes each section with the conclusion that section supports.

Run:
    python src/build_project_walkthrough.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "notebooks" / "00_project_walkthrough.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def figure(filename: str, caption: str) -> dict:
    return md(f"![{caption}](../artifacts/figures/{filename})\n\n*{caption}*\n")


def conclusion(text: str) -> dict:
    return md(f"> **Conclusion.** {text}\n")


def section(number: str, title: str, what: str, built_by: str, written_to: str) -> dict:
    return md(
        f"---\n\n## {number} - {title}\n\n"
        f"{what}\n\n"
        f"| | |\n|---|---|\n"
        f"| **Built by** | {built_by} |\n"
        f"| **Written to** | {written_to} |\n"
    )


HELPERS = r'''
SQL_DIR = ROOT / "sql" / "duckdb"


def show_sql(obj, lines=None):
    """Print the production SQL that builds `obj`.

    The text is read from the file the pipeline actually executes, so what
    is shown here and what runs cannot drift apart.
    """
    for path in sorted(SQL_DIR.glob("*.sql")):
        body = path.read_text(encoding="utf-8")
        for kind in ("TABLE", "VIEW"):
            marker = f"CREATE OR REPLACE {kind} {obj} AS"
            if marker not in body:
                continue
            statement = []
            for row in body[body.index(marker):].splitlines():
                statement.append(row)
                if row.rstrip().endswith(";"):
                    break
            shown = statement if lines is None else statement[:lines]
            print(f"--- sql/duckdb/{path.name} - {len(statement)} lines " + "-" * 22)
            print("\n".join(shown))
            if lines is not None and len(statement) > lines:
                print(f"... {len(statement) - lines} more lines, in the file")
            return
    print(f"{obj} is not built by a SQL module.")


def show_py(filename, func, lines=None):
    """Print one function from a production file in src/."""
    rows = (ROOT / "src" / filename).read_text(encoding="utf-8").splitlines()
    start = next(i for i, r in enumerate(rows) if r.startswith(f"def {func}("))
    end = start + 1
    while end < len(rows) and not rows[end].startswith(("def ", "class ", "@")):
        end += 1
    block = rows[start:end]
    while block and not block[-1].strip():
        block.pop()
    shown = block if lines is None else block[:lines]
    print(f"--- src/{filename} - def {func} - {len(block)} lines " + "-" * 16)
    print("\n".join(shown))
    if lines is not None and len(block) > lines:
        print(f"... {len(block) - lines} more lines, in the file")
'''


cells: list[dict] = []

# ============================================================ OPENING
cells += [
    md(
        "# TheLook eCommerce - Project Walkthrough\n"
        "\n"
        "**Commercial analytics on a 180,000-line retail dataset: a governed warehouse,\n"
        "a plan-versus-actual layer fed by a second source system, and the controls that\n"
        "stop a wrong number reaching a report.**\n"
        "\n"
        "---\n"
        "\n"
        "### How to read this\n"
        "\n"
        "This notebook **does not build anything**. The pipeline builds; this reads. It\n"
        "opens the finished warehouse read-only and walks it in the order it was\n"
        "constructed, so the whole project can be followed in one pass instead of across\n"
        "twenty files.\n"
        "\n"
        "Every section has the same shape:\n"
        "\n"
        "| | |\n"
        "|---|---|\n"
        "| **What it does** | the purpose of the layer, in a few sentences |\n"
        "| **Built by** | the production file that owns it |\n"
        "| **Written to** | where the output lands on disk |\n"
        "| **Result** | a live query against the warehouse |\n"
        "| **Conclusion** | what that result supports |\n"
        "\n"
        "### Seeing the code, not a description of it\n"
        "\n"
        "Where a section is about engineering rather than a result, the notebook prints the\n"
        "**production code itself**. `show_sql(\"mart.plan_vs_actual_monthly\")` reads that\n"
        "statement out of `sql/duckdb/` while the cell runs; `show_py(...)` does the same for a\n"
        "function in `src/`. Nothing is copied into this notebook, so what you read here and\n"
        "what the pipeline executes cannot drift apart. Long statements are cut off with a line\n"
        "count and the file name so the rest is one click away.\n"
        "\n"
        "### Running it yourself\n"
        "\n"
        "One command rebuilds everything from the seven source CSVs - warehouse, exports,\n"
        "figures, Excel pack, notebooks and the validation gate:\n"
        "\n"
        "```bash\n"
        "python src/run_all.py --source-csv-dir <folder with the 7 CSVs> --rebuild\n"
        "```\n"
        "\n"
        "What that runs, in what order, how to run a single stage while developing, and why\n"
        "the work is split across many files instead of one, is set out in\n"
        "[`docs/how_to_run.md`](../docs/how_to_run.md).\n"
        "\n"
        "### Where the exploring happens\n"
        "\n"
        "This notebook is the finished account. The working surface is\n"
        "[`notebooks/90_workbench.ipynb`](90_workbench.ipynb), backed by `src/explore.py` -\n"
        "a read-only handle on the warehouse with the verbs you need before writing anything:\n"
        "`cols()` for types and null counts, `grain()` for whether a key is unique, `overlap()`\n"
        "for whether two keys actually match, and `tie()` for whether a total survived a layer.\n"
        "\n"
        "### If you want to read the code\n"
        "\n"
        "[`docs/code_map.md`](../docs/code_map.md) indexes **every object in the warehouse to\n"
        "the file and line that builds it**, with the statement length beside it, so it is clear\n"
        "which objects carry real logic and which are a projection. It is generated from the\n"
        "files on every build, so it cannot go stale. The full source of any object can also be\n"
        "printed on demand with `w.source(\"mart.price_volume_mix\")` from the workbench.\n"
    ),
    md(
        "### The project in one page\n"
        "\n"
        "```\n"
        "  7 source CSVs          2 reference seeds        1 plan submission file\n"
        "  (TheLook export)       (country, FX)            (regional, local currency)\n"
        "         |                      |                          |\n"
        "         +----------------------+--------------------------+\n"
        "                                |\n"
        "                      [ raw ]   ingested exactly as delivered\n"
        "                                |\n"
        "                   SOURCE QUALITY GATE   runs before any model exists\n"
        "                                |\n"
        "                      [ stg ]   typed, renamed, harmonised\n"
        "                                |\n"
        "                      [ core ]  conformed dimensions and facts\n"
        "                                |\n"
        "                      [ mart ]  one table per business question\n"
        "                                |\n"
        "                  WAREHOUSE AND COMMERCIAL GATES\n"
        "                                |\n"
        "         +----------------------+--------------------------+\n"
        "         |                      |                          |\n"
        "   Power BI, 8 pages      CSV / Parquet exports      Excel management pack\n"
        "```\n"
        "\n"
        "| Folder | Holds |\n"
        "|---|---|\n"
        "| `src/` | the pipeline, the orchestrator, the Python analytics |\n"
        "| `sql/duckdb/` | ten numbered SQL files, run in sequence |\n"
        "| `seeds/` | small reference tables that are committed, not derived |\n"
        "| `data/planning/` | the regional plan submission file - a second source |\n"
        "| `artifacts/` | the warehouse, the figures, the run metadata |\n"
        "| `outputs/` | QA evidence and the modelled exports |\n"
        "| `docs/` | the written analysis and reference documents |\n"
        "| `power_bi/` | the report and its DAX measures |\n"
    ),
]

# ============================================================ PART 1
cells += [
    md("---\n\n## Part 1 - Open the warehouse\n"),
    code(
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "import duckdb\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "\n"
        'pd.set_option("display.width", 220)\n'
        'pd.set_option("display.max_columns", 50)\n'
        'pd.set_option("display.max_colwidth", 70)\n'
        '# Previews show at least 10 rows - 3 is not enough to see a pattern,\n'
        '# a null cluster, or a grain that is finer than you assumed.\n'
        'pd.set_option("display.max_rows", 40)\n'
        'pd.set_option("display.min_rows", 20)\n'
        "\n"
        "# Read-only on purpose. The pipeline owns the warehouse; nothing here writes to it.\n"
        "CURRENT = Path.cwd()\n"
        'ROOT = CURRENT.parent if CURRENT.name == "notebooks" else CURRENT\n'
        'DB = ROOT / "artifacts" / "thelook_analytics.duckdb"\n'
        "db = duckdb.connect(str(DB), read_only=True)\n"
        "\n"
        "\n"
        "def q(sql: str) -> pd.DataFrame:\n"
        '    """Run SQL against the production warehouse and return a DataFrame."""\n'
        "    return db.execute(sql).fetchdf()\n"
        "\n"
        + HELPERS
        + "\n"
        'print(f"Warehouse : {DB.name}")\n'
        'print(f"Size      : {DB.stat().st_size / 1_048_576:.0f} MB")'
    ),
    code(
        "# What the pipeline produced, by layer.\n"
        'display(q("""\n'
        "    SELECT table_schema AS layer, COUNT(*) AS objects\n"
        "    FROM information_schema.tables\n"
        "    WHERE table_schema IN ('raw','stg','core','mart','qa')\n"
        "    GROUP BY 1\n"
        "    ORDER BY CASE table_schema WHEN 'raw' THEN 1 WHEN 'stg' THEN 2\n"
        "                               WHEN 'core' THEN 3 WHEN 'mart' THEN 4 ELSE 5 END\n"
        '"""))'
    ),
]

# ============================================================ PART 2
cells += [
    section(
        "Part 2", "The sources",
        "**What it does.** Three independent inputs feed this project. The seven TheLook\n"
        "CSVs are the transactional source. Two committed seed files carry reference data\n"
        "the source does not contain. A regional plan submission file is a genuine second\n"
        "source system, arriving in local currency with the defects a real planning cycle\n"
        "produces.",
        "`src/pipeline.py` (ingestion), `src/build_plan_source.py` (plan file)",
        "the `raw` schema in `artifacts/thelook_analytics.duckdb`",
    ),
    code(
        'display(q("""\n'
        "    SELECT table_name, estimated_size AS rows\n"
        "    FROM duckdb_tables() WHERE schema_name = 'raw'\n"
        "    ORDER BY rows DESC\n"
        '"""))'
    ),
    md(
        "### Why the seeds are committed rather than derived\n"
        "\n"
        "`seeds/country_master.csv` maps every country spelling the source emits onto a\n"
        "canonical market. `seeds/fx_budget_rates.csv` holds the budget FX rate fixed at\n"
        "the planning-cycle open. Neither can be inferred from transactional data - they\n"
        "are decisions, so they are version-controlled alongside the code.\n"
    ),
    code(
        'print("The alias rows are the ones that matter:")\n'
        'display(q("""\n'
        "    SELECT source_country_value, canonical_country, region, is_alias, alias_reason\n"
        "    FROM raw.country_master\n"
        "    WHERE is_alias = 1 OR canonical_country IN ('Brazil','Spain','Germany')\n"
        "    ORDER BY canonical_country, is_alias DESC\n"
        '"""))'
    ),
    conclusion(
        "TheLook's own `users.csv` carries **15 country spellings for 13 markets** - "
        "`Brasil` and `Brazil`, `Espana` and `Spain`, `Deutschland` and `Germany`. "
        "This is a master-data defect present in the source, not one introduced here, "
        "and it is the reason a country dimension exists at all."
    ),
]

# ============================================================ PART 3
cells += [
    section(
        "Part 3", "The source quality gate",
        "**What it does.** Nine checks that need nothing but the `raw` schema, run before a\n"
        "single model is built. If a source is broken there is no reason to compute\n"
        "twenty-six marts on it. A failure here stops the build before any downstream\n"
        "object exists and before anything is exported.\n"
        "\n"
        "Two of the checks catch a **new** value rather than a known bad one, which is the\n"
        "difference between a test that ages well and one that does not:\n"
        "\n"
        "- `country_master_covers_source` - every spelling in `users.csv` must map to a market\n"
        "- `fx_rates_cover_plan_currencies` - every plan currency must have a budget rate",
        "`sql/duckdb/00_raw_quality.sql`, enforced by `assert_no_blocking_failures()` in `src/pipeline.py`",
        "`qa.raw_test_results`, exported to `outputs/qa/raw_test_results.csv`",
    ),
    code(
        'display(q("""\n'
        "    SELECT check_name, severity, failure_count, denominator, status, notes\n"
        "    FROM qa.raw_test_results\n"
        "    ORDER BY CASE status WHEN 'FAIL' THEN 1 WHEN 'WARN' THEN 2 ELSE 3 END, check_name\n"
        '"""))'
    ),
    conclusion(
        "Nine checks, zero blocking failures. The one WARN is an INFO-severity observation "
        "that event `user_id` is sparse - a known source condition, reported every build and "
        "deliberately non-blocking. **The gate is enforced, not just reported**: the pipeline "
        "raises `QualityGateFailed` and stops before the staging layer if any blocking check fails."
    ),
]

# ============================================================ PART 4
cells += [
    section(
        "Part 4", "Staging",
        "**What it does.** One view per source table. Types are cast, columns renamed to a\n"
        "consistent convention, and nothing else. No joins, no filtering, no business logic -\n"
        "so any warehouse row can be traced back to the source row it came from.",
        "`sql/duckdb/01_staging.sql`",
        "the `stg` schema (views, not tables - they cost nothing to keep current)",
    ),
    code(
        "# The production SQL, read from the file the pipeline runs.\n"
        'show_sql("stg.order_items")'
    ),
    code(
        'display(q("""\n'
        "    SELECT table_name, table_type\n"
        "    FROM information_schema.tables WHERE table_schema = 'stg'\n"
        "    ORDER BY table_name\n"
        '"""))'
    ),
    conclusion(
        "Staging is deliberately boring. Keeping it a one-to-one mirror of the source is what "
        "makes the reconciliation in Part 13 possible - row counts and values must match the "
        "source exactly at this layer, so any later discrepancy is attributable to a specific "
        "modelling step."
    ),
]

# ============================================================ PART 5
cells += [
    section(
        "Part 5", "Core - conformed dimensions",
        "**What it does.** The dimensions every fact joins to. This is where the country\n"
        "master is applied, so `Brasil` and `Brazil` become one market everywhere downstream.\n"
        "\n"
        "One modelling decision is worth stating. `dim_country` is a **mapping table** - one\n"
        "row per observed source spelling, so `canonical_country` repeats inside it. It\n"
        "therefore cannot serve as the \"one\" side of a BI relationship. `dim_market` exists\n"
        "separately with one row per market, and `dim_month` exists for the same reason\n"
        "because `dim_date` is at day grain.",
        "`sql/duckdb/02_core_dimensions.sql`",
        "the `core` schema; `dim_market`, `dim_month` and `dim_country` are exported to `data/processed/power_bi/`",
    ),
    code(
        "# How the country master is applied. This is the join that ends the Brasil/Brazil problem.\n"
        'show_sql("core.dim_country")'
    ),
    code(
        'print("dim_country - a mapping table, canonical_country repeats:")\n'
        'display(q("SELECT COUNT(*) AS rows, COUNT(DISTINCT canonical_country) AS markets FROM core.dim_country"))\n'
        "\n"
        'print("\\ndim_market - one row per market, safe as a BI dimension:")\n'
        'display(q("SELECT COUNT(*) AS rows, COUNT(DISTINCT canonical_country) AS markets FROM core.dim_market"))'
    ),
    conclusion(
        "Pointing a BI relationship at `dim_country` would create a many-to-many join and "
        "silently double every market total. Splitting the mapping table from the dimension "
        "is not pedantry - it is the difference between a report that is right and one that "
        "looks right."
    ),
]

# ============================================================ PART 6
cells += [
    section(
        "Part 6", "Core - facts",
        "**What it does.** The transactional grain. `fact_order_item` is one row per line\n"
        "item, enriched with the product, customer and date keys, and carrying the derived\n"
        "measures the marts aggregate: gross sales, net sales, net profit and the status\n"
        "flags that define what \"sold\" means.",
        "`sql/duckdb/03_core_facts.sql`",
        "the `core` schema; `fact_order_item` is exported to `data/processed/power_bi/`",
    ),
    code(
        "# Where gross, net and profit are defined. Every mart number traces back to these CASE expressions.\n"
        'show_sql("core.fact_order_item", lines=40)'
    ),
    code(
        'display(q("""\n'
        "    SELECT COUNT(*) AS line_items,\n"
        "           COUNT(DISTINCT order_id) AS orders,\n"
        "           COUNT(DISTINCT customer_id) AS customers,\n"
        "           ROUND(SUM(gross_sales_value), 0) AS gross_sales,\n"
        "           ROUND(SUM(net_sales_value), 0) AS net_sales,\n"
        "           ROUND(SUM(net_profit_value), 0) AS net_profit\n"
        "    FROM core.fact_order_item\n"
        '"""))'
    ),
    code(
        "# Gross minus net is not noise - it is cancelled and returned value.\n"
        'display(q("""\n'
        "    SELECT item_status, COUNT(*) AS line_items,\n"
        "           ROUND(SUM(gross_sales_value), 0) AS gross_value\n"
        "    FROM core.fact_order_item GROUP BY 1 ORDER BY line_items DESC\n"
        '"""))'
    ),
    conclusion(
        "**One line item in four never completes** - 27,072 cancelled and 18,041 returned out "
        "of 180,862. That 25% gap between gross and net is the single largest commercial fact "
        "in the dataset, and it is why every mart reports net rather than gross."
    ),
]

# ============================================================ PART 7
cells += [
    section(
        "Part 7", "Marts - acquisition and funnel",
        "**What it does.** Session-level behaviour rebuilt from 2.4 million raw events:\n"
        "channel quality, the session funnel from view to cart to purchase, and cart\n"
        "abandonment by segment.",
        "`sql/duckdb/04_mart_acquisition_funnel.sql`",
        "`mart.channel_quality`, `mart.funnel_monthly_channel`, `mart.cart_abandonment_segments`, `mart.acquisition_source_value`",
    ),
    code(
        'display(q("""\n'
        "    SELECT traffic_source, sessions, purchase_sessions,\n"
        "           ROUND(session_conversion_rate, 4) AS conversion_rate,\n"
        "           ROUND(cart_abandonment_rate, 4) AS abandonment_rate\n"
        "    FROM mart.channel_quality ORDER BY sessions DESC\n"
        '"""))'
    ),
    figure("funnel_by_channel.png", "Session funnel by acquisition channel"),
    conclusion(
        "Cart-to-purchase conversion is **uniform across every channel**. Channels differ in "
        "the volume they bring, not in the quality of the traffic, so the lever is acquisition "
        "spend allocation rather than channel-specific funnel optimisation."
    ),
]

# ============================================================ PART 8
cells += [
    section(
        "Part 8", "Marts - revenue, product and customer",
        "**What it does.** The descriptive core: monthly sales and profit, category and brand\n"
        "performance, geography, cohort retention and the customer 360 table.",
        "`sql/duckdb/05_mart_revenue_customer.sql`",
        "`mart.sales_monthly`, `mart.product_performance_category`, `mart.product_performance_brand`, "
        "`mart.geography_performance_country`, `mart.cohort_retention`, `mart.customer_360`",
    ),
    code(
        'display(q("""\n'
        "    SELECT month_start, ROUND(net_sales_value, 0) AS net_sales,\n"
        "           ROUND(net_profit_value, 0) AS net_profit,\n"
        "           ROUND(net_margin_rate, 4) AS margin_rate, orders, customers\n"
        "    FROM mart.sales_monthly WHERE is_complete_month = 1\n"
        "    ORDER BY month_start DESC LIMIT 12\n"
        '"""))'
    ),
    figure("monthly_sales_profit.png", "Monthly net sales and net profit"),
    figure("category_sales_margin.png", "Category value and margin - where the money and the margin are"),
    code(
        'print("Geography, after the country master is applied:")\n'
        'display(q("""\n'
        "    SELECT country, region, ROUND(net_sales_value, 0) AS net_sales,\n"
        "           customers, source_spellings\n"
        "    FROM mart.geography_performance_country ORDER BY net_sales DESC\n"
        '"""))'
    ),
    figure("cohort_retention_heatmap.png", "Cohort retention by acquisition month"),
    conclusion(
        "Net margin sits at a flat **51.8%** every month across five years, which is a property "
        "of how TheLook generates its data rather than a commercial finding - worth stating "
        "plainly rather than presenting as a margin achievement. The `source_spellings` column "
        "is the audit trail: it shows which raw spellings were folded into each market."
    ),
]

# ============================================================ PART 9
cells += [
    section(
        "Part 9", "Marts - operations and inventory",
        "**What it does.** Delivery lead time decomposed into warehouse processing and carrier\n"
        "transit, return and cancellation rates over time, and inventory sell-through and\n"
        "ageing by category and distribution centre.",
        "`sql/duckdb/06_mart_operations_inventory.sql`",
        "`mart.operations_monthly`, `mart.delivery_performance_dc`, `mart.inventory_performance`, `mart.return_risk_segments`",
    ),
    code(
        'display(q("""\n'
        "    SELECT distribution_center_name,\n"
        "           ROUND(avg_ship_lead_days, 2) AS warehouse_days,\n"
        "           ROUND(avg_delivery_lead_days, 2) AS carrier_days,\n"
        "           ROUND(avg_end_to_end_lead_days, 2) AS total_days\n"
        "    FROM mart.delivery_performance_dc ORDER BY total_days DESC LIMIT 10\n"
        '"""))'
    ),
    figure("delivery_lead_time_dc.png", "Delivery lead time by distribution centre"),
    conclusion(
        "Lead time is **identical across all ten distribution centres** - 1.5 days in the "
        "warehouse and 2.5 days in transit. There is no underperforming site to fix; the only "
        "lever on delivery speed is the carrier contract, which is a procurement decision "
        "rather than an operations one."
    ),
]

# ============================================================ PART 10
cells += [
    section(
        "Part 10", "Warehouse quality gates",
        "**What it does.** The checks that compare one layer against another - staged rows\n"
        "versus modelled rows, referential integrity, timestamp ordering. They cannot run any\n"
        "earlier than this because they need the warehouse to exist. The source-level checks\n"
        "already ran in Part 3.",
        "`sql/duckdb/07_quality_and_snapshots.sql`",
        "`qa.test_results` and `qa.metric_reconciliation`, exported to `outputs/qa/`",
    ),
    code(
        'display(q("""\n'
        "    SELECT check_name, layer, severity, failure_count, denominator, status\n"
        "    FROM qa.test_results\n"
        "    ORDER BY CASE status WHEN 'FAIL' THEN 1 WHEN 'WARN' THEN 2 ELSE 3 END, check_name\n"
        '"""))'
    ),
    conclusion(
        "Fourteen checks, zero blocking failures. The two WARNs are known source conditions - "
        "sparse event user IDs and a small number of invalid timestamp sequences - which are "
        "reported on every build and excluded from the lead-time calculations rather than "
        "silently included."
    ),
]

# ============================================================ PART 11
cells += [
    section(
        "Part 11", "The second source - regional plan submissions",
        "**What it does.** TheLook ships no budget data, so a planning file is constructed from\n"
        "a transparent, deterministic rule and written to `data/planning/` as a committed\n"
        "source artifact. It is then treated exactly like any other source system - ingested,\n"
        "gated, staged and validated with no privileged knowledge of how it was produced.\n"
        "\n"
        "```\n"
        "plan(country, month) = actual(same month last year)\n"
        "                     x trailing_growth(country, planning cycle)\n"
        "                     x ambition(country)\n"
        "                     x seasonal_uplift(month)\n"
        "```\n"
        "\n"
        "`trailing_growth` is the country's own CY(n-1)/CY(n-2) rate - the last complete year\n"
        "a planner could have seen when writing the plan. Planning off a trailing rate rather\n"
        "than off hindsight is what makes the resulting variance realistic instead of\n"
        "trivially positive.\n"
        "\n"
        "**Defects deliberately present**, because a validation suite that only ever passes\n"
        "proves nothing: local-language country names, one market submitting two months late,\n"
        "four blank cells, one negative target, and trailing whitespace on a country key.",
        "`src/build_plan_source.py`",
        "`data/planning/regional_plan_submissions.csv`, ingested to `raw.plan_submissions`",
    ),
    code(
        'print("The source file, as submitted - local currency, no USD:")\n'
        'display(q("SELECT * FROM raw.plan_submissions LIMIT 12"))\n'
        "\n"
        'print("\\nRows carrying a defect:")\n'
        'display(q("""\n'
        "    SELECT submission_batch, submitted_country, plan_month, currency_code,\n"
        "           plan_net_sales_local,\n"
        "           CASE WHEN plan_net_sales_local IS NULL THEN 'blank target'\n"
        "                WHEN plan_net_sales_local < 0 THEN 'negative target'\n"
        "                WHEN submitted_country <> TRIM(submitted_country) THEN 'trailing whitespace'\n"
        "                ELSE 'non-English country name' END AS defect\n"
        "    FROM raw.plan_submissions\n"
        "    WHERE plan_net_sales_local IS NULL OR plan_net_sales_local < 0\n"
        "       OR submitted_country <> TRIM(submitted_country)\n"
        "       OR submitted_country NOT IN (SELECT canonical_country FROM raw.country_master)\n"
        "    ORDER BY defect, submitted_country, plan_month LIMIT 12\n"
        '"""))'
    ),
    conclusion(
        "The plan file is **constructed, and the construction rule is published** in the module "
        "docstring and in `docs/commercial_analytics.md`. The alternative - inventing a budget "
        "with no stated rule - would make every variance number in this project unfalsifiable."
    ),
]

# ============================================================ PART 12
cells += [
    section(
        "Part 12", "The commercial layer",
        "**What it does.** Harmonises the submission against the country master, converts local\n"
        "currency to USD at the fixed budget rate, consolidates to a conformed country-month\n"
        "grain, and builds the plan-versus-actual and price-volume-mix layers on top.\n"
        "\n"
        "The staging view keeps every submitted row and adds judgement as **flag columns**\n"
        "rather than filtering. `core.fact_plan` then takes only the rows that pass. That\n"
        "separation is what makes a rejected row traceable back to the submission it came from.",
        "`sql/duckdb/08_commercial_planning.sql`",
        "`stg.plan_submissions`, `core.fact_plan`, `mart.plan_vs_actual_monthly`, "
        "`mart.price_volume_mix`, `mart.commercial_scorecard`",
    ),
    code(
        "# Harmonisation, FX conversion and the flag columns - all in one view.\n"
        'show_sql("stg.plan_submissions", lines=45)'
    ),
    code(
        'print("One row traced through all four layers:")\n'
        'print("\\nRAW - exactly as submitted")\n'
        'display(q("""SELECT * FROM raw.plan_submissions\n'
        "             WHERE submitted_country = 'Deutschland' AND plan_month = '2023-01-01'\"\"\"))\n"
        "\n"
        'print("STG - harmonised, FX-converted, flagged")\n'
        'display(q("""SELECT submitted_country, canonical_country, region, currency_code,\n'
        "                    budget_rate_to_usd, plan_net_sales_local, plan_net_sales_usd,\n"
        "                    flag_unmapped_country, flag_negative_target\n"
        "             FROM stg.plan_submissions\n"
        "             WHERE submitted_country = 'Deutschland' AND plan_month = DATE '2023-01-01'\"\"\"))\n"
        "\n"
        'print("CORE - accepted rows only, on the conformed grain")\n'
        'display(q("""SELECT canonical_country, region, plan_month, plan_net_sales_usd, plan_units\n'
        "             FROM core.fact_plan\n"
        "             WHERE canonical_country = 'Germany' AND plan_month = DATE '2023-01-01'\"\"\"))"
    ),
    md(
        "### Plan versus actual\n"
        "\n"
        "A full outer join, so three outcomes are visible rather than two: months with both,\n"
        "months with an actual and no plan, and months with a plan and no actual yet.\n"
    ),
    code(
        "# The full outer join, and the COALESCE that rebuilds the key from whichever side exists.\n"
        'show_sql("mart.plan_vs_actual_monthly", lines=40)'
    ),
    code(
        'display(q("""\n'
        "    SELECT plan_status, COUNT(*) AS months,\n"
        "           ROUND(SUM(actual_net_sales_usd), 0) AS actual_usd,\n"
        "           ROUND(SUM(plan_net_sales_usd), 0) AS plan_usd\n"
        "    FROM mart.plan_vs_actual_monthly GROUP BY 1 ORDER BY months DESC\n"
        '"""))'
    ),
    code(
        "# Like-for-like achievement: complete months where both a plan and an actual exist.\n"
        'display(q("""\n'
        "    SELECT canonical_country,\n"
        "           ROUND(SUM(actual_net_sales_usd), 0) AS actual_usd,\n"
        "           ROUND(SUM(plan_net_sales_usd), 0) AS plan_usd,\n"
        "           ROUND(SUM(actual_net_sales_usd) / SUM(plan_net_sales_usd), 3) AS achievement\n"
        "    FROM mart.plan_vs_actual_monthly\n"
        "    WHERE is_complete_month = 1 AND plan_net_sales_usd IS NOT NULL\n"
        "      AND actual_net_sales_usd IS NOT NULL\n"
        "    GROUP BY 1 ORDER BY achievement\n"
        '"""))'
    ),
    figure("plan_achievement_by_market.png", "Plan achievement by market"),
    conclusion(
        "Group achievement is **106.2% on a like-for-like basis**. Two markets are below plan: "
        "Poland at 72%, because it submitted two months late and those months carry revenue with "
        "no target against them, and Colombia at 85% on a base so small that the plan is barely "
        "meaningful. Eleven markets are between 101% and 117%."
    ),
    md(
        "### The price-volume-mix bridge\n"
        "\n"
        "Revenue is three numbers multiplied together - market units, this category's share of\n"
        "them, and its average selling price. Changing one at a time and measuring each step\n"
        "decomposes any revenue movement into exactly three causes.\n"
        "\n"
        "```\n"
        "volume = (Q1 - Q0) x s0 x P0      the market grew, we were carried with it\n"
        "mix    =  Q1 x (s1 - s0) x P0     we took a different share of it\n"
        "price  =  q1 x (P1 - P0)          we sold at a different price\n"
        "```\n"
        "\n"
        "The sequence is fixed and not arbitrary: volume is measured first and therefore at the\n"
        "prior share and price, mix second at the new market size but the old price, price last\n"
        "at current volume and share. That ordering is what makes the three effects sum to the\n"
        "variance exactly, with no residual bucket.\n"
    ),
    code(
        "# The three effects, computed in SQL. The sided CTE is where the ordering is enforced.\n"
        'show_sql("mart.price_volume_mix", lines=45)'
    ),
    code(
        'display(q("""\n'
        "    SELECT comparison_label,\n"
        "           ROUND(SUM(revenue_prior), 0) AS revenue_prior,\n"
        "           ROUND(SUM(revenue_current), 0) AS revenue_current,\n"
        "           ROUND(SUM(total_variance), 0) AS total_variance,\n"
        "           ROUND(SUM(volume_effect), 0) AS volume,\n"
        "           ROUND(SUM(mix_effect), 0) AS mix,\n"
        "           ROUND(SUM(price_effect), 0) AS price,\n"
        "           ROUND(ABS(SUM(volume_effect) + SUM(mix_effect) + SUM(price_effect)\n"
        "                     - SUM(total_variance)), 6) AS residual\n"
        "    FROM mart.price_volume_mix GROUP BY 1, comparison_order ORDER BY comparison_order\n"
        '"""))'
    ),
    figure("price_volume_mix_bridge.png", "Price-volume-mix bridge"),
    conclusion(
        "Growth in CY2023 was **almost entirely volume** - 1.23 million of a 1.21 million variance, "
        "with mix and price both slightly negative. The company grew by selling more, while quietly "
        "discounting. By April 2024 the price effect had turned positive at +13,444 and average "
        "selling price had risen from 59.52 to 60.36, which is a different and better quality of growth. "
        "The residual is zero on all three comparisons."
    ),
]

# ============================================================ PART 13
cells += [
    section(
        "Part 13", "Commercial quality gates and reconciliation",
        "**What it does.** Twelve checks on the commercial layer, and an end-to-end\n"
        "reconciliation statement that can be handed to a reviewer as it is.\n"
        "\n"
        "The design decision matters more than the checks. **Structural defects block the\n"
        "build** - an unmapped country, a broken grain, an FX conversion that does not\n"
        "reproduce, a consolidation that does not tie, a bridge whose effects do not sum.\n"
        "Each of those makes the consolidated number *wrong*, and publishing a wrong number is\n"
        "worse than publishing nothing. **Submission defects quarantine and warn** - blank\n"
        "cells, a sign error, a late region. Those make the plan *incomplete* rather than\n"
        "wrong; the month-end review still has to happen, and the defect goes back to the\n"
        "submitting market.",
        "`sql/duckdb/09_quality_commercial.sql`",
        "`qa.plan_validation`, `qa.plan_rejects`, `qa.reconciliation_statement`, exported to `outputs/qa/`",
    ),
    code(
        "# The twelve checks, as written. Severity is set per check, and severity is what decides whether a build stops.\n"
        'show_sql("qa.plan_validation", lines=45)'
    ),
    code(
        'print("Validation")\n'
        'display(q("""SELECT check_name, severity, failure_count, denominator, status\n'
        "             FROM qa.plan_validation\n"
        "             ORDER BY CASE status WHEN 'FAIL' THEN 1 WHEN 'WARN' THEN 2 ELSE 3 END,\n"
        "                      check_name\"\"\"))"
    ),
    code(
        'print("Quarantined rows - the list that goes back to the submitting market")\n'
        'display(q("SELECT * FROM qa.plan_rejects ORDER BY reject_reason"))'
    ),
    code(
        'print("End-to-end reconciliation")\n'
        'display(q("""SELECT stream, stage, entity, row_count, ROUND(value_usd, 2) AS value_usd,\n'
        "                    row_delta, expectation\n"
        "             FROM qa.reconciliation_statement ORDER BY stream, step_order\"\"\"))"
    ),
    conclusion(
        "**292 rows submitted, 5 quarantined, 287 accepted**, and the money ties at every stage. "
        "The one that matters commercially is Belgium: a single row submitted at -2,685.19 was "
        "subtracting from the consolidated plan, making the group budget 2,900 dollars easier to "
        "beat. A sign error does not announce itself - it just quietly flatters every achievement "
        "percentage computed against it."
    ),
]

# ============================================================ PART 14
cells += [
    section(
        "Part 14", "Customer concentration and segmentation",
        "**What it does.** Two questions a commercial team asks about its customer base: how\n"
        "concentrated is spend, and does the base split into groups worth treating differently.\n"
        "\n"
        "The Gini coefficient measures concentration on a 0 to 1 scale - 0 is perfectly even\n"
        "spend across all customers, 1 is a single customer holding everything. RFM segmentation\n"
        "clusters customers on recency, frequency and monetary value, with k chosen on silhouette\n"
        "score rather than assumed.",
        "`src/advanced_analytics.py`",
        "`artifacts/advanced_metrics.json`, `data/processed/advanced/rfm_segments.csv`",
    ),
    code(
        "# The segmentation as the pipeline runs it - k is chosen on silhouette score, not assumed.\n"
        'show_py("advanced_analytics.py", "rfm_segmentation", lines=45)'
    ),
    code(
        "# Gini coefficient on customer net spend.\n"
        "# Population: everyone who placed an order. Customers whose orders all cancelled\n"
        "# or returned net to zero are KEPT - they are real customers who contributed\n"
        "# nothing, and excluding them would understate concentration.\n"
        "spend = q(\"\"\"SELECT customer_id, SUM(net_sales_value) AS net_spend\n"
        "             FROM core.fact_order_item GROUP BY 1\n"
        "             HAVING SUM(net_sales_value) >= 0\"\"\")\n"
        "values = np.sort(spend.net_spend.to_numpy())\n"
        "n = len(values)\n"
        "gini = (2 * np.arange(1, n + 1) - n - 1).dot(values) / (n * values.sum())\n"
        "\n"
        "print(f\"Customers who placed an order : {n:,}\")\n"
        "print(f\"  of whom net spend is zero   : {(values == 0).sum():,} ({(values == 0).mean():.1%})\")\n"
        "print(f\"Gini coefficient              : {gini:.3f}\")\n"
        "print(f\"Top 10% share of net revenue  : {values[int(n * 0.9):].sum() / values.sum():.1%}\")\n"
        "print(f\"Top 20% share of net revenue  : {values[int(n * 0.8):].sum() / values.sum():.1%}\")\n"
        "\n"
        "# Sensitivity: the same measure on contributing customers only.\n"
        "pos = values[values > 0]\n"
        "m = len(pos)\n"
        "gini_pos = (2 * np.arange(1, m + 1) - m - 1).dot(pos) / (m * pos.sum())\n"
        "print(f\"Excluding zero-spend customers, Gini falls to {gini_pos:.3f} on {m:,} customers.\")"
    ),
    code(
        "# RFM segments, as computed by the pipeline.\n"
        "metrics = json.loads((ROOT / \"artifacts\" / \"advanced_metrics.json\").read_text(encoding=\"utf-8\"))\n"
        "rfm = pd.DataFrame(metrics[\"rfm_segmentation\"][\"segments\"])\n"
        "rfm[\"revenue_share\"] = rfm.total_net_sales / rfm.total_net_sales.sum()\n"
        "rfm[\"customer_share\"] = rfm.customers / rfm.customers.sum()\n"
        "display(rfm[[\"segment\", \"customers\", \"customer_share\", \"median_recency_days\",\n"
        "             \"mean_order_count\", \"median_net_sales\", \"total_net_sales\",\n"
        "             \"revenue_share\"]].round(3))\n"
        "sel = metrics[\"rfm_segmentation\"]\n"
        "print(f\"k selected on silhouette score: k={sel['selected_k']}, \"\n"
        "      f\"score={sel['silhouette_selected_k']:.3f}\")"
    ),
    figure("rfm_segments.png", "RFM segments - size against value"),
    conclusion(
        "Spend is **concentrated** - a Gini of 0.58, with the top 10% of customers holding 39% of "
        "net revenue and the top 20% holding 59%. A second finding sits inside that number: "
        "**17% of customers who placed an order contributed zero net revenue**, because everything "
        "they ordered was cancelled or returned. Excluding them drops the Gini to 0.49, which is "
        "why the population is stated rather than assumed. The segmentation splits 66,215 customers "
        "into three groups: **Champions are 30% of the base and 53% of revenue**, Hibernating are "
        "51% of the base and 32% of revenue, and New/Developing are the remainder. The commercial "
        "implication is that retention spend targeted at Champions protects more revenue per dollar "
        "than broad reactivation of the Hibernating group."
    ),
]

# ============================================================ PART 15
cells += [
    section(
        "Part 15", "Forecasting - and the audit that released it",
        "**What it does.** Forecasts monthly net sales to the end of the plan year, picks the\n"
        "method by rolling-origin backtest rather than in-sample fit, allocates the group number\n"
        "to markets on trailing share, and compares the result against plan.\n"
        "\n"
        "This module sat under *Next steps* for a long time. It was written and it ran, but it\n"
        "had not been read line by line, and a number I cannot defend undoes the point of\n"
        "everything before it. What follows is the audit that changed that.",
        "`src/forecasting.py`",
        "`mart.forecast_monthly`, `mart.forecast_accuracy`, `mart.forecast_backtest_detail`, "
        "`mart.forecast_scenarios`, `mart.forecast_country_month`, `mart.forecast_vs_plan`",
    ),
    md(
        "### The three candidates\n"
        "\n"
        "| Method | What it assumes |\n"
        "|---|---|\n"
        "| `seasonal_naive` | next January looks like last January. The benchmark any method has to beat before it earns its complexity |\n"
        "| `seasonal_naive_drift` | the same, scaled by the latest year-on-year movement. Captures trend without fitting anything |\n"
        "| `holt_winters_log` | additive trend and seasonality fitted on log net sales, which is multiplicative on the original scale |\n"
        "\n"
        "Deliberately small and deliberately conventional. A planning committee has to be able to\n"
        "follow the method, and whoever inherits the project has to be able to rerun it.\n"
    ),
    code(
        'scores = db.execute("SELECT * FROM mart.forecast_accuracy ORDER BY mape").fetchdf()\n'
        "for col in [\"mape\", \"mape_first_step\", \"mape_final_step\", \"worst_month_ape\", \"bias\"]:\n"
        '    scores[col] = (scores[col] * 100).round(1).astype(str) + "%"\n'
        "scores"
    ),
    md(
        "### The defect this audit found\n"
        "\n"
        "The backtest scored every model **one month ahead**. The production forecast then ran\n"
        "the winner **eight months ahead**.\n"
        "\n"
        "Forecast error grows with horizon, and not at the same rate for every method. A rule\n"
        "that carries last year's shape forward degrades slowly; a fitted trend compounds its\n"
        "trend error every step. Scoring at step one measures the first of those and says\n"
        "nothing about the second.\n"
        "\n"
        "`mart.forecast_backtest_detail` holds every fold, so the decay is queryable rather than\n"
        "a claim:\n"
    ),
    code(
        'decay = db.execute("""\n'
        "    SELECT step,\n"
        "           ROUND(AVG(CASE WHEN model = 'seasonal_naive_drift'\n"
        "                     THEN absolute_percentage_error END) * 100, 1) AS drift_pct,\n"
        "           ROUND(AVG(CASE WHEN model = 'holt_winters_log'\n"
        "                     THEN absolute_percentage_error END) * 100, 1) AS holt_winters_pct,\n"
        "           ROUND(AVG(CASE WHEN model = 'seasonal_naive'\n"
        "                     THEN absolute_percentage_error END) * 100, 1) AS benchmark_pct,\n"
        "           COUNT(*) AS folds\n"
        "    FROM mart.forecast_backtest_detail\n"
        "    GROUP BY step ORDER BY step\n"
        '""").fetchdf()\n'
        "decay"
    ),
    md(
        "At one month the two serious candidates look comparable. By month eight they are not -\n"
        "and month eight is the one the plan conversation is actually about.\n"
        "\n"
        "**The honest version.** The original design did not pick the wrong model. It picked the\n"
        "right one with almost no evidence: over its six one-step folds the two candidates split\n"
        "them three-three. It could as easily have landed on the other.\n"
        "\n"
        "**The fix.** `backtest()` now takes the production horizon and scores every step at\n"
        "every origin - 24 origins x 8 steps = 192 folds instead of 6 - and `run()` computes the\n"
        "horizon first so the two can no longer drift apart.\n"
    ),
    code('show_py("forecasting.py", "backtest", lines=40)'),
    md(
        "### Six more checks, specified before they were run\n"
        "\n"
        "| # | Check | Result |\n"
        "|---|---|---|\n"
        "| 2 | Does `exp(mean of logs)` bias Holt-Winters low? | **rejected** - measured bias +0.6%, negligible on this series |\n"
        "| 3 | Does MAPE's asymmetry distort the ranking? | **rejected** - MAPE, sMAPE, RMSE% and median APE all rank identically |\n"
        "| 4 | Is the ranking stable, or an artefact of six folds? | **defect** - re-scored over 32 origins the champion wins 27 of 27 windows, but the code had not established that |\n"
        "| 5 | Does the drift clip `[0.5, 2.5]` ever bind? | **pass** - raw ratio ranged 1.54 to 2.39, clip bound 0 times |\n"
        "| 6 | Is the incomplete final month excluded? | **pass** - `WHERE is_complete_month = 1`, May 2024 held out |\n"
        "| 7 | Does the country allocation sum back to the total? | **pass** - max delta 0.000000 |\n"
        "\n"
        "Two of the three most interesting hypotheses turned out to be wrong. That is worth\n"
        "saying out loud: a review that confirms everything it suspected is not a review.\n"
        "\n"
        "The full write-up is `docs/forecast_review.md`.\n"
    ),
    code(
        "# Check 7, re-run here rather than asserted.\n"
        'db.execute("""\n'
        "    SELECT f.month_start,\n"
        "           ROUND(f.forecast_net_sales_usd, 2) AS total,\n"
        "           ROUND(a.allocated, 2)              AS allocated_to_markets,\n"
        "           ROUND(a.allocated - f.forecast_net_sales_usd, 6) AS delta\n"
        "    FROM mart.forecast_monthly f\n"
        "    JOIN (SELECT month_start, SUM(forecast_net_sales_usd) AS allocated\n"
        "          FROM mart.forecast_country_month GROUP BY 1) a USING (month_start)\n"
        "    ORDER BY f.month_start\n"
        '""").fetchdf()'
    ),
    md("### The forecast itself, against plan\n"),
    code(
        'db.execute("""\n'
        "    SELECT month_start, basis,\n"
        "           ROUND(expected_net_sales_usd) AS expected,\n"
        "           ROUND(plan_net_sales_usd)     AS plan,\n"
        "           ROUND(gap_to_plan_usd)        AS gap,\n"
        "           ROUND(expected_achievement_rate * 100, 1) AS achievement_pct\n"
        "    FROM mart.forecast_vs_plan\n"
        "    WHERE plan_net_sales_usd IS NOT NULL\n"
        "    ORDER BY month_start\n"
        '""").fetchdf()'
    ),
    md(
        "### Two limitations that survive the audit\n"
        "\n"
        "**TheLook is synthetic.** Its growth curve is far smoother than real demand, which\n"
        "carries promotional spikes, stockouts and competitive shocks. An 8.0% MAPE here\n"
        "demonstrates a validation method; it is not an accuracy claim that transfers to a real\n"
        "business.\n"
        "\n"
        "**The plan is constructed.** TheLook ships no budget data, so `src/build_plan_source.py`\n"
        "generates it from a published deterministic rule. `mart.forecast_vs_plan` therefore\n"
        "compares a real forecast against a synthetic target, and the achievement rate above\n"
        "inherits that.\n"
    ),
    conclusion(
        "The module was held back from every presented surface until it had been audited to the "
        "standard of the warehouse, and the audit found two things worth fixing and rejected two "
        "hypotheses that sounded right. That sequence - hold it back, specify the checks, publish "
        "what the checks found including the ones that found nothing - is the part of this "
        "section worth more than the forecast."
    ),
]

# ============================================================ PART 16
cells += [
    section(
        "Part 16", "Where the outputs go",
        "**What it does.** Everything the pipeline produces lands in one of four places, and\n"
        "every one of them is regenerated on each run so nothing can drift from the warehouse.",
        "`src/render_outputs.py`, `src/render_commercial_figures.py`, `src/build_excel_pack.py`",
        "see the table below",
    ),
    md(
        "| Destination | Contents | Consumed by |\n"
        "|---|---|---|\n"
        "| `data/processed/power_bi/` | 34 CSV and Parquet exports | the Power BI report |\n"
        "| `data/processed/analysis/` | 23 analysis-ready CSVs | ad-hoc analysis, this notebook's figures |\n"
        "| `outputs/qa/` | 6 QA evidence files | reviewers, the validation gate |\n"
        "| `artifacts/figures/` | 12 rendered charts | the README and this notebook |\n"
        "| `reports/` | the Excel management pack | commercial colleagues who do not open Power BI |\n"
        "\n"
        "### On the Excel pack\n"
        "\n"
        "The Power BI report is the self-service surface and this notebook is the technical\n"
        "walkthrough, so the Excel workbook is neither of those - it is the **distribution**\n"
        "artifact. It is what circulates by email in a commercial team, where most readers will\n"
        "never open a BI tool. It is regenerated from the warehouse on every run, so it cannot\n"
        "drift from the dashboard, and it is one file rather than a folder of CSVs. It is not\n"
        "needed to understand the project, which is why it is named here rather than rebuilt in\n"
        "this notebook.\n"
    ),
    code(
        "for folder in [\"data/processed/power_bi/csv\", \"data/processed/analysis\",\n"
        '               "outputs/qa", "artifacts/figures", "reports"]:\n'
        "    path = ROOT / folder\n"
        "    if path.exists():\n"
        "        files = sorted(p.name for p in path.iterdir() if p.is_file())\n"
        '        print(f"{folder:<34} {len(files):>3} files")\n'
        "    else:\n"
        '        print(f"{folder:<34}   - not present")'
    ),
    code(
        "# The validation gate - the last thing the pipeline runs before it reports success.\n"
        'report = json.loads((ROOT / "artifacts" / "validation_report.json").read_text(encoding="utf-8"))\n'
        'print(json.dumps(report, indent=2)[:1200])'
    ),
    conclusion(
        "Every number in the dashboard, the Excel pack and this notebook comes from the same "
        "warehouse, regenerated by the same command. There is no manual step between the source "
        "CSVs and any published figure, which is what makes the whole thing reproducible rather "
        "than merely documented."
    ),
]

# ============================================================ PART 17
cells += [
    md(
        "---\n"
        "\n"
        "## Part 17 - Next steps\n"
        "\n"
        "Three pieces of work that are **not finished**, named here rather than shown. No\n"
        "results from any of them appear in this walkthrough, the dashboard or the management\n"
        "pack - they are scoped, not delivered.\n"
    ),
    md(
        "### 17.1 Return-propensity model - needs better features, not a better algorithm\n"
        "\n"
        "A logistic regression on price, margin, category and department, trained on pre-2023\n"
        "line items and tested on 2023 onward.\n"
        "\n"
        "**Built by** `src/advanced_analytics.py` - **Result in** `artifacts/advanced_metrics.json`\n"
    ),
    md(
        "The model was trained and scored, and the result is an **ROC AUC of 0.50** - a coin\n"
        "flip. The numbers are in `artifacts/advanced_metrics.json`; they are not reproduced\n"
        "here, because a model this project does not stand behind should not be given the\n"
        "visual weight of a result.\n"
    ),
    md(
        "**Next step.** The recommendation is to instrument better outcome logging - capture a\n"
        "return reason code and size/fit at the point of return - rather than to try another\n"
        "algorithm on the same features. Deploying a 0.50 AUC model would create work without\n"
        "creating value.\n"
    ),
    md(
        "### 17.2 Customer lifetime value - not attempted\n"
        "\n"
        "CLV is the natural extension of the RFM work in Part 14, and it is deliberately absent.\n"
        "\n"
        "**Next step.** A BG/NBD plus Gamma-Gamma model on the transaction history would give a\n"
        "forward-looking value per customer, which turns the segmentation from descriptive into\n"
        "actionable - it tells you what a Champion is worth over the next twelve months rather\n"
        "than what they have been worth historically. The data supports it; the time did not.\n"
    ),
]

# ============================================================ CLOSE
cells += [
    md(
        "---\n"
        "\n"
        "## What this project demonstrates\n"
        "\n"
        "| | |\n"
        "|---|---|\n"
        "| **Data engineering** | a layered warehouse, ten SQL modules run in sequence, idempotent and rebuildable from the seven source CSVs by one command |\n"
        "| **Integration** | two independent source systems reconciled onto a conformed country-month grain, with FX conversion at a fixed budget rate |\n"
        "| **Master data** | a genuine defect found in the source - 15 spellings for 13 markets - resolved with a committed country master and a gate that catches the sixteenth |\n"
        "| **Data quality** | 35 checks across three gates, with a stated rule for what blocks a build and what quarantines and warns |\n"
        "| **Reconciliation** | a statement a reviewer can audit without reading the code: 292 submitted, 5 quarantined, 287 accepted, money tying at every stage |\n"
        "| **Commercial analysis** | plan-versus-actual variance, a price-volume-mix bridge that reconciles to the cent, and a monthly scorecard |\n"
        "| **Forecasting** | three methods compared on 192 rolling-origin folds at the horizon actually used, with the audit that found two defects in the first version published alongside |\n"
        "| **Honesty** | a failed model reported as failed, a flat margin named as a dataset property, a constructed plan file with its construction rule published, and two forecast hypotheses tested and reported as wrong |\n"
        "\n"
        "### Limitations, stated\n"
        "\n"
        "- The planning file is **constructed**, from a published deterministic rule. No budget ships with TheLook.\n"
        "- Net margin is flat at 51.8% every month, which is a property of how the dataset was generated, not a commercial finding.\n"
        "- There is no price variation in the source, so the price elasticity work is method rather than evidence.\n"
        "- The return model failed, and the recommendation is better logging rather than a better algorithm.\n"
        "- The forecast MAPE is optimistic: synthetic growth is smoother than real demand, and the plan it\n"
        "  is measured against is constructed rather than supplied.\n"
        "\n"
        "---\n"
        "\n"
        "*Full written analysis: `docs/analysis_and_findings.md` and `docs/commercial_analytics.md`.*\n"
        "*Technical reference: `docs/technical_reference.md`. Metric definitions: `docs/kpi_dictionary.md`.*\n"
    ),
    code('db.close()\nprint("Walkthrough complete. The warehouse connection is closed.")'),
]

# ============================================================ WRITE
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
print(f"{OUT.relative_to(ROOT)}: {len(cells)} cells")
