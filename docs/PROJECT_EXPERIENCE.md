# Resume and interview package

## Project title

**Marketplace Customer Growth & Fulfilment Analytics | Independent Portfolio Project**  
**Python | SQL (SQLite) | Power BI-ready model | Azure architecture**  
**August 2026**

Always describe this as a self-initiated portfolio project using public, anonymised historical data. Do not imply that Olist commissioned the work or implemented the recommendations.

## Resume version that is truthful now

- Built a reproducible Python and SQL analytics workflow across nine public e-commerce datasets containing 1.55M source rows and 96,478 delivered orders; designed separate order/item facts and conformed dimensions, with primary-key, foreign-key, timestamp and GMV reconciliation controls.
- Applied SQL CTEs and window functions plus Python cohort and rule-based RFM analysis, identifying a 3.00% observed repeat-customer rate, a 2.28% censoring-adjusted 90-day second-purchase rate, and 12,790 at-risk high-value customers representing 33.8% of observed GMV.
- Quantified fulfilment and customer-experience patterns, finding 91.9% on-time delivery and a 5.9x higher 1-2-star review rate among late versus on-time reviewed orders; translated results into second-purchase, CRM and regional delivery recommendations while documenting causal and data limitations.
- Designed a Power BI-ready multi-fact semantic model, DAX measure library and five-page dashboard specification, together with an Azure deployment blueprint using ADLS Gen2, Azure Data Factory, Azure SQL Database and Power BI.

If space is limited, use the first three bullets and place `Power BI-ready model | Azure architecture` in the project technology line.

## Replaceable bullet after the Power BI report is actually built

Replace the fourth current bullet with:

> Built a five-page interactive Power BI report with a conformed dimensional model and DAX measures for delivered GMV, cohort retention, RFM segments, delivery SLA and customer reviews; reconciled all headline measures to the SQL analytical layer.

Do not use this sentence until the report, model relationships, DAX and screenshots exist.

## Replaceable bullet after the Azure proof of concept is actually deployed

Add or replace a bullet with:

> Implemented an Azure batch proof of concept that staged nine source files in ADLS Gen2, orchestrated parameterised ingestion through Azure Data Factory, loaded analytical facts and dimensions into Azure SQL Database and served the verified model to Power BI.

Do not claim `production-grade`, `real-time`, `enterprise-scale` or `automated cloud deployment` unless those capabilities have actually been implemented and tested.

## Short LinkedIn or portfolio description

> I built an independent end-to-end marketplace analytics project using Olist's public, anonymised e-commerce data. I processed nine relational files with Python, created order- and item-level facts and reusable SQL marts, and analysed growth quality, second-purchase behaviour, customer segments, fulfilment and reviews. The analysis showed that only 3.00% of observed customers purchased more than once, while late deliveries were associated with a 5.9x higher low-review rate. I translated the findings into CRM and operational priorities, created a Power BI-ready semantic model and documented an Azure Data Factory/ADLS/Azure SQL deployment path. All metrics, limitations and code are reproducible in the project repository.

## 30-second interview answer

> I wanted a portfolio project that demonstrated an end-to-end business decision rather than just a collection of charts. I used nine public Olist marketplace datasets and built a Python and SQL workflow covering data validation, dimensional modelling, cohort and RFM analysis. I found that only 3.00% of observed customers purchased more than once and that late reviewed orders were 5.9 times more likely to receive a one- or two-star rating. I used those findings to propose a second-purchase test, a high-value reactivation audience and targeted delivery analysis. I also prepared a Power BI semantic model and an Azure deployment blueprint, while clearly separating what I implemented locally from what still requires cloud deployment.

## Two-minute STAR answer

> **Situation:** I wanted to build a portfolio project that reflected a real commercial analytics problem rather than producing a generic sales dashboard. I selected Olist's public, anonymised marketplace dataset, which contains approximately 100,000 historical orders across nine relational files, including customers, products, sellers, payments, delivery timestamps and reviews. I framed the question as: how could a marketplace improve the quality of GMV growth through repeat purchase and a better post-purchase experience?
>
> **Task:** My objective was to build a reliable analytical model, understand whether growth was supported by repeat behaviour, identify commercially important customer groups and determine where fulfilment performance was associated with poor customer experience.
>
> **Action:** I used Python to ingest and profile 1.55 million source rows, translate product categories, create delivery and review features, and run key, null, timestamp and financial reconciliation checks. I kept order and item grains separate because directly joining items, payments and reviews would duplicate financial values. I loaded the model into SQLite and used SQL CTEs and window functions to create monthly performance, customer lifecycle, cohort, repeat-window, category, state, payment and delivery marts. I used `customer_unique_id`, rather than the order-level customer ID, for repeat analysis and excluded customers without a complete follow-up window from the 90-day rate. I then created a transparent RFM-style segmentation and prepared a Power BI-ready dimensional model and Azure batch architecture.
>
> **Result:** The validated model covered 96,478 delivered orders and BRL 13.22 million in delivered item GMV. Only 3.00% of observed customers placed at least two delivered orders, and the adjusted 90-day second-purchase rate was 2.28%. An at-risk high-value segment represented 13.7% of customers but 33.8% of observed GMV. Delivery was on time for 91.9% of orders, but 54.0% of reviewed late orders received a score of one or two, versus 9.2% of reviewed on-time orders. Based on this, I recommended testing a defined second-purchase journey, creating a controlled reactivation experiment and prioritising high-GMV regional or seller delivery exceptions. I described the review relationship as an association rather than claiming that delay caused the ratings.

