# Portfolio and interview notes

## Project summary

**Marketplace Customer Growth & Fulfilment Analytics | Independent Portfolio Project**  
**Python | SQL (SQLite) | Power BI | Azure architecture blueprint**

An independent project using Olist's public historical marketplace data. The repository contains a reproducible local Python/SQL workflow and a completed two-page Power BI report. The Azure architecture is documented as a proposed proof of concept.

## Resume bullets

- Built a Python and SQL analytics workflow across nine public e-commerce files containing 1.55M source rows and 96,478 delivered orders; designed separate order/item facts with key, timestamp and GMV reconciliation controls.
- Applied SQL CTEs, window functions and customer cohort/RFM analysis, identifying a 3.00% observed repeat-customer rate and a 2.28% second-purchase rate among customers with a complete 90-day observation window.
- Delivered a two-page Power BI report covering marketplace growth, category/state value concentration, fulfilment and customer reviews, with Period and State slicers and headline KPIs matching the committed analytical results.
- Found a 5.9× higher low-review rate among reviewed late orders than reviewed on-time orders, and translated the association into regional delivery investigations and controlled customer-growth test proposals.

## Short portfolio description

I built a marketplace analytics project using Olist's public e-commerce data. Python prepares and validates the order/item facts and dimensions; SQLite provides reusable marts for growth, customer behaviour and delivery analysis. A two-page Power BI report presents the commercial findings. The analysis covers R$ 13.22M in delivered GMV and shows limited observed repeat purchasing alongside a strong association between late delivery and poor reviews. The repository includes the final PBIX, screenshots, source code, metric definitions and an Azure deployment blueprint.

## 30-second interview answer

I wanted to understand whether marketplace growth was supported by repeat purchases and where delivery performance affected the customer experience. I built a Python and SQL workflow over nine Olist datasets, then delivered two Power BI pages for growth and commercial/fulfilment performance. Only 3% of observed customers purchased more than once, while the low-review rate was 5.9 times higher among late reviewed orders. I proposed second-purchase tests and targeted regional delivery investigations. These are analytical recommendations; I did not measure an implemented intervention.

## Technical discussion

### Why separate order and item facts?

Orders can have multiple items, payments and reviews. Joining every detail table directly on `order_id` creates fan-out and can overstate financial values. The pipeline aggregates data to the required grain and reconciles delivered GMV between the order and item facts.

### Why use `customer_unique_id`?

It identifies customers across orders. Olist's `customer_id` is tied to an order-level customer record, so it is unsuitable for identifying repeat purchasers.

### Why GMV rather than revenue?

The dataset includes item prices and payments but not platform commissions, accounting revenue or operating costs. Delivered item value is a GMV proxy; it does not establish revenue, profit or margin.

### How is the 90-day rate adjusted?

The denominator includes first-time customers with at least 90 days of follow-up before the observation endpoint. The eligible group contains 75,320 customers, of whom 1,714 make a second delivered purchase within 90 days.

### Does late delivery cause low reviews?

The analysis is observational. Among reviewed orders, the 1–2-star rate is 54.0% for late deliveries and 9.2% for on-time or early deliveries. Seller, product, category and geography may affect both outcomes.

### What was delivered in Power BI?

Two pages: Marketplace Performance Overview and Commercial & Fulfilment Performance. They include growth, first/repeat order contribution, category/state performance, freight, delivery and review metrics. Cohort and RFM results are supporting analytical exports, not additional report pages.

### What was delivered in Azure?

A documented batch architecture using ADLS Gen2, Data Factory and Azure SQL. The repository does not provide evidence of a deployed cloud environment or published Power BI Service report.

## Evidence

- [Final Power BI report](../powerbi/Dashboard_Commercial_Fulfilment_Final.pbix)
- [Report previews and project overview](../README.md#dashboard-previews)
- [Headline metrics](../results/headline_metrics.json)
- [Data-quality report](../results/data_quality_report.json)
- [Executive summary](../results/executive_summary.md)

Describe this as independent portfolio work. No employment relationship with Olist, causal finding, implemented business uplift or cloud deployment is implied.
