# Reproduce the analysis

[Project overview](../README.md) · [Metric definitions and quality](METRICS_AND_QUALITY.md) · [Power BI opening and refresh guide](../powerbi/POWER_BI_BUILD_GUIDE.md)

The Python/SQL pipeline rebuilds the analytical database, CSVs and result files. Opening the saved PBIX is a separate workflow: its imported snapshot can be viewed without running these scripts, but refreshing it requires Power BI Desktop on Windows and valid source-file connections.

## 1. Get the repository and dataset

Use **Python 3.10 or later**. Clone or download the repository:

```bash
git clone https://github.com/Nell0413/Marketplace-customer-growth-analytics.git
cd Marketplace-customer-growth-analytics
```

Download the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), then place its nine CSVs in `data/raw/`, preserving their original filenames:

```text
data/raw/
  olist_customers_dataset.csv
  olist_geolocation_dataset.csv
  olist_order_items_dataset.csv
  olist_order_payments_dataset.csv
  olist_order_reviews_dataset.csv
  olist_orders_dataset.csv
  olist_products_dataset.csv
  olist_sellers_dataset.csv
  product_category_name_translation.csv
```

The raw and processed data directories are excluded from Git. Downloading the repository alone does not supply the raw data for a full rebuild.

## 2. Create a Python environment

From the repository root:

```bash
python -m venv .venv
```

Activate it in **Windows PowerShell**:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or in **macOS / Linux**:

```bash
source .venv/bin/activate
```

Install the declared dependencies:

```bash
python -m pip install -r requirements.txt
```

Use `python3` instead of `python` for environment creation if that is how Python 3 is installed on your system. Subsequent examples assume the environment is active. Dependency ranges are recorded in [`requirements.txt`](../requirements.txt); they are not an exact environment lockfile.

## Run the tests

From the repository root, with dependencies installed:

```bash
python -m unittest discover -s tests -v
```

The tests use small synthetic fixtures and do not require a Kaggle download or Power BI Desktop. They exercise edge cases such as duplicate orders, missing reviews and the 90-day second-purchase boundary. They should be run before a full-data rebuild.

These checks serve different purposes:

| Check | What it establishes |
| :--- | :--- |
| Fixture tests | Defined transformations and SQL boundary cases behave as expected on controlled inputs. |
| Full-data pipeline checks | The supplied dataset passes the implemented validation and order/item GMV reconciliation. |
| Power BI Desktop refresh and visual checks | The report can reconnect to the chosen files, evaluate its model and render the intended interactions. Python tests do not execute these steps. |

## 3. Build and export

Run the build before the analysis:

```bash
python src/build_project.py
python src/run_analysis.py
```

The build replaces the generated SQLite database and exports model CSVs. The analysis overwrites the generated result files, including the executive summary. Keep any manual edits or comparison copies elsewhere before rerunning.

| Output | Contents |
| :--- | :--- |
| `data/processed/olist_analytics.db` | SQLite staging tables, analytical tables and SQL views. |
| `data/processed/fact_orders.csv` | Order-level fact. |
| `data/processed/fact_sales.csv` | Item-level fact. |
| `data/processed/dim_customer.csv` | Customer dimension with latest observed customer location. |
| `data/processed/dim_product.csv` | Product/category dimension. |
| `data/processed/dim_seller.csv` | Seller dimension. |
| `data/processed/dim_date.csv` | Calendar dimension. |
| `data/processed/mart_customer_rfm.csv` | Rule-based customer segments. |
| `results/data_quality_report.json` | Source checks, reconciliation and quality observations. |
| `results/headline_metrics.json` | Machine-readable headline metrics. |
| `results/*.csv` | Monthly, cohort, repeat-window, category, state, delivery, payment and RFM analyses. |
| `results/executive_summary.md` | Generated business summary. |

Compare the regenerated metrics with [the documented baseline](METRICS_AND_QUALITY.md#baseline-results). For the original source dataset, delivered GMV should be **R$ 13,221,498.11**, with **96,478** delivered orders, **93,358** observed customers and a **R$ 0.00** order/item GMV reconciliation difference. A different source dataset can legitimately produce different results and should not be described as the same baseline.

## 4. Run from another working directory

Both entry-point scripts resolve the repository root from their own file location using `Path(__file__).resolve().parents[1]`. Input/output locations therefore follow the repository, not the shell's current directory. Moving only a script without its accompanying repository files is not supported.

With the environment active, call the scripts by their absolute paths. For example, replace the paths below with your own checkout location:

```bash
python "/path/to/Marketplace-customer-growth-analytics/src/build_project.py"
python "/path/to/Marketplace-customer-growth-analytics/src/run_analysis.py"
```

On Windows PowerShell:

```powershell
python "C:\projects\Marketplace-customer-growth-analytics\src\build_project.py"
python "C:\projects\Marketplace-customer-growth-analytics\src\run_analysis.py"
```

The source CSVs must still be in that checkout's `data/raw/`. Confirm that outputs are written to that checkout's `data/processed/` and `results/`, rather than to the directory from which you invoked Python. A successful Python build from another directory does **not** establish that Power Query's connections are portable.

## 5. Open or refresh Power BI

Download [`Dashboard_Commercial_Fulfilment_Final.pbix`](https://github.com/Nell0413/Marketplace-customer-growth-analytics/raw/refs/heads/main/powerbi/Dashboard_Commercial_Fulfilment_Final.pbix) and open it in Power BI Desktop on Windows. Its imported analytical snapshot can be viewed without the source CSVs.

For a refresh, follow the [Power BI guide](../powerbi/POWER_BI_BUILD_GUIDE.md#refresh-on-another-computer) to reconnect the report to the regenerated model files. Confirm the source paths, column types and relationships, refresh, and reconcile the unfiltered headline cards. Also inspect Page 2, the Period and State slicers, and the fixed Jan–Jul comparison using the [model and filter guide](POWER_BI_MODEL.md).

Save a separate refreshed PBIX after these checks. A source-level or synthetic-test pass is not a substitute for executing this Desktop procedure.

## Troubleshooting

- **Missing CSV:** check `data/raw/` in the same repository as the invoked script and verify the original filenames.
- **Missing Python package:** activate the intended environment and rerun `python -m pip install -r requirements.txt`.
- **SQLite database or view unavailable:** run `src/build_project.py` successfully before `src/run_analysis.py`.
- **Validation failure:** inspect the reported keys or references; do not bypass the error just to produce output.
- **PBIX shows a source-file error:** update its connections in Desktop using the Power BI guide. Rebuilding the Python outputs does not itself rewrite saved Power Query paths.
- **Filtered totals differ from the baseline:** clear report filters first; use the model guide to distinguish selected-period measures from the fixed-year comparison.
