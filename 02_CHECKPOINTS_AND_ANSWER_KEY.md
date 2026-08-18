# Practice checkpoints and answer key

Use this file only after completing the matching stage in
`01_BUILD_IT_YOURSELF_GUIDE.md`.

The expected values below come from the same seven original CSV files used by the
finished project. If the source files change, fingerprints and counts may change.

---

# Checkpoint 0 — business framing

## Self-review

- [ ] I can state the project’s decisions, not only its charts.
- [ ] I separated session traffic source from customer acquisition source.
- [ ] I declared one grain for every planned dimension, fact, and mart.
- [ ] Every rate has a named numerator and denominator.
- [ ] I documented what the data cannot prove.

## Explain aloud

Answer these without opening code:

1. Why is `order_items` safer than `orders` for product sales and margin?
2. Why does `COUNT(order_id)` over an item-grain table overcount orders?
3. Why is cart abandonment divided by cart sessions rather than all sessions?
4. Why can an observational channel comparison not be called an A/B test?

If any answer is unclear, revisit Stage 0.

---

# Checkpoint 1 — folders and environment

## Self-review

- [ ] Human-written code is in `src/` and `sql/`.
- [ ] Human-written documentation is in `docs/` and `power_bi/`.
- [ ] Generated data is under `data/processed/`.
- [ ] Database/figures are under `artifacts/`.
- [ ] QA exports are under `outputs/qa/`.
- [ ] `.gitignore` excludes generated and local files.
- [ ] `python -c "import duckdb"` succeeds inside `.venv`.

## Common mistakes

- Putting source CSVs beside SQL and committing them.
- Using global Python packages and being unable to reproduce the environment.
- Committing a `.pbix` without documenting how it is built.
- Keeping generated outputs and hand-written files in the same folder.

---

# Checkpoint 2 — source inventory

## Expected source contract

| File | Expected rows |
|---|---:|
| `users.csv` | 100,000 |
| `products.csv` | 29,120 |
| `orders.csv` | 124,814 |
| `order_items.csv` | 180,862 |
| `events.csv` | 2,420,661 |
| `inventory_events.csv` | 488,146 |
| `distribution_centers.csv` | 10 |

## Self-review

- [ ] Exactly seven required files are whitelisted.
- [ ] A missing required file raises an error.
- [ ] `dim_sessions.csv` is neither required nor ingested.
- [ ] The inventory stores size, row count, columns, and SHA-256 fingerprint.
- [ ] Original files remain unchanged.
- [ ] I identified direct PII fields and a downstream exclusion policy.

## Diagnostic questions

If a count differs:

1. Did the profiler subtract exactly one header row?
2. Is the CSV quoted correctly, including embedded commas?
3. Are you pointing to the correct source folder?
4. Did a source file change? Compare SHA-256.
5. Did you accidentally include the legacy derived session file?

---

# Checkpoint 3 — raw ingestion

Run in Python:

```python
import duckdb

connection = duckdb.connect(
    "artifacts/practice_analytics.duckdb",
    read_only=True,
)
print(
    connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'raw'
        ORDER BY table_name
        """
    ).fetchdf()
)
connection.close()
```

## Expected raw tables

```text
distribution_centers
events
inventory_events
order_items
orders
products
users
```

## Self-review

- [ ] Seven and only seven raw tables exist.
- [ ] Raw row counts match the source profile.
- [ ] No business metric, cleaned category, or derived session exists in raw.
- [ ] The database can be rebuilt without manually editing the source.
- [ ] Run metadata identifies the original source folder and fingerprints.

## Explain aloud

“Raw” does not necessarily mean all columns are strings. In this project,
`read_csv_auto` may infer physical types. It means the raw layer has no semantic
cleaning or derived business logic, the source files are immutable, and provenance is
recorded. For stricter text preservation, use `all_varchar=true` and cast everything
in staging.

---

# Checkpoint 4 — staging and sessionization

## Expected lineage

| Metric | Expected |
|---|---:|
| Staged event rows | 2,420,661 |
| Distinct nonblank `session_id` | 680,862 |
| Derived `stg.sessions` rows | 680,862 |
| Sum of derived `event_count` | 2,420,661 |

## Reconciliation query

