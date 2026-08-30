CREATE INDEX IF NOT EXISTS idx_fact_orders_order_id
    ON fact_orders(order_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_customer
    ON fact_orders(customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_purchase_month
    ON fact_orders(purchase_month);
CREATE INDEX IF NOT EXISTS idx_fact_sales_order_id
    ON fact_sales(order_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_category
    ON fact_sales(product_category_name_english);
CREATE INDEX IF NOT EXISTS idx_stg_payments_order_id
    ON stg_order_payments(order_id);

DROP VIEW IF EXISTS vw_delivered_orders;
CREATE VIEW vw_delivered_orders AS
SELECT *
FROM fact_orders
WHERE order_status = 'delivered';

DROP VIEW IF EXISTS mart_executive_monthly;
CREATE VIEW mart_executive_monthly AS
WITH monthly AS (
    SELECT
        purchase_month,
        COUNT(DISTINCT order_id) AS delivered_orders,
        COUNT(DISTINCT customer_unique_id) AS active_customers,
        SUM(item_gmv) AS delivered_gmv_brl,
        SUM(freight_value) AS freight_brl,
        SUM(CASE WHEN first_observed_delivered_order_flag = 1 THEN item_gmv ELSE 0 END)
            AS first_order_gmv_brl,
        SUM(CASE WHEN first_observed_delivered_order_flag = 0 THEN item_gmv ELSE 0 END)
            AS repeat_order_gmv_brl,
        AVG(on_time_flag) AS on_time_delivery_rate,
        AVG(review_score) AS average_review_score
    FROM vw_delivered_orders
    GROUP BY purchase_month
), trended AS (
    SELECT
        *,
        LAG(delivered_gmv_brl) OVER (ORDER BY purchase_month) AS previous_month_gmv_brl,
        LAG(delivered_orders) OVER (ORDER BY purchase_month) AS previous_month_orders
    FROM monthly
)
SELECT
    purchase_month,
    delivered_orders,
    active_customers,
    delivered_gmv_brl,
    freight_brl,
    delivered_gmv_brl / NULLIF(delivered_orders, 0) AS average_order_value_brl,
    delivered_orders * 1.0 / NULLIF(active_customers, 0) AS purchase_frequency,
    freight_brl / NULLIF(delivered_gmv_brl, 0) AS freight_to_gmv_ratio,
    first_order_gmv_brl,
    repeat_order_gmv_brl,
    repeat_order_gmv_brl / NULLIF(delivered_gmv_brl, 0) AS repeat_order_gmv_share,
    on_time_delivery_rate,
    average_review_score,
    (delivered_gmv_brl - previous_month_gmv_brl)
        / NULLIF(previous_month_gmv_brl, 0) AS gmv_mom_rate,
    (delivered_orders - previous_month_orders) * 1.0
        / NULLIF(previous_month_orders, 0) AS orders_mom_rate
FROM trended;

DROP VIEW IF EXISTS mart_customer_lifecycle;
CREATE VIEW mart_customer_lifecycle AS
WITH sequenced AS (
    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp,
        item_gmv,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY order_purchase_timestamp, order_id
        ) AS order_number,
        LEAD(order_purchase_timestamp) OVER (
            PARTITION BY customer_unique_id
            ORDER BY order_purchase_timestamp, order_id
        ) AS next_purchase_timestamp
    FROM vw_delivered_orders
)
SELECT
    customer_unique_id,
    MIN(order_purchase_timestamp) AS first_purchase_timestamp,
    MAX(order_purchase_timestamp) AS last_purchase_timestamp,
    COUNT(DISTINCT order_id) AS delivered_orders,
    SUM(item_gmv) AS observed_gmv_brl,
    MIN(
        CASE
            WHEN order_number = 1 AND next_purchase_timestamp IS NOT NULL
            THEN julianday(next_purchase_timestamp) - julianday(order_purchase_timestamp)
        END
    ) AS days_to_second_order
FROM sequenced
GROUP BY customer_unique_id;

DROP VIEW IF EXISTS mart_cohort_retention;
CREATE VIEW mart_cohort_retention AS
WITH customer_months AS (
    SELECT DISTINCT
        customer_unique_id,
        purchase_month AS order_month
    FROM vw_delivered_orders
), cohort AS (
    SELECT
        customer_unique_id,
        MIN(order_month) AS cohort_month
    FROM customer_months
    GROUP BY customer_unique_id
), activity AS (
    SELECT
        c.cohort_month,
        m.order_month,
        (
            CAST(substr(m.order_month, 1, 4) AS INTEGER) * 12
            + CAST(substr(m.order_month, 6, 2) AS INTEGER)
        ) - (
            CAST(substr(c.cohort_month, 1, 4) AS INTEGER) * 12
            + CAST(substr(c.cohort_month, 6, 2) AS INTEGER)
        ) AS cohort_period,
        COUNT(DISTINCT m.customer_unique_id) AS active_customers
    FROM customer_months AS m
    JOIN cohort AS c
      ON m.customer_unique_id = c.customer_unique_id
    GROUP BY c.cohort_month, m.order_month, cohort_period
), cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(*) AS cohort_customers
    FROM cohort
    GROUP BY cohort_month
)
SELECT
    a.cohort_month,
    a.order_month,
    a.cohort_period,
    a.active_customers,
    s.cohort_customers,
    a.active_customers * 1.0 / NULLIF(s.cohort_customers, 0) AS retention_rate
FROM activity AS a
JOIN cohort_sizes AS s
  ON a.cohort_month = s.cohort_month;

DROP VIEW IF EXISTS mart_repeat_windows;
CREATE VIEW mart_repeat_windows AS
WITH sequenced AS (
    SELECT
        customer_unique_id,
        order_purchase_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY order_purchase_timestamp, order_id
        ) AS order_number,
        LEAD(order_purchase_timestamp) OVER (
            PARTITION BY customer_unique_id
            ORDER BY order_purchase_timestamp, order_id
        ) AS next_purchase_timestamp
    FROM vw_delivered_orders
), first_orders AS (
    SELECT
        customer_unique_id,
        order_purchase_timestamp AS first_purchase_timestamp,
        next_purchase_timestamp
    FROM sequenced
    WHERE order_number = 1
), observation AS (
    SELECT MAX(order_purchase_timestamp) AS observation_end
    FROM vw_delivered_orders
), windows AS (
    SELECT 30 AS window_days
    UNION ALL SELECT 60
    UNION ALL SELECT 90
    UNION ALL SELECT 180
    UNION ALL SELECT 365
)
SELECT
    w.window_days,
    SUM(
        CASE
            WHEN julianday(o.observation_end) - julianday(f.first_purchase_timestamp)
                >= w.window_days
            THEN 1 ELSE 0
        END
    ) AS eligible_customers,
    SUM(
        CASE
            WHEN julianday(o.observation_end) - julianday(f.first_purchase_timestamp)
                >= w.window_days
             AND f.next_purchase_timestamp IS NOT NULL
             AND julianday(f.next_purchase_timestamp) - julianday(f.first_purchase_timestamp)
                <= w.window_days
            THEN 1 ELSE 0
        END
    ) AS repeat_customers,
    SUM(
        CASE
            WHEN julianday(o.observation_end) - julianday(f.first_purchase_timestamp)
                >= w.window_days
             AND f.next_purchase_timestamp IS NOT NULL
             AND julianday(f.next_purchase_timestamp) - julianday(f.first_purchase_timestamp)
                <= w.window_days
            THEN 1 ELSE 0
        END
    ) * 1.0 / NULLIF(
        SUM(
            CASE
                WHEN julianday(o.observation_end) - julianday(f.first_purchase_timestamp)
                    >= w.window_days
                THEN 1 ELSE 0
            END
        ), 0
    ) AS repeat_purchase_rate
