-- ============================================================
-- FILE: 02_import_data.sql
-- PURPOSE: Import CSV data into MySQL tables
-- NOTE: Run AFTER 01_create_database.sql
-- NOTE: Update the file paths below to match YOUR system path
-- ============================================================

USE ecommerce_churn;

-- Allow local file loading
SET GLOBAL local_infile = 1;

-- ============================================================
-- IMPORT customers
-- ============================================================
LOAD DATA LOCAL INFILE 'C:/Users/invin/OneDrive/Desktop/PRT2/Dataset/olist_customers_dataset.csv'
INTO TABLE customers
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(customer_id, customer_unique_id, customer_zip_code, customer_city, customer_state);

SELECT CONCAT('Customers imported: ', COUNT(*)) AS status FROM customers;

-- ============================================================
-- IMPORT orders
-- ============================================================
LOAD DATA LOCAL INFILE 'C:/Users/invin/OneDrive/Desktop/PRT2/Dataset/olist_orders_dataset.csv'
INTO TABLE orders
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(order_id, customer_id, order_status,
 @purchase, @approved, @carrier, @delivered, @estimated)
SET
  order_purchase_timestamp      = NULLIF(@purchase, ''),
  order_approved_at             = NULLIF(@approved, ''),
  order_delivered_carrier_date  = NULLIF(@carrier, ''),
  order_delivered_customer_date = NULLIF(@delivered, ''),
  order_estimated_delivery_date = NULLIF(@estimated, '');

SELECT CONCAT('Orders imported: ', COUNT(*)) AS status FROM orders;

-- ============================================================
-- IMPORT order_items
-- ============================================================
LOAD DATA LOCAL INFILE 'C:/Users/invin/OneDrive/Desktop/PRT2/Dataset/olist_order_items_dataset.csv'
INTO TABLE order_items
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(order_id, order_item_id, product_id, seller_id,
 @ship_limit, price, freight_value)
SET shipping_limit_date = NULLIF(@ship_limit, '');

SELECT CONCAT('Order Items imported: ', COUNT(*)) AS status FROM order_items;

-- ============================================================
-- IMPORT payments
-- ============================================================
LOAD DATA LOCAL INFILE 'C:/Users/invin/OneDrive/Desktop/PRT2/Dataset/olist_order_payments_dataset.csv'
INTO TABLE payments
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(order_id, payment_sequential, payment_type, payment_installments, payment_value);

SELECT CONCAT('Payments imported: ', COUNT(*)) AS status FROM payments;

-- ============================================================
-- IMPORT reviews
-- ============================================================
LOAD DATA LOCAL INFILE 'C:/Users/invin/OneDrive/Desktop/PRT2/Dataset/olist_order_reviews_dataset.csv'
INTO TABLE reviews
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(review_id, order_id, review_score,
 @title, @message, @created, @answered)
SET
  review_comment_title    = NULLIF(@title, ''),
  review_comment_message  = NULLIF(@message, ''),
  review_creation_date    = NULLIF(@created, ''),
  review_answer_timestamp = NULLIF(@answered, '');

SELECT CONCAT('Reviews imported: ', COUNT(*)) AS status FROM reviews;

-- ============================================================
-- VERIFY all imports
-- ============================================================
SELECT 'customers'   AS table_name, COUNT(*) AS total_rows FROM customers  UNION ALL
SELECT 'orders'      AS table_name, COUNT(*) AS total_rows FROM orders      UNION ALL
SELECT 'order_items' AS table_name, COUNT(*) AS total_rows FROM order_items UNION ALL
SELECT 'payments'    AS table_name, COUNT(*) AS total_rows FROM payments    UNION ALL
SELECT 'reviews'     AS table_name, COUNT(*) AS total_rows FROM reviews;
