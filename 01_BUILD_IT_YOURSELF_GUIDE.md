# Build TheLook DA/BI project yourself

This is an execution manual, not just a description. Follow the stages in order.
Commands assume PowerShell on Windows and that your terminal is open in:

```text
C:\Users\phanh\data_analysis\p_projects\the_look_ecommerce\practice_analysis
```

The source folder is:

```text
C:\Users\phanh\data_analysis\p_projects\the_look_ecommerce\original_analysis\5_the_look_ecommerce\csv_version\3_thelookecommerce
```

If your source location differs, change only the configuration/command argument. Do
not hard-code it inside SQL.

---

# Stage 0 — frame the business before touching data

## Purpose

A DA/BI project is not “make charts from all columns.” It is a controlled path from
a business decision to a trusted metric. Before SQL, define:

- the decision or question;
- the entity being counted;
- the time grain;
- the numerator and denominator;
- the exclusions;
- the output that will support the decision.

## Tool

Markdown in VS Code.

## Input

The challenge topics and the seven-table source list.

## Action

Create `docs/business_questions.md` and organize the project into four connected
business themes:

1. Acquisition, onsite behavior, funnel, and cart abandonment.
2. Revenue, profit, product, geography, and customer value.
3. Operations, delivery lead time, returns, and inventory.
4. Advanced decision support: segmentation, prediction, product association, and
   experiment design.

For each question, use this template:

```markdown
## Which traffic sources create valuable customers?

- Decision: where should marketing focus?
- Unit of analysis: traffic source.
- Population: sessions for behavior; registered customers/orders for value.
- Time grain: total and month.
- KPIs: sessions, purchase sessions, conversion rate, net sales per customer.
- Dimensions: traffic source, month, browser, country.
- Caveat: event traffic source and user acquisition source are different concepts.
- Output: channel-quality mart and acquisition-value mart.
```

This prevents a common error: treating two similarly named fields as one concept.
`events.traffic_source` describes the source attached to a browsing session.
`users.traffic_source` describes the registered user’s acquisition source. They
support related but different questions.

## Declare grains

Create a table in `docs/data_dictionary.md`:

| Planned table | Grain |
|---|---|
| `core.dim_customer` | one row per `user_id` |
| `core.dim_product` | one row per `product_id` |
| `core.fact_order` | one row per `order_id` |
| `core.fact_order_item` | one row per `order_item_id` |
| `core.fact_session` | one row per event-derived `session_id` |
| `core.fact_inventory` | one row per `inventory_item_id` |
| `mart.sales_monthly` | one row per month |
| `mart.channel_quality` | one row per event traffic source |

**Why grain matters:** if one order has three items, joining `orders` to
`order_items` produces three rows. `COUNT(order_id)` becomes 3, but
`COUNT(DISTINCT order_id)` remains 1. Most BI errors are grain errors disguised as
calculation errors.

## Completion gate

Do not continue until every planned fact and mart has a one-sentence grain.

---

# Stage 1 — create the public project structure

## Purpose

The folders separate human-written source code, generated outputs, documentation,
and BI assets. This makes the project reproducible and prevents generated data from
being confused with source code.

## Tool

PowerShell.

## Action and code

Run this from the practice root:

```powershell
$folders = @(
    "data",
    "data\processed\analysis",
    "data\processed\advanced",
    "data\processed\power_bi\csv",
    "data\processed\power_bi\parquet",
    "artifacts",
    "artifacts\figures",
    "docs",
    "logs",
    "notebooks",
    "outputs\qa",
    "power_bi",
    "sql\duckdb",
    "src",
    "tests"
)

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
}
```

### What the code elements mean

- `$folders = @(...)` creates a PowerShell array.
- `foreach` repeats the same directory-creation action for every element.
- `-Force` makes the command idempotent: rerunning it does not fail because the
  folder already exists.
- `Out-Null` hides unhelpful command output.

Create `data/README.md`:

```markdown
# Data policy

The original seven CSV files remain outside this project and are never edited.
`data/processed/` contains pipeline-generated exports and is excluded from Git.
The DuckDB warehouse is generated in `artifacts/` and is also excluded from Git.
```

## Create `.gitignore`

```gitignore
# Original and generated data
data/raw/
data/processed/
*.duckdb
*.duckdb.wal
*.parquet

# Generated artifacts, QA output, and logs
artifacts/
logs/
outputs/

# Power BI local/binary files
*.pbix
*.pbit

# Local configuration and secrets
.env
config.local.json

# Python and Jupyter
.venv/
__pycache__/
*.py[cod]
.ipynb_checkpoints/
```

The practice project has no private-review folder. If you later add personal notes,
add that folder to `.gitignore` before writing anything private.

## Completion gate

Run:

```powershell
Get-ChildItem -Force
```

Confirm that code/document folders are visible and generated folders are empty.

---

# Stage 2 — create a reproducible Python environment

## Purpose

Your project should use the same package versions tomorrow or on another computer.
A virtual environment keeps project packages separate from system Python.

## Tool

Python and PowerShell.

## Action

Create `requirements.txt`:

```text
duckdb==1.5.5
pandas>=2.2
numpy>=2.0
scikit-learn>=1.5
scipy>=1.13
matplotlib>=3.9
seaborn>=0.13
jupyter>=1.1
nbformat>=5.10
nbclient>=0.10
Pillow>=10.0
```

Then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify:

```powershell
python -c "import duckdb, pandas, sklearn; print(duckdb.__version__)"
```

### What each major package is for

| Package | Role |
|---|---|
| DuckDB | Local analytical database and SQL engine |
| pandas | Table manipulation and model inputs in Python |
| NumPy | Numerical arrays and calculations |
| scikit-learn | Clustering and predictive modeling |
| SciPy | Statistical tests |
| Matplotlib/Seaborn | Static analytical figures |
| Jupyter | Executable analysis narrative |
| nbformat/nbclient | Programmatic notebook creation/execution |
| Pillow | Image validation |

## DuckDB in plain language

DuckDB is like a compact analytics warehouse stored in one local file. You use SQL
against millions of rows without running a database server.

Example:

```python
import duckdb

connection = duckdb.connect("artifacts/practice_analytics.duckdb")
result = connection.execute(
    "SELECT COUNT(*) AS event_rows FROM raw.events"
).fetchone()
print(result[0])
connection.close()
```

- `connect(...)` opens or creates the database file.
- `execute(...)` runs SQL inside it.
- `fetchone()` retrieves one result row into Python.
- Closing the connection flushes and releases the file.

Think of the `.duckdb` file as a local warehouse, not as an Excel workbook. Tables,
views, schemas, joins, aggregations, and window functions all live inside it.

## Completion gate

The verification command prints a DuckDB version and no import error.

---

# Stage 3 — establish the source contract and profile the seven CSVs

## Purpose

Before transforming data, prove which files arrived, their size, fingerprint, row
count, columns, and obvious risks. This is **source inventory** and
**source-preserving ingestion**.

Source-preserving does not mean “never cast anything anywhere.” It means:

- the original files remain unchanged;
- the raw layer contains no business cleaning or derived calculations;
- cleaning happens downstream in staging;
- the project records file fingerprints and row counts.

If a later result changes, the fingerprint tells you whether the source changed.

## Tool

Python standard library and DuckDB.

## Input

The seven original CSV files.

## Create `config.example.json`

```json
{
  "source_csv_dir": "../original_analysis/5_the_look_ecommerce/csv_version/3_thelookecommerce",
  "duckdb_path": "artifacts/practice_analytics.duckdb",
  "power_bi_export_format": ["csv", "parquet"],
  "complete_period_rule": "Exclude the maximum source month from period comparisons when it is incomplete."
}
```

This file documents expected settings and is safe to commit. If you create
`config.local.json` with machine-specific values, Git ignores it.

## Create `src/profile_sources.py`

```python
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
```

Run:

```powershell
python src\profile_sources.py `
  --project-root . `
  --source-csv-dir "C:\Users\phanh\data_analysis\p_projects\the_look_ecommerce\original_analysis\5_the_look_ecommerce\csv_version\3_thelookecommerce"
```

### Code explanation

- `SOURCE_TABLES` is an explicit contract. An unexpected legacy CSV is not silently
  treated as a source.
- `Path` creates safe path objects instead of manually concatenating slashes.
- SHA-256 reads the file in chunks so a large event file is not loaded into memory.
- `next(reader)` skips the header before counting records.
- `raise FileNotFoundError` stops early. A missing source is a blocking condition.
- The JSON artifact is machine-readable provenance. It is generated, so it stays out
  of Git; summarize its stable schema in `docs/source_inventory.md`.

## Privacy inspection

