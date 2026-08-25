from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline import run as run_pipeline


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv-dir", type=Path, required=True)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    source_csv_dir = args.source_csv_dir.resolve()
    python = sys.executable

    steps: list[dict[str, str]] = []
    started = datetime.now(timezone.utc)
    run_pipeline(project_root, source_csv_dir, args.rebuild)
    steps.append({"step": "warehouse_pipeline", "status": "completed"})

    for script in (
        "advanced_analytics.py",
        "render_outputs.py",
        "build_notebooks.py",
    ):
        run_command(
            [
                python,
                str(project_root / "src" / script),
                "--project-root",
                str(project_root),
            ],
            project_root,
        )
        steps.append({"step": script, "status": "completed"})

    for notebook in (
        "notebooks/01_data_quality_and_core_analysis.ipynb",
        "notebooks/02_statistical_deep_dives.ipynb",
        "notebooks/03_event_sessionization_audit.ipynb",
    ):
        run_command(
            [
                python,
                "-m",
                "jupyter",
                "nbconvert",
                "--execute",
                "--to",
                "notebook",
                "--inplace",
                "--ExecutePreprocessor.timeout=600",
                notebook,
            ],
            project_root,
        )
        steps.append({"step": f"execute:{notebook}", "status": "completed"})

    run_command(
        [
            python,
            str(project_root / "src" / "validate_project.py"),
            "--project-root",
            str(project_root),
        ],
        project_root,
    )
    steps.append({"step": "validate_project", "status": "completed"})

    finished = datetime.now(timezone.utc)
    execution = {
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "elapsed_seconds": (finished - started).total_seconds(),
        "source_csv_dir": str(source_csv_dir),
        "project_root": str(project_root),
        "steps": steps,
    }
    log_path = project_root / "private_review" / "execution_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(execution, indent=2), encoding="utf-8")
    print(json.dumps(execution, indent=2))


if __name__ == "__main__":
    main()
