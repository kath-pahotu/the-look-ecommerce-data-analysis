from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def run(project_root: Path) -> dict[str, object]:
    errors: list[str] = []

    database_path = project_root / "artifacts" / "thelook_analytics.duckdb"
    if not database_path.exists():
        errors.append("Missing DuckDB warehouse")
    else:
        connection = duckdb.connect(str(database_path), read_only=True)
        try:
            raw_blocking = connection.execute(
                "SELECT COUNT(*) FROM qa.raw_test_results WHERE status = 'FAIL'"
            ).fetchone()[0]
            if raw_blocking:
                errors.append(f"{raw_blocking} blocking source-level tests failed")

            blocking = connection.execute(
                "SELECT COUNT(*) FROM qa.test_results WHERE status = 'FAIL'"
            ).fetchone()[0]
            if blocking:
                errors.append(f"{blocking} blocking data-quality tests failed")

            commercial_blocking = connection.execute(
                "SELECT COUNT(*) FROM qa.plan_validation WHERE status = 'FAIL'"
            ).fetchone()[0]
            if commercial_blocking:
                errors.append(
                    f"{commercial_blocking} blocking commercial-layer tests failed"
                )
        finally:
            connection.close()

    for relative in (
        "README.md",
        "docs/analysis_and_findings.md",
        "docs/technical_reference.md",
        "docs/commercial_analytics.md",
        "seeds/country_master.csv",
        "data/planning/regional_plan_submissions.csv",
    ):
        if not (project_root / relative).exists():
            errors.append(f"Missing required file: {relative}")

    report = {"status": "PASS" if not errors else "FAIL", "errors": errors}
    output_path = project_root / "artifacts" / "validation_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

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
