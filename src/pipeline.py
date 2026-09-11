from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import duckdb


ORIGINAL_SOURCE_TABLES = [
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

ANALYSIS_TABLES = [
    ("mart", "executive_snapshot"),
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


def configure_logging(project_root: Path) -> None:
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "pipeline.log", mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def sql_literal(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def check_source_files(csv_dir: Path) -> list[str]:
    files: list[str] = []
    for name in ORIGINAL_SOURCE_TABLES:
        path = csv_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Required source file is missing: {path}")
        files.append(path.name)
    return files


def ingest_raw(connection: duckdb.DuckDBPyConnection, csv_dir: Path) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table in ORIGINAL_SOURCE_TABLES:
        path = csv_dir / f"{table}.csv"
        logging.info("Loading raw.%s from %s", table, path)
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
    connection: duckdb.DuckDBPyConnection, sql_dir: Path
) -> list[str]:
    modules: list[str] = []
    for path in sorted(sql_dir.glob("*.sql")):
        logging.info("Executing %s", path.name)
        connection.execute(path.read_text(encoding="utf-8"))
        modules.append(path.name)
    return modules


def export_table(
    connection: duckdb.DuckDBPyConnection,
    schema: str,
    table: str,
    destination_dir: Path,
) -> dict[str, object]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    csv_path = destination_dir / "csv" / f"{table}.csv"
    parquet_path = destination_dir / "parquet" / f"{table}.parquet"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    connection.execute(
        f"COPY (SELECT * FROM {schema}.{table}) TO "
        f"'{sql_literal(csv_path)}' (HEADER, DELIMITER ',')"
    )
    connection.execute(
        f"COPY (SELECT * FROM {schema}.{table}) TO "
        f"'{sql_literal(parquet_path)}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    row_count = connection.execute(
        f"SELECT COUNT(*) FROM {schema}.{table}"
    ).fetchone()[0]
    return {
        "schema": schema,
        "table": table,
        "rows": int(row_count),
        "csv": str(csv_path),
        "parquet": str(parquet_path),
    }


def run(project_root: Path, csv_dir: Path, rebuild: bool) -> dict[str, object]:
    configure_logging(project_root)
    database_path = project_root / "artifacts" / "thelook_analytics.duckdb"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if rebuild:
        for generated_dir in (
            project_root / "data" / "processed",
            project_root / "outputs" / "qa",
            project_root / "artifacts" / "figures",
        ):
            if generated_dir.exists():
                for generated_file in generated_dir.rglob("*"):
                    if generated_file.is_file():
                        generated_file.unlink()
        if database_path.exists():
            database_path.unlink()

    started = time.perf_counter()
    source_files = check_source_files(csv_dir)
    connection = duckdb.connect(str(database_path))
    try:
        connection.execute("SET threads = 4")
        connection.execute("SET preserve_insertion_order = false")
        ingest_raw(connection, csv_dir)
        sql_modules = execute_sql_modules(
            connection, project_root / "sql" / "duckdb"
        )

        qa_dir = project_root / "outputs" / "qa"
        qa_dir.mkdir(parents=True, exist_ok=True)
        connection.execute(
            f"COPY qa.test_results TO '{sql_literal(qa_dir / 'test_results.csv')}' "
            "(HEADER, DELIMITER ',')"
        )
        connection.execute(
            f"COPY qa.metric_reconciliation TO "
            f"'{sql_literal(qa_dir / 'metric_reconciliation.csv')}' "
            "(HEADER, DELIMITER ',')"
        )

        exports: list[dict[str, object]] = []
        power_bi_root = project_root / "data" / "processed" / "power_bi"
        for schema, table in POWER_BI_TABLES:
            exports.append(export_table(connection, schema, table, power_bi_root))

        analysis_root = project_root / "data" / "processed" / "analysis"
        for schema, table in ANALYSIS_TABLES:
            csv_path = analysis_root / f"{table}.csv"
            analysis_root.mkdir(parents=True, exist_ok=True)
            connection.execute(
                f"COPY (SELECT * FROM {schema}.{table}) TO "
                f"'{sql_literal(csv_path)}' (HEADER, DELIMITER ',')"
            )

        raw_counts = {
            table: int(
                connection.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]
            )
            for table in ORIGINAL_SOURCE_TABLES
        }
        qa_status = {
            row[0]: int(row[1])
            for row in connection.execute(
                "SELECT status, COUNT(*) FROM qa.test_results GROUP BY status"
            ).fetchall()
        }
    finally:
        connection.close()

    metadata = {
        "source_files": source_files,
        "raw_row_counts": raw_counts,
        "sql_modules": sql_modules,
        "power_bi_tables": [
            {"schema": e["schema"], "table": e["table"], "rows": e["rows"]}
            for e in exports
        ],
        "qa_status": qa_status,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    metadata_path = project_root / "artifacts" / "pipeline_run.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logging.info("Pipeline completed in %.1f seconds", metadata["elapsed_seconds"])
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--source-csv-dir", type=Path, required=True)
    parser.add_argument("--rebuild", action="store_true")
    arguments = parser.parse_args()
    run(arguments.project_root.resolve(), arguments.source_csv_dir.resolve(), arguments.rebuild)


if __name__ == "__main__":
    main()
