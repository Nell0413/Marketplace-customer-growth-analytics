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

The saved queries reference local CSV files from the original authoring computer. Those paths are not portable. The supplied [RefreshQueries.pq](RefreshQueries.pq) replaces them with a shared folder parameter; it must first be applied in Desktop. The existing PBIX and the layout-only candidate do **not** already contain these replacements.

1. Follow [Reproducibility](../docs/REPRODUCIBILITY.md) to generate the seven model CSVs in `data/processed/`. Copy all seven together if using a different data directory.
2. Open **Transform data → Manage Parameters → New Parameter**. Name it `DataFolder`, type **Text**, and set its current value to your processed-data folder, for example `C:\\Projects\\Marketplace Data\\processed`. No trailing slash is needed.
3. Create a **Blank Query**, name it `RefreshQueries`, open **Advanced Editor**, and paste the complete contents of [RefreshQueries.pq](RefreshQueries.pq). Disable load for this helper query; it returns a record of seven tables.
4. In each of the existing seven CSV queries, replace the Advanced Editor content with `let Source = RefreshQueries[fact_orders] in Source`, replacing `fact_orders` with that query's exact existing name. Do not delete/recreate tables or change `_Measures`, calculated columns, relationships or State slicer bindings.
5. Apply changes, refresh, reset filters, and reconcile with [`results/headline_metrics.json`](../results/headline_metrics.json). Save as a separate PBIX.
6. Copy the CSVs to another folder containing spaces/non-ASCII characters, change **only** `DataFolder`, and refresh again. Compare totals and filter behaviour with the first location using the [Windows checklist](../docs/WINDOWS_VALIDATION.md).

The replacement queries read UTF-8 and quoted CSV fields, parse month keys explicitly, and preserve `dim_customer[Column1]`, `[Column2]` and `[State]` while correctly removing the CSV header row. `fact_sales[review_score]` is imported as a decimal, preserving averaged review values. These are source-level corrections; Windows runtime verification is still required.

Before Desktop refresh, validate both sets of files from any working directory:

```bash
python scripts/check_refresh_sources.py "/first/processed" --compare-with "/second/processed"
```

This checks seven CSV schemas, UTF-8 readability, row counts and byte-identical relocation. It does not execute Power Query or DAX. Microsoft's [parameter documentation](https://learn.microsoft.com/en-us/power-query/power-query-query-parameters) describes the parameter setup.

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

Delivered GMV excludes freight and is not revenue, profit or margin. Review rates use reviewed delivered orders. The late/on-time low-review multiple is an observational association, not a causal effect. See [Metrics and quality](../docs/METRICS_AND_QUALITY.md) and the [actual model, DAX and filter paths](../docs/POWER_BI_MODEL.md).
