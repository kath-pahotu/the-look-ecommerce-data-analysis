from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SOURCE_FILES = {
    "users.csv",
    "products.csv",
    "orders.csv",
    "order_items.csv",
    "events.csv",
    "inventory_events.csv",
    "distribution_centers.csv",
}


class ProjectContractTests(unittest.TestCase):
    def test_private_review_is_gitignored(self):
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("private_review/", gitignore)

    def test_power_bi_theme_is_valid_json(self):
        theme = json.loads(
            (PROJECT_ROOT / "power_bi" / "theme.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("name", theme)
        self.assertIn("dataColors", theme)

    def test_sql_modules_are_numbered(self):
        modules = sorted((PROJECT_ROOT / "sql" / "duckdb").glob("*.sql"))
        self.assertGreaterEqual(len(modules), 7)
        self.assertTrue(all(path.name[:2].isdigit() for path in modules))

    def test_pipeline_uses_only_original_source_files(self):
        pipeline = (
            PROJECT_ROOT / "src" / "pipeline.py"
        ).read_text(encoding="utf-8")
        for source_file in ORIGINAL_SOURCE_FILES:
            self.assertIn(source_file.removesuffix(".csv"), pipeline)
        self.assertNotIn('"dim_sessions"', pipeline)

    def test_implementation_has_no_legacy_session_source_dependency(self):
        implementation_files = list((PROJECT_ROOT / "src").glob("*.py"))
        implementation_files += list(
            (PROJECT_ROOT / "sql").rglob("*.sql")
        )
        for path in implementation_files:
            content = path.read_text(encoding="utf-8").lower()
            self.assertNotIn(
                "raw.dim_sessions", content, f"found in {path}"
            )
            self.assertNotIn(
                "dim_sessions.csv", content, f"found in {path}"
            )

    def test_sessionization_is_event_derived(self):
        staging_sql = (
            PROJECT_ROOT / "sql" / "duckdb" / "01_staging.sql"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("create or replace view stg.sessions", staging_sql)
        self.assertIn("from stg.events", staging_sql)
        self.assertIn("group by session_id", staging_sql)

    def test_navigation_entrypoint_exists(self):
        start = PROJECT_ROOT / "00_START_HERE.md"
        walkthrough = PROJECT_ROOT / "docs" / "01_PROJECT_WALKTHROUGH.md"
        self.assertTrue(start.exists())
        self.assertTrue(walkthrough.exists())


if __name__ == "__main__":
    unittest.main()
