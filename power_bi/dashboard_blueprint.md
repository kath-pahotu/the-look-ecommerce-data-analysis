# The Look Ecommerce — Dashboard Blueprint

A build spec for a 7-page Power BI report. Each page answers one business
question; each visual on a page handles one specific point; together the visuals
answer the page, and together the pages tell the whole performance story.

**Build source rule**
- **Interactive, sliceable visuals** → build from the **star** (`dim_*` + `fact_*` + your measures). These respond to global slicers.
- **Specialised pre-aggregated visuals** (cohort heatmap, RFM, funnel, DC percentiles) → build **directly from the matching mart** table. They are pre-computed and mostly *not* sliced.

---

## 1. Global design system

### Big title (report banner, every page)
- **Title:** `The Look — E-commerce Performance`
- **Per-page kicker** above/below it in smaller text: the page name (`Executive Overview`, `Acquisition & Funnel`, …).

### Subtitle (dynamic, one text/card)
Create a measure and put it in a Card (or use in a text box via a field):
```
_Subtitle =
"Apparel retail  ·  "
 & FORMAT ( MIN ( dim_date[calendar_date] ), "MMM yyyy" ) & " – "
 & FORMAT ( MAX ( dim_date[calendar_date] ), "MMM yyyy" )
 & "  ·  Updated " & FORMAT ( NOW (), "dd MMM yyyy" )
```
Reads: `Apparel retail · Jan 2022 – Aug 2024 · Updated 11 Aug 2026`. It restates
data coverage so no one misreads a partial period.

### Layout grid (keep identical on every page)
- **Top band (~90px):** title + subtitle (left), global slicers (right).
- **KPI row (~120px):** 5–6 cards.
- **Body:** a 2×2 or 2×3 grid of visuals.
- **Footer (~40px):** one-line "so what" insight text box (dynamic where useful).
- Left rail: the **Page navigator** you already built.

### Colour usage (from `theme.json`)
- Navy `#2D3A6E` = primary metric / main series.
- Ink `#051319` = text and the "bad/negative" emphasis (returns, cancellations).
- Periwinkle `#C9CEEC` = secondary / comparison series.
- Keep one meaning per colour across all pages (e.g. returns always ink).

---

## 2. Global filters and monitoring "knobs"

Put these in the top band, **sync across all pages** (View → Sync slicers).

| Knob | Field | Type | Purpose |
|---|---|---|---|
| **Date range** | `dim_date[calendar_date]` | Between slicer | The master time filter |
| **Category** | `dim_product[category]` | Dropdown | Product focus |
| **Country** | `dim_customer[country]` | Dropdown | Market focus |
| **Channel** | `dim_session_traffic_source[traffic_source]` | Dropdown | Traffic focus |
| **Gender / Age** | `dim_customer[gender]`, `[age_band]` | Dropdown (collapsed panel) | Demographic focus |

**Advanced knobs (the value-add):**
- **Metric selector (field parameter):** `{ Net Sales, Net Profit, Orders, AOV }` → lets one trend chart switch measures. Modeling → New parameter → Fields.
- **Breakdown selector (field parameter):** `{ Category, Brand, Country, Channel }` → lets one bar chart switch its dimension. Kills 4 redundant charts.
- **What-if: Net Margin target %** → numeric parameter (e.g. 0–50%) drawn as a reference line on margin visuals, so viewers test "are we above target?"
- **Bookmarks:** `Reset filters` button; a slide-in **filter panel** (show/hide bookmark) to keep the canvas clean.
- **Drillthrough pages:** hidden `Product detail`, `Customer detail`, `DC detail` pages reached by right-click → Drillthrough.
- **Report-page tooltips:** a mini tooltip page (sparkline + 3 KPIs) shown on hover over category/brand bars.

**Exclude the incomplete final month** from trend comparisons: add a page/visual
filter `dim_date[is_complete_month] = 1` on trend charts (or use
`sales_monthly[is_complete_month] = 1`).

