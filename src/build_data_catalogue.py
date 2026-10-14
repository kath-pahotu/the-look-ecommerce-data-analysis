"""Generate docs/warehouse_catalogue.md - every table, every column, from the warehouse.

Answers "what is in this thing" in one file: for each object, the row count, the
declared grain where there is one, and for each column the type, how many nulls,
how many distinct values and a real example.

Read from the live warehouse on every run, so it cannot drift from the data.

Run:
    python src/build_data_catalogue.py --project-root .
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

LAYER_ORDER = {"raw": 1, "stg": 2, "core": 3, "mart": 4, "qa": 5}

LAYER_NOTE = {
    "raw": "The source files, landed exactly as delivered. Nothing is typed, renamed or "
           "cleaned here - this layer exists so that every later number can be traced back "
           "to the row it came from.",
    "stg": "One view per source table. Types cast, columns renamed to a consistent "
           "convention, and nothing else: no joins, no filtering, no business logic. Row "
           "counts must equal the source exactly.",
    "core": "The conformed model. Dimensions every fact joins to, and facts at the "
            "transactional grain carrying the derived measures. This is where gross, net "
            "and profit are defined, and where the country master is applied.",
    "mart": "One table per business question, aggregated to the grain that question needs. "
            "Nothing here may introduce a number that cannot be derived from `core`.",
    "qa": "The evidence layer: check results, the quarantined rows, and the reconciliation "
          "statements. Exported to `outputs/qa/` on every build.",
}

GRAIN = {
    "stg.sessions": "one row per session_id",
    "core.dim_date": "one row per calendar day",
    "core.dim_customer": "one row per customer",
    "core.dim_product": "one row per product",
    "core.dim_country": "one row per observed source spelling (a mapping table - "
                        "canonical_country repeats)",
    "core.dim_market": "one row per canonical market",
    "core.dim_month": "one row per month",
    "core.fact_order": "one row per order",
    "core.fact_order_item": "one row per order line item",
    "core.fact_session": "one row per session",
    "core.fact_inventory": "one row per inventory item",
    "core.fact_plan": "one row per canonical_country x plan_month (accepted rows only)",
    "mart.sales_monthly": "one row per month",
    "mart.customer_360": "one row per customer",
    "mart.cohort_retention": "one row per acquisition cohort x months-since",
    "mart.actual_country_month": "one row per canonical_country x month",
    "mart.plan_vs_actual_monthly": "one row per canonical_country x month",
    "mart.plan_vs_actual_region": "one row per region",
    "mart.price_volume_mix": "one row per comparison x category",
    "mart.commercial_scorecard": "one row per KPI",
    "mart.operations_monthly": "one row per month",
    "mart.geography_performance_country": "one row per canonical market",
    "qa.raw_test_results": "one row per source check",
    "qa.test_results": "one row per warehouse check",
    "qa.plan_validation": "one row per commercial check",
    "qa.plan_rejects": "one row per quarantined submission",
    "qa.reconciliation_statement": "one row per stream x step",
}

DESCRIPTION = {
    "mart.funnel_stage_channel": "Funnel counts by stage and channel",
    "mart.funnel_monthly_channel": "The same funnel, by month",
    "mart.channel_quality": "Channel-level conversion and value",
    "mart.acquisition_source_value": "Lifetime value by acquisition source",
    "mart.cart_abandonment_segments": "Where carts are abandoned, and by whom",
    "mart.product_performance_category": "Sales and margin by category",
    "mart.product_performance_brand": "Sales and margin by brand",
    "mart.delivery_performance_dc": "Delivery lead time by distribution centre",
    "mart.return_risk_segments": "Return rate by segment",
    "mart.inventory_performance": "Stock age and cover",
    "mart.executive_snapshot": "The headline numbers, formatted for display",
}


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def catalogue(connection) -> str:
    objects = connection.execute(
        """
        SELECT schema_name AS layer, table_name AS name, 'table' AS kind
        FROM duckdb_tables()
        UNION ALL
        SELECT schema_name, view_name, 'view' FROM duckdb_views()
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
        """
    ).fetchall()
    objects = [o for o in objects if o[0] in LAYER_ORDER]
    objects.sort(key=lambda o: (LAYER_ORDER[o[0]], o[1]))

    lines: list[str] = []
    row_counts: dict[str, int] = {}
    add = lines.append
    total_columns = 0

    body: list[str] = []
    for layer, name, kind in objects:
        full = f"{layer}.{name}"
        rows = connection.execute(f"SELECT COUNT(*) FROM {full}").fetchone()[0]
        row_counts[full] = rows
        columns = connection.execute(
            f"""
            SELECT column_name, data_type FROM duckdb_columns()
            WHERE schema_name = '{layer}' AND table_name = '{name}'
            ORDER BY column_index
            """
        ).fetchall()
        total_columns += len(columns)

        pieces = []
        for column, _ in columns:
            c = quote(column)
            pieces.append(
                f"COUNT(*) - COUNT({c}), COUNT(DISTINCT {c}), "
                f"MIN(CAST({c} AS VARCHAR))"
            )
        stats = (
            connection.execute(f"SELECT {', '.join(pieces)} FROM {full}").fetchone()
            if columns and rows
            else [None] * (len(columns) * 3)
        )

        body.append(f"### `{full}`")
        body.append("")
        meta = [f"**{rows:,} rows**", f"`{kind}`"]
        if full in GRAIN:
            meta.append(f"grain: {GRAIN[full]}")
        body.append(" · ".join(meta))
        if full in DESCRIPTION:
            body.append("")
            body.append(DESCRIPTION[full])
        body.append("")
        body.append("| Column | Type | Nulls | Distinct | Example |")
        body.append("|---|---|---|---|---|")
        for index, (column, dtype) in enumerate(columns):
            nulls = stats[index * 3]
            distinct = stats[index * 3 + 1]
            example = stats[index * 3 + 2]
            if example is None:
                example = "-"
            example = str(example).replace("|", "\\|")
            if len(example) > 34:
                example = example[:31] + "..."
            null_cell = "-" if not nulls else f"{nulls:,}"
            body.append(
                f"| `{column}` | {dtype} | {null_cell} | "
                f"{distinct:,} | `{example}` |" if distinct is not None
                else f"| `{column}` | {dtype} | - | - | - |"
            )
        body.append("")

    add("# Warehouse catalogue")
    add("")
    add(f"Every object in the warehouse: **{len(objects)} tables and views, "
        f"{total_columns} columns**. Generated from the live warehouse by")
    add("`src/build_data_catalogue.py` on every build, so it cannot drift from the data.")
    add("")
    add("## How to read a column row")
    add("")
    add("| Column | Means |")
    add("|---|---|")
    add("| **Nulls** | how many rows have no value. A LEFT JOIN onto a column with nulls "
        "produces nulls downstream that were never planned for. |")
    add("| **Distinct** | how many different values. Equal to the row count means the "
        "column is a candidate key; very low means it is a category worth grouping by. |")
    add("| **Example** | a real value from the table, so the format is visible - "
        "`2024-01-27 22:36:43` versus `20240127` matters when writing a join. |")
    add("")
    add("For a live version of this on any single table, the workbench has "
        "`w.cols(\"core.fact_plan\")`.")
    add("")
    add("## Contents")
    add("")
    for layer in sorted({o[0] for o in objects}, key=lambda s: LAYER_ORDER[s]):
        names = [o[1] for o in objects if o[0] == layer]
        add(f"### [`{layer}`](#{layer}) - {len(names)} objects")
        add("")
        add("| Object | Rows | Grain |")
        add("|---|---|---|")
        for name in names:
            full = f"{layer}.{name}"
            anchor = full.replace(".", "").lower()
            rows = row_counts[full]
            add(f"| [`{full}`](#{anchor}) | {rows:,} | {GRAIN.get(full, '-')} |")
        add("")

    current = None
    for line in body:
        if line.startswith("### `"):
            layer = line.split("`")[1].split(".")[0]
            if layer != current:
                current = layer
                add("---")
                add("")
                add(f"## {layer}")
                add("")
                add(LAYER_NOTE[layer])
                add("")
        add(line)

    return "\n".join(lines) + "\n"


def run(project_root: Path) -> Path:
    database = project_root / "artifacts" / "thelook_analytics.duckdb"
    connection = duckdb.connect(str(database), read_only=True)
    try:
        text = catalogue(connection)
    finally:
        connection.close()
    out = project_root / "docs" / "warehouse_catalogue.md"
    out.write_text(text, encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.project_root.resolve()
    path = run(root)
    print(f"{path.relative_to(root)}  ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
