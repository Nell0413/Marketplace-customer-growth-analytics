# Windows acceptance checks before v1.0.0

Prepared **6 September 2026**. Publication date: **pending**. The v1.0.0 release is a draft until the candidate has been opened, saved and checked in Windows Power BI Desktop. The existing main-branch PBIX and its two screenshots remain the previous baseline.

## Candidate changes

Generate the non-overwriting layout candidate locally:

```bash
python scripts/prepare_page2_candidate.py --output Marketplace_v1.0.0_Windows_Check.pbix
```

The script changes four Page 2 visuals: it uses a continuous monthly date axis instead of crowded categorical month labels; expands the low-review axis from 65% to 100%; removes the scatter plot's 80% minimum and fixed GMV maximum, increases its plot height and reduces state-label size; and labels static priority actions as a full-data baseline. BA/RJ label placement still needs visual inspection after filtering.

It preserves the imported `DataModel` byte-for-byte, including DAX, relationships and **original source paths**. It changes only report definitions and associated archive integrity metadata. This candidate was constructed from the PBIX archive, not saved by Power BI Desktop. Successful archive/JSON validation is not a guarantee that Desktop will accept or render it correctly. Keep the original PBIX as the fallback.

## Acceptance checklist

1. **Open and save:** open the candidate in current Windows Power BI Desktop. If it cannot open, retain the original and apply the four visual changes above manually; do not publish the candidate. If it opens, save a fresh copy from Desktop.
2. **Page 2:** confirm month ticks include the year, the complete period is visible without a categorical scrollbar, BA and RJ remain distinguishable, and labels are not clipped. Check a narrow period/state with an on-time rate below 80% or low-review rate above 65%. Verify the new axes show those values.
3. **Baseline:** reset Period/State and check GMV R$13,221,498.11, orders 96,478, customers 93,358 and repeat customer rate about 3.0%. Check on-time delivery about 91.9% and average review 4.16. Totals need not match the baseline while filters are active.
4. **Filter paths:** select SP and then RJ. Order-level and item-level metrics must respond together. Change Period: main KPIs change while the fixed Jan–Jul 2018/2017 growth comparison retains its two fixed windows and still responds to State. Do not replace the slicer with `dim_customer[State]`.
5. **Portable refresh:** apply [RefreshQueries.pq](../powerbi/RefreshQueries.pq) using the [setup instructions](../powerbi/POWER_BI_BUILD_GUIDE.md#refresh-on-another-computer). Refresh against folder A; copy the same seven CSVs to folder B containing spaces/non-ASCII characters; change only `DataFolder` and refresh again. Baseline totals must agree. Inspect dates, accented city names and missing reviews.
6. **Complete the release:** save the accepted PBIX as `Marketplace_Customer_Growth_v1.0.0.pbix`; capture fresh screenshots from that file with filters reset. Replace the draft asset, record Desktop version, validation date and outcomes, then publish v1.0.0. Replace the repository baseline/screenshots only after acceptance.

## Evidence completed without Desktop

- The full Python/SQL pipeline was rebuilt in a fresh checkout and invoked from a different working directory. Delivered GMV reconciliation remained R$0.00.
- Synthetic tests cover duplicate order rejection, missing reviews, repeated items/payments/reviews without GMV fanout, inclusive day-90 repurchase and complete follow-up eligibility.
- Additional tests cover seven CSV contracts, UTF-8/quoted data in relocated directories, mismatched copies, and preservation of the original PBIX model while producing a layout candidate.
- GitHub Actions runs the fixtures and PBIX archive/JSON/canvas inspection. It does not launch Power BI Desktop, evaluate DAX or execute M.

Record the final Desktop results here before publishing; do not mark a check passed solely because a Python test passed.
