# Power BI report guide

## Delivered report

The repository includes [Dashboard_Commercial_Fulfilment_Final.pbix](Dashboard_Commercial_Fulfilment_Final.pbix), with two completed pages:

1. **Marketplace Performance Overview** — headline KPIs, monthly delivered GMV and orders, comparable-period growth, and first/repeat order GMV.
2. **Commercial & Fulfilment Performance** — category and state performance, freight burden, delivery reliability, and customer experience.

[Page 1 preview](../docs/images/marketplace-performance-overview.png) · [Page 2 preview](../docs/images/commercial-fulfilment-performance.png)

The screenshots were captured from this final PBIX in Power BI Desktop with Period and State set to All. The PBIX is the delivered implementation; the earlier five-page concept has been replaced by the two-page report. Cohort, RFM and fixed-window retention analyses remain available as [supporting results](../results/).

## Open and explore

1. Download the PBIX using GitHub's raw-file download, then open it in a current Windows version of Microsoft Power BI Desktop.
2. Select either report page and use the **Period** and **State** slicers.
3. Use the reset control to restore the page's default selection.
4. Save a local copy to preserve edits.

The PBIX contains its imported data snapshot. Viewing the saved report does not require the original CSV files. GitHub provides static previews; it does not run the interactive report.

### Filter behaviour and interpretation

- The main performance visuals respond to the selected observation period and state.
- The growth-driver chart deliberately compares **Jan–Jul 2018 with Jan–Jul 2017**, regardless of the Period selection. State filtering still applies.
- Repeat customers are counted within the selected observation window. First/repeat order classification uses order sequence across the available history.
- The category chart shows the top 10 categories by delivered GMV. The state opportunity chart shows the top 7 states by delivered GMV.
- Small charts may require horizontal scrolling in Desktop to inspect all month labels.
- The opening executive and priority-action text summarises the overall historical analysis; interpret it in that context when applying filters.

## Refresh on another computer

The saved queries reference local CSV files from the original authoring computer. Those paths are not portable.

1. Follow the [repository reproduction steps](../README.md#reproduce-the-analysis) to generate the model CSVs in `data/processed/`.
2. In Power BI Desktop, open **File → Options and settings → Data source settings**, select the file connections and update their paths. If a connection cannot be changed there, open **Transform data** and edit that query's Source step.
3. Check the applied steps, column names, encodings and data types before refreshing. Some imported dimension fields retain generic names such as `Column1`; preserve the names used by the existing relationships and DAX, or update their dependent references deliberately.
4. Apply changes, refresh, reset filters, and reconcile the headline cards with [`results/headline_metrics.json`](../results/headline_metrics.json).
5. Save the refreshed report as a separate local copy.

The refresh instructions describe the manual reconnection procedure; a refresh from an arbitrary new source directory is not automated.

Model source files:

| CSV | Grain / purpose |
| :--- | :--- |
| `fact_orders.csv` | One row per order; customer, delivery, review and order KPIs. |
| `fact_sales.csv` | One row per order item; product, seller, GMV and freight analysis. |
| `dim_customer.csv` | Customer dimension. |
| `dim_product.csv` | Product and translated category attributes. |
| `dim_seller.csv` | Seller dimension. |
| `dim_date.csv` | Calendar dates and time attributes. |
| `mart_customer_rfm.csv` | Observed customer recency, frequency, value and rule-based segments. |

See Microsoft's [data source documentation](https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-data-sources) for connection settings.

## Baseline reconciliation

The unfiltered saved report displays the following rounded values:

| Measure | Expected display |
| :--- | :--- |
| Delivered GMV | R$ 13.22M |
| Delivered orders | 96.5K |
| Active customers | 93.4K |
| Average order value | R$ 137.04 |
| Repeat customer rate | 3.0% |
| On-time delivery rate | 91.9% |
| Freight to GMV | 16.6% |
| Average delivery days | 12.6 |
| Average review score | 4.16 / 5 |
| Low-review rate | 12.8% |

Exact source results include delivered GMV of **R$ 13,221,498.11**, **96,478** delivered orders and **93,358** customers. The order/item GMV reconciliation difference in the committed data-quality output is **R$ 0.00**.

Delivered GMV excludes freight and is not revenue, profit or margin. Review rates use reviewed delivered orders. The late/on-time low-review multiple is an observational association, not a causal effect. Full metric definitions and limitations are in the [README](../README.md#data-and-metric-definitions).