---

## 3. Pages

Legend for each visual: **Type · Answers · Data · Elements · Why it's here · Advanced**

---

### PAGE 1 — Executive Overview
**Main question: What is happening overall, and is it good or bad?**

**KPI cards (row of 6)** — all from measures; format as noted:
| Card | Measure | Format |
|---|---|---|
| Net Sales | `[Net Sales]` | `$ #,0`, Millions |
| Net Profit | `[Net Profit]` | `$ #,0`, Millions |
| Net Margin % | `[Net Margin %]` | `0.0%` |
| Orders | `[Orders]` | `#,0` |
| Avg Order Value | `[Average Order Value]` | `$ #,0.0` |
| Return Rate | `[Return Rate]` | `0.0%` |

Add each card's **YoY %** as the callout's secondary value (`[Net Sales YoY %]`) so
every headline shows direction, not just level.

**Body visuals:**
1. **Monthly sales & profit trend** — *Line/combo* · "Is the business growing?" · X `dim_date[month_start]`, Y `[Net Sales]` + `[Net Profit]`, line `[Net Margin %]` on a secondary axis · Title "Net sales & profit by month", legend on, note "excludes incomplete final month" · Anchors the whole page in one trend. · *Advanced:* attach the **Metric selector** field parameter so execs flip Sales/Profit/Orders.
2. **Channel contribution** — *Stacked bar* · "Which channels drive sales?" · Axis **`fact_order_item[acquisition_source]`** (NOT `traffic_source` — that lives on sessions and is unrelated to sales; see note), value `[Net Sales]` · Sorted desc · Shows concentration/dependence on a channel. · No pie — bars compare length better.
   > ⚠️ **traffic_source vs acquisition_source:** `traffic_source` (dim_session_traffic_source) relates only to `fact_session` — use it for SESSION measures. `acquisition_source` (on fact_order_item / dim_customer) is the SALES channel — use it for sales/profit. A measure can only be sliced by a dimension related to its own table.
3. **Category drivers** — *Bar* · "Which categories drive sales & margin?" · From `mart.product_performance_category`: axis `category`, value `net_sales_value`, colour by `net_margin_rate` (conditional) · Surfaces high-sales-but-low-margin categories. · *Advanced:* data-bar conditional formatting on margin.
4. **Sales leakage callout** — *KPI + small bar* · "How much are we losing to cancels/returns?" · `[Cancelled Value]`, `[Returned Value]`, `[Sales Leakage %]` · Frames the operational pages that follow.

**Footer insight (dynamic text):** e.g. *"Net margin is [Net Margin %]; returns cost [Returned Value] this period."*

---

### PAGE 2 — Acquisition & Funnel
**Main question: Which channels create engagement and purchases, and where do carts fail?**

**KPI cards:** `[Sessions]`, `[Session Conversion Rate]`, `[Cart Abandonment Rate]`, `[Purchase Sessions]`, `[Identified Session Rate]`.

**Body visuals:**
1. **Conversion funnel** — *Funnel visual* · "Where do we lose visitors?" · From `mart.funnel_stage_channel`: category `stage` (ordered by `stage_order`), value `stage_sessions` · Title "Session → View → Cart → Purchase" · The single clearest drop-off picture. · *Advanced:* slice by channel via the Channel knob (funnel_monthly/stage has `traffic_source`).
2. **Channel quality matrix** — *Table/matrix* · "Which channel converts best, not just biggest?" · From `mart.channel_quality`: rows `traffic_source`; cols `sessions`, `session_conversion_rate`, `cart_abandonment_rate` · Conditional colour on conversion · Separates *volume* from *quality*.
3. **Monthly conversion trend** — *Line* · "Is conversion improving?" · From `mart.funnel_monthly_channel`: X `month_start`, Y `session_conversion_rate`, legend `traffic_source` · Trend, not snapshot.
4. **Cart abandonment by segment** — *Bar* · "Where specifically do carts fail?" · From `mart.cart_abandonment_segments`: axis `segment_value`, value `cart_abandonment_rate`, slicer `segment_type` (browser / source / country) · Pinpoints the failing surface. · *Advanced:* `segment_type` as a slicer turns 3 charts into 1.

