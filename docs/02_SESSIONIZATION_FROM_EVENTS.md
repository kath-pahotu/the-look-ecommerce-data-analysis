# Sessionization from events

## Decision

Sessions are a modeled analytical grain, not an original dataset file.

The source-of-truth is `events.csv`. The pipeline normalizes the event records and creates one session row for every distinct `session_id`.

## Where the transformation happens

- DuckDB: `sql/duckdb/01_staging.sql` → `stg.sessions`
- Final fact: `sql/duckdb/03_core_facts.sql` → `core.fact_session`
- Executable audit: `notebooks/03_event_sessionization_audit.ipynb`

The pipeline does not load or require a separate session CSV.

## Field derivation

| Session field | Event-based rule | Validation |
|---|---|---|
| `session_id` | Grouping key | Nonblank; unique after grouping |
| `customer_id` | Maximum nonnull `user_id` in the session | A session may contain at most one distinct nonnull user |
| `event_count` | Count of event rows | Sum across sessions equals source event rows |
| `events_with_user_id` | Count of events with nonnull `user_id` | Used for identity coverage |
| `session_start_at` | Minimum event timestamp | Must not exceed end timestamp |
| `session_end_at` | Maximum event timestamp | Used for session duration |
| `browser` | Browser on the first sequenced event | Browser must be stable within a session |
| `traffic_source` | Traffic source on the first sequenced event | Source must be stable within a session |
| `city/state/postal_code` | Location on the first sequenced event | Used only as supporting context |
| `first_event_type` | Event with minimum sequence number | Auditable funnel entry |
| `final_event_type` | Event with maximum sequence number | Auditable funnel exit |
| Funnel flags | `MAX(1)` when a stage event appears | Home, department, product, cart, purchase, cancel |
| `cart_abandoned_flag` | Cart reached and purchase not reached | Session-level definition |
| `highest_stage` | Highest observed funnel flag | Purchase → Cart → Product → Department → Home |

## Executed evidence

The pre-migration audit showed that event grouping reproduces the old derived artifact exactly, but the old artifact is not used in the corrected pipeline:

- 2,420,661 event rows;
- 680,862 distinct session IDs;
- zero blank session IDs;
- zero sessions containing multiple customer IDs;
- zero sessions containing multiple browsers;
- zero sessions containing multiple traffic sources;
- event count, start, end, customer, browser, channel, and final event all matched the old derived output in the one-time audit.

The final validation is stronger than a comparison with the old work: it checks the event source directly.

## Identity limitation

Event-level customer IDs are sparse:

- 1,124,527 events have no `user_id`;
- 180,862 sessions contain a customer ID;
- 500,000 sessions remain anonymous.

Anonymous sessions are valid for traffic-source and funnel analysis. They cannot be used for customer-demographic, RFM, cohort, or customer-lifetime analysis.

## What this changes downstream

The following remain valid because they use `core.fact_session`, which is now event-derived:

- session counts;
- source/channel distribution;
- product/cart/purchase funnel flags;
- conversion rate;
- cart abandonment;
- browser and country breakdowns;
- session duration;
- event identity coverage;
- A/B-test baseline and power plan.

The event-derived session model does not create product-level cart contents. Product-level cart abandonment remains out of scope.

## Quality gates

The pipeline blocks the build when:

- an event has no session ID;
- the derived session grain is duplicated;
- a session contains multiple users, browsers, or traffic sources;
- distinct event session IDs do not reconcile to fact-session rows;
- source event rows do not reconcile to the sum of session event counts.
