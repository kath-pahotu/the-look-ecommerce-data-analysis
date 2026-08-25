# Testing and validation strategy

## Source-contract checks

- raw schema contains exactly the seven original tables;
- pipeline metadata lists exactly seven source files;
- no implementation file loads a legacy derived session source;
- sessions are created from `events.csv` grouped by `session_id`.

## Data-quality checks

- primary-key uniqueness;
- source-to-model row reconciliation;
- referential integrity;
- nonnegative price/cost and cost <= retail;
- order/customer/product coverage;
- timestamp sequence validity;
- partial-period flagging;
- event identity completeness documentation.

## Session-lineage checks

- event session IDs are present;
- derived session IDs are unique;
- each session has at most one nonnull customer ID;
- browser and traffic source are stable within a session;
- distinct event session IDs equal `fact_session` rows;
- total event rows equal summed session `event_count`.

## Analytical validation

- gross sales independently reconciles to source `sale_price`;
- orders and items reconcile exactly;
- session metrics reconcile directly to the event source;
- rates use visible numerators and denominators;
- lead-time metrics filter invalid sequences;
- model validation uses an out-of-time holdout;
- statistical significance is paired with effect size or practical interpretation.

## Artifact validation

- all three notebooks execute top-to-bottom with no error outputs;
- required Power BI files and DAX measures exist;
- theme JSON parses;
- CSV and Parquet export sets contain exactly the approved 25 tables;
- generated PNGs meet resolution and nonblank checks;
- customer PII is absent from Power BI exports;
- navigation documents exist;
- `private_review/` is Git-ignored.