FROM first_orders AS f
CROSS JOIN observation AS o
CROSS JOIN windows AS w
GROUP BY w.window_days;

DROP VIEW IF EXISTS mart_category_performance;
CREATE VIEW mart_category_performance AS
WITH order_category AS (
    SELECT
        s.order_id,
        s.product_category_name_english AS category,
        SUM(s.price) AS category_gmv_brl,
        SUM(s.freight_value) AS category_freight_brl,
        COUNT(*) AS items,
        MAX(o.on_time_flag) AS on_time_flag,
        MAX(o.review_score) AS review_score
    FROM fact_sales AS s
    JOIN vw_delivered_orders AS o
      ON s.order_id = o.order_id
    GROUP BY s.order_id, s.product_category_name_english
)
SELECT
    category,
    COUNT(DISTINCT order_id) AS delivered_orders,
    SUM(items) AS delivered_items,
    SUM(category_gmv_brl) AS delivered_gmv_brl,
    SUM(category_freight_brl) AS freight_brl,
    SUM(category_gmv_brl) / NULLIF(COUNT(DISTINCT order_id), 0) AS average_order_value_brl,
    SUM(category_freight_brl) / NULLIF(SUM(category_gmv_brl), 0) AS freight_to_gmv_ratio,
    AVG(on_time_flag) AS on_time_delivery_rate,
    AVG(review_score) AS average_review_score