```sql
SELECT
    (SELECT COUNT(*) FROM stg.events) AS source_events,
    (SELECT COUNT(DISTINCT session_id) FROM stg.events)
        AS distinct_session_ids,
    (SELECT COUNT(*) FROM stg.sessions) AS derived_sessions,
    (SELECT SUM(event_count) FROM stg.sessions)
        AS events_represented_by_sessions;
```

## Self-review

- [ ] `stg.sessions` selects only from `stg.events`.
- [ ] It groups by `session_id`.
- [ ] It uses sequence-aware first/last logic.
- [ ] It creates stage flags with conditional aggregation.
- [ ] Session count and event count both reconcile.
- [ ] Missing event user IDs are measured, not filled with invented users.
- [ ] Direct customer PII is excluded from `stg.users`.

## Common mistakes

- Grouping by both `session_id` and `user_id`, which can split a session.
- Using one row per event as if it were one row per session.
- Summing event purchase flags without reducing them to a session-level flag.
- Joining events to orders on user ID and assuming the purchase event is a specific
  order.
- Recreating the legacy `dim_sessions.csv` dependency.

---

# Checkpoint 5 — dimensions

## Expected row counts

| Dimension | Expected rows |
|---|---:|
| `core.dim_customer` | 100,000 |
| `core.dim_product` | 29,120 |
| `core.dim_distribution_center` | 10 |

Traffic-source dimensions depend on distinct cleaned categories and should be checked
for uniqueness rather than a memorized count.

## Self-review

- [ ] Every dimension key is unique.
- [ ] `dim_customer` has no direct name, email, address, or IP columns.
- [ ] Age and price bands cover nulls and boundaries.
- [ ] `dim_date` covers the full source range.
- [ ] The maximum source month is identified as incomplete where applicable.
- [ ] Date keys have consistent `YYYYMMDD` integer form.

## Boundary test examples

- Age 24 → `18-24`; age 25 → `25-34`.
- Price 24.99 → `Under $25`; price 25 → `$25-$49`.

If you cannot say which band owns the boundary, the `CASE` logic is not fully
specified.

---

# Checkpoint 6 — facts

## Expected row counts

| Fact | Expected rows | Grain |
|---|---:|---|
| `core.fact_order` | 124,814 | one order |
| `core.fact_order_item` | 180,862 | one order item |
| `core.fact_session` | 680,862 | one event-derived session |
| `core.fact_inventory` | 488,146 | one inventory unit |

## Self-review

- [ ] Row count equals distinct natural key count for every fact.
- [ ] Required dimension joins produce zero orphans.
- [ ] Gross sales reconciles to staged `sale_price`.
- [ ] Net sales and net profit rules are documented.
- [ ] Return rate uses return-eligible items as its denominator.
- [ ] Invalid timestamp sequences produce null lead times and a validity flag.
- [ ] Unsold inventory age uses a fixed data as-of date, not today.

## Expected reconciliation

| Metric | Source | Modeled | Variance |
|---|---:|---:|---:|
| Orders rows | 124,814 | 124,814 | 0 |
| Order-item rows | 180,862 | 180,862 | 0 |
| Sessions from events | 680,862 | 680,862 | 0 |
| Events represented in sessions | 2,420,661 | 2,420,661 | 0 |
| Gross sales value | 10,796,335.701331269 | 10,796,335.701331269 | 0 |

Minor display rounding is acceptable; stored reconciliation variance should be zero
or within an explicitly documented numerical tolerance.

---

# Checkpoint 7 — marts

## Grain tests

Run examples:

```sql
SELECT month_start, COUNT(*) AS rows_at_grain
FROM mart.sales_monthly
GROUP BY month_start
HAVING COUNT(*) > 1;

SELECT traffic_source, COUNT(*) AS rows_at_grain
FROM mart.channel_quality
GROUP BY traffic_source
HAVING COUNT(*) > 1;

SELECT customer_id, COUNT(*) AS rows_at_grain
FROM mart.customer_360
GROUP BY customer_id
HAVING COUNT(*) > 1;
```

Every query should return zero rows.

## Self-review by topic

### Funnel

- [ ] Stage order is explicit.
- [ ] Conversion from session and from previous stage are distinguished.
- [ ] Abandonment denominator is cart sessions.
- [ ] Event traffic source is not mislabeled as customer acquisition source.

