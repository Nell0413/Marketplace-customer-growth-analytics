"""Run the portfolio project's business analysis and export verified results."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "olist_analytics.db"
RESULTS_DIR = ROOT / "results"


EXPORTS = {
    "monthly_performance": "SELECT * FROM mart_executive_monthly ORDER BY purchase_month",
    "cohort_retention": "SELECT * FROM mart_cohort_retention ORDER BY cohort_month, cohort_period",
    "repeat_purchase_windows": "SELECT * FROM mart_repeat_windows ORDER BY window_days",
    "category_performance": "SELECT * FROM mart_category_performance ORDER BY delivered_gmv_brl DESC",
    "state_performance": "SELECT * FROM mart_state_performance ORDER BY delivered_gmv_brl DESC",
    "delivery_experience": "SELECT * FROM mart_delivery_experience ORDER BY delivery_group",
    "payment_mix": "SELECT * FROM mart_payment_mix ORDER BY payment_value_brl DESC",
    "rfm_segment_summary": "SELECT * FROM mart_rfm_segment_summary ORDER BY observed_gmv_brl DESC",
}


def scalar_row(connection: sqlite3.Connection, query: str) -> dict[str, object]:
    return pd.read_sql_query(query, connection).iloc[0].to_dict()


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        frames: dict[str, pd.DataFrame] = {}
        for name, query in EXPORTS.items():
            frame = pd.read_sql_query(query, connection)
            frame.to_csv(RESULTS_DIR / f"{name}.csv", index=False)
            frames[name] = frame

        overall = scalar_row(
            connection,
            """
            SELECT
                MIN(order_purchase_timestamp) AS first_purchase_timestamp,
                MAX(order_purchase_timestamp) AS last_purchase_timestamp,
                COUNT(DISTINCT order_id) AS delivered_orders,
                COUNT(DISTINCT customer_unique_id) AS observed_customers,
                SUM(item_gmv) AS delivered_gmv_brl,
                SUM(freight_value) AS freight_brl,
                SUM(amount_paid) AS amount_paid_brl,
                SUM(item_gmv) / COUNT(DISTINCT order_id) AS average_order_value_brl,
                SUM(item_count) AS delivered_items,
                AVG(on_time_flag) AS on_time_delivery_rate,
                AVG(delivery_days) AS average_delivery_days,
                AVG(review_score) AS average_review_score,
                AVG(CASE WHEN review_score IS NOT NULL THEN low_review_flag END)
                    AS low_review_rate,
                SUM(CASE WHEN customer_delivered_order_number > 1 THEN item_gmv ELSE 0 END)
                    / SUM(item_gmv) AS repeat_order_gmv_share
            FROM vw_delivered_orders
            """,
        )
        repeat = scalar_row(
            connection,
            """
            WITH repeat_customers AS (
                SELECT customer_unique_id
                FROM mart_customer_lifecycle
                WHERE delivered_orders >= 2
            )
            SELECT
                (SELECT COUNT(*) FROM mart_customer_lifecycle) AS observed_customers,
                (SELECT COUNT(*) FROM repeat_customers) AS repeat_customers,
                (SELECT COUNT(*) FROM repeat_customers) * 1.0
                    / (SELECT COUNT(*) FROM mart_customer_lifecycle)
                    AS repeat_customer_rate,
                SUM(CASE WHEN r.customer_unique_id IS NOT NULL THEN o.item_gmv ELSE 0 END)
                    / SUM(o.item_gmv) AS repeat_customer_gmv_share
            FROM vw_delivered_orders AS o
            LEFT JOIN repeat_customers AS r
              ON o.customer_unique_id = r.customer_unique_id
            """,
        )
        growth = scalar_row(
            connection,
            """
            WITH period AS (
                SELECT
                    substr(purchase_month, 1, 4) AS year,
                    COUNT(DISTINCT order_id) AS orders,
                    COUNT(DISTINCT customer_unique_id) AS customers,
                    SUM(item_gmv) AS gmv
                FROM vw_delivered_orders
                WHERE CAST(substr(purchase_month, 6, 2) AS INTEGER) BETWEEN 1 AND 7
                  AND substr(purchase_month, 1, 4) IN ('2017', '2018')
                GROUP BY year
            )
            SELECT
                MAX(CASE WHEN year = '2017' THEN orders END) AS orders_2017_jan_jul,
                MAX(CASE WHEN year = '2018' THEN orders END) AS orders_2018_jan_jul,
                MAX(CASE WHEN year = '2018' THEN orders END) * 1.0
                    / MAX(CASE WHEN year = '2017' THEN orders END) - 1 AS orders_growth,
                MAX(CASE WHEN year = '2017' THEN gmv END) AS gmv_2017_jan_jul,
                MAX(CASE WHEN year = '2018' THEN gmv END) AS gmv_2018_jan_jul,
                MAX(CASE WHEN year = '2018' THEN gmv END) * 1.0
                    / MAX(CASE WHEN year = '2017' THEN gmv END) - 1 AS gmv_growth,
                MAX(CASE WHEN year = '2018' THEN customers END) * 1.0
                    / MAX(CASE WHEN year = '2017' THEN customers END) - 1 AS customer_growth
            FROM period
            """,
        )

    delivery = frames["delivery_experience"].set_index("delivery_group")
    late = delivery.loc["Late"]
    on_time = delivery.loc["On time or early"]
    repeat_90 = frames["repeat_purchase_windows"].set_index("window_days").loc[90]
    rfm = frames["rfm_segment_summary"].set_index("segment")
    at_risk = rfm.loc["At-risk high-value"]
    states = frames["state_performance"].set_index("customer_state")
    sp = states.loc["SP"]
    rj = states.loc["RJ"]
    ba = states.loc["BA"]
    top_three_state_share = (
        frames["state_performance"].head(3)["delivered_gmv_brl"].sum()
        / overall["delivered_gmv_brl"]
    )

    headline = {
        "overall": overall,
        "repeat": repeat,
        "growth_jan_to_jul_2018_vs_2017": growth,
        "delivery": {
            "late_order_rate": 1 - overall["on_time_delivery_rate"],
            "on_time_average_review": on_time["average_review_score"],
            "late_average_review": late["average_review_score"],
            "on_time_low_review_rate": on_time["low_review_rate"],
            "late_low_review_rate": late["low_review_rate"],
            "low_review_rate_multiple_late_vs_on_time": late["low_review_rate"]
            / on_time["low_review_rate"],
        },
        "retention": {
            "eligible_90_day_customers": int(repeat_90["eligible_customers"]),
            "repeat_within_90_days_customers": int(repeat_90["repeat_customers"]),
            "repeat_within_90_days_rate": repeat_90["repeat_purchase_rate"],
        },
        "rfm_opportunity": {
            "at_risk_high_value_customers": int(at_risk["customers"]),
            "at_risk_high_value_customer_share": at_risk["customer_share"],
            "at_risk_high_value_gmv_brl": at_risk["observed_gmv_brl"],
            "at_risk_high_value_gmv_share": at_risk["observed_gmv_share"],
        },
        "geography": {
            "sp_gmv_share": sp["delivered_gmv_brl"] / overall["delivered_gmv_brl"],
            "top_three_state_gmv_share": top_three_state_share,
            "sp_on_time_rate": sp["on_time_delivery_rate"],
            "rj_on_time_rate": rj["on_time_delivery_rate"],
            "ba_on_time_rate": ba["on_time_delivery_rate"],
        },
    }
    (RESULTS_DIR / "headline_metrics.json").write_text(
        json.dumps(headline, indent=2, default=str), encoding="utf-8"
    )

    summary = f"""# Executive analysis summary