## Tool-by-tool explanation

### Python

> I used Python for repeatable ingestion, profiling, data-quality checks, feature engineering, dimension/fact preparation and rule-based customer segmentation. The checks included key uniqueness, foreign-key coverage, non-negative monetary values, timestamp order and order/item GMV reconciliation.

### SQL

> I used SQLite as the local analytical database. I created reusable views with CTEs, conditional aggregation and window functions for monthly growth, order sequencing, customer lifecycle, cohort retention, fixed-window second purchases, category/state performance, payment mix and delivery experience.

### Power BI

Current answer before the report is built:

> I designed a Power BI-ready semantic model with conformed customer, date, product and seller dimensions and separate order and item facts. I also prepared the DAX measures and page designs, but I distinguish that design work from a completed `.pbix` implementation.

Answer after the report is built:

> I built and validated a five-page Power BI report covering executive growth, customer and cohort behaviour, fulfilment, commercial performance and methodology. I reconciled the headline cards to the SQL outputs and kept order-level measures away from the item fact to avoid weighting errors.

### Azure

Current answer before deployment:

> I designed an Azure-ready batch architecture using ADLS Gen2 for raw files, Azure Data Factory for parameterised copy orchestration, Azure SQL Database for staging and analytical tables, and Power BI as the presentation layer. The current implementation is local, so I do not describe the Azure design as deployed.

Answer after deployment:

> I implemented a proof of concept that staged the nine files in ADLS Gen2, used a parameterised ADF pipeline to load them to Azure SQL and connected Power BI to the curated model. I captured run history and reconciled source and sink row counts and delivered GMV.

## Technical questions and strong answers

### Why did you not join all source tables into one wide table?

> Several tables have different grains. One order can have multiple items, payments and review records. Joining all detail tables directly on `order_id` creates a many-to-many fan-out and duplicates monetary values. I aggregated each source to order grain for order KPIs and retained a separate item fact for product and seller analysis.

### Why use `customer_unique_id` rather than `customer_id`?

> Olist assigns a customer record to each order, while `customer_unique_id` is the cross-order identifier. Using `customer_id` would incorrectly classify almost every order as a different customer and understate repeat purchasing.

### Why call it GMV instead of revenue?

> The dataset contains item prices and payments but not Olist's commission, accounting revenue, cost of goods or operating costs. Item-price sum is therefore a delivered GMV proxy, not profit, margin or company revenue.

### How did you avoid right-censoring in the 90-day rate?

> I included only first-time customers whose first observed purchase occurred at least 90 days before the dataset's final purchase timestamp. Customers without a complete follow-up window were excluded from the denominator.

### Does delivery delay cause low reviews?

> No causal conclusion can be drawn from this observational analysis. I found a strong association: 54.0% of reviewed late orders received a score of one or two compared with 9.2% of reviewed on-time orders. Product, seller, category, geography or other factors may affect both delivery and reviews.

### Why use Azure Data Factory for static CSV files?

> It is a learning proof of concept for a repeatable batch-ingestion pattern: parameterised file handling, source-to-sink row-count logging and separation of raw, staging and analytical layers. I would not claim that the static source requires a production ADF platform or real-time architecture.

### What is the business action from the RFM segment?

> The segment provides a transparent test audience, not a guaranteed opportunity. I would run a controlled reactivation experiment and measure incremental repeat purchase or GMV against a holdout group rather than assuming all historically valuable customers are recoverable.

## Statements to avoid

- "I worked for Olist" or "Olist implemented my recommendations."
- "I increased retention" or "reduced delays" without a real intervention and post-period measurement.
- "This is current Australian customer behaviour."
- "GMV is profit/revenue" or "observed value is CLV."
- "I calculated website conversion" when the data has no visits or carts.
- "I deployed Azure" before a successful cloud run exists.
- "I built a Power BI dashboard" before the report and screenshots exist.
- "Delay caused low reviews" when the evidence is observational.

