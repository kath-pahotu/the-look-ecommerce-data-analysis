from __future__ import annotations

import argparse
import subprocess
import sys
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

    run_pipeline(project_root, source_csv_dir, args.rebuild)

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

    run_command(
        [
            python,
            str(project_root / "src" / "validate_project.py"),
            "--project-root",
            str(project_root),
        ],
        project_root,
    )


if __name__ == "__main__":
    main()