### Commercial

- [ ] Sales and profit are additive values.
- [ ] Margin is a ratio of sums.
- [ ] AOV divides by distinct orders.
- [ ] Category/brand rankings retain volume and return context.
- [ ] Incomplete periods are not used for misleading MoM/YoY claims.

### Customer

- [ ] Customer 360 has one row per purchasing customer.
- [ ] Recency uses a fixed data as-of date.
- [ ] Cohort size is fixed at the first active month.
- [ ] Retention counts distinct active customers.

### Operations and inventory

- [ ] Average, median, and P90 lead time are all available.
- [ ] Invalid timelines are controlled.
- [ ] Return segment marts have sample thresholds.
- [ ] Inventory sell-through and aging use inventory-unit grain.

---

# Checkpoint 8 — QA and reconciliation

## Verified finished-project outcome

- 21 checks total.
- 18 `PASS`.
- 3 `WARN`.
- 0 `FAIL`.

## Expected warnings

| Check | Failure count | Why it remains a warning |
|---|---:|---|
| `shipping_not_before_item_created` | 35,440 | Source timestamp anomaly; invalid rows are excluded from lead-time metrics |
| `events_user_id_missing` | 1,124,527 | Anonymous/unidentified event coverage; sessions remain valid |
| `partial_latest_month` | 1 | Maximum month is incomplete; exclude from period comparisons |

## Self-review

- [ ] Critical failures stop publishing.
- [ ] Warnings have nonblocking status and documented handling.
- [ ] Failure count and denominator are both available.
- [ ] A failure rate can be interpreted.
- [ ] Metric reconciliation is separate from rule checks.
- [ ] QA output is exported for review.

## Warning versus failure example

Missing session IDs would prevent reliable sessionization, so that is blocking.
Missing user IDs do not prevent anonymous session analysis, so they are a documented
coverage warning. Severity depends on the analytical use, not on whether a value is
simply null.

---

# Checkpoint 9 — Power BI exports and model

## Expected exports

- 25 CSV files.
- 25 Parquet files.

## Required table groups

### Dimensions

- `dim_date`
- `dim_customer`
- `dim_product`
- `dim_distribution_center`
- `dim_session_traffic_source`
- `dim_acquisition_source`

### Facts

- `fact_order`
- `fact_order_item`
- `fact_session`
- `fact_inventory`

### Marts

- `funnel_stage_channel`
- `funnel_monthly_channel`
- `channel_quality`
- `acquisition_source_value`
- `cart_abandonment_segments`
- `sales_monthly`
- `customer_360`
- `cohort_retention`
- `product_performance_category`
- `product_performance_brand`
- `geography_performance_country`
- `delivery_performance_dc`
- `operations_monthly`
- `return_risk_segments`
- `inventory_performance`

## Model self-review

- [ ] Dimensions are on the “one” side.
- [ ] Facts are on the “many” side.
- [ ] Filter direction is single unless explicitly justified.
- [ ] `dim_date` is marked as the date table.
- [ ] Technical keys are hidden.
- [ ] Measures live in a dedicated measure table.
- [ ] I did not load both CSV and Parquet copies.
- [ ] Raw or staging tables are not imported.
- [ ] Customer export has no direct PII.

## DAX self-review

- [ ] Net sales and net profit are sums of additive columns.
- [ ] Net margin is `[Net Profit] / [Net Sales]`.
- [ ] AOV uses distinct orders.
- [ ] Conversion uses purchase sessions / sessions.
- [ ] Abandonment uses abandoned cart sessions / cart sessions.
- [ ] Return rate uses returned / return-eligible.
- [ ] Time-intelligence measures use `dim_date`.

---

# Checkpoint 10 — dashboard

For every page:

- [ ] The page title is a business question or clear topic.
- [ ] KPI cards have definitions and filter context.
- [ ] Trends do not include an incomplete period in comparisons.
- [ ] Rankings show volume, value, and quality—not only revenue.
- [ ] Small samples are filtered or visibly labeled.
- [ ] Tooltips provide decision-relevant detail.
- [ ] Drill-through follows a useful investigation path.
- [ ] SQL and Power BI totals reconcile.
- [ ] A written takeaway explains what action the page supports.

## Visual choice examples

