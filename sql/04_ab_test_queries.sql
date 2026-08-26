-- ============================================================
-- FILE: 04_ab_test_queries.sql
-- PURPOSE: A/B Test Design & Analysis in SQL
-- Scenario: Did faster delivery reduce churn?
-- ============================================================

USE ecommerce_churn;

-- ============================================================
-- A/B TEST SETUP:
-- Group A (Control)   = Customers with avg delivery delay > 0 days (late)
-- Group B (Treatment) = Customers with avg delivery ON TIME or early
-- Metric              = Repeat purchase rate (did they buy again?)
-- ============================================================

WITH delivery_groups AS (
    SELECT
        c.customer_unique_id,
        ROUND(AVG(
            DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date)
        ), 1) AS avg_delay_days
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_unique_id
),
ab_groups AS (
    SELECT
        customer_unique_id,
        avg_delay_days,
        CASE
            WHEN avg_delay_days > 0 THEN 'Control (Late Delivery)'
            ELSE 'Treatment (On-Time Delivery)'
        END AS ab_group
    FROM delivery_groups
),
purchase_counts AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS total_orders
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT
    ab.ab_group,
    COUNT(ab.customer_unique_id)                                                        AS total_users,
    SUM(CASE WHEN COALESCE(pc.total_orders, 0) > 1 THEN 1 ELSE 0 END)                 AS repeat_buyers,
    ROUND(
        SUM(CASE WHEN COALESCE(pc.total_orders, 0) > 1 THEN 1 ELSE 0 END) * 100.0 /
        COUNT(ab.customer_unique_id), 2
    )                                                                                   AS repeat_purchase_rate_pct,
    ROUND(AVG(ab.avg_delay_days), 2)                                                   AS avg_delay_days
FROM ab_groups ab
LEFT JOIN purchase_counts pc ON ab.customer_unique_id = pc.customer_unique_id
GROUP BY ab.ab_group;


-- ============================================================
-- PAYMENT TYPE vs CHURN (Bonus insight for Power BI)
-- ============================================================
WITH payment_churn AS (
    SELECT
        p.payment_type,
        c.customer_unique_id,
        MAX(o.order_purchase_timestamp) AS last_order_date,
        CASE
            WHEN MAX(o.order_purchase_timestamp) < DATE_SUB('2018-10-01', INTERVAL 90 DAY)
            THEN 'Churned' ELSE 'Active'
        END AS churn_label
    FROM payments p
    JOIN orders o    ON p.order_id    = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.payment_type, c.customer_unique_id
)
SELECT
    payment_type,
    churn_label,
    COUNT(*)                                                        AS customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY payment_type), 2) AS pct_within_payment_type
FROM payment_churn
GROUP BY payment_type, churn_label
ORDER BY payment_type, churn_label;
