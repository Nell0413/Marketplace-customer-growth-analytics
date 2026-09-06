"""Small synthetic regression suite; no Kaggle download or Power BI required.

Run from the repository root: python -m unittest discover -s tests -v
These tests exercise the production transformation and SQL, not copied formulas.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_project", ROOT / "src/build_project.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

FILENAMES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def synthetic_sources(purchases=None):
    """One customer ID per order, with a stable person ID across repeat orders."""
    if purchases is None:
        purchases = [
            ("o1", "person1", "2018-01-01 12:00:00", "delivered"),
            ("o2", "person2", "2018-01-02 12:00:00", "delivered"),
            ("o3", "person3", "2018-01-03 12:00:00", "delivered"),
        ]
    customers, orders, items, payments, reviews = [], [], [], [], []
    for index, (order_id, person, timestamp, status) in enumerate(purchases):
        purchased = pd.Timestamp(timestamp)
        customers.append({
            "customer_id": f"customer-{order_id}", "customer_unique_id": person,
            "customer_city": "sao paulo", "customer_state": "SP",
            "customer_zip_code_prefix": 1000,
        })
        orders.append({
            "order_id": order_id, "customer_id": f"customer-{order_id}",
            "order_status": status, "order_purchase_timestamp": purchased,
            "order_approved_at": purchased + pd.Timedelta(hours=1),
            "order_delivered_carrier_date": purchased + pd.Timedelta(days=1),
            "order_delivered_customer_date": purchased + pd.Timedelta(
                days=10 if index % 2 == 0 else 2
            ),
            "order_estimated_delivery_date": purchased + pd.Timedelta(days=7),
        })
        items.append({
            "order_id": order_id, "order_item_id": 1, "product_id": "p1",
            "seller_id": "s1", "shipping_limit_date": purchased + pd.Timedelta(days=2),
            "price": 100.0, "freight_value": 5.0,
        })
        payments.append({
            "order_id": order_id, "payment_sequential": 1, "payment_type": "credit_card",
            "payment_installments": 1, "payment_value": 105.0,
        })
        if index < 2:
            reviews.append({
                "review_id": f"r-{order_id}", "order_id": order_id,
                "review_score": 1 if index == 0 else 5,
                "review_creation_date": purchased + pd.Timedelta(days=11),
                "review_answer_timestamp": purchased + pd.Timedelta(days=12),
            })
    # One order has two items, two payment rows and two review rows: a naive
    # all-table join would multiply item value. Later orders have no reviews.
    items.append({**items[0], "order_item_id": 2, "price": 50.0})
    payments.append({
        **payments[0], "payment_sequential": 2, "payment_type": "voucher", "payment_value": 55.0,
    })
    reviews.append({**reviews[0], "review_id": "second-review"})
    return {
        "customers": pd.DataFrame(customers),
        "orders": pd.DataFrame(orders),
        "order_items": pd.DataFrame(items),
        "order_payments": pd.DataFrame(payments),
        "order_reviews": pd.DataFrame(reviews),
        "geolocation": pd.DataFrame({"geolocation_zip_code_prefix": [1000]}),
        "products": pd.DataFrame([{
            "product_id": "p1", "product_category_name": "livros",
            "product_name_lenght": 10, "product_description_lenght": 20,
            "product_photos_qty": 1, "product_weight_g": 100,
            "product_length_cm": 10, "product_height_cm": 1, "product_width_cm": 10,
        }]),
        "sellers": pd.DataFrame([{
            "seller_id": "s1", "seller_city": "sao paulo", "seller_state": "SP",
        }]),
        "category_translation": pd.DataFrame([{
            "product_category_name": "livros", "product_category_name_english": "books",
        }]),
    }


def query_model(sources, query):
    """Use the real SQLite loader and production views in an isolated database."""
    tables = build.build_tables(sources, build.validate_raw(sources))
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary) / "analytics.db"
        with patch.object(build, "DB_PATH", database):
            build.load_sqlite(sources, tables)
        with closing(sqlite3.connect(database)) as connection:
            return connection.execute(query).fetchall()


class RawValidationTests(unittest.TestCase):
    def test_duplicate_orders_fail_loudly(self):
        sources = synthetic_sources()
        sources["orders"] = pd.concat([sources["orders"], sources["orders"].iloc[[0]]])
        with self.assertRaisesRegex(ValueError, "duplicate_order_ids.*1"):
            build.validate_raw(sources)

    def test_duplicate_order_item_keys_fail_loudly(self):
        sources = synthetic_sources()
        sources["order_items"] = pd.concat([
            sources["order_items"], sources["order_items"].iloc[[0]],
        ])
        with self.assertRaisesRegex(ValueError, "duplicate_order_item_keys.*1"):
            build.validate_raw(sources)

    def test_orphan_item_relationships_fail_loudly(self):
        for column, check in [
            ("order_id", "orphan_item_orders"),
            ("product_id", "orphan_item_products"),
            ("seller_id", "orphan_item_sellers"),
        ]:
            with self.subTest(column=column):
                sources = synthetic_sources()
                sources["order_items"].loc[0, column] = "missing-parent"
                with self.assertRaisesRegex(ValueError, check + ".*1"):
                    build.validate_raw(sources)


class MetricRegressionTests(unittest.TestCase):
    def test_multiple_items_payments_and_reviews_do_not_multiply_gmv(self):
        sources = synthetic_sources()
        tables = build.build_tables(sources, build.validate_raw(sources))
        self.assertEqual(len(tables["fact_orders"]), 3)
        self.assertEqual(len(tables["fact_sales"]), 4)
        self.assertAlmostEqual(tables["fact_orders"]["item_gmv"].sum(), 350.0)
        self.assertAlmostEqual(tables["fact_sales"]["price"].sum(), 350.0)
        self.assertAlmostEqual(tables["checks"]["gmv_reconciliation_difference"], 0.0)
        first = tables["fact_orders"].set_index("order_id").loc["o1"]
        self.assertEqual(first["item_count"], 2)
        self.assertEqual(first["review_count"], 2)
        self.assertAlmostEqual(first["amount_paid"], 160.0)

    def test_missing_review_stays_null_and_is_not_a_positive_review(self):
        sources = synthetic_sources()
        tables = build.build_tables(sources, build.validate_raw(sources))
        missing = tables["fact_orders"].set_index("order_id").loc["o3"]
        self.assertTrue(pd.isna(missing["review_score"]))
        self.assertTrue(pd.isna(missing["low_review_flag"]))
        self.assertAlmostEqual(tables["checks"]["review_coverage_delivered_orders"], 2 / 3)

    def test_missing_reviews_are_excluded_from_sql_rate_denominators(self):
        sources = synthetic_sources()
        state = query_model(sources, "SELECT low_review_rate, average_review_score FROM mart_state_performance")
        self.assertEqual(state, [(0.5, 3.0)])
        delivery = dict(query_model(sources, "SELECT delivery_group, low_review_rate FROM mart_delivery_experience"))
        self.assertEqual(delivery, {"Late": 1.0, "On time or early": 0.0})

    def test_all_missing_reviews_produce_null_not_zero(self):
        sources = synthetic_sources()
        sources["order_reviews"] = sources["order_reviews"].iloc[0:0]
        result = query_model(sources, "SELECT low_review_rate, average_review_score FROM mart_state_performance")
        self.assertEqual(result, [(None, None)])

    def test_90_day_boundary_is_inclusive_and_censored_customers_are_excluded(self):
        sources = synthetic_sources([
            ("a1", "at-boundary", "2018-01-01 12:00:00", "delivered"),
            ("a-cancelled", "at-boundary", "2018-01-02 12:00:00", "canceled"),
            ("a2", "at-boundary", "2018-04-01 12:00:00", "delivered"),
            ("b1", "one-second-late", "2018-01-01 12:00:00", "delivered"),
            ("b2", "one-second-late", "2018-04-01 12:00:01", "delivered"),
            ("c1", "recent-repeat", "2018-04-15 12:00:00", "delivered"),
            ("c2", "recent-repeat", "2018-04-20 12:00:00", "delivered"),
            ("d1", "exact-followup", "2018-01-31 12:00:00", "delivered"),
            ("e1", "short-followup", "2018-02-01 12:00:00", "delivered"),
            ("end", "observation-end", "2018-05-01 12:00:00", "delivered"),
        ])
        result = query_model(sources, "SELECT eligible_customers, repeat_customers, repeat_purchase_rate FROM mart_repeat_windows WHERE window_days = 90")
        # Eligible: at-boundary, one-second-late, exact-followup. Only the
        # first repeats within <=90 elapsed days. Recent repeat is censored.
        eligible, repeated, rate = result[0]
        self.assertEqual((eligible, repeated), (3, 1))
        self.assertAlmostEqual(rate, 1 / 3)
        lifecycle = dict(query_model(sources, "SELECT customer_unique_id, days_to_second_order FROM mart_customer_lifecycle"))
        self.assertAlmostEqual(lifecycle["at-boundary"], 90.0)
        self.assertGreater(lifecycle["one-second-late"], 90.0)

    def test_no_eligible_90_day_customers_returns_null_rate(self):
        result = query_model(synthetic_sources(), "SELECT eligible_customers, repeat_customers, repeat_purchase_rate FROM mart_repeat_windows WHERE window_days = 90")
        self.assertEqual(result, [(0, 0, None)])


class PathPortabilityTests(unittest.TestCase):
    def test_build_runs_from_outside_a_relocated_repository_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="marketplace-tests-") as temporary:
            relocated = Path(temporary) / "relocated project with spaces"
            outside = Path(temporary) / "unrelated working directory"
            outside.mkdir()
            for folder in ["src", "sql", "data/raw"]:
                (relocated / folder).mkdir(parents=True)
            shutil.copy2(ROOT / "src/build_project.py", relocated / "src/build_project.py")
            shutil.copy2(ROOT / "sql/01_create_analytics_views.sql", relocated / "sql/01_create_analytics_views.sql")
            for name, frame in synthetic_sources().items():
                frame.to_csv(relocated / "data/raw" / FILENAMES[name], index=False)
            process = subprocess.run(
                [sys.executable, str(relocated / "src/build_project.py")],
                cwd=outside, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertFalse((outside / "data").exists())
            self.assertFalse((outside / "results").exists())
            report = json.loads((relocated / "results/data_quality_report.json").read_text())
            self.assertEqual(report["fact_order_rows"], 3)
            self.assertAlmostEqual(report["delivered_gmv_from_order_fact"], 350.0)
            self.assertEqual(len(list((relocated / "data/processed").glob("*.csv"))), 7)
            with closing(sqlite3.connect(relocated / "data/processed/olist_analytics.db")) as connection:
                rate = connection.execute("SELECT low_review_rate FROM mart_state_performance").fetchone()[0]
                self.assertAlmostEqual(rate, 0.5)


if __name__ == "__main__":
    unittest.main()