Open only headers and a few rows. Identify direct identifiers such as:

- first and last name;
- email;
- street address;
- IP address.

These may exist in the raw source for lineage, but you will not select them into
`stg.users`, core dimensions, marts, or Power BI exports. This is data minimization:
the dashboard receives only fields needed for analysis.

## Completion gate

You see exactly seven files in the profile, and no `dim_sessions.csv`.

---

# Stage 4 — ingest the raw layer and orchestrate SQL modules

## Purpose

Load the seven files into a database without mixing ingestion with cleaning.

Raw answers: “What arrived?”

Staging answers: “How should it be interpreted?”

Keeping those questions separate lets you compare a cleaned value with its source.

## Tool

Python and DuckDB.

## Create `src/pipeline.py`

This is a complete learning version. Type it, run it, and then improve it.

```python
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import duckdb


SOURCE_TABLES = [
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


def sql_literal(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sources(csv_dir: Path) -> list[dict[str, object]]:
    inventory = []
    for table in SOURCE_TABLES:
        path = csv_dir / f"{table}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required source: {path}")
        inventory.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": fingerprint(path),
            }
        )
    return inventory


def ingest_raw(
    connection: duckdb.DuckDBPyConnection,
    csv_dir: Path,
) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table in SOURCE_TABLES:
        path = csv_dir / f"{table}.csv"
        print(f"Loading raw.{table}")
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
    connection: duckdb.DuckDBPyConnection,
    sql_dir: Path,
) -> list[dict[str, object]]:
    runs = []
    for path in sorted(sql_dir.glob("*.sql")):
        started = time.perf_counter()
        print(f"Executing {path.name}")
        connection.execute(path.read_text(encoding="utf-8"))
        runs.append(
            {
                "module": path.name,
                "seconds": round(time.perf_counter() - started, 3),
            }
        )
    return runs


def export_table(
    connection: duckdb.DuckDBPyConnection,
    project_root: Path,
    schema: str,
    table: str,
) -> dict[str, object]:
    export_root = project_root / "data" / "processed" / "power_bi"
    csv_path = export_root / "csv" / f"{table}.csv"
    parquet_path = export_root / "parquet" / f"{table}.parquet"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    connection.execute(
        f"COPY (SELECT * FROM {schema}.{table}) "
        f"TO '{sql_literal(csv_path)}' (HEADER, DELIMITER ',')"
    )
    connection.execute(
        f"COPY (SELECT * FROM {schema}.{table}) "
        f"TO '{sql_literal(parquet_path)}' "
        "(FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    rows = connection.execute(
        f"SELECT COUNT(*) FROM {schema}.{table}"
    ).fetchone()[0]
    return {"schema": schema, "table": table, "rows": int(rows)}


def run(project_root: Path, csv_dir: Path) -> dict[str, object]:
    database_path = project_root / "artifacts" / "practice_analytics.duckdb"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    inventory = validate_sources(csv_dir)
    connection = duckdb.connect(str(database_path))
    started = time.perf_counter()
    try:
        connection.execute("SET threads = 4")
        connection.execute("SET preserve_insertion_order = false")
        ingest_raw(connection, csv_dir)
        module_runs = execute_sql_modules(
            connection,
            project_root / "sql" / "duckdb",
        )

        qa_dir = project_root / "outputs" / "qa"
        qa_dir.mkdir(parents=True, exist_ok=True)
        connection.execute(
            f"COPY qa.test_results TO "
            f"'{sql_literal(qa_dir / 'test_results.csv')}' "
            "(HEADER, DELIMITER ',')"
        )
        connection.execute(
            f"COPY qa.metric_reconciliation TO "
            f"'{sql_literal(qa_dir / 'metric_reconciliation.csv')}' "
            "(HEADER, DELIMITER ',')"
        )

        exports = [
            export_table(connection, project_root, schema, table)
            for schema, table in POWER_BI_TABLES
        ]
        raw_counts = {
            table: int(
                connection.execute(
                    f"SELECT COUNT(*) FROM raw.{table}"
                ).fetchone()[0]
            )
            for table in SOURCE_TABLES
        }
    finally:
        connection.close()

    metadata = {
        "database_path": str(database_path),
        "source_csv_dir": str(csv_dir.resolve()),
        "source_inventory": inventory,
        "raw_row_counts": raw_counts,
        "sql_modules": module_runs,
        "exports": exports,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "session_source": "events.csv grouped by session_id",
        "legacy_dim_sessions_required": False,
    }
    metadata_path = project_root / "artifacts" / "pipeline_run.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--source-csv-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        args.project_root.resolve(),
        args.source_csv_dir.resolve(),
    )
    print(json.dumps(result["raw_row_counts"], indent=2))


if __name__ == "__main__":
    main()
```

### Important elements

- `SOURCE_TABLES` is a whitelist. The pipeline cannot accidentally ingest the legacy
  session file.
- Schemas (`raw`, `stg`, `core`, `mart`, `qa`) are namespaces inside one database.
- `CREATE OR REPLACE` makes a development rebuild repeatable.
- `read_csv_auto(... sample_size=-1)` examines the complete file when inferring
  types. No business cleaning occurs in raw.
- `sorted(sql_dir.glob("*.sql"))` makes filename numbers control execution order.
- `COPY` exports query results directly from DuckDB.
- Parquet is typed, compressed, and faster than CSV for large BI tables. CSV remains
  useful because it is universally inspectable.
- `pipeline_run.json` records provenance: input fingerprints, row counts, modules,
  exports, and elapsed time.

### Strict text-preserving variant

If you need every raw value stored as text, add `all_varchar = true` inside
`read_csv_auto`. Then every type conversion must occur in staging. The finished
project uses full-file type inference; both approaches are defensible when the raw
policy is documented and fingerprints are retained.

Do not run the full pipeline yet: the SQL modules do not exist. First build them.

---

# Stage 5 — create staging views and derive sessions from events

## Purpose

Staging gives raw fields reliable names and types, standardizes text, handles blanks,
and removes direct PII from downstream use. A view stores SQL logic without copying
the data again.

## Tool

DuckDB SQL.

## Create `sql/duckdb/01_staging.sql`

Start with one source and test it:

```sql
CREATE SCHEMA IF NOT EXISTS stg;

CREATE OR REPLACE VIEW stg.users AS
SELECT
    CAST(id AS BIGINT) AS user_id,
    TRY_CAST(age AS INTEGER) AS age,
    UPPER(TRIM(CAST(gender AS VARCHAR))) AS gender,
    NULLIF(TRIM(CAST(state AS VARCHAR)), '') AS state,
    NULLIF(TRIM(CAST(postal_code AS VARCHAR)), '') AS postal_code,
    NULLIF(TRIM(CAST(city AS VARCHAR)), '') AS city,
    NULLIF(TRIM(CAST(country AS VARCHAR)), '') AS country,
    TRY_CAST(latitude AS DOUBLE) AS latitude,
    TRY_CAST(longitude AS DOUBLE) AS longitude,
    COALESCE(
        NULLIF(TRIM(CAST(traffic_source AS VARCHAR)), ''),
        'Unknown'
    ) AS acquisition_source,
    CAST(created_at AS TIMESTAMP) AS registered_at
FROM raw.users;
```

Notice what is deliberately absent: name, email, street address, and IP address.

### SQL element explanations

- `CAST` converts a value and fails if conversion is impossible.
- `TRY_CAST` returns `NULL` instead of crashing on an invalid value. Use QA to count
  those nulls; do not silently forget them.
- `TRIM` removes leading and trailing whitespace.
- `NULLIF(value, '')` changes an empty string to SQL `NULL`.
- `COALESCE(value, 'Unknown')` supplies an analytical category for missing text.
- `AS user_id` applies a consistent business name.

Add the remaining source views using the same pattern. The critical event and session
logic is:

