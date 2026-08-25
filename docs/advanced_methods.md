# Advanced methods: statistical & modeling deep-dives

## 1. Gini coefficient & Lorenz curve

**Why it fits:** revenue concentration is a direct question about equity of spending across the customer base.

**Method:** compute the Gini coefficient on net customer spend, validate the formula against known extreme/mild-inequality examples, then plot the Lorenz curve.

**Value:** quantifies whether retention economics on a high-value tail beat blanket acquisition spend.

**Limitations:** a single summary statistic; it does not identify *which* customers to act on (RFM segmentation below does that).

## 2. RFM customer clustering

**Why it fits:** order history supports recency, frequency, monetary value, profit, and return behavior at customer grain.

**Method:** log-transform R/F/M, robust scale, compare K=2..8 using silhouette and inertia, select three action-oriented clusters (k=3, the silhouette-optimal choice), and publish customer assignments plus profiles.

**Value:** CRM targeting, lifecycle campaigns, VIP service, reactivation, and segment drill-through in Power BI.

**Limitations:** clusters describe observed behavior; they do not prove a treatment will work.

## 3. Return-propensity classification

**Why it fits:** Complete versus Returned item outcomes can be modeled from pre-outcome product, customer, price, order, time, and fulfillment-location features.

**Method:** eligibility restriction to Complete/Returned items, time-based train/test split, one-hot encoding, class-balanced logistic regression, ROC AUC, average precision, Brier score, coefficient review, decile lift, and leakage audit.

**Value:** portfolio-grade predictive workflow, risk-monitoring page, feature-gap diagnosis, and a blueprint for production scoring.

**Decision rule:** do not deploy if out-of-time lift is weak. The honest result on synthetic data is itself an analytical conclusion.