FROM order_category
GROUP BY category;

DROP VIEW IF EXISTS mart_state_performance;
CREATE VIEW mart_state_performance AS
SELECT
    customer_state,
    COUNT(DISTINCT order_id) AS delivered_orders,
    COUNT(DISTINCT customer_unique_id) AS active_customers,
    SUM(item_gmv) AS delivered_gmv_brl,
    SUM(item_gmv) / NULLIF(COUNT(DISTINCT order_id), 0) AS average_order_value_brl,
    AVG(on_time_flag) AS on_time_delivery_rate,
    AVG(review_score) AS average_review_score,
    AVG(CASE WHEN review_score IS NOT NULL THEN low_review_flag END) AS low_review_rate
FROM vw_delivered_orders
GROUP BY customer_state;

DROP VIEW IF EXISTS mart_delivery_experience;
CREATE VIEW mart_delivery_experience AS
SELECT
    CASE WHEN late_flag = 1 THEN 'Late' ELSE 'On time or early' END AS delivery_group,
    COUNT(DISTINCT order_id) AS delivered_orders,
    AVG(delivery_days) AS average_delivery_days,
    AVG(review_score) AS average_review_score,
    AVG(CASE WHEN review_score IS NOT NULL THEN low_review_flag END) AS low_review_rate,
    AVG(
        CASE
            WHEN review_score IS NULL THEN NULL
            WHEN review_score >= 4 THEN 1.0
            ELSE 0.0
        END
    )
        AS high_review_rate
FROM vw_delivered_orders
WHERE late_flag IS NOT NULL
GROUP BY delivery_group;

DROP VIEW IF EXISTS mart_payment_mix;
CREATE VIEW mart_payment_mix AS
WITH payment AS (
    SELECT
        p.payment_type,
        p.order_id,
        p.payment_value
    FROM stg_order_payments AS p
    JOIN vw_delivered_orders AS o
      ON p.order_id = o.order_id
), summary AS (
    SELECT
        payment_type,
        COUNT(*) AS payment_records,
        COUNT(DISTINCT order_id) AS orders,
        SUM(payment_value) AS payment_value_brl
    FROM payment
    GROUP BY payment_type
)
SELECT
    payment_type,
    payment_records,
    orders,
    payment_value_brl,
    payment_value_brl / SUM(payment_value_brl) OVER () AS payment_value_share
FROM summary;

DROP VIEW IF EXISTS mart_rfm_segment_summary;
CREATE VIEW mart_rfm_segment_summary AS
SELECT
    segment,
    COUNT(*) AS customers,
    SUM(observed_gmv) AS observed_gmv_brl,
    AVG(observed_gmv) AS average_observed_gmv_brl,
    COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS customer_share,
    SUM(observed_gmv) / SUM(SUM(observed_gmv)) OVER () AS observed_gmv_share
FROM mart_customer_rfm
GROUP BY segment;