```sql
CREATE OR REPLACE VIEW stg.events AS
SELECT
    CAST(id AS BIGINT) AS event_id,
    TRY_CAST(user_id AS BIGINT) AS user_id,
    CAST(sequence_number AS INTEGER) AS sequence_number,
    NULLIF(TRIM(CAST(session_id AS VARCHAR)), '') AS session_id,
    CAST(created_at AS TIMESTAMP) AS created_at,
    NULLIF(TRIM(CAST(city AS VARCHAR)), '') AS city,
    NULLIF(TRIM(CAST(state AS VARCHAR)), '') AS state,
    NULLIF(TRIM(CAST(postal_code AS VARCHAR)), '') AS postal_code,
    COALESCE(
        NULLIF(TRIM(CAST(browser AS VARCHAR)), ''),
        'Unknown'
    ) AS browser,
    COALESCE(
        NULLIF(TRIM(CAST(traffic_source AS VARCHAR)), ''),
        'Unknown'
    ) AS traffic_source,
    CAST(uri AS VARCHAR) AS uri,
    LOWER(TRIM(CAST(event_type AS VARCHAR))) AS event_type
FROM raw.events;

-- This is derived from events. It is not an original source table.
CREATE OR REPLACE VIEW stg.sessions AS
SELECT
    session_id,
    MAX(user_id) AS user_id,
    COUNT(*)::INTEGER AS event_count,
    COUNT(user_id)::INTEGER AS events_with_user_id,
    COUNT(user_id)::DOUBLE / NULLIF(COUNT(*), 0)
        AS event_identity_coverage_rate,
    MIN(created_at) AS session_start_at,
    MAX(created_at) AS session_end_at,
    arg_min(city, sequence_number) AS city,
    arg_min(state, sequence_number) AS state,
    arg_min(postal_code, sequence_number) AS postal_code,
    arg_min(browser, sequence_number) AS browser,
    arg_min(traffic_source, sequence_number) AS traffic_source,
    arg_min(event_type, sequence_number) AS first_event_type,
    arg_max(event_type, sequence_number) AS final_event_type,
    MAX(CASE WHEN event_type = 'home' THEN 1 ELSE 0 END) AS home_flag,
    MAX(CASE WHEN event_type = 'department' THEN 1 ELSE 0 END)
        AS department_flag,
    MAX(CASE WHEN event_type = 'product' THEN 1 ELSE 0 END)
        AS product_view_flag,
    MAX(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) AS cart_flag,
    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END)
        AS purchase_flag,
    MAX(CASE WHEN event_type = 'cancel' THEN 1 ELSE 0 END)
        AS cancel_event_flag
FROM stg.events
WHERE session_id IS NOT NULL
GROUP BY session_id;
```

### Sessionization example

Input events:

| session_id | sequence | event_type |
|---|---:|---|
| A | 1 | home |
| A | 2 | product |
| A | 3 | cart |
| B | 1 | product |
| B | 2 | purchase |

Output sessions:

| session_id | event_count | product_view_flag | cart_flag | purchase_flag |
|---|---:|---:|---:|---:|
| A | 3 | 1 | 1 | 0 |
| B | 2 | 1 | 0 | 1 |

`MAX(CASE WHEN ... THEN 1 ELSE 0 END)` asks: “Did this event happen at least once
inside the session?” `arg_min` takes the attribute attached to the smallest sequence
number; it is more intentional than an arbitrary `MIN(browser)`.

Add these remaining staging views:

- `stg.products`
- `stg.orders`
- `stg.order_items`
- `stg.inventory_events`
- `stg.distribution_centers`

Use the final module only after attempting them:
[complete staging answer key](<../new_analysis/sql/duckdb/01_staging.sql>).

## Run only this checkpoint

Create a temporary `src/checkpoint.py`:

```python
from pathlib import Path
import duckdb

from pipeline import ingest_raw

project_root = Path(__file__).resolve().parents[1]
source_dir = Path(
    r"C:\Users\phanh\data_analysis\p_projects\the_look_ecommerce"
    r"\original_analysis\5_the_look_ecommerce\csv_version"
    r"\3_thelookecommerce"
)
database = project_root / "artifacts" / "practice_analytics.duckdb"
connection = duckdb.connect(str(database))
ingest_raw(connection, source_dir)
connection.execute(
    (project_root / "sql" / "duckdb" / "01_staging.sql")
    .read_text(encoding="utf-8")
)

print(
    connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM stg.events) AS events,
            (SELECT COUNT(*) FROM stg.sessions) AS sessions,
            (SELECT SUM(event_count) FROM stg.sessions) AS reconciled_events
        """
    ).fetchdf()
)
connection.close()
```

Run:

```powershell
python src\checkpoint.py
```

Delete `src/checkpoint.py` after the checkpoint; it is a learning scratchpad, not the
final orchestrator.

## Completion gate

```sql
SELECT
    (SELECT COUNT(*) FROM stg.events) AS source_events,
    (SELECT COUNT(DISTINCT session_id) FROM stg.events) AS distinct_sessions,
    (SELECT COUNT(*) FROM stg.sessions) AS derived_sessions,
    (SELECT SUM(event_count) FROM stg.sessions) AS modeled_events;
```

Both session counts must match. Both event counts must match. A zero difference proves
that sessionization neither lost nor duplicated events.

---

# Stage 6 — create reusable dimensions

## Purpose

A dimension describes a business entity used to filter or group facts. A fact records
an event, transaction, or state at a declared grain.

Example:

- `dim_product`: category, brand, department, price band.
- `fact_order_item`: sale value, cost, margin, return flag.

Joining them lets you calculate margin by category without repeating product
attributes on every report query.

## Tool

DuckDB SQL.

## Create `sql/duckdb/02_core_dimensions.sql`

Begin:

```sql
CREATE SCHEMA IF NOT EXISTS core;

CREATE OR REPLACE TABLE core.dim_customer AS
SELECT
    user_id,
    age,
    CASE
        WHEN age IS NULL THEN 'Unknown'
        WHEN age < 25 THEN '18-24'
        WHEN age < 35 THEN '25-34'
        WHEN age < 45 THEN '35-44'
        WHEN age < 55 THEN '45-54'
        WHEN age < 65 THEN '55-64'
        ELSE '65+'
    END AS age_band,
    gender,
    COALESCE(country, 'Unknown') AS country,
    COALESCE(state, 'Unknown') AS state,
    COALESCE(city, 'Unknown') AS city,
    postal_code,
    latitude,
    longitude,
    acquisition_source,
    registered_at,
    CAST(strftime(registered_at, '%Y%m%d') AS INTEGER)
        AS registered_date_key
FROM stg.users;

CREATE OR REPLACE TABLE core.dim_product AS
SELECT
    product_id,
    category,
    product_name,
    brand,
    department,
    sku,
    distribution_center_id,
    unit_cost,
    retail_price,
    retail_price - unit_cost AS unit_margin,
    CASE
        WHEN retail_price > 0
        THEN (retail_price - unit_cost) / retail_price
    END AS unit_margin_rate,
    CASE
        WHEN retail_price < 25 THEN 'Under $25'
        WHEN retail_price < 50 THEN '$25-$49'
        WHEN retail_price < 100 THEN '$50-$99'
        WHEN retail_price < 200 THEN '$100-$199'
        ELSE '$200+'
    END AS price_band
FROM stg.products;

CREATE OR REPLACE TABLE core.dim_distribution_center AS
SELECT *
FROM stg.distribution_centers;

CREATE OR REPLACE TABLE core.dim_session_traffic_source AS
SELECT
    ROW_NUMBER() OVER (ORDER BY traffic_source)::INTEGER
        AS session_traffic_source_key,
    traffic_source
FROM (
    SELECT DISTINCT traffic_source
    FROM stg.sessions
);

CREATE OR REPLACE TABLE core.dim_acquisition_source AS
SELECT
    ROW_NUMBER() OVER (ORDER BY acquisition_source)::INTEGER
        AS acquisition_source_key,
    acquisition_source
FROM (
    SELECT DISTINCT acquisition_source
    FROM stg.users
);
```

Build `core.dim_date` from the minimum and maximum relevant timestamps. Do not use an
arbitrary date range. It needs:

- `date_key` in `YYYYMMDD` integer form;
- calendar date, year, quarter, month, week, day;
- month/quarter/year start dates;
- weekend flag;
- complete-month flag.

The complete date query is in the
[dimension answer key](<../new_analysis/sql/duckdb/02_core_dimensions.sql>).
Read it only after attempting `generate_series(min_date, max_date, INTERVAL 1 DAY)`.

## Why materialize dimensions as tables

Staging views are lightweight cleaning logic. Core tables are reusable modeled
outputs. Materializing them:

- provides stable column types;
- avoids repeating complex logic;
- gives Power BI a clear import surface;
- allows row-count and uniqueness tests.

## Completion gate

```sql
SELECT 'customer' AS entity, COUNT(*) AS rows,
       COUNT(DISTINCT user_id) AS unique_keys
FROM core.dim_customer
UNION ALL
SELECT 'product', COUNT(*), COUNT(DISTINCT product_id)
FROM core.dim_product
UNION ALL
SELECT 'distribution_center', COUNT(*),
       COUNT(DISTINCT distribution_center_id)
FROM core.dim_distribution_center;
```

For every dimension, `rows = unique_keys`.

Check privacy:

```sql
DESCRIBE core.dim_customer;
```

No direct name, email, address, or IP field should appear.

