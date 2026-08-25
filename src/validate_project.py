from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import nbformat
from PIL import Image, ImageStat


ORIGINAL_SOURCE_TABLES = {
    "users",
    "products",
    "orders",
    "order_items",
    "events",
    "inventory_events",
    "distribution_centers",
}

REQUIRED_FILES = [
    "00_START_HERE.md",
    "README.md",
    ".gitignore",
    "requirements.txt",
    "docs/01_PROJECT_WALKTHROUGH.md",
    "docs/02_SESSIONIZATION_FROM_EVENTS.md",
    "docs/analysis_findings.md",
    "docs/kpi_dictionary.md",
    "docs/data_dictionary.md",
    "docs/advanced_methods.md",
    "private_review/session_lineage_audit.md",
    "power_bi/README.md",
    "power_bi/data_model.md",
    "power_bi/dashboard_blueprint.md",
    "power_bi/measures.dax",
    "power_bi/theme.json",
    "notebooks/01_data_quality_and_core_analysis.ipynb",
    "notebooks/02_statistical_deep_dives.ipynb",
    "notebooks/03_event_sessionization_audit.ipynb",
]


def validate_notebook(path: Path) -> list[str]:
    issues: list[str] = []
    notebook = nbformat.read(path, as_version=4)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        if cell.get("execution_count") is None:
            issues.append(f"{path.name}: code cell {index} was not executed")
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                issues.append(
                    f"{path.name}: code cell {index} error "
                    f"{output.get('ename')}: {output.get('evalue')}"
                )
    return issues


def validate_image(path: Path) -> list[str]:
    issues: list[str] = []
    with Image.open(path) as image:
        if image.width < 800 or image.height < 400:
            issues.append(f"{path.name}: image resolution is too small")
        grayscale = image.convert("L")
        if ImageStat.Stat(grayscale).var[0] < 20:
            issues.append(f"{path.name}: image appears blank or nearly uniform")
    return issues


