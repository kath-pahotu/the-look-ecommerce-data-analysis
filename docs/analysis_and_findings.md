# Analysis & Findings

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

## Business questions & findings

### 1. Acquisition, onsite behavior, and funnel

**Questions addressed:** Which traffic sources drive session volume, purchase conversion, and acquisition-attributed value? Where do sessions exit between product view, cart, and purchase? Which channels show high cart abandonment? Is channel concentration creating growth risk?

| Channel | Sessions | Conversion | Cart Abandonment |
|---|---|---|---|
| Email | 306,377 | 26.6% | 58.0% |
| Adwords | 203,690 | 26.5% | 58.0% |
| YouTube | 68,524 | 26.5% | 58.1% |
| Facebook | 68,518 | 26.8% | 57.9% |
| Organic | 33,753 | 26.4% | 58.2% |

Traffic volume is concentrated in Email and Adwords. Every session field is rebuilt inside SQL by grouping `events.csv` on `session_id`; no source session file is used. `events.user_id` is missing on many individual events, but a session can still be linked when one of its events identifies the user.

Customer acquisition-source value is analyzed separately because its taxonomy (Search, Display, Organic, Facebook, Email) does not align one-to-one with session channels:

| Acquisition Source | Customers | Orders | Net Sales | Per Customer |
|---|---|---|---|---|
| Search | 56,086 | 87,383 | $5,670,117 | $101 |
| Organic | 11,949 | 18,599 | $1,199,982 | $100 |
| Facebook | 4,796 | 7,571 | $494,458 | $103 |
| Email | 4,058 | 6,280 | $412,225 | $102 |
| Display | 3,206 | 4,981 | $319,750 | $100 |

By country, China is the single largest net-sales market, ahead of every other country individually (including the United States, which ranks second) — see `mart.geography_performance_country` for the full breakdown. *(This paragraph reflects a dashboard read; the exact dollar figure populates automatically after the next `--rebuild`.)*

### 2. Revenue and growth

**Questions addressed:** How do gross sales, net sales, profit, customers, orders, and AOV move over time? Is growth driven by volume or basket value? Which trends are valid after excluding the incomplete latest month?

| Year | Net Sales (complete months) |
|---|---|
| 2019 | $148,302 |
| 2020 | $484,853 |
| 2021 | $926,102 |
| 2022 | $1,583,799 |
| 2023 | $2,793,942 |
| 2024 | $1,722,202 |

Do not compare the partial 2024 period against full prior years. The dashboard marks incomplete months and period measures use the complete-period flag.

### 3. Product and commercial performance

**Questions addressed:** Which categories lead sales, profit, units, and margin? Which high-volume products underperform on revenue or profit? Which product groups show elevated observed return rate?

| Category | Net Sales | Profit | Margin | Return Rate |
|---|---|---|---|---|
| Men - Outerwear & Coats | $664,594 | $371,425 | 55.9% | 29.8% |
| Men - Jeans | $591,181 | $276,794 | 46.8% | 27.9% |
| Men - Suits & Sport Coats | $469,628 | $280,452 | 59.7% | 28.4% |
| Men - Sweaters | $395,699 | $197,608 | 49.9% | 30.4% |
| Women - Jeans | $357,112 | $163,926 | 45.9% | 27.3% |

High volume, high revenue, and high margin are not interchangeable. The Product page therefore uses a sales-versus-margin quadrant with item volume and return rate as context.

### 4. Customers and lifecycle

**Questions addressed:** How large is the repeat-customer base? Which acquisition cohorts retain purchase activity? Which RFM segments should receive retention, reactivation, or VIP treatment?

Champions make up only 29.5% of segmented customers (19,550 of 66,215) but generate 63.3% of the combined Champions+Hibernating net sales ($4,388,338 vs. $2,546,517 from 33,688 Hibernating customers) — a small, high-value segment outweighing a much larger dormant one. Full segment profiles are in Advanced methods below.

### 5. Operations, delivery, returns, and inventory

**Questions addressed:** How long are order-to-ship, ship-to-delivery, and end-to-end stages? Which distribution centers have high median or tail (P90) lead time? Which inventory groups have low sell-through or aged unsold value?

- Inventory units: 488,146; sold units: 180,862; sell-through: 37.1%.
- Unsold inventory cost: $8,833,075; aged 181+ day units: 272,822.
- 35,440 order-item rows (19.6%) have `shipped_at < created_at`. Delivery metrics exclude those rows and display valid-record coverage.

## Advanced methods

### 1. Gini coefficient & Lorenz curve

**Why it fits:** revenue concentration is a direct question about equity of spending across the customer base.

**Method:** compute the Gini coefficient on net customer spend, validate the formula against known extreme/mild-inequality examples, then plot the Lorenz curve (see `notebooks/02_statistical_deep_dives.ipynb`).

**Value:** quantifies whether retention economics on a high-value tail beat blanket acquisition spend. It is a single summary statistic; it does not identify *which* customers to act on — RFM segmentation below does that.

### 2. RFM customer clustering

**Why it fits:** order history supports recency, frequency, monetary value, profit, and return behavior at customer grain.

**Method:** log-transform R/F/M, robust scale, compare K=2..8 using silhouette and inertia, and select 3 action-oriented clusters (silhouette 0.33).

**Result:** 66,215 customers segmented into 3 groups.

| Segment | Customers | Median Recency | Total Net Sales |
|---|---|---|---|
| Champions | 19,550 | 190 days | $4,388,338 |
| New / Developing | 12,977 | 32 days | $1,161,676 |
| Hibernating | 33,688 | 502 days | $2,546,517 |

**Value:** CRM targeting, lifecycle campaigns, VIP service, reactivation, and segment drill-through in Power BI. Clusters describe observed behavior; they do not prove a treatment will work.

### 3. Return-propensity classification

**Why it fits:** Complete versus Returned item outcomes can be modeled from pre-outcome product, customer, price, order, time, and fulfillment-location features.

**Method:** eligibility restriction to Complete/Returned items, time-based train/test split, one-hot encoding, class-balanced logistic regression, ROC AUC, average precision, Brier score, coefficient review, decile lift, and leakage audit.

**Result:** test ROC AUC is 0.501 and top-decile lift is 0.99x. This weak signal is an honest dataset finding — the model is a portfolio demonstration, not a production score.

**Decision rule:** do not deploy if out-of-time lift is weak. The honest result on synthetic data is itself an analytical conclusion.

### 4. Market-basket association rules

**Why it fits:** co-purchased categories inform cross-sell and merchandising design.

**Method:** category-level association mining over eligible multi-item orders, ranked by lift with support and pair count retained as guards.

**Result:** 488 directional category rules from 93,696 eligible orders. Use lift with support and pair count; do not rank on lift alone.

The data has no randomized assignment table, so a historical A/B effect cannot be estimated. A forward-looking power plan is included instead (see `docs/technical_reference.md`).

## Material limitations

- This is a synthetic dataset; patterns are analytical demonstrations, not evidence about a real company.
- Order and item status behave like snapshot categories. Net sales excludes Cancelled and Returned; gross sales remains available.
- Product-level cart abandonment cannot be attributed reliably because cart/purchase events do not contain cart contents or order IDs.
- External delivery benchmarks were not added; set SLA targets based on the portfolio scenario or verified market sources.
