from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import chi2_contingency, kruskal, norm
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
    silhouette_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler


RANDOM_STATE = 42
PALETTE = {
    "blue": "#2457A7",
    "gold": "#C9952E",
    "orange": "#D8783F",
    "olive": "#7E8D42",
    "pink": "#C46686",
    "ink": "#20242C",
    "grid": "#D9DEE7",
}


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close()


def rfm_segmentation(
    connection: duckdb.DuckDBPyConnection, output_dir: Path, figure_dir: Path
) -> dict[str, object]:
    customers = connection.execute(
        """
        SELECT customer_id, recency_days, order_count, net_sales_value,
               net_profit_value, observed_return_rate, country, acquisition_source
        FROM mart.customer_360
        WHERE net_sales_value > 0 AND order_count > 0
        """
    ).fetchdf()
    model_data = pd.DataFrame(
        {
            "recency": np.log1p(customers["recency_days"].clip(lower=0)),
            "frequency": np.log1p(customers["order_count"]),
            "monetary": np.log1p(customers["net_sales_value"]),
        }
    )
    scaler = RobustScaler()
    scaled = scaler.fit_transform(model_data)

    diagnostics: list[dict[str, float]] = []
    sample_size = min(12000, len(customers))
    rng = np.random.default_rng(RANDOM_STATE)
    sample_index = rng.choice(len(customers), size=sample_size, replace=False)
    for k in range(3, 7):
        candidate = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20)
        labels = candidate.fit_predict(scaled)
        diagnostics.append(
            {
                "k": k,
                "inertia": float(candidate.inertia_),
                "silhouette": float(
                    silhouette_score(scaled[sample_index], labels[sample_index])
                ),
            }
        )

    selected_k = 3
    model = KMeans(n_clusters=selected_k, random_state=RANDOM_STATE, n_init=30)
    customers["cluster_id"] = model.fit_predict(scaled)
    profile = (
        customers.groupby("cluster_id", as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            median_recency_days=("recency_days", "median"),
            mean_order_count=("order_count", "mean"),
            median_net_sales=("net_sales_value", "median"),
            total_net_sales=("net_sales_value", "sum"),
            mean_return_rate=("observed_return_rate", "mean"),
        )
    )
    profile["value_score"] = (
        profile["mean_order_count"].rank(pct=True)
        + profile["median_net_sales"].rank(pct=True)
        - profile["median_recency_days"].rank(pct=True)
    )
    ordered_clusters = profile.sort_values("value_score", ascending=False)[
        "cluster_id"
    ].tolist()
    ordered_labels = [
        "Champions",
        "New / Developing",
        "Hibernating",
    ]
    label_map = dict(zip(ordered_clusters, ordered_labels, strict=True))
    customers["segment"] = customers["cluster_id"].map(label_map)
    profile["segment"] = profile["cluster_id"].map(label_map)
    profile = profile.sort_values("value_score", ascending=False)

    customers.to_csv(output_dir / "customer_rfm_segments.csv", index=False)
    profile.to_csv(output_dir / "customer_rfm_segment_profiles.csv", index=False)
    pd.DataFrame(diagnostics).to_csv(
        output_dir / "customer_rfm_k_selection.csv", index=False
    )

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {
        "Champions": PALETTE["blue"],
        "New / Developing": PALETTE["gold"],
        "Hibernating": PALETTE["orange"],
    }
    plot_sample = customers.sample(min(12000, len(customers)), random_state=RANDOM_STATE)
    for segment, group in plot_sample.groupby("segment"):
        ax.scatter(
            group["recency_days"],
            group["net_sales_value"],
            s=np.clip(group["order_count"] * 8, 12, 80),
            alpha=0.35,
            label=segment,
            color=colors[segment],
            edgecolors="none",
        )
    ax.set_title("Customer RFM segments")
    ax.set_xlabel("Recency (days since last order)")
    ax.set_ylabel("Net sales per customer (USD)")
    ax.set_yscale("log")
    ax.legend(title="Segment", frameon=False)
    save_figure(figure_dir / "rfm_segments.png")

    return {
        "customers_segmented": int(len(customers)),
        "selected_k": selected_k,
        "silhouette_selected_k": next(
            row["silhouette"] for row in diagnostics if row["k"] == selected_k
        ),
        "segments": profile[
            [
                "segment",
                "customers",
                "median_recency_days",
                "mean_order_count",
                "median_net_sales",
                "total_net_sales",
            ]
        ].to_dict(orient="records"),
    }