---

# Stage 7 — create facts at controlled grains

## Purpose

Facts are the analytical backbone. Put additive values and event flags at the lowest
useful grain, then aggregate them into marts and measures.

## Create `sql/duckdb/03_core_facts.sql`

## 7.1 Order-item fact

```sql
CREATE OR REPLACE TABLE core.fact_order_item AS
SELECT
    i.order_item_id,
    i.order_id,
    i.user_id AS customer_id,
    i.product_id,
    i.inventory_item_id,
    p.distribution_center_id,
    c.acquisition_source,
    i.item_status,
    i.created_at AS order_item_created_at,
    i.shipped_at,
    i.delivered_at,
    i.returned_at,
    CAST(strftime(i.created_at, '%Y%m%d') AS INTEGER) AS order_date_key,
    i.sale_price,
    p.unit_cost,
    i.sale_price - p.unit_cost AS gross_margin_value,
    CASE
        WHEN i.sale_price > 0
        THEN (i.sale_price - p.unit_cost) / i.sale_price
    END AS gross_margin_rate,
    i.sale_price AS gross_sales_value,
    CASE WHEN i.item_status = 'Cancelled'
         THEN i.sale_price ELSE 0 END AS cancelled_value,
    CASE WHEN i.item_status = 'Returned'
         THEN i.sale_price ELSE 0 END AS returned_value,
    CASE WHEN i.item_status NOT IN ('Cancelled', 'Returned')
         THEN i.sale_price ELSE 0 END AS net_sales_value,
    CASE WHEN i.item_status NOT IN ('Cancelled', 'Returned')
         THEN i.sale_price - p.unit_cost ELSE 0 END AS net_profit_value,
    CASE WHEN i.item_status = 'Cancelled' THEN 1 ELSE 0 END
        AS cancelled_item_flag,
    CASE WHEN i.item_status = 'Returned' THEN 1 ELSE 0 END
        AS returned_item_flag,
    CASE WHEN i.item_status IN ('Complete', 'Returned') THEN 1 ELSE 0 END
        AS return_observation_eligible_flag,
    CASE WHEN i.shipped_at >= i.created_at
         THEN datediff('minute', i.created_at, i.shipped_at) / 1440.0
    END AS ship_lead_days,
    CASE WHEN i.delivered_at >= i.shipped_at
         THEN datediff('minute', i.shipped_at, i.delivered_at) / 1440.0
    END AS delivery_lead_days,
    CASE WHEN i.delivered_at >= i.created_at
         THEN datediff('minute', i.created_at, i.delivered_at) / 1440.0
    END AS end_to_end_lead_days,
    CASE
        WHEN i.shipped_at IS NOT NULL
             AND i.shipped_at < i.created_at THEN 0
        WHEN i.delivered_at IS NOT NULL
             AND (i.shipped_at IS NULL OR i.delivered_at < i.shipped_at) THEN 0
        WHEN i.returned_at IS NOT NULL
             AND (i.delivered_at IS NULL OR i.returned_at < i.delivered_at) THEN 0
        ELSE 1
    END AS valid_timeline_flag
FROM stg.order_items AS i
JOIN core.dim_product AS p
  ON i.product_id = p.product_id
JOIN core.dim_customer AS c
  ON i.user_id = c.user_id;
```

### Why these columns exist

- Store components (`sale_price`, `unit_cost`) and additive values
  (`net_sales_value`, `net_profit_value`).
- Do not aggregate `gross_margin_rate` with `AVG` for the company margin. Correct
  margin is `SUM(net_profit_value) / SUM(net_sales_value)`, a weighted ratio.
- The return denominator is not every item. `return_observation_eligible_flag`
  represents items with an observable final state.
- Negative timeline intervals become `NULL`, while `valid_timeline_flag` preserves
  the anomaly for QA. Never convert impossible lead times to positive values.

## 7.2 Session fact

```sql
CREATE OR REPLACE TABLE core.fact_session AS
SELECT
    s.session_id,
    s.user_id AS customer_id,
    s.session_start_at,
    s.session_end_at,
    CAST(strftime(s.session_start_at, '%Y%m%d') AS INTEGER)
        AS session_date_key,
    s.browser,
    s.traffic_source,
    COALESCE(c.country, 'Unknown') AS country,
    s.event_count,
    s.events_with_user_id,
    s.event_identity_coverage_rate,
    CASE WHEN s.events_with_user_id > 0 THEN 1 ELSE 0 END
        AS identified_session_flag,
    CASE
        WHEN s.session_end_at >= s.session_start_at
        THEN datediff('second', s.session_start_at, s.session_end_at)
    END AS session_duration_seconds,
    s.first_event_type,
    s.final_event_type,
    s.home_flag,
    s.department_flag,
    s.product_view_flag,
    s.cart_flag,
    s.purchase_flag,
    s.cancel_event_flag,
    CASE WHEN s.cart_flag = 1 AND s.purchase_flag = 0
         THEN 1 ELSE 0 END AS cart_abandoned_flag,
    CASE WHEN s.product_view_flag = 1
              AND s.cart_flag = 0
              AND s.purchase_flag = 0
         THEN 1 ELSE 0 END AS early_product_exit_flag,
    CASE
        WHEN s.purchase_flag = 1 THEN 'Purchase'
        WHEN s.cart_flag = 1 THEN 'Cart'
        WHEN s.product_view_flag = 1 THEN 'Product'
        WHEN s.department_flag = 1 THEN 'Department'
        ELSE 'Home'
    END AS highest_stage
FROM stg.sessions AS s
LEFT JOIN core.dim_customer AS c
  ON s.user_id = c.user_id;
```

## 7.3 Complete the other facts

Build:

- `core.fact_order`: order grain, order status, four timestamps, lead times, timeline
  validity, cancelled/returned/completed flags.
- `core.fact_inventory`: inventory-unit grain, created/sold timestamps, sold flag,
  days to sell, unsold age, age bucket.

Use the event maximum date as the inventory “as of” date so unsold age is relative to
the dataset, not today. Otherwise the same historic data changes every time you run
the project.

After attempting both, compare with the
[fact answer key](<../new_analysis/sql/duckdb/03_core_facts.sql>).

## Completion gate

```sql
SELECT 'orders' AS fact, COUNT(*) AS rows FROM core.fact_order
UNION ALL
SELECT 'order_items', COUNT(*) FROM core.fact_order_item
UNION ALL
SELECT 'sessions', COUNT(*) FROM core.fact_session
UNION ALL
SELECT 'inventory', COUNT(*) FROM core.fact_inventory;
```

Then test joins:

```sql
SELECT COUNT(*) AS orphan_order_items
FROM core.fact_order_item AS f
LEFT JOIN core.dim_product AS p
  ON f.product_id = p.product_id
WHERE p.product_id IS NULL;
```

The orphan count should be zero.

---

# Stage 8 — build business marts

## Purpose

A mart is a question-ready table at a convenient grain. It avoids forcing Power BI to
rebuild complex business rules repeatedly.

Examples:

- Fact: one row per order item.
- Mart: one row per month with sales and profit.
- Dashboard: a line chart using the monthly mart.

Marts should not replace facts. Facts support flexible drill-down; marts support
stable, fast, governed questions.

## Mart design checklist

Before writing SQL, document:

- business question;
- output grain;
- source fact(s);
- dimensions used;
- measures and denominators;
- minimum sample threshold;
- completeness rules.

## 8.1 Funnel marts

Create `sql/duckdb/04_mart_acquisition_funnel.sql`.

```sql
CREATE SCHEMA IF NOT EXISTS mart;

CREATE OR REPLACE TABLE mart.channel_quality AS
SELECT
    traffic_source,
    COUNT(*) AS sessions,
    COUNT(DISTINCT customer_id) AS users,
    SUM(cart_flag) AS cart_sessions,
    SUM(purchase_flag) AS purchase_sessions,
    SUM(cart_abandoned_flag) AS abandoned_cart_sessions,
    AVG(event_count) AS avg_events_per_session,
    AVG(event_identity_coverage_rate)
        AS avg_event_identity_coverage_rate,
    SUM(purchase_flag)::DOUBLE / NULLIF(COUNT(*), 0)
        AS session_conversion_rate,
    SUM(cart_abandoned_flag)::DOUBLE / NULLIF(SUM(cart_flag), 0)
        AS cart_abandonment_rate
FROM core.fact_session
GROUP BY traffic_source;
```

Why the abandonment denominator is `SUM(cart_flag)`: only sessions that reached the
cart were able to abandon it. Dividing by all sessions answers a different question.

Build these additional marts:

| Mart | Grain | Main use |
|---|---|---|
| `funnel_stage_channel` | traffic source × funnel stage | funnel visual |
| `funnel_monthly_channel` | month × traffic source | trend and seasonality |
| `cart_abandonment_segments` | segment type × segment value | risk pockets |
| `acquisition_source_value` | user acquisition source | customer/order value |

The complete module is the
[funnel answer key](<../new_analysis/sql/duckdb/04_mart_acquisition_funnel.sql>).

## 8.2 Commercial and customer marts

Create `sql/duckdb/05_mart_commercial_customer.sql`.

```sql
CREATE OR REPLACE TABLE mart.sales_monthly AS
SELECT
    d.month_start,
    d.year,
    d.month_number,
    MAX(d.is_complete_month) AS is_complete_month,
    COUNT(DISTINCT f.order_id) AS orders,
    COUNT(DISTINCT f.customer_id) AS customers,
    COUNT(*) AS items,
    SUM(f.gross_sales_value) AS gross_sales_value,
    SUM(f.cancelled_value) AS cancelled_value,
    SUM(f.returned_value) AS returned_value,
    SUM(f.net_sales_value) AS net_sales_value,
    SUM(f.net_profit_value) AS net_profit_value,
    SUM(f.net_profit_value) / NULLIF(SUM(f.net_sales_value), 0)
        AS net_margin_rate,
    SUM(f.net_sales_value) / NULLIF(COUNT(DISTINCT f.order_id), 0)
        AS average_order_value,
    COUNT(*)::DOUBLE / NULLIF(COUNT(DISTINCT f.order_id), 0)
        AS items_per_order,
    SUM(f.cancelled_item_flag)::DOUBLE / COUNT(*)
        AS item_cancellation_rate,
    SUM(f.returned_item_flag)::DOUBLE / COUNT(*)
        AS item_return_rate
FROM core.fact_order_item AS f
JOIN core.dim_date AS d
  ON f.order_date_key = d.date_key
GROUP BY d.month_start, d.year, d.month_number;
```

Build:

| Mart | Grain | Important rule |
|---|---|---|
| `product_performance_category` | department × category | weighted margin and eligible return denominator |
| `product_performance_brand` | brand | avoid ranking tiny brands without sample context |
| `geography_performance_country` | country | compare sales, AOV, return rate |
| `customer_360` | customer | recency, frequency, monetary value, repeat flag |
| `cohort_retention` | cohort month × months since first order | distinct active customers |

The complete module is the
[commercial answer key](<../new_analysis/sql/duckdb/05_mart_commercial_customer.sql>).

## 8.3 Operations and inventory marts

Create `sql/duckdb/06_mart_operations_inventory.sql`.

For lead time, report the median and P90 as well as the average:

```sql
CREATE OR REPLACE TABLE mart.operations_monthly AS
SELECT
    d.month_start,
    COUNT(*) AS items,
    SUM(f.valid_timeline_flag) AS valid_timeline_items,
    AVG(f.ship_lead_days) AS avg_ship_lead_days,
    median(f.ship_lead_days) AS median_ship_lead_days,
    quantile_cont(f.ship_lead_days, 0.90) AS p90_ship_lead_days,
    AVG(f.delivery_lead_days) AS avg_delivery_lead_days,
    median(f.delivery_lead_days) AS median_delivery_lead_days,
    quantile_cont(f.delivery_lead_days, 0.90)
        AS p90_delivery_lead_days,
    AVG(f.end_to_end_lead_days) AS avg_end_to_end_lead_days,
    median(f.end_to_end_lead_days) AS median_end_to_end_lead_days,
    quantile_cont(f.end_to_end_lead_days, 0.90)
        AS p90_end_to_end_lead_days,
    SUM(f.returned_item_flag)::DOUBLE
        / NULLIF(SUM(f.return_observation_eligible_flag), 0)
        AS observed_return_rate,
    SUM(f.cancelled_item_flag)::DOUBLE / COUNT(*)
        AS cancellation_rate
FROM core.fact_order_item AS f
JOIN core.dim_date AS d
  ON f.order_date_key = d.date_key
GROUP BY d.month_start;
```

Why P90 matters: if median delivery is 3 days and P90 is 12 days, the average alone
hides a long tail that affects customer experience.

Build:

| Mart | Grain | Main use |
|---|---|---|
| `delivery_performance_dc` | distribution center | compare lead-time stages |
| `return_risk_segments` | segment type × value | locate high-return groups |
| `inventory_performance` | department × category × center | sell-through and aging |

The complete module is the
[operations answer key](<../new_analysis/sql/duckdb/06_mart_operations_inventory.sql>).

## Completion gate

For each mart, run:

```sql
SELECT COUNT(*) FROM mart.sales_monthly;
SELECT * FROM mart.sales_monthly ORDER BY month_start DESC LIMIT 5;
DESCRIBE mart.sales_monthly;
```

Write the grain above the query in the SQL file as a comment. Confirm the key columns
are unique at that grain.

---

# Stage 9 — QA, warnings, and metric reconciliation

## Purpose

QA asks whether individual rules hold. Reconciliation proves that totals remain equal
across layers.

Examples:

- QA: no duplicate product keys.
- QA: every order item has a product.
- Reconciliation: raw item rows equal fact item rows.
- Reconciliation: sum of session event counts equals source event rows.
- Reconciliation: gross sales before and after modeling are equal.

## Severity model

| Severity/status | Meaning | Action |
|---|---|---|
| Critical failure | Model cannot be trusted | Stop publishing |
| High blocking failure | Important metric invalid | Stop affected output |
| Warning | Known anomaly with controlled handling | Continue and disclose |
| Info | Coverage/completeness observation | Document |

Warnings are not “tests that do not matter.” They are known limitations with a
documented decision.

## Create `sql/duckdb/07_quality_and_snapshots.sql`

Use one common output shape:

```sql
CREATE SCHEMA IF NOT EXISTS qa;

CREATE OR REPLACE TABLE qa.test_results AS
WITH checks AS (
    SELECT
        'users_primary_key_unique' AS check_name,
        'raw' AS layer,
        'CRITICAL' AS severity,
        COUNT(*)::BIGINT AS failure_count,
        (SELECT COUNT(*) FROM raw.users)::BIGINT AS denominator,
        1 AS blocking,
        'users.id must be unique' AS notes
    FROM (
        SELECT id
        FROM raw.users
        GROUP BY id
        HAVING COUNT(*) > 1
    )

    UNION ALL

    SELECT
        'order_items_have_product',
        'stg',
        'CRITICAL',
        COUNT(*),
        (SELECT COUNT(*) FROM stg.order_items),
        1,
        'Every order item must match a product'
    FROM stg.order_items AS i
    LEFT JOIN stg.products AS p
      ON i.product_id = p.product_id
    WHERE p.product_id IS NULL

    UNION ALL

    SELECT
        'session_event_count_reconciles',
        'core',
        'CRITICAL',
        ABS(
            (SELECT COUNT(*) FROM stg.events)
            - (SELECT SUM(event_count) FROM core.fact_session)
        ),
        (SELECT COUNT(*) FROM stg.events),
        1,
        'Summed session event counts must equal source event rows'

    UNION ALL

    SELECT
        'shipping_not_before_item_created',
        'core',
        'HIGH',
        COUNT(*),
        (SELECT COUNT(*) FROM core.fact_order_item),
        0,
        'Exclude invalid source timelines from lead-time metrics'
    FROM core.fact_order_item
    WHERE shipped_at < order_item_created_at
)
SELECT
    *,
    CASE
        WHEN failure_count = 0 THEN 'PASS'
        WHEN blocking = 1 THEN 'FAIL'
        ELSE 'WARN'
    END AS status,
    failure_count::DOUBLE / NULLIF(denominator, 0) AS failure_rate
FROM checks;
```

Add checks for:

- primary-key uniqueness for all natural keys;
- nonblank event session IDs;
- one derived row per session ID;
- consistent session attributes;
- order-to-user, item-to-order, item-to-product referential integrity;
- nonnegative prices and cost not above retail;
- timestamp sequence;
- missing event user ID coverage;
- incomplete maximum month.

Create reconciliation:

```sql
CREATE OR REPLACE TABLE qa.metric_reconciliation AS
SELECT
    'orders_rows' AS metric_name,
    (SELECT COUNT(*)::DOUBLE FROM stg.orders) AS source_value,
    (SELECT COUNT(*)::DOUBLE FROM core.fact_order) AS modeled_value,
    source_value - modeled_value AS variance

UNION ALL

SELECT
    'order_items_rows',
    (SELECT COUNT(*)::DOUBLE FROM stg.order_items),
    (SELECT COUNT(*)::DOUBLE FROM core.fact_order_item),
    source_value - modeled_value

UNION ALL

SELECT
    'sessions_from_events_rows',
    (SELECT COUNT(DISTINCT session_id)::DOUBLE FROM stg.events),
    (SELECT COUNT(*)::DOUBLE FROM core.fact_session),
    source_value - modeled_value

UNION ALL

SELECT
    'events_into_sessions_rows',
    (SELECT COUNT(*)::DOUBLE FROM stg.events),
    (SELECT SUM(event_count)::DOUBLE FROM core.fact_session),
    source_value - modeled_value

UNION ALL

SELECT
    'gross_sales_value',
    (SELECT SUM(sale_price)::DOUBLE FROM stg.order_items),
    (SELECT SUM(gross_sales_value)::DOUBLE FROM core.fact_order_item),
    source_value - modeled_value;
```

Use the complete
[QA answer key](<../new_analysis/sql/duckdb/07_quality_and_snapshots.sql>)
only after writing your own checklist.

## Run the warehouse

Now all seven SQL modules exist. Run:

```powershell
python src\pipeline.py `
  --project-root . `
  --source-csv-dir "C:\Users\phanh\data_analysis\p_projects\the_look_ecommerce\original_analysis\5_the_look_ecommerce\csv_version\3_thelookecommerce"
```

Inspect:

```powershell
Import-Csv outputs\qa\test_results.csv |
  Format-Table check_name, status, failure_count, denominator

Import-Csv outputs\qa\metric_reconciliation.csv |
  Format-Table
```

## Completion gate

- No blocking `FAIL`.
- Every reconciliation variance is zero.
- Every `WARN` has a written handling rule in
  `docs/assumptions_and_limitations.md`.

---

# Stage 10 — export for Power BI

## Purpose

Power BI should load modeled, documented, privacy-safe tables—not raw operational
files. The pipeline exports approved tables as both CSV and Parquet.

## Why both formats

| Format | Strength | Weakness |
|---|---|---|
| CSV | Easy to open and exchange | Larger, slower, weak typing |
| Parquet | Compressed, typed, columnar, faster | Not human-readable in a text editor |

For Power BI, prefer Parquet for large facts and CSV for quick inspection. Do not
import both versions of the same table.

## Validate exports

```powershell
Get-ChildItem data\processed\power_bi\csv -File |
  Select-Object Name, Length

Get-ChildItem data\processed\power_bi\parquet -File |
  Select-Object Name, Length
```

Open the header of `dim_customer.csv` and confirm no direct PII:

```powershell
Get-Content data\processed\power_bi\csv\dim_customer.csv -TotalCount 1
```

## Output contract

Keep the export list explicit in `POWER_BI_TABLES`. Do not export every database
table automatically. An allowlist protects privacy, prevents accidental experimental
tables, and makes schema changes visible in code review.

---

# Stage 11 — build the Power BI semantic model

## Purpose

SQL prepares trusted entities and metrics. Power BI provides interactive filter
context, relationships, measures, visuals, and drill-through.

## Input

`data/processed/power_bi/parquet/` or the CSV equivalent.

## Tool and actions

1. Open Power BI Desktop.
2. Select **Get data → Parquet** for each approved table. If your version makes
   multi-file selection awkward, use **Folder** and filter by filename, or load CSV.
3. In Power Query:
   - verify date/timestamp/number types;
   - rename queries to the table names;
   - disable load for helper queries;
   - do not reimplement SQL business logic;
   - close and apply.
4. In Model view, create one-to-many relationships from dimensions to facts.
5. Set cross-filter direction to **Single** unless a tested design requires otherwise.
6. Mark `dim_date[calendar_date]` as the date table.
7. Hide technical foreign keys from Report view.
8. Create measures in a dedicated measure table.

## Core relationships

| From (one) | To (many) | Key |
|---|---|---|
| `dim_date` | `fact_order_item` | `date_key → order_date_key` |
| `dim_date` | `fact_order` | `date_key → order_date_key` |
| `dim_date` | `fact_session` | `date_key → session_date_key` |
| `dim_customer` | `fact_order_item` | `user_id → customer_id` |
| `dim_customer` | `fact_order` | `user_id → customer_id` |
| `dim_customer` | `fact_session` | `user_id → customer_id` |
| `dim_product` | `fact_order_item` | `product_id → product_id` |
| `dim_product` | `fact_inventory` | `product_id → product_id` |
| `dim_distribution_center` | `fact_order_item` | `distribution_center_id` |
| `dim_distribution_center` | `fact_inventory` | `distribution_center_id` |

Do not connect every mart to every dimension merely because columns share a name.
Some marts can remain disconnected report tables, or be connected only where their
grain and key are unambiguous.

## Create `power_bi/measures.dax`

```dax
Gross Sales =
SUM ( fact_order_item[gross_sales_value] )

Net Sales =
SUM ( fact_order_item[net_sales_value] )

Net Profit =
SUM ( fact_order_item[net_profit_value] )

Net Margin % =
DIVIDE ( [Net Profit], [Net Sales] )

Orders =
DISTINCTCOUNT ( fact_order_item[order_id] )

Customers =
DISTINCTCOUNT ( fact_order_item[customer_id] )

Items =
COUNTROWS ( fact_order_item )

Average Order Value =
DIVIDE ( [Net Sales], [Orders] )

Sessions =
COUNTROWS ( fact_session )

Purchase Sessions =
SUM ( fact_session[purchase_flag] )

Session Conversion Rate =
DIVIDE ( [Purchase Sessions], [Sessions] )

Cart Sessions =
SUM ( fact_session[cart_flag] )

Abandoned Cart Sessions =
SUM ( fact_session[cart_abandoned_flag] )

Cart Abandonment Rate =
DIVIDE ( [Abandoned Cart Sessions], [Cart Sessions] )

Returned Items =
SUM ( fact_order_item[returned_item_flag] )

Return-Eligible Items =
SUM ( fact_order_item[return_observation_eligible_flag] )

Observed Return Rate =
DIVIDE ( [Returned Items], [Return-Eligible Items] )

Valid-Timeline Items =
CALCULATE (
    COUNTROWS ( fact_order_item ),
    fact_order_item[valid_timeline_flag] = 1
)

Average Ship Lead Days =
CALCULATE (
    AVERAGE ( fact_order_item[ship_lead_days] ),
    fact_order_item[valid_timeline_flag] = 1
)

Net Sales Previous Month =
CALCULATE (
    [Net Sales],
    DATEADD ( dim_date[calendar_date], -1, MONTH )
)

Net Sales MoM % =
DIVIDE (
    [Net Sales] - [Net Sales Previous Month],
    [Net Sales Previous Month]
)
```

### Why measures instead of calculated columns

A measure recalculates under the current filter context. If the user selects France
and 2023, `[Net Sales]` calculates only those rows. A calculated column is fixed at
data refresh time and occupies memory on every row.

`DIVIDE(a, b)` safely handles zero/blank denominators. Do not use `/` for KPI ratios
unless you explicitly handle zero.

## Dashboard pages

Create `power_bi/dashboard_blueprint.md` before building visuals.

| Page | Main question | Recommended visuals |
|---|---|---|
| Executive overview | What is happening overall? | KPI cards, monthly sales/profit trend, channel and category drivers |
| Acquisition and funnel | Which channels create engagement and purchases? | funnel, channel comparison, monthly conversion |
| Cart abandonment | Where do carts fail? | abandonment cards, browser/source/country bars |
| Revenue and product | What drives sales and margin? | category scatter, brand table, decomposition |
| Customer and cohort | Who is valuable and retained? | cohort heatmap, RFM segments, repeat customer trend |
| Geography | Where is performance strongest/weakest? | map, country matrix |
| Delivery and returns | Which operation stage/center needs work? | lead-time trend, DC median/P90, return segments |
| Inventory | Where is stock slow or aged? | sell-through, aging buckets, unsold value |
| Advanced analysis | What targeted actions are suggested? | RFM profile, return lift, product associations, test plan |

For every visual, write:

- decision supported;
- source table/measure;
- filters;
- tooltip fields;
- minimum sample rule;
- caveat.

## Power BI reconciliation

Create temporary cards for:

- rows in `fact_order_item`;
- `[Gross Sales]`;
- `[Sessions]`;
- sum of `fact_session[event_count]`.

Compare them with DuckDB:

```sql
SELECT
    COUNT(*) AS item_rows,
    SUM(gross_sales_value) AS gross_sales
FROM core.fact_order_item;

SELECT
    COUNT(*) AS sessions,
    SUM(event_count) AS events
FROM core.fact_session;
```

Do not proceed to formatting until the numbers match.