---

### PAGE 3 — Revenue & Product
**Main question: What drives sales and margin at the product level?**

**KPI cards:** `[Net Sales]`, `[Net Profit]`, `[Gross Margin %]`, `[Units Sold]`, `[Average Selling Price]`.

**Body visuals:**
1. **Category: sales vs margin** — *Scatter* · "Which categories are big AND profitable?" · From `mart.product_performance_category`: X `net_sales_value`, Y `net_margin_rate`, size `items`, play/legend `department` · The value/margin quadrant view. · *Advanced:* add average reference lines to form four quadrants (star / trap / niche / drag).
2. **Top brands table** — *Matrix* · "Which brands earn their shelf space?" · From `mart.product_performance_brand`: rows `brand`; `net_sales_value`, `net_margin_rate`, `observed_return_rate` · Sort by sales; colour return-rate red · One row per decision.
3. **Price-band mix** — *Stacked column* · "Where does revenue sit by price tier?" · Star: axis `dim_product[price_band]`, value `[Net Sales]` · Shows premium vs budget reliance.
4. **Decomposition tree** — *Decomposition tree* · "Why did sales change — drill freely." · `[Net Sales]` broken by `department` → `category` → `brand` · Self-serve root-cause. · *Advanced:* enable AI "high/low" splits.

---

### PAGE 4 — Customer & Cohort
**Main question: Who is valuable, and are we retaining them?**

**KPI cards:** `[Customers]`, `[Sales per Customer]`, `[Orders per Customer]`, **Repeat Customer Rate**, **New Customers**.
Supporting measures (add):
```
Repeat Customer Rate =
DIVIDE (
    CALCULATE ( COUNTROWS ( customer_360 ), customer_360[repeat_customer_flag] = 1 ),
    COUNTROWS ( customer_360 )
)
Customers (360) = COUNTROWS ( customer_360 )
```

**Body visuals:**
1. **Cohort retention heatmap** — *Matrix (colour scale)* · "How well do we retain by signup cohort?" · From `mart.cohort_retention`: rows `cohort_month`, cols `months_since_first_order`, values `retention_rate` · Background colour scale (theme sequential) · The definitive retention picture.
2. **RFM / value segments** — *Scatter or bar* · "Who are our best customers?" · From `mart.customer_360`: X `recency_days`, Y `order_count`, size `net_sales_value` (or bucket into segments) · Targets marketing spend. · *Advanced:* build an RFM segment calc column (High/Mid/Low) and colour by it.
3. **Repeat vs one-time trend** — *Line/column* · "Is loyalty growing?" · `customer_360[first_order_cohort_month]` vs repeat flag over time · Long-run health signal.
4. **Value by acquisition source** — *Bar* · "Which channel brings valuable customers?" · From `mart.acquisition_source_value`: axis `acquisition_source`, value `net_sales_per_customer` · Connects acquisition (Page 2) to lifetime value.

---

### PAGE 5 — Geography
**Main question: Where is performance strongest / weakest?**

**KPI cards:** `[Net Sales]`, `[Customers]`, `[Average Order Value]`, `[Return Rate]` (all respond to the Country knob).

**Body visuals:**
1. **Sales map** — *Filled map* · "Where does revenue come from?" · From `mart.geography_performance_country`: location `country`, colour saturation `net_sales_value` · Instant geographic read. · Use `dim_customer[latitude/longitude]` only if you need city bubbles.
2. **Country performance matrix** — *Matrix* · "Rank markets on value and quality." · rows `country`; `net_sales_value`, `average_order_value`, `observed_return_rate` · Sort by sales; flag high return-rate markets.
3. **AOV vs return rate scatter** — *Scatter* · "Which markets are high-value but high-risk?" · X `average_order_value`, Y `observed_return_rate`, size `orders` · Finds markets needing policy attention.