def run(project_root: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (project_root / relative).exists():
            errors.append(f"Missing required file: {relative}")

    database_path = project_root / "artifacts" / "thelook_analytics.duckdb"
    raw_tables_checked: list[str] = []
    session_lineage: dict[str, int] = {}
    if not database_path.exists():
        errors.append("Missing DuckDB warehouse")
    else:
        connection = duckdb.connect(str(database_path), read_only=True)
        try:
            raw_tables = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'raw'
                    """
                ).fetchall()
            }
            raw_tables_checked = sorted(raw_tables)
            if raw_tables != ORIGINAL_SOURCE_TABLES:
                errors.append(
                    "Raw source contract mismatch: "
                    f"expected {sorted(ORIGINAL_SOURCE_TABLES)}, found {sorted(raw_tables)}"
                )

            blocking = connection.execute(
                "SELECT COUNT(*) FROM qa.test_results WHERE status = 'FAIL'"
            ).fetchone()[0]
            if blocking:
                errors.append(f"{blocking} blocking data-quality tests failed")
            reconciliation = connection.execute(
                "SELECT metric_name, variance FROM qa.metric_reconciliation"
            ).fetchall()
            for metric, variance in reconciliation:
                if abs(variance) > 0.001:
                    errors.append(
                        f"Metric reconciliation failed: {metric} variance={variance}"
                    )
            expected_counts = {
                "core.dim_customer": 100000,
                "core.dim_product": 29120,
                "core.fact_order": 124814,
                "core.fact_order_item": 180862,
                "core.fact_inventory": 488146,
            }
            for table, expected in expected_counts.items():
                actual = connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                if actual != expected:
                    errors.append(
                        f"{table}: expected {expected:,} rows, found {actual:,}"
                    )

            source_events, source_sessions, fact_sessions, modeled_events = (
                connection.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM raw.events),
                        (SELECT COUNT(DISTINCT session_id) FROM stg.events),
                        (SELECT COUNT(*) FROM core.fact_session),
                        (SELECT SUM(event_count) FROM core.fact_session)
                    """
                ).fetchone()
            )
            session_lineage = {
                "source_events": int(source_events),
                "source_sessions": int(source_sessions),
                "fact_sessions": int(fact_sessions),
                "modeled_session_events": int(modeled_events),
            }
            if source_sessions != fact_sessions:
                errors.append(
                    "Session lineage failed: distinct events.session_id count "
                    f"{source_sessions:,} != fact_session rows {fact_sessions:,}"
                )
            if source_events != modeled_events:
                errors.append(
                    "Session lineage failed: source event rows "
                    f"{source_events:,} != summed session event_count {modeled_events:,}"
                )

            warnings_count = connection.execute(
                "SELECT COUNT(*) FROM qa.test_results WHERE status = 'WARN'"
            ).fetchone()[0]
            if warnings_count:
                warnings.append(
                    f"{warnings_count} documented data-quality warnings remain"
                )
        finally:
            connection.close()

    pipeline_metadata_path = project_root / "artifacts" / "pipeline_run.json"
    if not pipeline_metadata_path.exists():
        errors.append("Missing pipeline execution metadata")
    else:
        metadata = json.loads(pipeline_metadata_path.read_text(encoding="utf-8"))
        inventory_files = {
            item["file"] for item in metadata.get("source_inventory", [])
        }
        expected_files = {f"{table}.csv" for table in ORIGINAL_SOURCE_TABLES}
        if inventory_files != expected_files:
            errors.append(
                "Pipeline source inventory mismatch: "
                f"expected {sorted(expected_files)}, found {sorted(inventory_files)}"
            )
        policy = metadata.get("source_policy", {})
        if policy.get("legacy_derived_session_file_required") is not False:
            errors.append(
                "Pipeline metadata must explicitly state that the legacy "
                "derived session file is not required"
            )

    for relative in (
        "src/pipeline.py",
        "sql/duckdb/01_staging.sql",
        "sql/duckdb/03_core_facts.sql",
    ):
        implementation = (project_root / relative).read_text(
            encoding="utf-8"
        ).lower()
        forbidden_raw_table = "raw." + "dim_" + "sessions"
        forbidden_source_file = "dim_" + "sessions.csv"
        if (
            forbidden_raw_table in implementation
            or forbidden_source_file in implementation
        ):
            errors.append(
                f"Forbidden legacy session-source dependency remains in {relative}"
            )

    expected_power_bi_tables = {
        "dim_date", "dim_customer", "dim_product", "dim_distribution_center",
        "dim_session_traffic_source", "dim_acquisition_source", "fact_order",
        "fact_order_item", "fact_session", "fact_inventory",
        "funnel_stage_channel", "funnel_monthly_channel", "channel_quality",
        "acquisition_source_value", "cart_abandonment_segments", "sales_monthly",
        "customer_360", "cohort_retention", "product_performance_category",
        "product_performance_brand", "geography_performance_country",
        "delivery_performance_dc", "operations_monthly", "return_risk_segments",
        "inventory_performance",
    }
    for subfolder, suffix in (("csv", ".csv"), ("parquet", ".parquet")):
        folder = project_root / "data" / "processed" / "power_bi" / subfolder
        actual = (
            {path.stem for path in folder.glob(f"*{suffix}")}
            if folder.exists()
            else set()
        )
        missing = expected_power_bi_tables - actual
        unexpected = actual - expected_power_bi_tables
        if missing:
            errors.append(
                f"Power BI {subfolder} exports missing: {sorted(missing)}"
            )
        if unexpected:
            errors.append(
                f"Power BI {subfolder} stale/unexpected exports: {sorted(unexpected)}"
            )

    customer_export = (
        project_root / "data" / "processed" / "power_bi" / "csv" / "dim_customer.csv"
    )
    if customer_export.exists():
        header = customer_export.open(encoding="utf-8").readline().lower()
        for pii_field in (
            "first_name", "last_name", "email", "street_address", "ip_address"
        ):
            if pii_field in header:
                errors.append(
                    f"PII field {pii_field} appears in the Power BI customer export"
                )

    notebooks = sorted((project_root / "notebooks").glob("*.ipynb"))
    for notebook_path in notebooks:
        errors.extend(validate_notebook(notebook_path))

    figures = sorted((project_root / "artifacts" / "figures").glob("*.png"))
    if len(figures) < 8:
        errors.append(f"Expected at least 8 figures, found {len(figures)}")
    for figure in figures:
        errors.extend(validate_image(figure))

    try:
        json.loads(
            (project_root / "power_bi" / "theme.json").read_text(encoding="utf-8")
        )
    except Exception as error:
        errors.append(f"Power BI theme JSON is invalid: {error}")

    dax = (project_root / "power_bi" / "measures.dax").read_text(encoding="utf-8")
    for measure in (
        "Net Sales",
        "Net Profit",
        "Session Conversion Rate",
        "Cart Abandonment Rate",
        "Observed Return Rate",
    ):
        if f"[{measure}]" not in dax:
            errors.append(f"Missing required DAX measure: {measure}")

    gitignore = (project_root / ".gitignore").read_text(encoding="utf-8")
    if "private_review/" not in gitignore:
        errors.append("private_review/ is not excluded from Git")

    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "raw_tables_checked": raw_tables_checked,
        "session_lineage": session_lineage,
        "figures_checked": len(figures),
        "notebooks_checked": len(notebooks),
    }
    output_path = project_root / "artifacts" / "validation_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    private_path = project_root / "private_review" / "validation_report.md"
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_text(
        "# Validation report\n\n"
        f"Overall status: **{report['status']}**\n\n"
        "## Errors\n\n"
        + ("\n".join(f"- {item}" for item in errors) if errors else "- None")
        + "\n\n## Warnings\n\n"
        + ("\n".join(f"- {item}" for item in warnings) if warnings else "- None")
        + "\n\n## Source-lineage checks\n\n"
        + f"- Original raw tables: {', '.join(raw_tables_checked)}\n"
        + f"- Source events: {session_lineage.get('source_events', 0):,}\n"
        + f"- Distinct event sessions: {session_lineage.get('source_sessions', 0):,}\n"
        + f"- Modeled fact sessions: {session_lineage.get('fact_sessions', 0):,}\n"
        + f"- Reconciled modeled events: {session_lineage.get('modeled_session_events', 0):,}\n"
        + f"\nFigures checked: {len(figures)}. Notebooks checked: {len(notebooks)}.\n",
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("\n".join(errors))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.project_root.resolve())


if __name__ == "__main__":
    main()
