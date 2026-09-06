# Metrics, data quality and limitations

[Project overview](../README.md) · [Power BI model and DAX](POWER_BI_MODEL.md) · [Reproduction instructions](REPRODUCIBILITY.md)

## Dataset and analytical scope

The source is the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Its nine CSV files cover customers, orders, items, products, sellers, payments, reviews, geolocation and category translations. The committed pipeline results represent **1,550,922 source rows**.

The delivered-order purchase window runs from **15 September 2016 to 29 August 2018**. September 2016 and August 2018 are partial observation months. Values are in Brazilian reais (BRL / R$). Headline results below describe the full historical dataset, unless a narrower comparison is explicitly stated; they are not expected to remain unchanged when report filters are applied.

## Metric definitions

| Metric | Definition and interpretation |
| :--- | :--- |
| Delivered GMV | Sum of item `price` for delivered orders. Excludes freight; not platform revenue, profit or margin. |
| Delivered orders | Distinct `order_id` for delivered orders in the observation window. |
| Active / observed customers | Distinct `customer_unique_id` with a delivered order in the observation window; not the order-specific `customer_id`. |
| Average order value | Delivered GMV divided by delivered orders. |
| Repeat customer rate | Share of observed customers with at least two delivered orders in the observation window. It is not lifetime retention. See the [DAX guide](POWER_BI_MODEL.md) for report filter behaviour. |
| Repeat order GMV share | GMV from a customer's second or later delivered order divided by delivered GMV. Orders are sequenced across the available history, not renumbered when a date filter changes. |
| Repeat customer GMV share | All observed GMV from customers with at least two delivered orders, including their first order, divided by delivered GMV. This differs from repeat **order** GMV share. |
| Freight to GMV | Delivered freight value divided by delivered item GMV. |
| On-time delivery rate | Mean of the order-level on-time flag for delivered orders with actual and estimated delivery timestamps. Actual delivery must be on or before the estimated timestamp. Unknown flags are excluded, not treated as late. |
| Average delivery days | Mean elapsed time from purchase to customer delivery for delivered orders with available timestamps; expressed in days. |
| Average review score | Mean of the available order-level review scores for delivered orders. Where an order has multiple reviews, its review scores are averaged before joining to the order fact. |
| Low-review rate | Share of reviewed delivered orders whose order-level review score is at most 2. Missing reviews are excluded from both numerator and denominator. |
| Review coverage | Reviewed delivered orders divided by all delivered orders. Reported separately so missing feedback is visible. |
| 90-day second-purchase rate | Customers making a second delivered purchase within 90 elapsed days of their first, divided by customers with at least 90 days of follow-up before the observation end. Exactly 90 days is included. |
| Comparable-period growth | Jan–Jul 2018 versus Jan–Jul 2017, using the same seven calendar months. The report's fixed-year comparison is independent of the Period slicer; see the [filter guide](POWER_BI_MODEL.md) for State behaviour. |

The 90-day eligibility cutoff is the latest delivered-order purchase timestamp in the available dataset, not today's date. Recent first-time customers without a complete follow-up window are excluded even if they already made an early second purchase. This keeps the numerator and denominator on the same eligibility basis.

## Baseline results

These figures are supported by [`results/headline_metrics.json`](../results/headline_metrics.json), the [executive summary](../results/executive_summary.md) and the CSV outputs in [`results/`](../results/).

| Metric | Historical baseline |
| :--- | :--- |
| Delivered GMV | **R$ 13,221,498.11** (R$ 13.22M) |
| Delivered orders | **96,478** |
| Observed customers | **93,358** |
| Average order value | **R$ 137.04** |
| Repeat customers | **2,801**, or **3.00%** of observed customers |
| Repeat order GMV share | **2.90%** |
| Repeat customer GMV share | **5.51%** |
| Freight to GMV | **16.6%** |
| On-time delivery rate | **91.9%** |
| Average delivery days | **12.6** |
| Average review score | **4.16 / 5** |
| Low-review rate | **12.8%** of reviewed delivered orders |
| Review coverage | **99.33%** of delivered orders |
| 90-day second purchases | **1,714 / 75,320** eligible customers (**2.28%**) |

### Growth and retention

Jan–Jul delivered GMV increased **161.6%** from 2017 to 2018, while delivered orders increased **160.8%** and AOV increased about **0.3%**. Growth was therefore predominantly volume-led in this comparison.

Only **3.0%** of observed customers placed two or more delivered orders, and repeat orders contributed **2.9%** of delivered GMV. The rule-based **At-risk high-value** segment contains **12,790** customers (**13.7%** of observed customers) accounting for **33.8%** of observed GMV. These findings motivate testing a second-purchase journey; they do not establish that any particular intervention will work.

