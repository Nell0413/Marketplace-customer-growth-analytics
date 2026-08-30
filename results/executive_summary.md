# Executive analysis summary

## Scope

- Public, anonymised Olist marketplace data covering 96,478 delivered orders and 93,358 observed customers.
- Purchase period: 2016-09-15 to 2018-08-29.
- Currency: Brazilian real (BRL).
- `item_gmv` is a GMV proxy based on item price. It is not Olist revenue, profit, or margin.

## Verified headline metrics

- Delivered GMV: BRL 13,221,498.11; average order value: BRL 137.04.
- Jan-Jul 2018 delivered GMV was 161.6% above Jan-Jul 2017, while delivered order volume grew 160.8%.
- Only 3.00% of observed customers placed at least two delivered orders. Repeat orders generated 2.90% of delivered GMV.
- The censoring-adjusted 90-day second-purchase rate was 2.28% across 75,320 eligible first-time customers.
- 91.9% of delivered orders arrived by the estimated date. Late orders averaged 2.57/5 versus 4.29/5 for on-time or early orders.
- 54.0% of reviewed late orders received a score of 1-2, compared with 9.2% of reviewed on-time or early orders - a 5.9x difference. This is an association, not proof of causation.
- The rule-based `At-risk high-value` segment represented 12,790 customers (13.7%) and 33.8% of observed GMV.
- Sao Paulo represented 38.3% of delivered GMV; the top three states represented 63.4%. On-time performance was 94.1% in SP, versus 86.5% in RJ and 86.0% in BA.

## Commercial interpretation

1. **Growth quality:** Growth was strong, but repeat-order contribution remained small. A useful next test would target the second-purchase window rather than relying only on acquisition.
2. **Customer experience:** Delivery lateness is strongly associated with lower review scores. Operations should prioritise high-GMV seller/category/region combinations with weak on-time performance and then measure whether service interventions improve outcomes.
3. **CRM prioritisation:** The rule-based at-risk high-value segment provides a transparent starting audience for a reactivation experiment. It is observed historical value, not predicted lifetime value.
4. **Regional operations:** RJ and BA combine meaningful GMV with lower on-time performance than SP, making them candidates for deeper carrier, route, seller and category analysis.

## Data limitations

- Historical Brazil marketplace data from 2016-2018 is used to demonstrate transferable analytical methods, not to claim current Australian consumer insights.
- The data has no visits, impressions, carts or marketing spend, so it cannot support website conversion, CAC or ROAS.
- The data has no platform commission or cost of goods, so GMV cannot be treated as company revenue, profit or margin.
- Repeat purchase is measured only inside the observation window. It is not true lifetime retention or CLV.
- Delivery and review results are observational; unmeasured product, seller, region and customer factors may influence both.
