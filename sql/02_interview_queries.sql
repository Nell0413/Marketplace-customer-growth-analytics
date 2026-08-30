-- 1. Reconcile delivered GMV at the order and item grains.
WITH order_grain AS (
    SELECT SUM(item_gmv) AS gmv
    FROM fact_orders
    WHERE order_status = 'delivered'
), item_grain AS (
    SELECT SUM(price) AS gmv
    FROM fact_sales
    WHERE order_status = 'delivered'
)
SELECT
    o.gmv AS order_fact_gmv,
    i.gmv AS item_fact_gmv,
    o.gmv - i.gmv AS reconciliation_difference
FROM order_grain AS o
CROSS JOIN item_grain AS i;

-- 2. Find the top three categories by delivered GMV within each customer state.
WITH state_category AS (
    SELECT
        customer_state,
        product_category_name_english AS category,
        COUNT(DISTINCT order_id) AS delivered_orders,
        SUM(price) AS delivered_gmv_brl
    FROM fact_sales
    WHERE order_status = 'delivered'
    GROUP BY customer_state, product_category_name_english
), ranked AS (
    SELECT
        *,
        DENSE_RANK() OVER (
            PARTITION BY customer_state
            ORDER BY delivered_gmv_brl DESC
        ) AS category_rank
    FROM state_category
)
SELECT *
FROM ranked
WHERE category_rank <= 3
ORDER BY customer_state, category_rank;

-- 3. Build a seller scorecard without weighting order-level delivery and review
-- metrics by the number of item rows.
WITH order_seller AS (
    SELECT
        s.order_id,
        s.seller_id,
        SUM(s.price) AS seller_order_gmv_brl,
        SUM(s.freight_value) AS seller_order_freight_brl,
        MAX(o.on_time_flag) AS order_on_time_flag,
        MAX(o.review_score) AS order_review_score
    FROM fact_sales AS s
    JOIN vw_delivered_orders AS o
      ON s.order_id = o.order_id
    GROUP BY s.order_id, s.seller_id
), scorecard AS (
    SELECT
        seller_id,
        COUNT(*) AS delivered_orders,
        SUM(seller_order_gmv_brl) AS delivered_gmv_brl,
        AVG(order_on_time_flag) AS on_time_delivery_rate,
        AVG(order_review_score) AS associated_order_review_score
    FROM order_seller
    GROUP BY seller_id
)
SELECT
    *,
    DENSE_RANK() OVER (ORDER BY delivered_gmv_brl DESC) AS gmv_rank
FROM scorecard
WHERE delivered_orders >= 20
ORDER BY delivered_gmv_brl DESC;

-- 4. Compare review outcomes across delivery-delay bands. The result is an
-- association and should not be interpreted as a causal effect.
SELECT
    CASE
        WHEN delay_days <= 0 THEN 'On time or early'
        WHEN delay_days <= 3 THEN '1-3 days late'
        WHEN delay_days <= 7 THEN '4-7 days late'
        ELSE 'More than 7 days late'
    END AS delivery_band,
    COUNT(DISTINCT order_id) AS reviewed_orders,
    AVG(review_score) AS average_review_score,
    AVG(low_review_flag) AS low_review_rate
FROM vw_delivered_orders
WHERE review_score IS NOT NULL
  AND delay_days IS NOT NULL
GROUP BY delivery_band
ORDER BY MIN(delay_days);

-- 5. Show monthly GMV and its month-over-month change using a window function.
WITH monthly AS (
    SELECT
        purchase_month,
        COUNT(DISTINCT order_id) AS delivered_orders,
        SUM(item_gmv) AS delivered_gmv_brl
    FROM vw_delivered_orders
    GROUP BY purchase_month
), trended AS (
    SELECT
        *,
        LAG(delivered_gmv_brl) OVER (ORDER BY purchase_month) AS prior_month_gmv_brl
    FROM monthly
)
SELECT
    *,
    (delivered_gmv_brl - prior_month_gmv_brl)
        / NULLIF(prior_month_gmv_brl, 0) AS gmv_mom_rate
FROM trended
ORDER BY purchase_month;

