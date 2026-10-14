"""Generate docs/code_map.md - an index of every object to the file that builds it.

Parsed from the files themselves on every run, so it cannot drift from the code.
Answers the question "which file owns this number" without opening anything.

Run:
    python src/build_code_map.py --project-root .
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

CREATE = re.compile(
    r"^CREATE\s+(?:OR\s+REPLACE\s+)?(TABLE|VIEW)\s+([A-Za-z_][\w.]*)\s+AS", re.IGNORECASE
)

SQL_PURPOSE = {
    "00_raw_quality.sql": "Source quality gate - runs before any model exists",
    "01_staging.sql": "Typing and renaming only, one view per source table",
    "02_core_dimensions.sql": "Conformed dimensions, where the country master is applied",
    "03_core_facts.sql": "Transactional grain, where gross/net/profit are defined",
    "04_mart_acquisition_funnel.sql": "Acquisition, funnel and channel marts",
    "05_mart_revenue_customer.sql": "Revenue, product, geography and customer marts",
    "06_mart_operations_inventory.sql": "Operations, delivery and inventory marts",
    "07_quality_and_snapshots.sql": "Warehouse quality gate + the executive snapshot",
    "08_commercial_planning.sql": "The second source: harmonisation, FX, plan vs actual, PVM",
    "09_quality_commercial.sql": "Commercial quality gate + the reconciliation statement",
}

# Work that is scoped but not delivered. Listed separately at the end rather than
# mixed into the index, so the map shows what the project presents.
NEXT_STEP_MODULES: set[str] = set()
NEXT_STEP_FUNCTIONS = {
    "return_propensity_model", "market_basket",
    "experiment_power_plan", "hypothesis_tests",
}

ROUTES = [
    ("A number in the dashboard looks wrong", "`docs/kpi_dictionary.md`, then the mart below that owns it"),
    ("How is net sales defined", "`sql/duckdb/03_core_facts.sql` - `core.fact_order_item`"),
    ("How do you handle the country spellings", "`seeds/country_master.csv` + `sql/duckdb/02_core_dimensions.sql`"),
    ("Show me the plan-versus-actual logic", "`sql/duckdb/08_commercial_planning.sql` - `mart.plan_vs_actual_monthly`"),
    ("How does the price-volume-mix bridge work", "`sql/duckdb/08_commercial_planning.sql` - `mart.price_volume_mix`"),
    ("What stops a bad build", "`src/pipeline.py` - `assert_no_blocking_failures()`"),
    ("What exactly do you check", "`00_raw_quality.sql`, `07_quality_and_snapshots.sql`, `09_quality_commercial.sql`"),
    ("Which rows got rejected and why", "`sql/duckdb/08_commercial_planning.sql` - `qa.plan_rejects`"),
    ("Prove nothing was lost between layers", "`sql/duckdb/09_quality_commercial.sql` - `qa.reconciliation_statement`"),
    ("Where does the segmentation come from", "`src/advanced_analytics.py` - `rfm_segmentation()`"),
    ("How was the forecast model chosen", "`src/forecasting.py` - `backtest()`, and `docs/forecast_review.md`"),
    ("How do I rebuild this", "`docs/how_to_run.md`, then `src/run_all.py`"),
]


def scan_sql(sql_dir: Path) -> list[tuple[str, str, str, int, int]]:
    """(schema, object, file, line, statement_lines) for every created object."""
    found: list[tuple[str, str, str, int, int]] = []
    for path in sorted(sql_dir.glob("*.sql")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            match = CREATE.match(line.strip())
            if not match:
                continue
            name = match.group(2)
            schema = name.split(".")[0] if "." in name else "main"
            length = 1
            for row in lines[index:]:
                if row.rstrip().endswith(";"):
                    break
                length += 1
            found.append((schema, name, path.name, index + 1, length))
    return found


def scan_python(src_dir: Path) -> list[tuple[str, str, int, list[str]]]:
    """(file, one-line purpose, line count, public function names)."""
    out: list[tuple[str, str, int, list[str]]] = []
    for path in sorted(src_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        doc = ast.get_docstring(tree) or ""
        purpose = doc.strip().splitlines()[0] if doc.strip() else "-"
        functions = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
            and node.name not in {"main"}
            and node.name not in NEXT_STEP_FUNCTIONS
            and node.name not in {"build_forecast", "forecast_vs_plan", "backtest_accuracy"}
        ]
        out.append((path.name, purpose, len(text.splitlines()), functions))
    return out


SCHEMA_ORDER = {"qa": 4, "stg": 1, "core": 2, "mart": 3}


def render(project_root: Path) -> str:
    objects = scan_sql(project_root / "sql" / "duckdb")
    modules = scan_python(project_root / "src")

    lines: list[str] = []
    add = lines.append

    add("# Code map")
    add("")
    add("Every object in the warehouse, and the file and line that builds it. Generated")
    add("from the files themselves by `src/build_code_map.py` on every run, so it cannot")
    add("drift from the code.")
    add("")
    add("---")
    add("")
    add("## If you are looking for one thing")
    add("")
    add("| Question | Open |")
    add("|---|---|")
    for question, answer in ROUTES:
        add(f"| {question} | {answer} |")
    add("")
    add("---")
    add("")
    add("## The SQL build, in run order")
    add("")
    add("`src/pipeline.py` globs `sql/duckdb/*.sql` and runs them in name order. The")
    add("numbering is the dependency order, not a filing convention.")
    add("")
    add("| # | File | Builds | Objects |")
    add("|---|---|---|---|")
    counts: dict[str, int] = {}
    for _, _, filename, _, _ in objects:
        counts[filename] = counts.get(filename, 0) + 1
    for filename, purpose in SQL_PURPOSE.items():
        add(f"| {filename[:2]} | `{filename}` | {purpose} | {counts.get(filename, 0)} |")
    add("")
    add("---")
    add("")
    add("## Every warehouse object")
    add("")
    add("`lines` is the length of the statement, so you can see at a glance which objects")
    add("carry real logic and which are a straight projection.")
    add("")

    for schema in sorted({o[0] for o in objects}, key=lambda s: SCHEMA_ORDER.get(s, 9)):
        rows = [o for o in objects if o[0] == schema]
        add(f"### `{schema}` - {len(rows)} objects")
        add("")
        add("| Object | File | Line | Lines |")
        add("|---|---|---|---|")
        for _, name, filename, line, length in sorted(rows, key=lambda r: r[1]):
            add(f"| `{name}` | `sql/duckdb/{filename}` | {line} | {length} |")
        add("")

    add("---")
    add("")
    add("## The Python modules")
    add("")
    add("| File | Lines | Does |")
    add("|---|---|---|")
    for filename, purpose, length, _ in modules:
        if filename in NEXT_STEP_MODULES:
            continue
        add(f"| `src/{filename}` | {length} | {purpose} |")
    add("")
    add("### Public functions worth knowing")
    add("")
    add("| File | Functions |")
    add("|---|---|")
    for filename, _, _, functions in modules:
        if filename in NEXT_STEP_MODULES:
            continue
        if functions:
            shown = ", ".join(f"`{f}()`" for f in functions[:8])
            add(f"| `src/{filename}` | {shown} |")
    add("")
    add("---")
    add("")
    add("## Scoped but not delivered")
    add("")
    add("Present in the repository, listed in the walkthrough under Next steps, and")
    add("deliberately absent from the index above, the dashboard and the management pack.")
    add("No result from any of it is presented as a finding.")
    add("")
    add("| Where | What |")
    add("|---|---|")
    add("| `src/advanced_analytics.py` | `return_propensity_model()`, `market_basket()`, `experiment_power_plan()`, `hypothesis_tests()` |")
    add("")
    add("---")
    add("")
    add("## Reading any of it without leaving a notebook")
    add("")
    add("```python")
    add('import sys; sys.path.insert(0, "../src")')
    add("from explore import open_warehouse")
    add("")
    add("w = open_warehouse()")
    add('w.source("mart.price_volume_mix")        # the full statement, from the file')
    add('w.source("core.fact_order_item", 40)    # the first 40 lines of it')
    add('w.owns("qa.plan_rejects")               # just the file and line')
    add("```")
    add("")
    return "\n".join(lines) + "\n"


def run(project_root: Path) -> Path:
    out = project_root / "docs" / "code_map.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(project_root), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    path = run(args.project_root.resolve())
    print(f"{path.relative_to(args.project_root.resolve())}")


if __name__ == "__main__":
    main()