---

### PAGE 6 — Operations: Delivery & Returns
**Main question: Which fulfilment stage or centre needs work?**
> Lead-time visuals use measures that already exclude `valid_timeline_flag = 0`,
> or the mart columns which are computed on valid timelines only.

**KPI cards:** `[Avg Ship Lead Days]`, `[Avg Delivery Lead Days]`, `[Avg End to End Lead Days]`, `[Return Rate]`, `[Cancellation Rate]`.

**Body visuals:**
1. **Lead-time trend** — *Line* · "Is fulfilment getting faster or slower?" · From `mart.operations_monthly`: X `month_start`, Y `median_delivery_lead_days` + `p90_delivery_lead_days` · Median = typical, P90 = worst-case tail. · *Advanced:* shade the median–P90 band to show consistency.
2. **DC performance** — *Bar (median + P90)* · "Which distribution centre is slow?" · From `mart.delivery_performance_dc`: axis `distribution_center_name`, values `median_end_to_end_lead_days`, `p90_end_to_end_lead_days` · Pinpoints the centre to fix.
3. **Return-risk segments** — *Bar* · "Where do returns concentrate?" · From `mart.return_risk_segments`: axis `segment_value`, value `observed_return_rate`, slicer `segment_type`, size by `returned_value` · Prioritises returns work by $ impact.
4. **Invalid-timeline note** — *Card/text* · "Data-quality transparency." · Count/% of `valid_timeline_flag = 0` excluded · Shows rigour (ties to your QA layer).

---

### PAGE 7 — Inventory
**Main question: Where is stock slow, aged, or tying up cash?**

**KPI cards:** `[Inventory Units]`, `[Sell Through Rate]`, `[Avg Days to Sell]`, `[Unsold Inventory Cost]`, `[Unsold Inventory Retail Value]`.

**Body visuals:**
1. **Sell-through by category** — *Bar* · "What sells through vs sits?" · From `mart.inventory_performance`: axis `category`, value `sell_through_rate` · Ranks stock efficiency.
2. **Aging buckets** — *Column* · "How much stock is old?" · `aged_181_plus_units` by `category`/`distribution_center_name` · Flags write-down risk.
3. **Unsold value treemap** — *Treemap* · "Where is cash trapped?" · size `unsold_inventory_cost`, group `department`→`category` · Cash-at-risk at a glance.
4. **Days-to-sell distribution** — *Bar* · "How fast does stock move by DC?" · `median_days_to_sell`, `p90_days_to_sell` by `distribution_center_name` · Operational tail view.

---

## 4. Build-support checklist

**Before visuals work:**
- Relationships: 12 clean fact→dim (see model); marts stay unrelated.
- `dim_date` **marked as a date table** on `calendar_date` (for time intelligence).
- Global slicers created once and **synced** across pages.

**Extra measures to add (beyond the 48):**
- `_Subtitle` (above), `Repeat Customer Rate`, `Customers (360)`.
- Optional: `New Customers = CALCULATE(COUNTROWS(customer_360), customer_360[repeat_customer_flag]=0)`.

**Calculated columns (optional, for segmentation):**
- `customer_360` RFM tier (High/Mid/Low) from `recency_days`, `order_count`, `net_sales_value`.
- `dim_product` — already has `price_band`; reuse it.

**Field parameters to create:** Metric selector, Breakdown selector (Section 2).
**What-if parameter:** Net Margin target %.
**Drillthrough pages:** Product detail, Customer detail, DC detail.

---

## 5. How the pages ladder up
1 **Overview** → *what & how much* → 2 **Acquisition** → *how they arrive* →
3 **Product** → *what they buy* → 4 **Customer** → *who they are & do they stay* →
5 **Geography** → *where* → 6 **Operations** → *how well we deliver* →
7 **Inventory** → *what stock supports it all*.
Each page ends one question and hands the next page its natural follow-up.
