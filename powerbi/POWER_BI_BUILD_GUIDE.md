# Power BI build guide

## Current status

The repository contains a Power BI-ready model and verified outputs. A `.pbix` file has not been generated in this environment. Do not claim a completed Power BI dashboard until the report has been built, validated and saved with screenshots.

On macOS, Power BI Desktop requires a Windows environment. Power BI Service or a Windows virtual machine can be used instead.

## Import tables

Import these files from `data/processed/`:

- `fact_orders.csv`
- `fact_sales.csv`
- `dim_customer.csv`
- `dim_product.csv`
- `dim_seller.csv`
- `dim_date.csv`
- `mart_customer_rfm.csv`

Set the following data types explicitly:

- IDs: Text
- `purchase_date` and `dim_date[date]`: Date
- timestamps: Date/Time
- price, freight, GMV, payment and review values: Decimal number
- count and flag columns: Whole number

## Relationships

Use one-to-many, single-direction relationships from dimensions to facts:

```text
dim_date[date] 1 ─── * fact_orders[purchase_date]
dim_date[date] 1 ─── * fact_sales[purchase_date]

dim_customer[customer_unique_id] 1 ─── * fact_orders[customer_unique_id]
dim_customer[customer_unique_id] 1 ─── * fact_sales[customer_unique_id]
dim_customer[customer_unique_id] 1 ─── 1 mart_customer_rfm[customer_unique_id]

dim_product[product_id] 1 ─── * fact_sales[product_id]
dim_seller[seller_id] 1 ─── * fact_sales[seller_id]
```

Do not relate `fact_orders` directly to `fact_sales`. They are separate facts with shared dimensions. Do not switch relationships to bidirectional merely to make a visual work; diagnose the intended filter path instead.

Mark `dim_date` as the date table using `dim_date[date]`.

## Core DAX measures

```DAX
Delivered GMV =
CALCULATE(
    SUM(fact_sales[price]),
    fact_sales[order_status] = "delivered"
)

Delivered Freight =
CALCULATE(
    SUM(fact_sales[freight_value]),
    fact_sales[order_status] = "delivered"
)

Delivered Orders =
CALCULATE(
    DISTINCTCOUNT(fact_orders[order_id]),
    fact_orders[order_status] = "delivered"
)

Active Customers =
CALCULATE(
    DISTINCTCOUNT(fact_orders[customer_unique_id]),
    fact_orders[order_status] = "delivered"
)

Delivered AOV =
DIVIDE([Delivered GMV], [Delivered Orders])

Purchase Frequency =
DIVIDE([Delivered Orders], [Active Customers])

Freight to GMV % =
DIVIDE([Delivered Freight], [Delivered GMV])

Observed Repeat Customers =
CALCULATE(
    DISTINCTCOUNT(mart_customer_rfm[customer_unique_id]),
    mart_customer_rfm[frequency] >= 2
)

Observed Customers =
DISTINCTCOUNT(mart_customer_rfm[customer_unique_id])

Observed Repeat Customer % =
DIVIDE([Observed Repeat Customers], [Observed Customers])

Repeat Order GMV =
CALCULATE(
    SUM(fact_orders[item_gmv]),
    fact_orders[order_status] = "delivered",
    fact_orders[customer_delivered_order_number] > 1
)

Repeat Order GMV % =
DIVIDE([Repeat Order GMV], [Delivered GMV])

On-Time Delivered Orders =
CALCULATE(
    [Delivered Orders],
    fact_orders[on_time_flag] = 1
)

On-Time Delivery % =
DIVIDE([On-Time Delivered Orders], [Delivered Orders])

Average Delivery Days =
CALCULATE(
    AVERAGE(fact_orders[delivery_days]),
    fact_orders[order_status] = "delivered"
)

Average Review Score =
CALCULATE(
    AVERAGE(fact_orders[review_score]),
    fact_orders[order_status] = "delivered"
)

Reviewed Orders =
CALCULATE(
    DISTINCTCOUNT(fact_orders[order_id]),
    fact_orders[order_status] = "delivered",
    NOT ISBLANK(fact_orders[review_score])
)

Low Review Orders =
CALCULATE(
    DISTINCTCOUNT(fact_orders[order_id]),
    fact_orders[order_status] = "delivered",
    fact_orders[low_review_flag] = 1
)

Low Review % =
DIVIDE([Low Review Orders], [Reviewed Orders])

At-Risk High-Value Customers =
CALCULATE(
    DISTINCTCOUNT(mart_customer_rfm[customer_unique_id]),
    mart_customer_rfm[segment] = "At-risk high-value"
)

At-Risk High-Value Observed GMV =
CALCULATE(
    SUM(mart_customer_rfm[observed_gmv]),
    mart_customer_rfm[segment] = "At-risk high-value"
)

GMV Previous Month =
CALCULATE(
    [Delivered GMV],
    DATEADD(dim_date[date], -1, MONTH)
)

GMV MoM % =
DIVIDE(
    [Delivered GMV] - [GMV Previous Month],
    [GMV Previous Month]
)

Data Through =
MAX(fact_orders[purchase_date])
```

