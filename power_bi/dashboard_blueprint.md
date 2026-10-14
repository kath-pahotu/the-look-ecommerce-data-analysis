# Dashboard blueprint

7-page report. Default date filter uses complete months through April 2024. Global slicers: Date, Country, Traffic Source, Department, Category, Brand, Distribution Center.

## Page 1 — Executive Overview

KPI cards (Net Sales, Net Profit, Orders, Customers, Conversion, Return Rate), monthly trend with partial-period shading, sales-leakage waterfall, top categories bar.

## Page 2 — Acquisition & Funnel

Session funnel by channel (Sessions → Product View → Cart → Purchase), conversion and abandonment by month/source, acquisition-source value bar.

## Page 3 — Revenue & Product Mix

Gross/Net Sales cards, prior-year trend line, category value-margin scatter, top brands bar, decomposition tree by geography/department/category.

## Page 4 — Profitability & Returns

Gross-to-net profit bridge waterfall, return rate by category, return-risk model summary (AUC, lift, honest weak-result callout).

## Page 5 — Customer & Cohort

Purchasing/repeat customer cards, cohort retention heatmap, RFM segment bars and scatter.

## Page 6 — Operations

Median/P90 lead-time cards, delivery stages bar, lead time by distribution center, SLA breach what-if parameter.

## Page 7 — Inventory

Sell-through cards, age-bucket stacked bar, stock-efficiency scatter (sell-through vs. days to sell), unsold cost table.

## Page 8 — Plan & Commercial Performance

**Purpose:** answer "are we on plan, and why did the number move?" in one screen.

Top row of cards: Net Sales, Plan Net Sales, Plan Achievement %, Markets Below Plan, Bridge Residual (shows 0 — proof the bridge ties).

Left: Price-Volume-Mix waterfall from `price_volume_mix`, with a comparison slicer bound to `comparison_label` so the reader can switch between CY2023 vs CY2022, YTD 2024 vs 2023, and the latest month. Right: category contribution table with Volume / Mix / Price columns, conditional-formatted on Total variance.

Bottom: plan achievement by market as a horizontal bar with a reference line at 100%, conditional colour from `[Plan Status]`. Drill-through to a country detail page showing the monthly plan-vs-actual line.

Slicers: Region, Country, Department, Comparison.

## Page 9 — Forecast, Scenarios & Plan Landing

**Purpose:** answer "are we going to land the year?"

Top row: Expected Net Sales, Plan Net Sales, Expected Achievement %, Gap to Plan, Backtest MAPE, Champion Model (the last two make the validation visible rather than implied).

Main chart: Actual / Forecast / Plan lines over the plan horizon from `forecast_vs_plan`, with the forecast segment dotted.

Right panel: scenario comparison bars (Base / Upside / Downside) on Net Sales and Net Profit, with the stated assumption shown as a tooltip from `forecast_scenarios[narrative]`.

Interactive: a **Volume Adjustment** what-if parameter (-20% to +20%, 1% increment) feeding `[Adjusted Forecast]` and `[Adjusted Achievement %]`, so a stakeholder can flex the assumption live in the review.

Bottom strip: backtest table by model (MAPE, worst month, bias) — included deliberately so the weakest benchmark is visible next to the chosen model.

## Page 10 — Data Quality & Reconciliation

**Purpose:** the page you open when someone asks whether the numbers can be trusted.

Cards: Blocking Test Failures (0), Quarantined Plan Rows, Plan Rows Accepted %.

Table 1: `plan_validation` — check, severity, failures, status, and what it protects. Conditional formatting: PASS green, WARN amber, FAIL red.

Table 2: `reconciliation_statement` — source file through to mart, rows and value at each stage with the delta between stages.

Table 3: `plan_rejects` — the quarantined rows with their reason, framed as the list to send back to the submitting region.
