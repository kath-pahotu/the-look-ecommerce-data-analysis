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

Targets are not hard-coded because the dataset has no owner-approved business plan or verified external benchmark. Use baseline distributions to propose provisional ranges, then replace them with approved targets.
