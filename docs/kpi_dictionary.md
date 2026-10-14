# KPI dictionary

| KPI | Definition | Grain / denominator | Primary source | Caveat |
|---|---|---|---|---|
| Gross Sales | Sum of `sale_price` for all order items | item | `fact_order_item` | Demand value before leakage |
| Cancelled Value | Sum of `sale_price` where status = Cancelled | item | `fact_order_item` | Snapshot status |
| Returned Value | Sum of `sale_price` where status = Returned | item | `fact_order_item` | Snapshot status |
| Net Sales | Gross Sales - Cancelled Value - Returned Value | item | `fact_order_item` | Primary executive sales KPI |
| Net Profit | Sum of sale price - product cost for non-cancelled/non-returned items | item | `fact_order_item` | Excludes overhead, tax, and logistics |
| Net Margin % | Net Profit / Net Sales | item | `fact_order_item` | Use non-zero denominator |
| Orders | Distinct `order_id` | order | item fact or order fact | Use distinct count on item fact |
| Customers | Distinct purchasing `customer_id` | customer | item fact | Not all registered users |
| AOV | Net Sales / Orders | order | item fact | Excludes cancellations and returns |
| Items per Order | Item rows / distinct orders | order | item fact | Gross item count |
| Sessions | Distinct `events.session_id` values | session | `fact_session` | Reconstructed from event rows |
| Purchase Sessions | Sessions containing a purchase event | session | `fact_session` | Not number of orders |
| Session Conversion % | Purchase Sessions / Sessions | session | `fact_session` | Channel-quality outcome |
| Cart Abandonment % | Cart sessions without purchase / cart sessions | session | `fact_session` | Cannot attribute to product |
| Event Identity Coverage % | Events with user_id / events within derived session | event/session | `fact_session` | Anonymous sessions remain in funnel denominators |
| Repeat Customer % | Customers with 2+ orders / purchasing customers | customer | `customer_360` | Snapshot lifetime measure |
| Purchase Cohort Retention % | Customers purchasing in month N / cohort size | cohort customer | `cohort_retention` | E-commerce repeat purchase, not subscription retention |
| Observed Return % | Returned / (Complete + Returned) items | eligible item | `fact_order_item` | Avoids incomplete-status censoring |
| Item Cancellation % | Cancelled items / all items | item | `fact_order_item` | Snapshot status |
| Median End-to-End Days | Median valid created-to-delivered days | delivered item | item fact | Invalid timestamp sequences excluded |
| P90 End-to-End Days | 90th percentile valid created-to-delivered days | delivered item | item fact | Tail service metric |
| Sell-through % | Sold inventory items / inventory items | inventory item | `fact_inventory` | As of max event date |
| Aged Inventory Cost | Cost of unsold units aged 181+ days | inventory item | `fact_inventory` | Synthetic inventory snapshot |

## Commercial planning KPIs

These back dashboard pages 8 and 9 and the Excel management pack. Plan figures
originate from a constructed planning scenario, not from source data - see
[`commercial_analytics.md`](commercial_analytics.md) section 1.

| KPI | Definition | Grain / denominator | Primary source | Caveat |
|---|---|---|---|---|
| Plan Net Sales | Submitted regional target, converted to USD at the fixed budget FX rate | country x month | `core.fact_plan` | Accepted submissions only; quarantined rows excluded |
| Plan Units | Submitted unit target | country x month | `core.fact_plan` | Same exclusion as above |
| Plan Achievement % | Actual Net Sales / Plan Net Sales | country x month | `mart.plan_vs_actual_monthly` | Undefined where no plan exists; shown as "Actual with no plan" |
| Plan Variance | Actual Net Sales - Plan Net Sales | country x month | `mart.plan_vs_actual_monthly` | USD at budget rate, not spot |
| Plan Status | On or above plan / Within 5% / Below plan / No plan | country x month | `mart.plan_vs_actual_monthly` | 95% band is a stated convention, not an approved tolerance |
| Average Selling Price (ASP) | Net Sales / net units, computed within a category and period | category x period | `mart.price_volume_mix` | Net of cancelled and returned units |
| Volume Effect | (Q1 - Q0) x prior mix share x prior ASP | category x comparison | `mart.price_volume_mix` | Growth held at prior mix and prior price |
| Mix Effect | Q1 x (current share - prior share) x prior ASP | category x comparison | `mart.price_volume_mix` | Share is of total units, not revenue |
| Price Effect | Current units x (current ASP - prior ASP) | category x comparison | `mart.price_volume_mix` | Not price elasticity; this is realised ASP movement |
| Bridge Residual | Volume + Mix + Price - Total Variance | comparison | `mart.price_volume_mix` | Must be 0; asserted below $0.01 by `pvm_decomposition_is_exact` |
| Forecast Net Sales | Point forecast from the backtest-selected model | month | `mart.forecast_monthly` | Global; country split is top-down by trailing 6-month share |
| Backtest MAPE | Mean absolute percentage error, rolling origin, 1 month ahead | model | `mart.forecast_accuracy` | Optimistic: synthetic growth is smoother than real demand |
| Forecast Bias | Mean of (predicted / actual - 1) across backtest folds | model | `mart.forecast_accuracy` | Published because the lowest-MAPE model is biased low |
| Expected Net Sales | Actual where the month is complete, forecast beyond | month | `mart.forecast_vs_plan` | Mixed basis; the `basis` column states which |
| Expected Achievement % | Expected Net Sales / Plan Net Sales | month | `mart.forecast_vs_plan` | Landing estimate, not a commitment |
| Scenario Net Profit | Scenario Net Sales x assumed margin rate | scenario x month | `mart.forecast_scenarios` | Margin assumption is stated per scenario |
| Plan Rows Accepted % | Accepted rows / submitted rows | submission | `core.fact_plan`, `qa.plan_rejects` | Currently 287 / 292 |

## Conformed dimensions

| Attribute | Definition | Caveat |
|---|---|---|
| Canonical Country | Market name after mapping source spellings via `seeds/country_master.csv` | 16 observed spellings resolve to 13 markets; 3 were aliases |
| Region | AMER / EMEA / APAC roll-up of canonical country | Assigned in the seed, not derived from the data |
| Fiscal Year | Group fiscal year starting 1 October; FY2024 = Oct 2023 to Sep 2024 | The start month is an assumption, set in `02_core_dimensions.sql` |

## On targets

The transactional dataset ships no owner-approved business plan and no verified external benchmark, so no target is hard-coded against the sales KPIs above. The planning layer supplies targets for Net Sales and Units only, and those come from a constructed planning scenario built on a documented rule rather than from an approved budget. Treat every achievement figure as a demonstration of the variance *method*. Operational KPIs (lead time, sell-through, return rate) still carry no target; use baseline distributions to propose provisional ranges and replace them with approved targets.
