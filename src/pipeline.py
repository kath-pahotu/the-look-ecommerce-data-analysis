from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import duckdb


SOURCE_TABLES = [
    "users",
    "products",
    "orders",
    "order_items",
    "events",
    "inventory_events",
    "distribution_centers",
]

POWER_BI_TABLES = [
    ("core", "dim_date"),
    ("core", "dim_customer"),
    ("core", "dim_product"),
    ("core", "dim_distribution_center"),
    ("core", "dim_session_traffic_source"),
    ("core", "dim_acquisition_source"),
    ("core", "fact_order"),
    ("core", "fact_order_item"),
    ("core", "fact_session"),
    ("core", "fact_inventory"),
    ("mart", "funnel_stage_channel"),
    ("mart", "funnel_monthly_channel"),
    ("mart", "channel_quality"),
    ("mart", "acquisition_source_value"),
    ("mart", "cart_abandonment_segments"),
    ("mart", "sales_monthly"),
    ("mart", "customer_360"),
    ("mart", "cohort_retention"),
    ("mart", "product_performance_category"),
    ("mart", "product_performance_brand"),
    ("mart", "geography_performance_country"),
    ("mart", "delivery_performance_dc"),
    ("mart", "operations_monthly"),
    ("mart", "return_risk_segments"),
    ("mart", "inventory_performance"),
]

# Curated, readable, already-aggregated tables for ad-hoc analysis (CSV only).
# Mirrors new_analysis: mart summary tables + the KPI snapshot, but deliberately
# EXCLUDES the granular customer_360 (1 row/customer) and the funnel_stage_channel
# visual-support table. Practice has qa.metric_snapshot instead of new_analysis's
# mart.executive_snapshot, so the snapshot ships as metric_snapshot.csv.
ANALYSIS_TABLES = [
    ("qa", "metric_snapshot"),
    ("mart", "channel_quality"),
    ("mart", "funnel_monthly_channel"),
    ("mart", "acquisition_source_value"),
    ("mart", "cart_abandonment_segments"),
    ("mart", "sales_monthly"),
    ("mart", "product_performance_category"),
    ("mart", "product_performance_brand"),
    ("mart", "geography_performance_country"),
    ("mart", "cohort_retention"),
    ("mart", "delivery_performance_dc"),
    ("mart", "operations_monthly"),
    ("mart", "return_risk_segments"),
    ("mart", "inventory_performance"),
]


def sql_literal(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sources(csv_dir: Path) -> list[dict[str, object]]:
    inventory = []
    for table in SOURCE_TABLES:
        path = csv_dir / f"{table}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required source: {path}")
        inventory.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": fingerprint(path),
            }
        )
    return inventory


def ingest_raw(
    connection: duckdb.DuckDBPyConnection,
    csv_dir: Path,
) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table in SOURCE_TABLES:
        path = csv_dir / f"{table}.csv"
        print(f"Loading raw.{table}")
        connection.execute(
            f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT *
            FROM read_csv_auto(
                '{sql_literal(path)}',
                header = true,
                sample_size = -1,
                nullstr = ''
            )
            """
        )


def execute_sql_modules(
    connection: duckdb.DuckDBPyConnection,
    sql_dir: Path,
) -> list[dict[str, object]]:
    runs = []
    for path in sorted(sql_dir.glob("*.sql")):
        started = time.perf_counter()
        print(f"Executing {path.name}")
        connection.execute(path.read_text(encoding="utf-8"))
        runs.append(
            {
                "module": path.name,
                "seconds": round(time.perf_counter() - started, 3),
            }
        )
    return runs


def export_table(
    connection: duckdb.DuckDBPyConnection,
    project_root: Path,
    schema: str,
    table: str,
) -> dict[str, object]:
    export_root = project_root / "data" / "processed" / "power_bi"
    csv_path = export_root / "csv" / f"{table}.csv"
    parquet_path = export_root / "parquet" / f"{table}.parquet"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    connection.execute(
        f"COPY (SELECT * FROM {schema}.{table}) "
        f"TO '{sql_literal(csv_path)}' (HEADER, DELIMITER ',')"
    )
    connection.execute(
        f"COPY (SELECT * FROM {schema}.{table}) "
        f"TO '{sql_literal(parquet_path)}' "
        "(FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    rows = connection.execute(
        f"SELECT COUNT(*) FROM {schema}.{table}"
    ).fetchone()[0]
    return {"schema": schema, "table": table, "rows": int(rows)}


def run(project_root: Path, csv_dir: Path) -> dict[str, object]:
    database_path = project_root / "artifacts" / "practice_analytics.duckdb"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    inventory = validate_sources(csv_dir)
    connection = duckdb.connect(str(database_path))
    started = time.perf_counter()
    try:
        connection.execute("SET threads = 4")
        connection.execute("SET preserve_insertion_order = false")
        ingest_raw(connection, csv_dir)
        module_runs = execute_sql_modules(
            connection,
            project_root / "sql" / "duckdb",
        )

        qa_dir = project_root / "outputs" / "qa"
        qa_dir.mkdir(parents=True, exist_ok=True)
        connection.execute(
            f"COPY qa.test_results TO "
            f"'{sql_literal(qa_dir / 'test_results.csv')}' "
            "(HEADER, DELIMITER ',')"
        )
        connection.execute(
            f"COPY qa.metric_reconciliation TO "
            f"'{sql_literal(qa_dir / 'metric_reconciliation.csv')}' "
            "(HEADER, DELIMITER ',')"
        )

        exports = [
            export_table(connection, project_root, schema, table)
            for schema, table in POWER_BI_TABLES
        ]

        analysis_root = project_root / "data" / "processed" / "analysis"
        analysis_root.mkdir(parents=True, exist_ok=True)
        analysis_exports = []
        for schema, table in ANALYSIS_TABLES:
            csv_path = analysis_root / f"{table}.csv"
            connection.execute(
                f"COPY (SELECT * FROM {schema}.{table}) "
                f"TO '{sql_literal(csv_path)}' (HEADER, DELIMITER ',')"
            )
            rows = connection.execute(
                f"SELECT COUNT(*) FROM {schema}.{table}"
            ).fetchone()[0]
            analysis_exports.append(
                {"schema": schema, "table": table, "rows": int(rows)}
            )

        raw_counts = {
            table: int(
                connection.execute(
                    f"SELECT COUNT(*) FROM raw.{table}"
                ).fetchone()[0]
            )
            for table in SOURCE_TABLES
        }
    finally:
        connection.close()

    metadata = {
        "database_path": str(database_path),
        "source_csv_dir": str(csv_dir.resolve()),
        "source_inventory": inventory,
        "raw_row_counts": raw_counts,
        "sql_modules": module_runs,
        "exports": exports,
        "analysis_exports": analysis_exports,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "session_source": "events.csv grouped by session_id",
        "legacy_dim_sessions_required": False,
    }
    metadata_path = project_root / "artifacts" / "pipeline_run.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--source-csv-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        args.project_root.resolve(),
        args.source_csv_dir.resolve(),
    )
    print(json.dumps(result["raw_row_counts"], indent=2))


if __name__ == "__main__":
    main()