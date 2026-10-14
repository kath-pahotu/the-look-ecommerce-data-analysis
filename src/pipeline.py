from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import duckdb


# Reference data committed with the project. These are seeds, not extracts:
# small, hand-maintained, and version-controlled alongside the code.
SEED_SOURCES = [
    ("country_master", "seeds/country_master.csv"),
    ("fx_budget_rates", "seeds/fx_budget_rates.csv"),
]

# The second source system. Regional plan submissions arrive as a flat file
# in local currency. Generated once by src/build_plan_source.py and then
# committed, because a plan is an input to the warehouse, not an output.
PLANNING_SOURCES = [
    ("plan_submissions", "data/planning/regional_plan_submissions.csv"),
]

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
    ("core", "dim_country"),
    ("core", "dim_market"),
    ("core", "dim_month"),
    ("core", "fact_plan"),
    ("mart", "actual_country_month"),
    ("mart", "plan_vs_actual_monthly"),
    ("mart", "plan_vs_actual_region"),
    ("mart", "price_volume_mix"),
    ("mart", "commercial_scorecard"),
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
    ("mart", "plan_vs_actual_monthly"),
    ("mart", "plan_vs_actual_region"),
    ("mart", "price_volume_mix"),
    ("mart", "commercial_scorecard"),
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


def ingest_file(
    connection: duckdb.DuckDBPyConnection, table: str, path: Path
) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required source file is missing: {path}")
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


def ingest_reference(connection: duckdb.DuckDBPyConnection, project_root: Path) -> list[str]:
    """Load the seeds and the planning submissions into the raw schema."""
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
    loaded: list[str] = []
    for table, relative in SEED_SOURCES + PLANNING_SOURCES:
        ingest_file(connection, table, project_root / relative)
        loaded.append(relative)
    return loaded


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


class QualityGateFailed(RuntimeError):
    """Raised when a blocking test fails, before anything downstream runs."""


def assert_no_blocking_failures(
    connection: duckdb.DuckDBPyConnection, table: str, stage: str
) -> None:
    """Stop the build if `table` contains any row with status = FAIL.

    Called at two points: once after the source gate, so a broken extract
    never gets modelled, and once after the warehouse is built, so a broken
    model never gets exported. Without the second call the pipeline would
    still fail overall, but 34 CSV files and the Excel pack would already
    have been written to disk by then.
    """
    failures = connection.execute(
        f"""
        SELECT check_name, severity, failure_count, notes
        FROM {table} WHERE status = 'FAIL' ORDER BY check_name
        """
    ).fetchall()
    if not failures:
        passed = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE status = 'PASS'"
        ).fetchone()[0]
        warned = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE status = 'WARN'"
        ).fetchone()[0]
        logging.info(
            "%s gate passed - %s PASS, %s WARN, 0 FAIL (%s)",
            stage, passed, warned, table,
        )
        return

    detail = "\n".join(
        f"    - {name} [{severity}]: {count} failures - {notes}"
        for name, severity, count, notes in failures
    )
    raise QualityGateFailed(
        f"{stage} gate failed with {len(failures)} blocking test(s).\n"
        f"{detail}\n"
        "Nothing downstream was built or exported."
    )


def execute_sql_modules(
    connection: duckdb.DuckDBPyConnection,
    sql_dir: Path,
    only: list[str] | None = None,
) -> list[str]:
    modules: list[str] = []
    for path in sorted(sql_dir.glob("*.sql")):
        if only is not None and path.name not in only:
            continue
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
        reference_files = ingest_reference(connection, project_root)

        # Phase 1 - source gate. Checks that need nothing but the raw schema,
        # run before a single model exists.
        sql_dir = project_root / "sql" / "duckdb"
        available = sorted(path.name for path in sql_dir.glob("*.sql"))
        gate_modules = [name for name in available if name.startswith("00_")]
        model_modules = [name for name in available if not name.startswith("00_")]

        sql_modules = execute_sql_modules(connection, sql_dir, only=gate_modules)
        assert_no_blocking_failures(connection, "qa.raw_test_results", "Source")

        # Phase 2 - build the warehouse, then gate again before exporting.
        sql_modules += execute_sql_modules(connection, sql_dir, only=model_modules)
        assert_no_blocking_failures(connection, "qa.test_results", "Warehouse")
        assert_no_blocking_failures(connection, "qa.plan_validation", "Commercial")

        qa_dir = project_root / "outputs" / "qa"
        qa_dir.mkdir(parents=True, exist_ok=True)
        connection.execute(
            f"COPY qa.raw_test_results TO "
            f"'{sql_literal(qa_dir / 'raw_test_results.csv')}' "
            "(HEADER, DELIMITER ',')"
        )
        connection.execute(
            f"COPY qa.test_results TO '{sql_literal(qa_dir / 'test_results.csv')}' "
            "(HEADER, DELIMITER ',')"
        )
        connection.execute(
            f"COPY qa.metric_reconciliation TO "
            f"'{sql_literal(qa_dir / 'metric_reconciliation.csv')}' "
            "(HEADER, DELIMITER ',')"
        )
        connection.execute(
            f"COPY qa.plan_rejects TO '{sql_literal(qa_dir / 'plan_rejects.csv')}' "
            "(HEADER, DELIMITER ',')"
        )
        connection.execute(
            f"COPY qa.plan_validation TO "
            f"'{sql_literal(qa_dir / 'plan_validation.csv')}' "
            "(HEADER, DELIMITER ',')"
        )
        connection.execute(
            f"COPY qa.reconciliation_statement TO "
            f"'{sql_literal(qa_dir / 'reconciliation_statement.csv')}' "
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
                """
                SELECT status, COUNT(*) FROM (
                    SELECT status FROM qa.raw_test_results
                    UNION ALL SELECT status FROM qa.test_results
                    UNION ALL SELECT status FROM qa.plan_validation
                ) GROUP BY status
                """
            ).fetchall()
        }
    finally:
        connection.close()

    metadata = {
        "source_files": source_files,
        "reference_files": reference_files,
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