Validate the headline cards against `results/headline_metrics.json` before adding filters or more complex measures.

## Page 1 - Executive growth overview

**Audience:** Head of Analytics, Commercial Lead, Growth Lead.

Cards:

- Delivered GMV
- Delivered orders
- Active customers
- Delivered AOV
- Observed repeat-customer rate
- On-time delivery rate

Visuals:

- Monthly Delivered GMV and orders line/column chart
- First-order versus repeat-order GMV contribution
- GMV by customer state
- Top categories by delivered GMV
- Monthly on-time delivery and review trend

The page should answer whether growth is acquisition-, frequency- or order-value-led.

## Page 2 - Customer and second purchase

**Audience:** CRM, Customer Analytics, Product Growth.

Cards:

- Observed customers
- Observed repeat customers
- Repeat-order GMV share
- At-risk high-value customers
- At-risk high-value observed GMV

Visuals:

- Cohort heatmap using `results/cohort_retention.csv`
- 30/60/90/180-day second-purchase rates using `results/repeat_purchase_windows.csv`
- RFM segment customer share versus observed GMV share
- Segment by state and first observed month

Use the wording `observed repeat purchase` rather than lifetime retention.

## Page 3 - Fulfilment and customer experience

**Audience:** Operations, Customer Experience, Seller Management.

Cards:

- On-time delivery rate
- Average delivery days
- Average review score
- Low-review rate

Visuals:

- On-time versus late review-score distribution
- Low-review rate by delivery group
- On-time delivery rate by state
- State/category scatter: delivered GMV versus on-time delivery rate, sized by orders
- Delivery and review trend by month

Add a visible note: delivery and review results show association, not causation.

## Page 4 - Commercial portfolio

**Audience:** Commercial, Category and Seller teams.

Visuals:

- Category GMV, orders, AOV and freight-to-GMV ratio
- Category GMV versus on-time rate, coloured by average review
- Top states and categories matrix
- Payment-value share and instalment profile
- Drill-through category profile with trend and customer mix

Do not label item GMV as profit, margin or platform revenue.

## Page 5 - Methodology and data quality

Include:

- Source and observation period
- Fact-table grains
- KPI definitions
- Latest refresh date
- Source and output row counts
- GMV reconciliation difference
- Known exclusions and limitations

This page materially strengthens the portfolio because it demonstrates that metric quality, grain and reconciliation were treated as part of the analysis.

## Required screenshots before claiming Power BI experience

Save evidence of:

1. Model view and relationships.
2. Executive page.
3. Customer page with cohort or RFM analysis.
4. Fulfilment page.
5. DAX measure definitions.
6. Reconciliation of headline numbers against `results/headline_metrics.json`.

