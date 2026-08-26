-- ============================================================
-- FILE: 03_churn_analysis.sql
-- PURPOSE: FAANG-level SQL queries for Churn Analysis
-- Run AFTER data is imported
-- ============================================================

USE ecommerce_churn;

-- ============================================================
-- QUERY 1: Overall Dataset Summary
-- ============================================================
SELECT 
    COUNT(DISTINCT c.customer_unique_id)    AS unique_customers,
    COUNT(DISTINCT o.order_id)              AS total_orders,
    ROUND(SUM(p.payment_value), 2)          AS total_revenue,
    ROUND(AVG(p.payment_value), 2)          AS avg_order_value,
    MIN(o.order_purchase_timestamp)         AS first_order_date,
    MAX(o.order_purchase_timestamp)         AS last_order_date
FROM customers c
JOIN orders o    ON c.customer_id  = o.customer_id
JOIN payments p  ON o.order_id     = p.order_id
WHERE o.order_status = 'delivered';


-- ============================================================
-- QUERY 2: Churn Rate Calculation
-- Definition: No purchase in 90+ days = Churned
-- Reference date = 2018-10-01 (dataset end)
-- ============================================================
WITH last_purchase AS (
    SELECT
        c.customer_unique_id,
        MAX(o.order_purchase_timestamp) AS last_order_date
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
churn_labels AS (
    SELECT
        customer_unique_id,
        last_order_date,
        DATEDIFF('2018-10-01', last_order_date) AS days_since_last_order,
        CASE
            WHEN DATEDIFF('2018-10-01', last_order_date) > 90
            THEN 'Churned'
            ELSE 'Active'
        END AS churn_status
    FROM last_purchase
)
SELECT
    churn_status,
    COUNT(*)                                                    AS customer_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2)         AS percentage
FROM churn_labels
GROUP BY churn_status;


-- ============================================================
-- QUERY 3: Customer Revenue Segmentation using NTILE
-- (Window Function — FAANG Interview Favourite)
-- ============================================================
WITH customer_revenue AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id)     AS total_orders,
        ROUND(SUM(p.payment_value), 2) AS total_revenue,
        ROUND(AVG(p.payment_value), 2) AS avg_order_value,
        MAX(o.order_purchase_timestamp) AS last_order_date
    FROM customers c
    JOIN orders o   ON c.customer_id = o.customer_id
    JOIN payments p ON o.order_id    = p.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
ranked AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY total_revenue DESC) AS revenue_quartile
    FROM customer_revenue
)
SELECT
    revenue_quartile,
    CASE revenue_quartile
        WHEN 1 THEN 'Top 25% (VIP)'
        WHEN 2 THEN 'Mid-High 25%'
        WHEN 3 THEN 'Mid-Low 25%'
        WHEN 4 THEN 'Bottom 25%'
    END                                             AS segment_name,
    COUNT(*)                                        AS customer_count,
    ROUND(SUM(total_revenue), 2)                   AS segment_revenue,
    ROUND(AVG(avg_order_value), 2)                 AS avg_order_value,
    ROUND(AVG(total_orders), 2)                    AS avg_orders_per_customer
FROM ranked
GROUP BY revenue_quartile
ORDER BY revenue_quartile;