def return_propensity_model(
    connection: duckdb.DuckDBPyConnection, output_dir: Path, figure_dir: Path
) -> dict[str, object]:
    features = connection.execute(
        """
        WITH brand_volume AS (
            SELECT p.brand, COUNT(*) AS items,
                   ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, p.brand) AS brand_rank
            FROM core.fact_order_item f
            JOIN core.dim_product p ON f.product_id = p.product_id
            GROUP BY p.brand
        )
        SELECT
            f.order_item_id,
            f.order_item_created_at::DATE AS order_date,
            f.returned_item_flag AS return_flag,
            f.sale_price,
            f.unit_cost,
            f.gross_margin_rate,
            o.item_count AS order_item_count,
            p.category,
            p.department,
            CASE WHEN b.brand_rank <= 100 THEN p.brand ELSE 'Other brands' END AS brand_group,
            CAST(f.distribution_center_id AS VARCHAR) AS distribution_center,
            c.age,
            c.age_band,
            c.gender,
            c.country,
            c.acquisition_source,
            CAST(EXTRACT(month FROM f.order_item_created_at) AS VARCHAR) AS order_month,
            CAST(EXTRACT(isodow FROM f.order_item_created_at) AS VARCHAR) AS order_weekday
        FROM core.fact_order_item f
        JOIN core.fact_order o ON f.order_id = o.order_id
        JOIN core.dim_product p ON f.product_id = p.product_id
        JOIN core.dim_customer c ON f.customer_id = c.user_id
        JOIN brand_volume b ON p.brand = b.brand
        WHERE f.return_observation_eligible_flag = 1
        """
    ).fetchdf()
    features["order_date"] = pd.to_datetime(features["order_date"])
    train = features[features["order_date"] < "2023-01-01"].copy()
    test = features[features["order_date"] >= "2023-01-01"].copy()
    target = "return_flag"
    identifiers = ["order_item_id", "order_date", target]
    categorical = [
        "category",
        "department",
        "brand_group",
        "distribution_center",
        "age_band",
        "gender",
        "country",
        "acquisition_source",
        "order_month",
        "order_weekday",
    ]
    numeric = [
        "sale_price",
        "unit_cost",
        "gross_margin_rate",
        "order_item_count",
        "age",
    ]

    preprocessor = ColumnTransformer(
        [
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    min_frequency=20,
                    sparse_output=True,
                ),
                categorical,
            ),
            ("numeric", RobustScaler(), numeric),
        ]
    )
    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    solver="saga",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    pipeline.fit(train[categorical + numeric], train[target])
    probabilities = pipeline.predict_proba(test[categorical + numeric])[:, 1]
    predictions = test[identifiers].copy()
    predictions["return_probability"] = probabilities
    predictions["risk_decile"] = (
        pd.qcut(
            predictions["return_probability"],
            10,
            labels=False,
            duplicates="drop",
        )
        + 1
    )
    predictions.to_csv(output_dir / "return_propensity_scores_test.csv", index=False)

    lift = (
        predictions.groupby("risk_decile", as_index=False)
        .agg(
            items=("order_item_id", "count"),
            returned_items=("return_flag", "sum"),
            avg_predicted_probability=("return_probability", "mean"),
            observed_return_rate=("return_flag", "mean"),
        )
        .sort_values("risk_decile", ascending=False)
    )
    baseline = float(test[target].mean())
    lift["lift_vs_baseline"] = lift["observed_return_rate"] / baseline
    lift.to_csv(output_dir / "return_propensity_decile_lift.csv", index=False)

    transformer = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]
    coefficient_table = pd.DataFrame(
        {
            "feature": transformer.get_feature_names_out(),
            "coefficient": classifier.coef_[0],
        }
    )
    coefficient_table["absolute_coefficient"] = coefficient_table[
        "coefficient"
    ].abs()
    coefficient_table = coefficient_table.sort_values(
        "absolute_coefficient", ascending=False
    )
    coefficient_table.to_csv(
        output_dir / "return_propensity_coefficients.csv", index=False
    )

    roc_auc = float(roc_auc_score(test[target], probabilities))
    average_precision = float(average_precision_score(test[target], probabilities))
    brier = float(brier_score_loss(test[target], probabilities))
    top_decile = lift.iloc[0]

    fig, ax = plt.subplots(figsize=(9, 5))
    ordered = lift.sort_values("risk_decile")
    ax.bar(
        ordered["risk_decile"].astype(str),
        ordered["observed_return_rate"],
        color=PALETTE["blue"],
    )
    ax.axhline(
        baseline,
        color=PALETTE["ink"],
        linestyle="--",
        linewidth=1.5,
        label=f"Baseline {baseline:.1%}",
    )
    ax.set_title("Observed return rate by model risk decile")
    ax.set_xlabel("Risk decile (10 = highest predicted risk)")
    ax.set_ylabel("Observed return rate")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.legend(frameon=False)
    save_figure(figure_dir / "return_model_lift.png")

    return {
        "eligible_rows": int(len(features)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_end": "2022-12-31",
        "test_start": "2023-01-01",
        "test_return_rate": baseline,
        "roc_auc": roc_auc,
        "average_precision": average_precision,
        "brier_score": brier,
        "top_decile_return_rate": float(top_decile["observed_return_rate"]),
        "top_decile_lift": float(top_decile["lift_vs_baseline"]),
        "interpretation": (
            "AUC near 0.50 indicates limited predictive signal in the available "
            "pre-outcome features; use this as a methodology demonstration, not a "
            "production scoring system."
        ),
    }


def market_basket(
    connection: duckdb.DuckDBPyConnection, output_dir: Path, figure_dir: Path
) -> dict[str, object]:
    rules = connection.execute(
        """
        WITH eligible AS (
            SELECT DISTINCT f.order_id, p.category
            FROM core.fact_order_item f
            JOIN core.dim_product p ON f.product_id = p.product_id
            WHERE f.net_sales_value > 0
        ),
        total AS (
            SELECT COUNT(DISTINCT order_id)::DOUBLE AS total_orders FROM eligible
        ),
        counts AS (
            SELECT category, COUNT(DISTINCT order_id)::DOUBLE AS category_orders
            FROM eligible GROUP BY category
        ),
        pairs AS (
            SELECT
                a.category AS category_a,
                b.category AS category_b,
                COUNT(DISTINCT a.order_id)::DOUBLE AS pair_orders
            FROM eligible a
            JOIN eligible b
              ON a.order_id = b.order_id
             AND a.category < b.category
            GROUP BY a.category, b.category
            HAVING COUNT(DISTINCT a.order_id) >= 25
        ),
        directional AS (
            SELECT category_a AS antecedent, category_b AS consequent, pair_orders FROM pairs
            UNION ALL
            SELECT category_b, category_a, pair_orders FROM pairs
        )
        SELECT
            d.antecedent,
            d.consequent,
            d.pair_orders::BIGINT AS pair_orders,
            d.pair_orders / t.total_orders AS support,
            d.pair_orders / ca.category_orders AS confidence,
            (d.pair_orders / ca.category_orders) /
                (cb.category_orders / t.total_orders) AS lift,
            ca.category_orders::BIGINT AS antecedent_orders,
            cb.category_orders::BIGINT AS consequent_orders,
            t.total_orders::BIGINT AS eligible_orders
        FROM directional d
        JOIN counts ca ON d.antecedent = ca.category
        JOIN counts cb ON d.consequent = cb.category
        CROSS JOIN total t
        ORDER BY lift DESC, pair_orders DESC
        """
    ).fetchdf()
    rules.to_csv(output_dir / "category_association_rules.csv", index=False)
    top_rules = rules[rules["support"] >= rules["support"].quantile(0.50)].head(15)

    fig, ax = plt.subplots(figsize=(10, 6))
    labels = top_rules["antecedent"] + " -> " + top_rules["consequent"]
    ax.barh(
        labels.iloc[::-1],
        top_rules["lift"].iloc[::-1],
        color=PALETTE["olive"],
    )
    ax.axvline(1.0, color=PALETTE["ink"], linestyle="--", linewidth=1.2)
    ax.set_title("Category association-rule lift")
    ax.set_xlabel("Lift (>1 indicates positive association)")
    ax.set_ylabel("")
    save_figure(figure_dir / "category_association_rules.png")

    return {
        "rules_generated": int(len(rules)),
        "eligible_orders": int(rules["eligible_orders"].iloc[0]) if len(rules) else 0,
        "top_rules": rules.head(10)[
            ["antecedent", "consequent", "pair_orders", "support", "confidence", "lift"]
        ].to_dict(orient="records"),
    }


def experiment_power_plan(
    connection: duckdb.DuckDBPyConnection, output_dir: Path
) -> dict[str, object]:
    cart_sessions, purchase_sessions = connection.execute(
        """
        SELECT SUM(cart_flag), SUM(CASE WHEN cart_flag = 1 THEN purchase_flag ELSE 0 END)
        FROM core.fact_session
        """
    ).fetchone()
    baseline = purchase_sessions / cart_sessions
    rows: list[dict[str, float]] = []
    for power in (0.80, 0.90):
        for absolute_mde in (0.01, 0.02, 0.03):
            p1 = baseline
            p2 = min(0.999, p1 + absolute_mde)
            p_bar = (p1 + p2) / 2
            numerator = (
                norm.ppf(1 - 0.05 / 2) * math.sqrt(2 * p_bar * (1 - p_bar))
                + norm.ppf(power)
                * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
            ) ** 2
            sample_per_variant = math.ceil(numerator / absolute_mde**2)
            rows.append(
                {
                    "baseline_cart_to_purchase_rate": baseline,
                    "absolute_mde": absolute_mde,
                    "relative_mde": absolute_mde / baseline,
                    "alpha": 0.05,
                    "power": power,
                    "sample_per_variant": sample_per_variant,
                    "total_sample": sample_per_variant * 2,
                }
            )
    plan = pd.DataFrame(rows)
    plan.to_csv(output_dir / "ab_test_power_plan.csv", index=False)
    return {
        "baseline_cart_to_purchase_rate": float(baseline),
        "plans": plan.to_dict(orient="records"),
        "note": (
            "The dataset has no randomized assignment or exposure table, so no "
            "historical A/B effect is estimated. This is a forward-looking power plan."
        ),
    }


def hypothesis_tests(
    connection: duckdb.DuckDBPyConnection, output_dir: Path
) -> dict[str, object]:
    return_table = connection.execute(
        """
        SELECT p.category, f.returned_item_flag, COUNT(*) AS items
        FROM core.fact_order_item f
        JOIN core.dim_product p ON f.product_id = p.product_id
        WHERE f.return_observation_eligible_flag = 1
        GROUP BY p.category, f.returned_item_flag
        """
    ).fetchdf()
    contingency = return_table.pivot(
        index="category", columns="returned_item_flag", values="items"
    ).fillna(0)
    chi2, p_value, _, _ = chi2_contingency(contingency)
    total = contingency.to_numpy().sum()
    min_dimension = min(contingency.shape) - 1
    cramers_v = math.sqrt(chi2 / (total * min_dimension))

    lead_time = connection.execute(
        """
        SELECT CAST(distribution_center_id AS VARCHAR) AS distribution_center,
               ship_lead_days
        FROM core.fact_order_item
        WHERE ship_lead_days IS NOT NULL AND valid_timeline_flag = 1
        """
    ).fetchdf()
    groups = [
        group["ship_lead_days"].to_numpy()
        for _, group in lead_time.groupby("distribution_center")
        if len(group) >= 30
    ]
    kruskal_stat, kruskal_p = kruskal(*groups)

    results = {
        "return_rate_by_category": {
            "test": "Chi-square independence test",
            "chi_square": float(chi2),
            "p_value": float(p_value),
            "cramers_v": float(cramers_v),
            "interpretation": (
                "Statistical significance should be interpreted with Cramer's V; "
                "large samples can make negligible differences significant."
            ),
        },
        "ship_lead_time_by_distribution_center": {
            "test": "Kruskal-Wallis rank test",
            "statistic": float(kruskal_stat),
            "p_value": float(kruskal_p),
            "groups": len(groups),
            "interpretation": (
                "This is an association test, not causal evidence. Invalid source "
                "timestamp sequences are excluded."
            ),
        },
    }
    (output_dir / "hypothesis_test_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    return results


def run(project_root: Path) -> dict[str, object]:
    output_dir = project_root / "data" / "processed" / "advanced"
    figure_dir = project_root / "artifacts" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(
        str(project_root / "artifacts" / "thelook_analytics.duckdb"),
        read_only=True,
    )
    try:
        results = {
            "rfm_segmentation": rfm_segmentation(connection, output_dir, figure_dir),
            "return_propensity": return_propensity_model(
                connection, output_dir, figure_dir
            ),
            "market_basket": market_basket(connection, output_dir, figure_dir),
            "experiment_power": experiment_power_plan(connection, output_dir),
            "hypothesis_tests": hypothesis_tests(connection, output_dir),
        }
    finally:
        connection.close()
    metrics_path = project_root / "artifacts" / "advanced_metrics.json"
    metrics_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.project_root.resolve())


if __name__ == "__main__":
    main()
