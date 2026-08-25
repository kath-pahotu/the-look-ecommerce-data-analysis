# TheLook eCommerce - validated analysis findings

## Decision summary

The dataset supports a connected BI story across acquisition, funnel behavior, commercial performance, customer value, product mix, returns, fulfillment, and inventory. Use **net sales** (gross sales less cancelled and returned item value) for executive performance, keep gross sales visible as demand, and treat May 2024 as a partial month.

## Headline metrics

- Data coverage: January 2019 to May 2024; May 2024 is incomplete.
- Gross sales value: $10,796,336.
- Cancelled value: $1,623,638; returned value: $1,076,166.
- Net sales: $8,096,531; net profit: $4,201,367.
- Orders: 124,814; purchasing customers: 80,095.
- Sessions: 680,862; purchase sessions: 180,862; session conversion: 26.6%.
- Cart sessions: 430,614; abandoned cart sessions: 249,752; cart abandonment: 58.0%.
- Repeat-customer rate: 37.3%.

## Growth and period handling

- 2019: $148,302 net sales (complete months only)
- 2020: $484,853 net sales (complete months only)
- 2021: $926,102 net sales (complete months only)
- 2022: $1,583,799 net sales (complete months only)
- 2023: $2,793,942 net sales (complete months only)
- 2024: $1,722,202 net sales (complete months only)

Do not compare the partial 2024 period against full prior years. The dashboard marks incomplete months and period measures use the complete-period flag.

## Acquisition and funnel

- Email: 306,377 sessions, 26.6% conversion, 58.0% cart abandonment
- Adwords: 203,690 sessions, 26.5% conversion, 58.0% cart abandonment
- YouTube: 68,524 sessions, 26.5% conversion, 58.1% cart abandonment
- Facebook: 68,518 sessions, 26.8% conversion, 57.9% cart abandonment
- Organic: 33,753 sessions, 26.4% conversion, 58.2% cart abandonment

Traffic volume is concentrated in Email and Adwords. Every session field is rebuilt inside SQL by grouping `events.csv` on `session_id`; no source session file is used. `events.user_id` is missing on many individual events, but a session can still be linked when one of its events identifies the user.

Customer acquisition-source value is analyzed separately because its taxonomy (Search, Display, Organic, Facebook, Email) does not align one-to-one with session channels:

- Search: 56,086 customers, 87,383 orders, $5,670,117 net sales, $101 per customer
- Organic: 11,949 customers, 18,599 orders, $1,199,982 net sales, $100 per customer
- Facebook: 4,796 customers, 7,571 orders, $494,458 net sales, $103 per customer
- Email: 4,058 customers, 6,280 orders, $412,225 net sales, $102 per customer
- Display: 3,206 customers, 4,981 orders, $319,750 net sales, $100 per customer

## Product and commercial performance

- Men - Outerwear & Coats: $664,594 net sales, $371,425 profit, 55.9% margin, 29.8% observed return rate
- Men - Jeans: $591,181 net sales, $276,794 profit, 46.8% margin, 27.9% observed return rate
- Men - Suits & Sport Coats: $469,628 net sales, $280,452 profit, 59.7% margin, 28.4% observed return rate
- Men - Sweaters: $395,699 net sales, $197,608 profit, 49.9% margin, 30.4% observed return rate
- Women - Jeans: $357,112 net sales, $163,926 profit, 45.9% margin, 27.3% observed return rate

High volume, high revenue, and high margin are not interchangeable. The Product page therefore uses a sales-versus-margin quadrant with item volume and return rate as context.

## Operations and inventory

- Inventory units: 488,146; sold units: 180,862; sell-through: 37.1%.
- Unsold inventory cost: $8,833,075; aged 181+ day units: 272,822.
- 35,440 order-item rows (19.6%) have `shipped_at < created_at`. Delivery metrics exclude those rows and display valid-record coverage.

## Advanced analytics

1. **Gini coefficient & Lorenz curve** on net customer spend quantifies revenue concentration —
   the basis for prioritizing retention economics over blanket acquisition spend.
2. **RFM clustering** segments 66,215 customers into three action-oriented groups. It is suitable for lifecycle targeting and dashboard drill-through.
3. **Return propensity modeling** uses a time-based holdout and pre-outcome features only. Test ROC AUC is 0.501 and top-decile lift is 0.99x. This weak signal is an honest dataset finding; the model is a portfolio demonstration, not a production score.

## Material limitations

- This is a synthetic dataset; patterns are analytical demonstrations, not evidence about a real company.
- Order and item status behave like snapshot categories. Net sales excludes Cancelled and Returned; gross sales remains available.
- Product-level cart abandonment cannot be attributed reliably because cart/purchase events do not contain cart contents or order IDs.
- External delivery benchmarks were not added; set SLA targets based on the portfolio scenario or verified market sources.