The finished implementation is documented in
[Power BI README](<../new_analysis/power_bi/README.md>),
[data model](<../new_analysis/power_bi/data_model.md>), and
[dashboard blueprint](<../new_analysis/power_bi/dashboard_blueprint.md>).

---

# Stage 12 — add advanced analytics that fit this dataset

The three highest-value methods are:

1. **RFM customer segmentation** — actionable customer strategy and a good bridge
   from SQL to unsupervised learning.
2. **Return propensity model** — predicts a useful operational/commercial risk and
   teaches leakage-safe classification and lift.
3. **Market-basket association rules** — creates product bundling and merchandising
   ideas from multi-item orders.

Hypothesis tests and A/B-test power planning are supporting methods. This dataset has
no randomized experiment assignment, so you can design an experiment but must not
claim a historical causal A/B result.

## 12.1 RFM segmentation

### Question

Which customers have similar value and engagement behavior, and what action fits
each group?

### Input

`mart.customer_360`.

### Core Python pattern

```python
import duckdb
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

connection = duckdb.connect(
    "artifacts/practice_analytics.duckdb",
    read_only=True,
)
customers = connection.execute(
    """
    SELECT
        customer_id,
        recency_days,
        order_count AS frequency,
        net_sales_value AS monetary
    FROM mart.customer_360
    WHERE recency_days IS NOT NULL
      AND order_count > 0
      AND net_sales_value > 0
    """
).fetchdf()
connection.close()

features = customers[["recency_days", "frequency", "monetary"]].copy()
features["monetary"] = features["monetary"].clip(
    upper=features["monetary"].quantile(0.99)
)
scaled = StandardScaler().fit_transform(features)

scores = []
for k in range(2, 7):
    model = KMeans(n_clusters=k, random_state=42, n_init=20)
    labels = model.fit_predict(scaled)
    scores.append({"k": k, "silhouette": silhouette_score(scaled, labels)})

best_k = max(scores, key=lambda item: item["silhouette"])["k"]
model = KMeans(n_clusters=best_k, random_state=42, n_init=20)
customers["cluster"] = model.fit_predict(scaled)

profiles = customers.groupby("cluster").agg(
    customers=("customer_id", "count"),
    median_recency=("recency_days", "median"),
    median_frequency=("frequency", "median"),
    median_monetary=("monetary", "median"),
)

customers.to_csv(
    "data/processed/advanced/customer_rfm_segments.csv",
    index=False,
)
profiles.to_csv(
    "data/processed/advanced/customer_rfm_segment_profiles.csv"
)
```

### What to interpret

KMeans returns cluster numbers, not business names. Review the profiles and then name
segments such as Champions, Loyal, New, At Risk, or Low Engagement. Do not assign a
name before looking at the centers.

The silhouette score compares within-cluster cohesion with between-cluster
separation. It helps choose `k`, but business usefulness also matters.

## 12.2 Return propensity

### Question

Which order items have a higher probability of return, so teams can improve sizing,
product information, or quality checks?

### Target

`returned_item_flag`, using only `return_observation_eligible_flag = 1`.

### Leakage warning

Do not use `returned_at`, `item_status`, or anything learned after the return. Those
fields directly reveal the target.

### Core pattern

```python
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

model_data = connection.execute(
    """
    SELECT
        f.returned_item_flag AS target,
        f.sale_price,
        p.unit_margin_rate,
        p.category,
        p.department,
        p.price_band,
        c.age_band,
        c.country,
        f.acquisition_source,
        f.distribution_center_id
    FROM core.fact_order_item AS f
    JOIN core.dim_product AS p ON f.product_id = p.product_id
    JOIN core.dim_customer AS c ON f.customer_id = c.user_id
    WHERE f.return_observation_eligible_flag = 1
    """
).fetchdf()

target = model_data.pop("target")
categorical = model_data.select_dtypes(include="object").columns.tolist()
numeric = [column for column in model_data.columns if column not in categorical]

preprocess = ColumnTransformer(
    [
        ("numeric", StandardScaler(), numeric),
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            categorical,
        ),
    ]
)

pipeline = Pipeline(
    [
        ("preprocess", preprocess),
        (
            "model",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ]
)

x_train, x_test, y_train, y_test = train_test_split(
    model_data,
    target,
    test_size=0.25,
    stratify=target,
    random_state=42,
)
pipeline.fit(x_train, y_train)
probability = pipeline.predict_proba(x_test)[:, 1]
print("ROC AUC:", roc_auc_score(y_test, probability))
```

Evaluate decile lift, calibration, and class prevalence—not accuracy alone. A model
that predicts “not returned” for every row can have high accuracy when returns are
rare and still be useless.

This is an association/prediction model. It does not prove that a feature causes
returns.

## 12.3 Market-basket association

### Question

Which product categories co-occur inside multi-item orders more often than expected?

### Definitions

- Support(A,B): share of eligible orders containing both A and B.
- Confidence(A→B): among orders containing A, share also containing B.
- Lift(A→B): confidence divided by the overall frequency of B.
- Lift greater than 1 means positive association, not causation.

### SQL/Python pattern

```python
from collections import Counter
from itertools import combinations

basket_rows = connection.execute(
    """
    SELECT
        f.order_id,
        list(DISTINCT p.category ORDER BY p.category) AS categories
    FROM core.fact_order_item AS f
    JOIN core.dim_product AS p ON f.product_id = p.product_id
    WHERE f.net_sales_value > 0
    GROUP BY f.order_id
    HAVING COUNT(DISTINCT p.category) >= 2
    """
).fetchall()

single_counts = Counter()
pair_counts = Counter()
for _, categories in basket_rows:
    for category in categories:
        single_counts[category] += 1
    for left, right in combinations(categories, 2):
        pair_counts[(left, right)] += 1

eligible_orders = len(basket_rows)
rules = []
for (left, right), pair_count in pair_counts.items():
    support = pair_count / eligible_orders
    confidence = pair_count / single_counts[left]
    right_support = single_counts[right] / eligible_orders
    lift = confidence / right_support
    rules.append(
        {
            "antecedent": left,
            "consequent": right,
            "support": support,
            "confidence": confidence,
            "lift": lift,
            "orders": pair_count,
        }
    )
```

Apply a minimum-order threshold. A spectacular lift based on two orders is not
commercial evidence.

## 12.4 Hypothesis testing

Good questions:

- Is return behavior associated with product category?
- Do ship lead-time distributions differ by distribution center?

Use a chi-square test for categorical association and Kruskal–Wallis for skewed
lead-time comparisons. Always report:

- null and alternative hypotheses;
- sample and exclusions;
- test statistic and p-value;
- effect size;
- practical interpretation;
- why this is not causal evidence.

With millions of rows, very small differences can have tiny p-values. Effect size is
essential.

## 12.5 A/B-test power plan

Since there is no experiment assignment table, design a future test:

- intervention: improved cart page, sizing information, or delivery promise;
- primary metric: session conversion or cart abandonment;
- baseline rate: measured from current data;
- minimum detectable effect: business decision, not a value discovered by searching;
- significance: commonly 5%;
- power: commonly 80%;
- unit of randomization: user or session;
- duration: required sample divided by eligible daily traffic;
- guardrails: return rate, margin, cancellation rate, page latency.

Do not label an observational channel comparison as an A/B test.

The complete implementation is the
[advanced analytics answer key](<../new_analysis/src/advanced_analytics.py>).

---

# Stage 13 — build reproducible notebooks and figures

## Purpose

SQL files create production tables. A notebook records analytical reasoning:
question → query → result → chart → interpretation → caveat.

## Tool

Jupyter.

## Action

Start:

```powershell
python -m jupyter lab
```

Create:

1. `01_data_quality_and_core_analysis.ipynb`
2. `02_advanced_methods.ipynb`
3. `03_event_sessionization_audit.ipynb`

Every notebook should begin with:

```python
from pathlib import Path
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = Path.cwd()
if PROJECT_ROOT.name == "notebooks":
    PROJECT_ROOT = PROJECT_ROOT.parent

connection = duckdb.connect(
    str(PROJECT_ROOT / "artifacts" / "practice_analytics.duckdb"),
    read_only=True,
)
```

## Notebook 1 outline

1. Objective and source contract.
2. Raw row counts.
3. QA status table.
4. Metric reconciliation.
5. Monthly sales/profit.
6. Funnel by channel.
7. Product/category performance.
8. Delivery and inventory.
9. Findings and limitations.

## Notebook 2 outline

1. RFM method and cluster selection.
2. Segment profiles and actions.
3. Return model sample, leakage policy, evaluation, lift.
4. Market-basket rules and sample thresholds.
5. Hypothesis tests and effect sizes.
6. Experiment power plan.