## Scope

- Public, anonymised Olist marketplace data covering {int(overall['delivered_orders']):,} delivered orders and {int(overall['observed_customers']):,} observed customers.
- Purchase period: {str(overall['first_purchase_timestamp'])[:10]} to {str(overall['last_purchase_timestamp'])[:10]}.
- Currency: Brazilian real (BRL).
- `item_gmv` is a GMV proxy based on item price. It is not Olist revenue, profit, or margin.

## Verified headline metrics

- Delivered GMV: BRL {overall['delivered_gmv_brl']:,.2f}; average order value: BRL {overall['average_order_value_brl']:,.2f}.
- Jan-Jul 2018 delivered GMV was {growth['gmv_growth']:.1%} above Jan-Jul 2017, while delivered order volume grew {growth['orders_growth']:.1%}.
- Only {repeat['repeat_customer_rate']:.2%} of observed customers placed at least two delivered orders. Repeat orders generated {overall['repeat_order_gmv_share']:.2%} of delivered GMV.
- The censoring-adjusted 90-day second-purchase rate was {repeat_90['repeat_purchase_rate']:.2%} across {int(repeat_90['eligible_customers']):,} eligible first-time customers.
- {overall['on_time_delivery_rate']:.1%} of delivered orders arrived by the estimated date. Late orders averaged {late['average_review_score']:.2f}/5 versus {on_time['average_review_score']:.2f}/5 for on-time or early orders.
- {late['low_review_rate']:.1%} of reviewed late orders received a score of 1-2, compared with {on_time['low_review_rate']:.1%} of reviewed on-time or early orders - a {late['low_review_rate'] / on_time['low_review_rate']:.1f}x difference. This is an association, not proof of causation.
- The rule-based `At-risk high-value` segment represented {int(at_risk['customers']):,} customers ({at_risk['customer_share']:.1%}) and {at_risk['observed_gmv_share']:.1%} of observed GMV.
- Sao Paulo represented {sp['delivered_gmv_brl'] / overall['delivered_gmv_brl']:.1%} of delivered GMV; the top three states represented {top_three_state_share:.1%}. On-time performance was {sp['on_time_delivery_rate']:.1%} in SP, versus {rj['on_time_delivery_rate']:.1%} in RJ and {ba['on_time_delivery_rate']:.1%} in BA.

## Commercial interpretation

1. **Growth quality:** Growth was strong, but repeat-order contribution remained small. A useful next test would target the second-purchase window rather than relying only on acquisition.
2. **Customer experience:** Delivery lateness is strongly associated with lower review scores. Operations should prioritise high-GMV seller/category/region combinations with weak on-time performance and then measure whether service interventions improve outcomes.
3. **CRM prioritisation:** The rule-based at-risk high-value segment provides a transparent starting audience for a reactivation experiment. It is observed historical value, not predicted lifetime value.
4. **Regional operations:** RJ and BA combine meaningful GMV with lower on-time performance than SP, making them candidates for deeper carrier, route, seller and category analysis.

## Data limitations

- Historical Brazil marketplace data from 2016-2018 is used to demonstrate transferable analytical methods, not to claim current Australian consumer insights.
- The data has no visits, impressions, carts or marketing spend, so it cannot support website conversion, CAC or ROAS.
- The data has no platform commission or cost of goods, so GMV cannot be treated as company revenue, profit or margin.
- Repeat purchase is measured only inside the observation window. It is not true lifetime retention or CLV.
- Delivery and review results are observational; unmeasured product, seller, region and customer factors may influence both.
"""
    (RESULTS_DIR / "executive_summary.md").write_text(summary, encoding="utf-8")
    print(f"Wrote verified results to {RESULTS_DIR}")


if __name__ == "__main__":
    main()

