"""Interactive exploration helpers for the DuckDB warehouse. Read-only.

This module is NOT part of the pipeline and nothing depends on it. It is the
workbench used *before* writing a join, a quality check or a reconciliation
step: what tables exist, what columns they hold, how many nulls, whether a key
is unique at the grain you assumed, and whether two keys actually overlap.

Every connection is opened read-only, so an exploratory session cannot alter
the warehouse the reports depend on.

Usage, from a notebook or a plain Python session:

    import sys; sys.path.insert(0, "../src")
    from explore import open_warehouse

    w = open_warehouse()
    w.tables("mart")
    w.cols("core.fact_order_item")
    w.peek("stg.plan_submissions", 10)
    w.grain("core.fact_plan", "canonical_country", "plan_month")
    w.overlap("stg.plan_submissions", "canonical_country",
              "core.dim_market", "canonical_country")
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

DEFAULT_DB = "artifacts/thelook_analytics.duckdb"


def _quote(identifier: str) -> str:
    """Quote one identifier part so a reserved word or odd name still works."""
    return '"' + identifier.replace('"', '""') + '"'


def _split(table: str) -> tuple[str, str]:
    """Split 'schema.table' into its parts. Defaults to the main schema."""
    if "." in table:
        schema, name = table.split(".", 1)
        return schema, name
    return "main", table


class Warehouse:
    """A read-only handle on the warehouse, with the inspection verbs."""

    def __init__(self, path: Path, root: Path | None = None):
        self.path = path
        self.root = root or path.parents[1]
        self.db = duckdb.connect(str(path), read_only=True)

    # ------------------------------------------------------------ basics
    def q(self, sql: str) -> pd.DataFrame:
        """Run any SQL and return a DataFrame."""
        return self.db.execute(sql).fetchdf()

    def close(self) -> None:
        self.db.close()

    # ------------------------------------------------- what exists here
    def tables(self, schema: str | None = None) -> pd.DataFrame:
        """Every table and view, with an estimated row count."""
        where = f"WHERE schema_name = '{schema}'" if schema else ""
        tables = self.q(
            f"""
            SELECT schema_name AS schema, table_name AS name,
                   'table' AS kind, estimated_size AS rows
            FROM duckdb_tables() {where}
            """
        )
        where_v = f"WHERE schema_name = '{schema}'" if schema else ""
        views = self.q(
            f"""
            SELECT schema_name AS schema, view_name AS name,
                   'view' AS kind, NULL::BIGINT AS rows
            FROM duckdb_views() {where_v}
              AND schema_name NOT IN ('information_schema', 'pg_catalog')
            """
            if where_v
            else """
            SELECT schema_name AS schema, view_name AS name,
                   'view' AS kind, NULL::BIGINT AS rows
            FROM duckdb_views()
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
            """
        )
        both = pd.concat([tables, views], ignore_index=True)
        return both.sort_values(["schema", "kind", "name"]).reset_index(drop=True)

    def find(self, pattern: str) -> pd.DataFrame:
        """Every column anywhere in the warehouse whose name matches `pattern`.

        Use this when you know the concept but not where it lives -
        w.find("country") finds every country column in every layer.
        """
        return self.q(
            f"""
            SELECT schema_name AS schema, table_name AS "table",
                   column_name AS column, data_type AS type
            FROM duckdb_columns()
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
              AND lower(column_name) LIKE lower('%{pattern}%')
            ORDER BY schema, "table", "column"
            """
        )

    # ------------------------------------------------ what is in a table
    def cols(self, table: str) -> pd.DataFrame:
        """Column profile: type, nulls, distinct values, and one example.

        This is the call to make before writing any join. `distinct` against
        `rows` tells you the grain; `nulls` tells you whether a LEFT JOIN is
        going to quietly produce NULLs you did not plan for.
        """
        schema, name = _split(table)
        info = self.q(
            f"""
            SELECT column_name AS column, data_type AS type
            FROM duckdb_columns()
            WHERE schema_name = '{schema}' AND table_name = '{name}'
            ORDER BY column_index
            """
        )
        if info.empty:
            raise ValueError(f"{table} has no columns - check the name")

        rows = int(self.q(f"SELECT COUNT(*) AS n FROM {table}").n.iloc[0])
        pieces = []
        for column in info.column:
            c = _quote(column)
            pieces.append(
                f"COUNT(*) - COUNT({c}) AS {_quote(column + '::nulls')}, "
                f"COUNT(DISTINCT {c}) AS {_quote(column + '::distinct')}, "
                f"MIN(CAST({c} AS VARCHAR)) AS {_quote(column + '::example')}"
            )
        stats = self.q(f"SELECT {', '.join(pieces)} FROM {table}").iloc[0]

        info["rows"] = rows
        info["nulls"] = [int(stats[f"{c}::nulls"]) for c in info.column]
        info["null_pct"] = (info.nulls / rows if rows else 0).round(4)
        info["distinct"] = [int(stats[f"{c}::distinct"]) for c in info.column]
        info["example"] = [stats[f"{c}::example"] for c in info.column]
        return info

    def peek(self, table: str, n: int = 10, where: str | None = None) -> pd.DataFrame:
        """The first `n` rows, optionally filtered."""
        clause = f"WHERE {where}" if where else ""
        return self.q(f"SELECT * FROM {table} {clause} LIMIT {n}")

    def values(self, table: str, column: str, n: int = 20) -> pd.DataFrame:
        """Value counts for one column - the fastest way to spot a defect."""
        c = _quote(column)
        return self.q(
            f"""
            SELECT {c} AS value, COUNT(*) AS rows,
                   ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (), 4) AS share
            FROM {table} GROUP BY 1 ORDER BY rows DESC LIMIT {n}
            """
        )

    # ------------------------------------------------- reading the real code
    def owns(self, obj: str) -> pd.DataFrame:
        """Which SQL file builds `obj`, and at what line."""
        for path in sorted((self.root / "sql" / "duckdb").glob("*.sql")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                for kind in ("TABLE", "VIEW"):
                    if line.strip().upper().startswith(
                        f"CREATE OR REPLACE {kind} {obj.upper()} AS"
                    ):
                        length = 1
                        for row in lines[index:]:
                            if row.rstrip().endswith(";"):
                                break
                            length += 1
                        return pd.DataFrame(
                            [{
                                "object": obj,
                                "file": f"sql/duckdb/{path.name}",
                                "line": index + 1,
                                "statement_lines": length,
                            }]
                        )
        return pd.DataFrame([{"object": obj, "file": "not built by a SQL module",
                              "line": None, "statement_lines": None}])

    def source(self, obj: str, lines: int | None = None) -> None:
        """Print the production SQL that builds `obj`, straight from the file.

        Nothing is copied or cached - change the SQL file and this changes with
        it. Use this when someone asks to see the logic behind a number.
        """
        for path in sorted((self.root / "sql" / "duckdb").glob("*.sql")):
            body = path.read_text(encoding="utf-8")
            for kind in ("TABLE", "VIEW"):
                marker = f"CREATE OR REPLACE {kind} {obj} AS"
                if marker not in body:
                    continue
                statement = []
                for row in body[body.index(marker):].splitlines():
                    statement.append(row)
                    if row.rstrip().endswith(";"):
                        break
                shown = statement if lines is None else statement[:lines]
                print(f"--- sql/duckdb/{path.name} - {len(statement)} lines " + "-" * 22)
                print("\n".join(shown))
                if lines is not None and len(statement) > lines:
                    print(f"... {len(statement) - lines} more lines, in the file")
                return
        print(f"{obj} is not built by a SQL module.")

    def source_py(self, filename: str, func: str, lines: int | None = None) -> None:
        """Print one function from a production file in src/."""
        rows = (self.root / "src" / filename).read_text(encoding="utf-8").splitlines()
        start = next(i for i, r in enumerate(rows) if r.startswith(f"def {func}("))
        end = start + 1
        while end < len(rows) and not rows[end].startswith(("def ", "class ", "@")):
            end += 1
        block = rows[start:end]
        while block and not block[-1].strip():
            block.pop()
        shown = block if lines is None else block[:lines]
        print(f"--- src/{filename} - def {func} - {len(block)} lines " + "-" * 16)
        print("\n".join(shown))
        if lines is not None and len(block) > lines:
            print(f"... {len(block) - lines} more lines, in the file")

    # -------------------------------------------- the three real questions
    def grain(self, table: str, *keys: str) -> pd.DataFrame:
        """Is `table` unique at (`keys`)? Answer before you join on them.

        A duplicate grain is the defect that multiplies rows through every
        downstream join, and it never announces itself - the total just gets
        bigger.
        """
        if not keys:
            raise ValueError("name at least one key column")
        key_list = ", ".join(_quote(k) for k in keys)
        return self.q(
            f"""
            SELECT '{table}' AS "table", '{", ".join(keys)}' AS keys,
                   COUNT(*) AS rows,
                   COUNT(DISTINCT ({key_list})) AS distinct_keys,
                   COUNT(*) - COUNT(DISTINCT ({key_list})) AS duplicates,
                   CASE WHEN COUNT(*) = COUNT(DISTINCT ({key_list}))
                        THEN 'unique at this grain'
                        ELSE 'NOT unique - a join on these keys will multiply rows'
                   END AS verdict
            FROM {table}
            """
        )

    def duplicates(self, table: str, *keys: str, n: int = 20) -> pd.DataFrame:
        """The actual offending rows when `grain()` says NOT unique."""
        key_list = ", ".join(_quote(k) for k in keys)
        return self.q(
            f"""
            SELECT {key_list}, COUNT(*) AS rows
            FROM {table} GROUP BY {key_list}
            HAVING COUNT(*) > 1 ORDER BY rows DESC LIMIT {n}
            """
        )

    def overlap(
        self, left: str, left_key: str, right: str, right_key: str, n: int = 10
    ) -> dict[str, pd.DataFrame]:
        """Do two keys actually match? The anti-join, both directions.

        Returns a summary plus the unmatched values on each side. Run this
        before every join: a LEFT JOIN that silently matches nothing still
        returns rows, just with NULLs where the measures should be.
        """
        lk, rk = _quote(left_key), _quote(right_key)
        summary = self.q(
            f"""
            WITH l AS (SELECT DISTINCT {lk} AS k FROM {left} WHERE {lk} IS NOT NULL),
                 r AS (SELECT DISTINCT {rk} AS k FROM {right} WHERE {rk} IS NOT NULL)
            SELECT (SELECT COUNT(*) FROM l) AS left_distinct,
                   (SELECT COUNT(*) FROM r) AS right_distinct,
                   (SELECT COUNT(*) FROM l JOIN r USING (k)) AS matched,
                   (SELECT COUNT(*) FROM l LEFT JOIN r USING (k)
                    WHERE r.k IS NULL) AS left_only,
                   (SELECT COUNT(*) FROM r LEFT JOIN l USING (k)
                    WHERE l.k IS NULL) AS right_only
            """
        )
        left_only = self.q(
            f"""
            SELECT DISTINCT {lk} AS unmatched_in_left FROM {left}
            WHERE {lk} IS NOT NULL
              AND {lk} NOT IN (SELECT {rk} FROM {right} WHERE {rk} IS NOT NULL)
            ORDER BY 1 LIMIT {n}
            """
        )
        right_only = self.q(
            f"""
            SELECT DISTINCT {rk} AS unmatched_in_right FROM {right}
            WHERE {rk} IS NOT NULL
              AND {rk} NOT IN (SELECT {lk} FROM {left} WHERE {lk} IS NOT NULL)
            ORDER BY 1 LIMIT {n}
            """
        )
        return {"summary": summary, "left_only": left_only, "right_only": right_only}

    def tie(self, label: str, left_sql: str, right_sql: str) -> pd.DataFrame:
        """One reconciliation line: does this total survive the next layer?

        Each argument is a SQL expression returning exactly one number, e.g.
            w.tie("gross sales",
                  "SELECT SUM(sale_price) FROM stg.order_items",
                  "SELECT SUM(gross_sales_value) FROM core.fact_order_item")
        """
        left = float(self.db.execute(left_sql).fetchone()[0] or 0)
        right = float(self.db.execute(right_sql).fetchone()[0] or 0)
        delta = right - left
        return pd.DataFrame(
            [
                {
                    "check": label,
                    "left": round(left, 2),
                    "right": round(right, 2),
                    "delta": round(delta, 2),
                    "verdict": "ties" if abs(delta) < 0.01 else "DOES NOT TIE",
                }
            ]
        )


def open_warehouse(project_root: Path | str | None = None) -> Warehouse:
    """Open the warehouse read-only from anywhere in the project."""
    if project_root is None:
        here = Path.cwd()
        project_root = here.parent if here.name in {"notebooks", "src"} else here
    path = Path(project_root) / DEFAULT_DB
    if not path.exists():
        raise FileNotFoundError(
            f"No warehouse at {path}. Run src/run_all.py first - see docs/how_to_run.md."
        )
    return Warehouse(path, Path(project_root))