## Notebook 3 outline

1. State that sessions are derived from events.
2. Event count, distinct session count, modeled session count.
3. Event reconciliation.
4. Attribute consistency.
5. Missing user-ID coverage.
6. Funnel flags and sample sessions.

## Execute notebooks as a test

```powershell
python -m jupyter nbconvert `
  --execute `
  --to notebook `
  --inplace `
  --ExecutePreprocessor.timeout=600 `
  notebooks\01_data_quality_and_core_analysis.ipynb
```

Repeat for all three. An executed notebook is a reproducibility check: another person
can see both the code and the result.

## Figure rules

- descriptive title;
- units and axes;
- readable labels;
- consistent colors;
- sample size where material;
- no 3D charts;
- no truncated axis that exaggerates differences;
- save at least 1600×900 or equivalent readable resolution.

Save generated images in `artifacts/figures/`. Do not commit them unless you decide
they are final portfolio assets; the current `.gitignore` excludes artifacts.

---

# Stage 14 — automate and validate the project

## Purpose

At first, manual runs help you understand dependencies. At the end, one command
should rebuild and validate everything. Automation is the proof that the project is
reproducible.

## Create `tests/test_project_contracts.py`

```python
from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProjectContractTests(unittest.TestCase):
    def test_sql_modules_are_numbered(self):
        modules = sorted((PROJECT_ROOT / "sql" / "duckdb").glob("*.sql"))
        self.assertEqual(7, len(modules))
        self.assertTrue(all(path.name[:2].isdigit() for path in modules))

    def test_pipeline_uses_only_original_sources(self):
        pipeline = (PROJECT_ROOT / "src" / "pipeline.py").read_text(
            encoding="utf-8"
        ).lower()
        for table in (
            "users",
            "products",
            "orders",
            "order_items",
            "events",
            "inventory_events",
            "distribution_centers",
        ):
            self.assertIn(f'"{table}"', pipeline)
        self.assertNotIn('"dim_sessions"', pipeline)

    def test_sessions_are_event_derived(self):
        staging = (
            PROJECT_ROOT / "sql" / "duckdb" / "01_staging.sql"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("create or replace view stg.sessions", staging)
        self.assertIn("from stg.events", staging)
        self.assertIn("group by session_id", staging)


if __name__ == "__main__":
    unittest.main()
```

Run:

```powershell
python -m unittest discover -s tests -v
```

## Create `src/validate_project.py`

At minimum, validate:

- seven and only seven raw tables;
- expected core row counts;
- zero blocking QA failures;
- zero reconciliation variance;
- event/session lineage;
- 25 CSV and 25 Parquet exports;
- no PII in the customer export;
- executed notebooks with no error output;
- valid Power BI theme JSON;
- required DAX measure names.

Start with this database gate:

```python
from pathlib import Path
import duckdb

project_root = Path(__file__).resolve().parents[1]
connection = duckdb.connect(
    str(project_root / "artifacts" / "practice_analytics.duckdb"),
    read_only=True,
)

blocking_failures = connection.execute(
    """
    SELECT COUNT(*)
    FROM qa.test_results
    WHERE status = 'FAIL'
    """
).fetchone()[0]

nonzero_variances = connection.execute(
    """
    SELECT COUNT(*)
    FROM qa.metric_reconciliation
    WHERE ABS(variance) > 0.001
    """
).fetchone()[0]

connection.close()

if blocking_failures:
    raise SystemExit(f"{blocking_failures} blocking QA checks failed")
if nonzero_variances:
    raise SystemExit(f"{nonzero_variances} reconciliation checks failed")

print("Validation PASS")
```

Extend it checkpoint by checkpoint. Compare with the
[validator answer key](<../new_analysis/src/validate_project.py>).

## Create `src/run_all.py`

```python
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from pipeline import run as run_pipeline


def run_command(command: list[str], cwd: Path) -> None:
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv-dir", type=Path, required=True)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    python = sys.executable

    run_pipeline(project_root, args.source_csv_dir.resolve())

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
        "01_data_quality_and_core_analysis.ipynb",
        "02_advanced_methods.ipynb",
        "03_event_sessionization_audit.ipynb",
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
                str(project_root / "notebooks" / notebook),
            ],
            project_root,
        )

    run_command(
        [python, str(project_root / "src" / "validate_project.py")],
        project_root,
    )


if __name__ == "__main__":
    main()
```

### Why `check=True` matters

If an upstream step fails, `subprocess.run(..., check=True)` raises an error and stops
the workflow. Continuing after a failed warehouse build could publish stale exports.

## Final full run

```powershell
python src\run_all.py `
  --project-root . `
  --source-csv-dir "C:\Users\phanh\data_analysis\p_projects\the_look_ecommerce\original_analysis\5_the_look_ecommerce\csv_version\3_thelookecommerce"
```

The final run should create the warehouse, tables, QA files, exports, advanced
outputs, figures, executed notebooks, and a passing validation result.

---

# Stage 15 — finish documentation and make the project portfolio-ready

## Purpose

Documentation is not an appendix written after the project. It is the map that lets
someone understand the source, logic, decisions, limitations, and reproduction path.

## Write these public files

| File | What it must answer |
|---|---|
| `README.md` | What is the project, why does it matter, and how do I run it? |
| `docs/architecture.md` | How does data move between layers? |
| `docs/source_inventory.md` | What are the seven sources and their grains? |
| `docs/data_dictionary.md` | What does every modeled table/important column mean? |
| `docs/kpi_dictionary.md` | Exact KPI numerator, denominator, grain, exclusions |
| `docs/assumptions_and_limitations.md` | What cannot be concluded and how anomalies are handled |
| `docs/analysis_findings.md` | What did the validated evidence show and what should happen next? |
| `docs/advanced_methods.md` | Why each method fits, evaluation, risks, outputs |
| `power_bi/README.md` | Exact import and refresh steps |
| `power_bi/data_model.md` | Relationships, cardinality, filter direction |
| `power_bi/dashboard_blueprint.md` | Page purpose, visuals, filters, drill paths |

## KPI dictionary template

```markdown
## Net Sales

- Business meaning: sales value retained after cancelled and returned items.
- Grain of source: order item.
- Numerator: SUM(fact_order_item[net_sales_value]).
- Denominator: none.
- Time field: order_item_created_at / order_date_key.
- Exclusions: cancelled and returned items contribute zero.
- Caveat: this is modeled order-item value, not payment-settlement accounting.
- SQL owner: sql/duckdb/03_core_facts.sql.
- Power BI measure: [Net Sales].
```

For every rate, explicitly document both numerator and denominator.

## README execution section

Include:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src\run_all.py `
  --project-root . `
  --source-csv-dir "PATH_TO_THE_SEVEN_CSV_FILES"
```

Also include the seven-file source contract, output locations, QA result, project
architecture, main business themes, advanced methods, limitations, and Power BI
instructions.

## Git workflow

Suggested commits:

1. `docs: define business questions and source contract`
2. `build: add DuckDB ingestion and staging`
3. `feat: add dimensional model and business marts`
4. `test: add QA and metric reconciliation`
5. `feat: add Power BI model and measures`
6. `analysis: add advanced methods and notebooks`
7. `docs: publish findings and reproducible run guide`

Before every commit:

```powershell
git status --short
git check-ignore -v artifacts\practice_analytics.duckdb
git check-ignore -v data\processed\power_bi\csv\fact_session.csv
```

Confirm that source data, generated data, the database, logs, local config, and Power
BI binaries are not staged.

---

# How to use the finished project as an answer key

Use this order:

1. Write your version.
2. Predict its result.
3. Run it.
4. Inspect rows and QA.
5. Explain any difference.
6. Only then open the matching answer-key file.

Important reference entry points:

- [finished project start page](<../new_analysis/00_START_HERE.md>)
- [project walkthrough](<../new_analysis/docs/01_PROJECT_WALKTHROUGH.md>)
- [sessionization explanation](<../new_analysis/docs/02_SESSIONIZATION_FROM_EVENTS.md>)
- [pipeline](<../new_analysis/src/pipeline.py>)
- [DuckDB SQL modules](<../new_analysis/sql/duckdb/>)
- [advanced analytics](<../new_analysis/src/advanced_analytics.py>)
- [Power BI guide](<../new_analysis/power_bi/README.md>)
- [validation logic](<../new_analysis/src/validate_project.py>)

If your logic differs but passes lineage, grain, privacy, and metric-definition
checks, the difference may be a valid design choice. Document it. The goal is not to
copy identical text; the goal is to build a model whose numbers you can defend.

