# Data dictionary and metric definitions

## Model grains

| Table | Grain | Primary key | Main analytical use |
|---|---|---|---|
| `fact_orders` | One row per order | `order_id` | Order status, customer, delivery, payment, review and order-level KPIs |
| `fact_sales` | One row per order item | `order_id + order_item_id` | Item GMV, freight, product, category and seller analysis |
| `dim_customer` | One row per observed long-term customer | `customer_unique_id` | Customer filtering and latest observed location |
| `dim_product` | One row per product | `product_id` | Product category and physical attributes |
| `dim_seller` | One row per seller | `seller_id` | Seller location and seller-level slicing |
| `dim_date` | One row per calendar date | `date_key` | Date, month, quarter and year analysis |
| `mart_customer_rfm` | One row per customer with a delivered order | `customer_unique_id` | Recency, frequency, observed value and rule-based CRM segments |

## Important keys

- `customer_id` identifies the customer record attached to an individual order.
- `customer_unique_id` is the cross-order identifier used for observed repeat-purchase analysis.
- `order_id` is a degenerate business key shared across order, item, payment and review sources.
- An order may contain multiple items, sellers, payment records or reviews. Directly joining all detail tables creates fan-out duplication.

## Core calculated fields

| Field | Definition |
|---|---|
| `item_gmv` | Sum of item `price` at order grain |
| `freight_value` | Sum of item freight at order grain |
| `amount_paid` | Sum of all payment records at order grain |
| `delivery_days` | Actual customer delivery timestamp minus purchase timestamp, in days |
| `delay_days` | Actual customer delivery timestamp minus estimated delivery timestamp, in days |
| `late_flag` | 1 if delivered after the estimated date; 0 if on time or early |
| `low_review_flag` | 1 for a review score of 1 or 2; null when no score is observed |
| `customer_delivered_order_number` | Delivered-order sequence within `customer_unique_id` |
| `first_observed_delivered_order_flag` | 1 for the first delivered order observed for the customer |
| `freight_to_item_value` | Order freight divided by item GMV when item GMV is positive |

## KPI definitions

### Growth

- **Delivered GMV:** Sum of item price for orders with `order_status = 'delivered'`.
- **Delivered orders:** Distinct delivered `order_id`.
- **Active customers:** Distinct `customer_unique_id` with a delivered order in the selected period.
- **Average order value:** Delivered GMV divided by delivered orders.
- **Purchase frequency:** Delivered orders divided by active customers.
- **Repeat-order GMV share:** GMV from observed delivered order number 2 or later divided by delivered GMV.

### Retention

- **Observed repeat customer:** A `customer_unique_id` with at least two delivered orders in the dataset.
- **Observed repeat-customer rate:** Observed repeat customers divided by observed customers.
- **N-day second-purchase rate:** Eligible first-time customers with a second delivered order within N days divided by first-time customers with at least N days remaining in the observation window.
- **Monthly cohort retention:** Customers active in cohort period N divided by customers in the cohort's first observed purchase month.
- **Observed GMV:** Cumulative delivered item GMV inside the dataset. This is not customer lifetime value.

### Customer experience

- **On-time delivery rate:** Delivered orders with actual delivery on or before estimated delivery, divided by delivered orders with both dates.
- **Average delivery days:** Mean purchase-to-customer-delivery duration for delivered orders.
- **Average review score:** Mean order-level review score after averaging duplicate review records to one order.
- **Low-review rate:** Reviewed orders with score 1 or 2 divided by reviewed orders.

### Commercial

- **Category GMV:** Delivered item price grouped by translated product category.
- **Freight-to-GMV ratio:** Delivered freight divided by delivered item GMV.
- **Payment-value share:** Payment value for a method divided by all payment value on delivered orders.

## Rule-based RFM segmentation

The reference date is one day after the latest observed delivered purchase. The high-value threshold is the 75th percentile of observed customer GMV: **BRL 154.7375**.

| Segment | Rule |
|---|---|
| Active repeat | Frequency at least 2 and recency no more than 180 days |
| Lapsed repeat | Frequency at least 2 and recency above 180 days |
| Recent high-value | Frequency 1, recency no more than 90 days and observed GMV at least the high-value threshold |
| Recent first-time | Frequency 1 and recency no more than 90 days, excluding recent high-value |
| At-risk high-value | Frequency 1, recency above 180 days and observed GMV at least the high-value threshold |
| Lapsed one-time | Frequency 1 and recency above 180 days, excluding at-risk high-value |
| Mid-cycle one-time | Remaining one-time customers |

The segment labels are analytical rules, not verified causal risk scores or predicted CLV.

