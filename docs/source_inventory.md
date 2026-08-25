# Source inventory

The project accepts exactly seven original dataset files.

| Source | Grain | Candidate key | Primary analytical use |
|---|---|---|---|
| `users.csv` | user | `id` | demographics, geography, customer acquisition source |
| `products.csv` | product | `id` | catalog, price, cost, margin, distribution center |
| `orders.csv` | order | `order_id` | status and order-level delivery lifecycle |
| `order_items.csv` | order item | `id` | revenue, profit, product, returns, fulfillment |
| `events.csv` | event | `id` | session reconstruction, behavior sequence, funnel reach |
| `inventory_events.csv` | inventory item | `id` | sell-through, inventory age, time to sell |
| `distribution_centers.csv` | distribution center | `id` | location and operations breakdown |

## Derived session policy

A session file is not part of the source inventory. The pipeline creates `stg.sessions` from `events.csv` by grouping on `session_id`.

The source folder may still contain artifacts from the original analysis. They are ignored because `src/pipeline.py` loads only the seven declared files.

## Execution evidence

`artifacts/pipeline_run.json` records:

- the seven accepted filenames;
- byte sizes;
- modification timestamps;
- SHA-256 checksums;
- raw row counts;
- an explicit statement that sessions come from `events.csv`;
- an explicit statement that the legacy derived session artifact is not required.