-- ============================================================
-- QUERY 4: Monthly Cohort Retention Analysis
-- Shows how many customers from each cohort return in later months
-- ============================================================
WITH first_order AS (
    SELECT
        c.customer_unique_id,
        DATE_FORMAT(MIN(o.order_purchase_timestamp), '%Y-%m') AS cohort_month
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
all_orders AS (
    SELECT
        c.customer_unique_id,
        DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS order_month
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_customers
    FROM first_order
    GROUP BY cohort_month
)
SELECT
    f.cohort_month,
    cs.cohort_customers,
    a.order_month,
    COUNT(DISTINCT a.customer_unique_id)                                         AS retained_customers,
    ROUND(COUNT(DISTINCT a.customer_unique_id) * 100.0 / cs.cohort_customers, 2) AS retention_rate_pct
FROM first_order f
JOIN all_orders a  ON f.customer_unique_id  = a.customer_unique_id
JOIN cohort_size cs ON f.cohort_month       = cs.cohort_month
WHERE a.order_month >= f.cohort_month
GROUP BY f.cohort_month, cs.cohort_customers, a.order_month
ORDER BY f.cohort_month, a.order_month;


-- ============================================================
-- QUERY 5: Review Score vs Churn Correlation
-- ============================================================
WITH avg_review AS (
    SELECT
        o.customer_id,
        ROUND(AVG(r.review_score), 2) AS avg_review_score
    FROM orders o
    JOIN reviews r ON o.order_id = r.order_id
    GROUP BY o.customer_id
),
churn_status AS (
    SELECT
        c.customer_id,
        CASE
            WHEN MAX(o.order_purchase_timestamp) < DATE_SUB('2018-10-01', INTERVAL 90 DAY)
            THEN 'Churned'
            ELSE 'Active'
        END AS churn_label
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_id
)
SELECT
    cs.churn_label,
    ROUND(AVG(ar.avg_review_score), 2) AS avg_review_score,
    COUNT(*)                           AS customer_count
FROM churn_status cs
JOIN avg_review ar ON cs.customer_id = ar.customer_id
GROUP BY cs.churn_label;


-- ============================================================
-- QUERY 6: Delivery Delay Impact on Churn
-- (Late deliveries → lower satisfaction → higher churn)
-- ============================================================
WITH delivery_stats AS (
    SELECT
        c.customer_unique_id,
        ROUND(AVG(
            DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date)
        ), 1) AS avg_delay_days,
        CASE
            WHEN MAX(o.order_purchase_timestamp) < DATE_SUB('2018-10-01', INTERVAL 90 DAY)
            THEN 'Churned'
            ELSE 'Active'
        END AS churn_label
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_unique_id
)
SELECT
    churn_label,
    ROUND(AVG(avg_delay_days), 2)  AS avg_delivery_delay_days,
    COUNT(*)                        AS customers,
    SUM(CASE WHEN avg_delay_days > 0 THEN 1 ELSE 0 END)  AS late_deliveries,
    ROUND(
        SUM(CASE WHEN avg_delay_days > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
    ) AS late_delivery_pct
FROM delivery_stats
GROUP BY churn_label;


-- ============================================================
-- QUERY 7: Running Revenue using Cumulative Window Function
-- ============================================================
WITH monthly_revenue AS (
    SELECT
        DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')  AS month,
        ROUND(SUM(p.payment_value), 2)                    AS monthly_revenue
    FROM orders o
    JOIN payments p ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')
)
SELECT
    month,
    monthly_revenue,
    ROUND(SUM(monthly_revenue) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING), 2) AS cumulative_revenue,
    ROUND(
        (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY month)) * 100.0 /
        LAG(monthly_revenue) OVER (ORDER BY month), 2
    ) AS mom_growth_pct
FROM monthly_revenue
ORDER BY month;


-- ============================================================
-- QUERY 8: Top States by Churn Rate
-- ============================================================
WITH state_churn AS (
    SELECT
        c.customer_state,
        COUNT(DISTINCT c.customer_unique_id) AS total_customers,
        SUM(CASE
            WHEN MAX_order.last_order < DATE_SUB('2018-10-01', INTERVAL 90 DAY)
            THEN 1 ELSE 0
        END) AS churned_customers
    FROM customers c
    JOIN (
        SELECT customer_id, MAX(order_purchase_timestamp) AS last_order
        FROM orders
        WHERE order_status = 'delivered'
        GROUP BY customer_id
    ) AS MAX_order ON c.customer_id = MAX_order.customer_id
    GROUP BY c.customer_state
)
SELECT
    customer_state,
    total_customers,
    churned_customers,
    ROUND(churned_customers * 100.0 / total_customers, 2) AS churn_rate_pct
FROM state_churn
ORDER BY churn_rate_pct DESC
LIMIT 10;
