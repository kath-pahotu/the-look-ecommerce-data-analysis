# Power BI semantic model

```mermaid
erDiagram
    dim_date ||--o{ fact_order : order_date_key
    dim_date ||--o{ fact_order_item : order_date_key
    dim_date ||--o{ fact_session : session_date_key
    dim_date ||--o{ fact_inventory : inventory_created_date_key
    dim_customer ||--o{ fact_order : customer_id
    dim_customer ||--o{ fact_order_item : customer_id
    dim_customer ||--o{ fact_session : customer_id
    dim_product ||--o{ fact_order_item : product_id
    dim_product ||--o{ fact_inventory : product_id
    dim_distribution_center ||--o{ fact_order_item : distribution_center_id
    dim_distribution_center ||--o{ fact_inventory : distribution_center_id
    dim_session_traffic_source ||--o{ fact_session : traffic_source
    dim_acquisition_source ||--o{ fact_order : acquisition_source
    dim_acquisition_source ||--o{ fact_order_item : acquisition_source
```

## Relationship rules

| From | To | Cardinality | Filter |
|---|---|---|---|
| `dim_date[date_key]` | each fact date key | 1:* | Single |
| `dim_customer[user_id]` | customer facts | 1:* | Single |
| `dim_product[product_id]` | item/inventory facts | 1:* | Single |
| `dim_distribution_center[distribution_center_id]` | item/inventory facts | 1:* | Single |
| `dim_session_traffic_source[traffic_source]` | session source | 1:* | Single |
| `dim_acquisition_source[acquisition_source]` | order/item acquisition source | 1:* | Single |

Marts and advanced outputs should normally remain disconnected or connect only to the exact conformed dimension keys they contain. Never create a shortcut relationship that produces multiple active filter paths.

Session traffic source and customer acquisition source are intentionally separate dimensions because their source labels are not a one-to-one taxonomy.


## Session-source lineage

`fact_session` is not imported from an original session file. The backend builds it from `events.csv` grouped by `session_id`, then exports the modeled fact to Power BI. `dim_session_traffic_source` is a small modeled dimension created from the distinct traffic-source values in those derived sessions.