| Relationship | Suitable visual |
|---|---|
| Metric over time | Line chart |
| Categories ranked by one metric | Bar chart |
| Sales versus margin with volume | Scatter plot |
| Funnel stages | Funnel or ordered bars |
| Cohort month versus age | Heatmap |
| Distribution including long tail | Box plot or median/P90 comparison |
| Exact audit values | Table/matrix |

Avoid a pie chart when there are many categories or when precise comparison matters.

---

# Checkpoint 11 — advanced methods

## RFM

- [ ] Features have correct direction: lower recency is better; higher frequency and
  monetary are better.
- [ ] Extreme values are examined or capped with a documented rule.
- [ ] Features are scaled before KMeans.
- [ ] Several `k` values are evaluated.
- [ ] Cluster names come from profiles, not cluster numbers.
- [ ] Every segment has a proposed action and guardrail.

## Return propensity

- [ ] Only return-observable rows enter the model.
- [ ] Post-outcome fields are excluded.
- [ ] Train/test split is reproducible and stratified.
- [ ] Categorical values handle unseen categories.
- [ ] Evaluation includes ROC AUC and decile lift.
- [ ] Class prevalence and calibration are reviewed.
- [ ] Results are described as predictive association, not causation.

## Market basket

- [ ] Basket grain is order.
- [ ] Cancelled/returned value rules are explicit.
- [ ] Only multi-category orders enter pair analysis.
- [ ] Support, confidence, lift, and order count are reported.
- [ ] A minimum support/order threshold prevents tiny-sample rules.
- [ ] Rules are treated as hypotheses for bundles or recommendations.

## Statistics and experimentation

- [ ] Every hypothesis test states H0 and H1.
- [ ] Effect size accompanies p-value.
- [ ] Assumptions and exclusions are documented.
- [ ] The A/B work is a future power plan, not a historical causal claim.
- [ ] Randomization unit, primary metric, MDE, power, alpha, duration, and guardrails
  are specified.

---

# Checkpoint 12 — notebooks, automation, and public readiness

## Reproducibility

- [ ] All notebook code cells have execution counts.
- [ ] No notebook contains an error output.
- [ ] Figures are readable and nonblank.
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] `run_all.py` stops when a step fails.
- [ ] A clean full run ends in `Validation PASS`.
- [ ] Run metadata records source paths, fingerprints, counts, modules, and exports.

## Documentation

- [ ] `README.md` lets a new user run the project.
- [ ] Architecture explains raw → staging → core → mart → QA → export → Power BI.
- [ ] Source inventory names exactly seven original tables.
- [ ] Data dictionary states grains and key fields.
- [ ] KPI dictionary states formulas, denominators, time fields, and exclusions.
- [ ] Findings separate evidence from recommendation.
- [ ] Limitations disclose source anomalies and noncausal methods.
- [ ] Power BI instructions include import, relationships, measures, pages, and QA.

## Git/public safety

- [ ] Original CSVs are not staged.
- [ ] Generated CSV/Parquet files are not staged.
- [ ] DuckDB files are not staged.
- [ ] Logs and local configuration are not staged.
- [ ] Direct customer identifiers are absent from committed outputs.
- [ ] The project contains no dependency on `dim_sessions.csv`.

---

# Final oral exam

If you can answer these clearly, you understand the project architecture:

1. Why preserve raw when staging already looks cleaner?
2. What is a schema in DuckDB, and why use five of them?
3. What is the difference between a view and a table here?
4. What is the grain of each core fact?
5. How are sessions reconstructed, and how do you prove no event was lost?
6. Why keep both reusable facts and aggregated marts?
7. What is the difference between QA and reconciliation?
8. Why is margin a ratio of sums instead of an average of row margins?
9. Why are some data-quality issues warnings rather than failures?
10. Why should Power BI load modeled exports rather than the original seven CSVs?
11. Why is Parquet usually better than CSV for large facts?
12. What makes the return model leakage-safe?
13. Why is a statistically significant result not automatically important?
14. Why is an A/B power plan valid here but a historical A/B result is not?
15. What files must another analyst have to reproduce the project?

When you can rebuild the warehouse, explain every layer, reconcile the core totals,
and defend the measures and limitations without opening the answer key, the practice
project is complete.