Cohort retention, fixed-window second purchases and RFM segmentation are supporting SQL/Python analyses, not additional pages in the two-page PBIX.

### Regional and delivery priorities

- SP contributes **38.3%** of delivered GMV and has an on-time delivery rate of **94.1%**.
- On-time rates are **86.5%** in RJ and **86.0%** in BA, identifying regional gaps worth investigating alongside their commercial importance.
- Reviewed late orders have an average score of **2.57 / 5**, versus **4.29 / 5** for reviewed on-time/early orders.
- Low-review rates are **54.0%** for reviewed late orders and **9.2%** for reviewed on-time/early orders: a **5.9×** association, not a causal estimate.

## Implementation and table grains

The workflow is: source CSVs → Python validation/transformation → SQLite tables and SQL marts → analytical result files and Power BI-ready CSVs → an imported Power BI model.

| Component | Responsibility |
| :--- | :--- |
| [`src/build_project.py`](../src/build_project.py) | Ingestion, category translation, delivery/review features, repeat-order sequencing, dimensional exports and rule-based segmentation. |
| [`sql/01_create_analytics_views.sql`](../sql/01_create_analytics_views.sql) | CTEs and window functions for monthly performance, cohorts, second-purchase windows, category/state performance and delivery experience. |
| [`src/run_analysis.py`](../src/run_analysis.py) | SQL-based result exports, headline metrics and the executive summary. |
| [`powerbi/`](../powerbi/) | The saved two-page report and its opening/refresh instructions; see the [model guide](POWER_BI_MODEL.md) for relationships and DAX. |
| [`azure/`](../azure/) | An ADLS Gen2 / Data Factory / Azure SQL deployment blueprint. It is not a claim of cloud deployment. |

`fact_orders` has **one row per order**; `fact_sales` has **one row per order item**. Items, payments and reviews are aggregated to the required order grain before joining to the order fact, preventing monetary fan-out from multiple records. Product/category analysis uses the item fact. The [data dictionary](DATA_DICTIONARY.md) describes the fields and analytical outputs.

The exported customer dimension records each customer's **latest observed location**, while facts retain the order's customer state. These are different geographical definitions for customers who moved. The report's actual State filtering is documented in the [model guide](POWER_BI_MODEL.md); it should not be inferred solely from a dimension's name.

## Recorded data-quality evidence

The committed [`results/data_quality_report.json`](../results/data_quality_report.json) records the following results for the full source dataset. These are baseline observations, not a claim that an arbitrary future input has already been validated.

| Check | Recorded result |
| :--- | :--- |
| Order / item rows | **99,441 / 112,650** |
| Delivered orders | **96,478** |
| Duplicate customer, order, product and seller keys | **0** in each tested entity |
| Duplicate `(order_id, order_item_id)` keys | **0** |
| Orphan item references to orders, products or sellers | **0** |
| Negative item prices / freight values | **0 / 0** |
| Deliveries before purchase | **0** |
| Delivered GMV: order fact | **R$ 13,221,498.11** |
| Delivered GMV: item fact | **R$ 13,221,498.11** |
| Order/item GMV reconciliation difference | **R$ 0.00** |
| Delivered-order review coverage | **99.33%** |
| Item rows with unknown translated category | **1.44%** |

Source-key, orphan-reference and negative-value checks raise errors when violated. The transformation also checks that delivered GMV reconciles between facts within R$ 0.01. Unknown translated categories remain labelled `unknown` rather than being silently dropped. Missing review scores remain missing; their absence must not be converted into positive feedback or included in the low-review denominator.

Run the small-fixture regression suite with `python -m unittest discover -s tests -v`; see [Reproducibility](REPRODUCIBILITY.md#run-the-tests) for the distinction between automated tests, full-data reconciliation and a Desktop refresh check.

## Limitations

- This is an independent portfolio project with no affiliation to Olist. The data describes a historical Brazilian marketplace, not current market behaviour.
- The observation period is finite and its first/last months are partial. Observed repeat purchasing is not lifetime retention or customer lifetime value, and an apparently first-time customer may have purchased before the dataset began.
- There are no visits, carts or marketing costs, so conversion, cart abandonment, CAC and ROAS cannot be calculated. Platform commissions and costs are also unavailable; GMV is not revenue, profit or margin.
- Review coverage is high but incomplete, and submitted reviews may differ systematically from missing feedback. Delivery/review comparisons are observational and can reflect seller, product, geographic or other differences.
- RFM segment labels are transparent rules, not a validated churn model. Recommendations are proposals for testing; no intervention, retention uplift or operational improvement has been measured.
- Source-file and SQL tests do not execute the Power BI engine or establish that all report interactions work. Report refresh and visual checks require Power BI Desktop; their scope is documented separately.
- Credit belongs to Olist and the dataset contributors. Consult the original dataset page for its terms.
