from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SOURCE_TABLES = [
    "users",
    "products",
    "orders",
    "order_items",
    "events",
    "inventory_events",
    "distribution_centers",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        next(reader)
        return sum(1 for _ in reader)


def csv_columns(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return next(csv.reader(stream))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv-dir", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()

    inventory = []
    for table in SOURCE_TABLES:
        path = args.source_csv_dir / f"{table}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required source: {path}")
        inventory.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "rows": csv_row_count(path),
                "columns": csv_columns(path),
                "sha256": sha256(path),
            }
        )

    output = args.project_root / "artifacts" / "source_profile.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    for item in inventory:
        print(f"{item['file']:<28} {item['rows']:>10,} rows")


if __name__ == "__main__":
    main()