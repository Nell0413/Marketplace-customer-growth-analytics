"""Build the local analytical model for the Olist portfolio project.

The script keeps each source table's grain intact, creates order- and item-level
facts, produces conformed dimensions, loads a SQLite analytical database, and
exports Power BI-ready CSV files. It intentionally avoids claiming that the
local build is an Azure deployment.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
SQL_FILE = ROOT / "sql" / "01_create_analytics_views.sql"
DB_PATH = PROCESSED_DIR / "olist_analytics.db"


def load_sources() -> dict[str, pd.DataFrame]:
    """Load all nine public files with explicit timestamp parsing."""
    return {
        "customers": pd.read_csv(RAW_DIR / "olist_customers_dataset.csv"),
        "geolocation": pd.read_csv(RAW_DIR / "olist_geolocation_dataset.csv"),
        "order_items": pd.read_csv(
            RAW_DIR / "olist_order_items_dataset.csv",
            parse_dates=["shipping_limit_date"],
        ),
        "order_payments": pd.read_csv(RAW_DIR / "olist_order_payments_dataset.csv"),
        "order_reviews": pd.read_csv(
            RAW_DIR / "olist_order_reviews_dataset.csv",
            parse_dates=["review_creation_date", "review_answer_timestamp"],
        ),
        "orders": pd.read_csv(
            RAW_DIR / "olist_orders_dataset.csv",
            parse_dates=[
                "order_purchase_timestamp",
                "order_approved_at",
                "order_delivered_carrier_date",
                "order_delivered_customer_date",
                "order_estimated_delivery_date",
            ],
        ),
        "products": pd.read_csv(RAW_DIR / "olist_products_dataset.csv"),
        "sellers": pd.read_csv(RAW_DIR / "olist_sellers_dataset.csv"),
        "category_translation": pd.read_csv(
            RAW_DIR / "product_category_name_translation.csv"
        ),
    }


def validate_raw(sources: dict[str, pd.DataFrame]) -> dict[str, object]:
    """Run source-level checks that should fail loudly if the inputs change."""
    customers = sources["customers"]
    orders = sources["orders"]
    items = sources["order_items"]
    products = sources["products"]
    sellers = sources["sellers"]

    checks = {
        "raw_row_counts": {name: int(len(df)) for name, df in sources.items()},
        "duplicate_customer_ids": int(customers["customer_id"].duplicated().sum()),
        "duplicate_order_ids": int(orders["order_id"].duplicated().sum()),
        "duplicate_product_ids": int(products["product_id"].duplicated().sum()),
        "duplicate_seller_ids": int(sellers["seller_id"].duplicated().sum()),
        "duplicate_order_item_keys": int(
            items.duplicated(["order_id", "order_item_id"]).sum()
        ),
        "orphan_item_orders": int((~items["order_id"].isin(orders["order_id"])).sum()),
        "orphan_item_products": int(
            (~items["product_id"].isin(products["product_id"])).sum()
        ),
        "orphan_item_sellers": int(
            (~items["seller_id"].isin(sellers["seller_id"])).sum()
        ),
        "negative_item_prices": int((items["price"] < 0).sum()),
        "negative_freight_values": int((items["freight_value"] < 0).sum()),
    }

    required_zero = [
        "duplicate_customer_ids",
        "duplicate_order_ids",
        "duplicate_product_ids",
        "duplicate_seller_ids",
        "duplicate_order_item_keys",
        "orphan_item_orders",
        "orphan_item_products",
        "orphan_item_sellers",
        "negative_item_prices",
        "negative_freight_values",
    ]
    failures = {key: checks[key] for key in required_zero if checks[key] != 0}
    if failures:
        raise ValueError(f"Raw-data validation failed: {failures}")
    return checks


def build_tables(
    sources: dict[str, pd.DataFrame], checks: dict[str, object]
) -> dict[str, pd.DataFrame]:
    """Create facts, dimensions, and a customer segmentation mart."""
    customers = sources["customers"].copy()
    orders = sources["orders"].copy()
    items = sources["order_items"].copy()
    payments = sources["order_payments"].copy()
    reviews = sources["order_reviews"].copy()
    products = sources["products"].copy()
    sellers = sources["sellers"].copy()
    translation = sources["category_translation"].copy()

    products = products.merge(translation, on="product_category_name", how="left")
    products["product_category_name_english"] = products[
        "product_category_name_english"
    ].fillna("unknown")

    item_enriched = items.merge(
        products[["product_id", "product_category_name_english"]],
        on="product_id",
        how="left",
        validate="many_to_one",
    )
    item_enriched["product_category_name_english"] = item_enriched[
        "product_category_name_english"
    ].fillna("unknown")

    item_order = (
        item_enriched.groupby("order_id", as_index=False)
        .agg(
            item_gmv=("price", "sum"),
            freight_value=("freight_value", "sum"),
            item_count=("order_item_id", "count"),
            seller_count=("seller_id", "nunique"),
            category_count=("product_category_name_english", "nunique"),
        )
    )

    payment_order = (
        payments.groupby("order_id", as_index=False)
        .agg(
            amount_paid=("payment_value", "sum"),
            max_installments=("payment_installments", "max"),
            payment_method_count=("payment_type", "nunique"),
        )
    )
    payment_by_type = (
        payments.groupby(["order_id", "payment_type"], as_index=False)[
            "payment_value"
        ]
        .sum()
        .sort_values(["order_id", "payment_value"], ascending=[True, False])
    )
    primary_payment = payment_by_type.drop_duplicates("order_id").rename(
        columns={"payment_type": "primary_payment_type"}
    )[["order_id", "primary_payment_type"]]
    payment_order = payment_order.merge(
        primary_payment, on="order_id", how="left", validate="one_to_one"
    )

    review_order = (
        reviews.groupby("order_id", as_index=False)
        .agg(review_score=("review_score", "mean"), review_count=("review_id", "count"))
    )

    fact_orders = (
        orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
        .merge(item_order, on="order_id", how="left", validate="one_to_one")
        .merge(payment_order, on="order_id", how="left", validate="one_to_one")
        .merge(review_order, on="order_id", how="left", validate="one_to_one")
    )
    fact_orders["purchase_date"] = fact_orders["order_purchase_timestamp"].dt.date
    fact_orders["purchase_month"] = fact_orders[
        "order_purchase_timestamp"
    ].dt.to_period("M").astype(str)
    fact_orders["delivery_days"] = (
        fact_orders["order_delivered_customer_date"]
        - fact_orders["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    fact_orders["delay_days"] = (
        fact_orders["order_delivered_customer_date"]
        - fact_orders["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    has_delivery = fact_orders[
        ["order_delivered_customer_date", "order_estimated_delivery_date"]
    ].notna().all(axis=1)
    fact_orders["late_flag"] = pd.Series(pd.NA, index=fact_orders.index, dtype="Int64")
    fact_orders.loc[has_delivery, "late_flag"] = (
        fact_orders.loc[has_delivery, "delay_days"] > 0
    ).astype(int)
    fact_orders["on_time_flag"] = pd.Series(
        pd.NA, index=fact_orders.index, dtype="Int64"
    )
    fact_orders.loc[has_delivery, "on_time_flag"] = (
        fact_orders.loc[has_delivery, "delay_days"] <= 0
    ).astype(int)
    fact_orders["low_review_flag"] = pd.Series(
        pd.NA, index=fact_orders.index, dtype="Int64"
    )
    reviewed = fact_orders["review_score"].notna()
    fact_orders.loc[reviewed, "low_review_flag"] = (
        fact_orders.loc[reviewed, "review_score"] <= 2
    ).astype(int)
    fact_orders["is_delivered"] = fact_orders["order_status"].eq("delivered").astype(int)
    fact_orders["freight_to_item_value"] = np.where(
        fact_orders["item_gmv"].gt(0),
        fact_orders["freight_value"] / fact_orders["item_gmv"],
        np.nan,
    )

    fact_orders = fact_orders.sort_values(
        ["customer_unique_id", "order_purchase_timestamp", "order_id"]
    )
    fact_orders["customer_delivered_order_number"] = pd.Series(
        pd.NA, index=fact_orders.index, dtype="Int64"
    )
    delivered_idx = fact_orders.index[fact_orders["is_delivered"].eq(1)]
    fact_orders.loc[delivered_idx, "customer_delivered_order_number"] = (
        fact_orders.loc[delivered_idx]
        .groupby("customer_unique_id")
        .cumcount()
        .add(1)
        .astype("Int64")
    )
    fact_orders["first_observed_delivered_order_flag"] = (
        fact_orders["customer_delivered_order_number"].eq(1).fillna(False).astype(int)
    )

    fact_sales = item_enriched.merge(
        fact_orders[
            [
                "order_id",
                "customer_unique_id",
                "order_status",
                "purchase_date",
                "purchase_month",
                "customer_state",
                "on_time_flag",
                "late_flag",
                "review_score",
                "low_review_flag",
                "primary_payment_type",
                "max_installments",
            ]
        ],
        on="order_id",
        how="left",
        validate="many_to_one",
    )

    latest_customer_location = (
        fact_orders.sort_values("order_purchase_timestamp")
        .drop_duplicates("customer_unique_id", keep="last")
        [["customer_unique_id", "customer_city", "customer_state"]]
    )
    dim_customer = latest_customer_location.reset_index(drop=True)
    dim_product = products[
        [
            "product_id",
            "product_category_name_english",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ]
    ].copy()
    dim_seller = sellers.copy()

    min_date = fact_orders["order_purchase_timestamp"].min().normalize()
    max_date = fact_orders["order_purchase_timestamp"].max().normalize()
    date_values = pd.date_range(min_date, max_date, freq="D")
    dim_date = pd.DataFrame({"date": date_values})
    dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["quarter"] = "Q" + dim_date["date"].dt.quarter.astype(str)
    dim_date["month_number"] = dim_date["date"].dt.month
    dim_date["month_name"] = dim_date["date"].dt.month_name().str[:3]
    dim_date["year_month"] = dim_date["date"].dt.strftime("%Y-%m")
    dim_date["week_of_year"] = dim_date["date"].dt.isocalendar().week.astype(int)
    dim_date["day_of_week"] = dim_date["date"].dt.day_name().str[:3]

    delivered = fact_orders[fact_orders["is_delivered"].eq(1)].copy()
    reference_date = delivered["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    customer_rfm = (
        delivered.groupby("customer_unique_id", as_index=False)
        .agg(
            first_purchase=("order_purchase_timestamp", "min"),
            last_purchase=("order_purchase_timestamp", "max"),
            frequency=("order_id", "nunique"),
            observed_gmv=("item_gmv", "sum"),
        )
    )
    customer_rfm["recency_days"] = (
        reference_date - customer_rfm["last_purchase"]
    ).dt.days
    high_value_threshold = float(customer_rfm["observed_gmv"].quantile(0.75))
    conditions = [
        customer_rfm["frequency"].ge(2) & customer_rfm["recency_days"].le(180),
        customer_rfm["frequency"].ge(2) & customer_rfm["recency_days"].gt(180),
        customer_rfm["frequency"].eq(1)
        & customer_rfm["recency_days"].le(90)
        & customer_rfm["observed_gmv"].ge(high_value_threshold),
        customer_rfm["frequency"].eq(1) & customer_rfm["recency_days"].le(90),
        customer_rfm["frequency"].eq(1)
        & customer_rfm["recency_days"].gt(180)
        & customer_rfm["observed_gmv"].ge(high_value_threshold),
        customer_rfm["frequency"].eq(1) & customer_rfm["recency_days"].gt(180),
    ]
    labels = [
        "Active repeat",
        "Lapsed repeat",
        "Recent high-value",
        "Recent first-time",
        "At-risk high-value",
        "Lapsed one-time",
    ]
    customer_rfm["segment"] = np.select(
        conditions, labels, default="Mid-cycle one-time"
    )
    customer_rfm["high_value_threshold_brl"] = high_value_threshold

    delivered_gmv_from_orders = float(delivered["item_gmv"].sum())
    delivered_gmv_from_items = float(
        fact_sales.loc[fact_sales["order_status"].eq("delivered"), "price"].sum()
    )
    checks.update(
        {
            "fact_order_rows": int(len(fact_orders)),
            "fact_sales_rows": int(len(fact_sales)),
            "delivered_order_rows": int(len(delivered)),
            "delivered_gmv_from_order_fact": delivered_gmv_from_orders,
            "delivered_gmv_from_item_fact": delivered_gmv_from_items,
            "gmv_reconciliation_difference": delivered_gmv_from_orders
            - delivered_gmv_from_items,
            "review_coverage_delivered_orders": float(
                delivered["review_score"].notna().mean()
            ),
            "unknown_category_item_share": float(
                fact_sales["product_category_name_english"].eq("unknown").mean()
            ),
            "invalid_delivery_before_purchase": int(
                (
                    fact_orders["order_delivered_customer_date"]
                    < fact_orders["order_purchase_timestamp"]
                ).sum()
            ),
            "rfm_high_value_threshold_brl": high_value_threshold,
        }
    )
    if abs(checks["gmv_reconciliation_difference"]) > 0.01:
        raise ValueError("Delivered GMV does not reconcile between facts")

    return {
        "fact_orders": fact_orders,
        "fact_sales": fact_sales,
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_seller": dim_seller,
        "dim_date": dim_date,
        "mart_customer_rfm": customer_rfm,
        "checks": checks,
    }


def sqlite_ready(df: pd.DataFrame) -> pd.DataFrame:
    """Convert extension dtypes and dates to SQLite-friendly values."""
    output = df.copy()
    for column in output.columns:
        if isinstance(output[column].dtype, pd.Int64Dtype):
            output[column] = output[column].astype("float64")
    return output


def load_sqlite(
    sources: dict[str, pd.DataFrame], tables: dict[str, pd.DataFrame]
) -> None:
    """Load staging and analytical tables, then create reusable SQL views."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        for name, dataframe in sources.items():
            sqlite_ready(dataframe).to_sql(
                f"stg_{name}",
                connection,
                if_exists="replace",
                index=False,
                chunksize=500,
                method="multi",
            )
        for name in [
            "fact_orders",
            "fact_sales",
            "dim_customer",
            "dim_product",
            "dim_seller",
            "dim_date",
            "mart_customer_rfm",
        ]:
            sqlite_ready(tables[name]).to_sql(
                name,
                connection,
                if_exists="replace",
                index=False,
                chunksize=500,
                method="multi",
            )
        connection.executescript(SQL_FILE.read_text(encoding="utf-8"))


def export_power_bi_tables(tables: dict[str, pd.DataFrame]) -> None:
    """Export curated model tables for Power BI Desktop or Service."""
    for name in [
        "fact_orders",
        "fact_sales",
        "dim_customer",
        "dim_product",
        "dim_seller",
        "dim_date",
        "mart_customer_rfm",
    ]:
        tables[name].to_csv(PROCESSED_DIR / f"{name}.csv", index=False)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    checks = validate_raw(sources)
    tables = build_tables(sources, checks)
    load_sqlite(sources, tables)
    export_power_bi_tables(tables)
    (RESULTS_DIR / "data_quality_report.json").write_text(
        json.dumps(tables["checks"], indent=2, default=str), encoding="utf-8"
    )
    print(f"Built analytical database: {DB_PATH}")
    print(f"Delivered GMV reconciliation difference: {tables['checks']['gmv_reconciliation_difference']:.2f}")


if __name__ == "__main__":
    main()
