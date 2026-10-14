# How to run this project

Everything in this repository is produced by code. There is no manual step between the
seven source CSVs and any published number. This page says how to run it — the whole
thing in one command, or one stage at a time while developing — and why the work is
split across many files instead of one.

---

## 1. The short version

```bash
cd new_analysis
python src/run_all.py --source-csv-dir "../original_analysis/5_the_look_ecommerce/csv_version/3_thelookecommerce" --rebuild
```

That is the only command needed. It takes roughly two to four minutes and rebuilds the
warehouse, every export, every figure, the Excel pack, all five notebooks and the final
validation gate. `--rebuild` deletes the existing warehouse and generated files first, so
nothing stale can survive a run.

Drop `--rebuild` to run incrementally against the existing warehouse — faster, but a
table removed from the SQL would still be sitting there from the previous build. Use
`--rebuild` whenever the result matters.

### First time only

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```

---

## 2. What that one command actually does

`src/run_all.py` is an orchestrator. It holds no logic of its own — it calls the modules
in the only order they can legally run in, and stops at the first failure.

| # | Stage | Runs | Produces |
|---|---|---|---|
| 1 | **Pipeline** | `src/pipeline.py` → `sql/duckdb/00` … `09` | the warehouse, the QA evidence, 34 Power BI exports, 23 analysis CSVs |
| 2 | **Python analytics** | `advanced_analytics.py`, `forecasting.py` | `artifacts/advanced_metrics.json`, `artifacts/forecast_summary.json`, the forecast marts |
| 3 | **Rendering** | `build_excel_pack.py`, `render_outputs.py`, `render_commercial_figures.py` | `reports/*.xlsx`, `artifacts/figures/*.png` |
| 4 | **Notebook build** | `build_notebooks.py`, `build_commercial_notebook.py`, `build_project_walkthrough.py` | the five `.ipynb` files, written but not yet executed |
| 5 | **Notebook execution** | `jupyter nbconvert --execute --inplace` | the same notebooks, now carrying their outputs |
| 6 | **Validation gate** | `validate_project.py` | `artifacts/validation_report.json` — the run only "passed" if this passes |

Stage 1 is itself two phases, and the split is deliberate:

```
  ingest raw  ->  SOURCE GATE (00_raw_quality.sql)      <- stops here if a source is broken
                      |
                  01 staging -> 02 core dims -> 03 core facts
                      |
                  04/05/06 marts -> 07 warehouse QA
                      |
                  08 commercial planning -> 09 commercial QA
                      |
                  WAREHOUSE + COMMERCIAL GATES          <- stops here before anything is exported
                      |
                  export 34 Power BI tables, 23 analysis CSVs, 6 QA files
```

The source gate runs before a single model exists, because there is no point computing
twenty-six marts on a broken extract. The second gate runs before the exports, because
without it a failing build would still have written 34 CSV files and an Excel pack to
disk before reporting failure.

---

## 3. Running one stage at a time

This is what the development loop actually looks like. Nobody re-runs everything to test
a change to one SQL file.

**Change SQL, rebuild the warehouse only:**

```bash
python src/pipeline.py --project-root . --source-csv-dir "../original_analysis/5_the_look_ecommerce/csv_version/3_thelookecommerce" --rebuild
```

**Re-run one Python module against the existing warehouse:**

```bash
python src/advanced_analytics.py --project-root .
python src/render_commercial_figures.py --project-root .
python src/build_project_walkthrough.py
```

Every module in `src/` can be run alone, and all of them except
`build_project_walkthrough.py` (which resolves the project root from its own location)
take `--project-root`. They all read the warehouse that stage 1 already built, so they
are cheap to re-run.

**Query the warehouse directly without running anything:**

```python
import duckdb
db = duckdb.connect("artifacts/thelook_analytics.duckdb", read_only=True)
db.execute("SELECT * FROM mart.commercial_scorecard").fetchdf()
```

`read_only=True` matters. It guarantees an exploratory session cannot alter the thing
every report depends on.

### Looking at the data while you work

Before writing a join, a quality check or a reconciliation line, you need to see the
columns, the nulls, the distinct values and whether two keys actually overlap. That is
what [`src/explore.py`](../src/explore.py) and
[`notebooks/90_workbench.ipynb`](../notebooks/90_workbench.ipynb) are for.

```python
import sys; sys.path.insert(0, "../src")
from explore import open_warehouse

w = open_warehouse()
w.cols("core.fact_plan")                                  # types, nulls, distinct, example
w.grain("core.fact_plan", "canonical_country", "plan_month")   # is it unique at this grain
w.overlap("stg.plan_submissions", "submitted_country",
          "core.dim_market", "canonical_country")         # do the keys match
w.tie("gross sales",
      "SELECT SUM(sale_price) FROM stg.order_items",
      "SELECT SUM(gross_sales_value) FROM core.fact_order_item")
```

The connection is read-only, so exploring cannot alter the warehouse. `90_workbench.ipynb`
is the one notebook in the project that is **not** generated — nothing overwrites it, and
it is meant to be edited.

**Re-execute one notebook:**

```bash
python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=600 notebooks/00_project_walkthrough.ipynb
```

---

## 4. Why many files and not one script

If one command runs everything, the obvious question is why the work is spread across ten
SQL files and thirteen Python modules rather than living in a single script. Four reasons,
and they are the same four in any production pipeline.

**Failure has to be locatable.** When a build fails, the log names the module and the
statement. In one 4,000-line script the error says line 2,817 and nothing about which
business concept broke.

**Order is a real constraint, and the file names encode it.** `03_core_facts.sql` cannot
run before `02_core_dimensions.sql`, because the facts join to the dimensions. Numbering
the files makes the dependency visible to a reader instead of hiding it inside control
flow. The orchestrator globs the directory and runs them in name order — adding a stage
means adding a file, not editing a list.

**Not everything needs to re-run.** Changing a chart should not rebuild a warehouse.
Separate modules mean a two-second re-run instead of a four-minute one, which is the
difference between iterating and not bothering.

**Each file has one owner and one purpose.** `08_commercial_planning.sql` is the only
place plan data is modelled. Anyone asking "where does plan versus actual come from"
has exactly one file to read, and anyone changing it knows the full blast radius.

The orchestrator exists so that none of this is the user's problem. A reviewer who just
wants the output runs one command; a developer who is changing one thing runs one module.
Both are supported on purpose.

---

## 5. Checking a run worked

```bash
cat artifacts/validation_report.json      # the gate's own verdict
cat artifacts/pipeline_run.json           # row counts, timings, SQL modules executed
cat logs/pipeline.log                     # the full build log, overwritten each run
```

Then the evidence a reviewer would actually read:

| File | Answers |
|---|---|
| `outputs/qa/raw_test_results.csv` | did the source gate pass |
| `outputs/qa/test_results.csv` | did the warehouse gate pass |
| `outputs/qa/plan_validation.csv` | did the commercial gate pass |
| `outputs/qa/plan_rejects.csv` | which submitted rows were quarantined, and why |
| `outputs/qa/reconciliation_statement.csv` | does the money tie from submission to mart |

A build that reports success with a failing check is not possible: `assert_no_blocking_failures()`
in `src/pipeline.py` raises `QualityGateFailed` and the process exits non-zero.

---

## 6. When it fails

| Message | Cause | Fix |
|---|---|---|
| `Required source file is missing` | `--source-csv-dir` is wrong, or a CSV is absent | point it at the folder holding the seven TheLook CSVs |
| `QualityGateFailed: Source` | a blocking check in `00_raw_quality.sql` failed | read `outputs/qa/raw_test_results.csv`; the `notes` column names the rows |
| `QualityGateFailed: Commercial` | the plan layer broke a structural rule | read `outputs/qa/plan_validation.csv` |
| `IO Error: database is locked` | a notebook or DuckDB session still holds the file | close it, or reconnect with `read_only=True` |
| nbconvert timeout | a notebook cell ran past 600 seconds | raise `--ExecutePreprocessor.timeout` |

The Power BI report is the one thing **not** rebuilt by this command. It reads the
Parquet exports in `data/processed/power_bi/parquet/`, so a pipeline run refreshes its
data, but the `.pbix` itself has to be opened and refreshed by hand.
