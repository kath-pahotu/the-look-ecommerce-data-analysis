# Dashboard blueprint

This is the 7-page report as built. Page names and groupings match the screenshots in the root `README.md`.

## Global conventions

- Audience: BI/analytics portfolio reviewers and e-commerce leaders.
- Default date filter: complete months through April 2024.
- Global slicers: Date, Country, Traffic Source, Department, Category, Brand, Distribution Center.
- KPI cards include prior-period delta only when the comparison window is complete.
- Use median and P90 together for lead time; display valid-record coverage.
- Use accessible color plus labels/shape; do not depend on color alone.

## Page 1 - Executive Overview

**Question:** Is the business growing profitably and where should leaders focus?

- Cards: Net Sales, Net Profit, Orders, Customers, Session Conversion, Observed Return Rate.
- Line: monthly Net Sales and Net Profit, with partial-period shading.
- Waterfall (sales leakage): Gross Sales -> Cancelled Value -> Returned Value -> Net Sales.
- Ranked bar: top categories by Net Sales.
- Compact matrix: Traffic Source with Sessions, Conversion, Net Sales/Session.
- Callout: partial period and valid delivery-record coverage.

## Page 2 - Acquisition & Funnel

**Question:** Which channels bring volume and quality, and where does the session funnel leak?

- Stage bars/funnel: Sessions -> Product Viewed -> Cart Reached -> Purchase.
- Small multiples: conversion and cart abandonment by month and source.
- Scatter: Sessions (x), Conversion (y), Cart Abandonment (size), session-source labels.
- Separate bar: customer acquisition source by Net Sales and Net Sales per Customer.
- Bar: cart abandonment by Browser and Country, minimum-volume filtered.
- Tooltip: sessions, users, events/session, identity coverage, cart/purchase counts.

## Page 3 - Revenue & Product Mix

**Question:** What drives sales movement, and which products balance demand, sales, and margin?

- Cards: Gross Sales, Net Sales, Leakage %, AOV, Items/Order, Average Selling Price.
- Line: Net Sales with prior year (units-sold trend as secondary series).
- Scatter (value-margin matrix): category Net Sales vs Net Margin %, size by items.
- Ranked bars: top brands by Net Sales; categories by item volume.
- Decomposition tree: Net Sales by Country -> Department -> Category -> Brand -> Source.
- Matrix: year/month performance with MoM and YoY.

## Page 4 - Profitability & Returns

**Question:** How much profit survives leakage, and where do returns concentrate?

- Cards: Net Profit, Net Margin %, Observed Return Rate, Cancelled Value, Returned Value.
- Waterfall (gross-to-net profit bridge): Gross Sales -> Cancelled -> Returned -> Net Sales -> Product Cost -> Net Profit.
- Bar with reference: observed return rate by category (top return drivers), minimum eligible items.
- Return-risk model outputs: ROC AUC, average precision, Brier score, decile lift.
- Methodology callout: synthetic data, observational results, weak model reported honestly and not deployed.

## Page 5 - Customer & Cohort

**Question:** Which customers are valuable, repeat, retained, or at risk?

- Cards: Purchasing Customers, Repeat Customers, Repeat Rate, Net Sales/Customer.
- Heatmap: cohort retention months 0-12.
- Bar: RFM segment size and total Net Sales.
- Scatter: segment recency versus median Net Sales, size by customers.
- Drill-through customer table uses numeric ID only; no PII.

## Page 6 - Operations

**Question:** Where are fulfillment delays and tail risks?

- Cards: Median Ship Days, Median Delivery Days, Median E2E Days, P90 E2E Days, Valid Timeline %.
- Stage bar: order-created -> shipped -> delivered -> returned median days.
- Grouped horizontal bars: median and P90 by Distribution Center.
- Trend: monthly median and P90 E2E.
- SLA breach simulator: what-if parameter on a lead-time threshold, showing the share of orders that would breach.
- Detail table: DC, items, valid coverage, return rate.

## Page 7 - Inventory

**Question:** Where is capital tied up in unsold stock?

- Cards: Inventory Units, Sell-through %, Unsold Cost, 181+ Day Units.
- Stacked bar: inventory age buckets by category.
- Scatter (stock efficiency matrix): sell-through vs median days to sell, size by unsold cost.
- Table: highest unsold retail value by category and DC.

## Tooltip pages

- Channel tooltip: sessions, users, conversion, abandonment, events/session, net sales/session.
- Product tooltip: items, orders, net sales, margin, returns, inventory.
- Operations tooltip: record count, valid coverage, median/P90 lead times.

## Drill-through pages

- Customer (numeric ID only).
- Product.
- Distribution center.
