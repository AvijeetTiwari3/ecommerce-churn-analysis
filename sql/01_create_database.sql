-- ============================================================
-- FILE: 01_create_database.sql
-- PURPOSE: Create database and all tables for Churn Analysis
-- Run this FIRST in MySQL Workbench
-- ============================================================

CREATE DATABASE IF NOT EXISTS ecommerce_churn;
USE ecommerce_churn;

-- ============================================================
-- TABLE 1: customers
-- ============================================================
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id         VARCHAR(50) PRIMARY KEY,
    customer_unique_id  VARCHAR(50) NOT NULL,
    customer_zip_code   VARCHAR(10),
    customer_city       VARCHAR(100),
    customer_state      VARCHAR(5)
);

-- ============================================================
-- TABLE 2: orders
-- ============================================================
CREATE TABLE orders (
    order_id                        VARCHAR(50) PRIMARY KEY,
    customer_id                     VARCHAR(50),
    order_status                    VARCHAR(30),
    order_purchase_timestamp        DATETIME,
    order_approved_at               DATETIME,
    order_delivered_carrier_date    DATETIME,
    order_delivered_customer_date   DATETIME,
    order_estimated_delivery_date   DATETIME,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- ============================================================
-- TABLE 3: order_items
-- ============================================================
CREATE TABLE order_items (
    order_id            VARCHAR(50),
    order_item_id       INT,
    product_id          VARCHAR(50),
    seller_id           VARCHAR(50),
    shipping_limit_date DATETIME,
    price               DECIMAL(10,2),
    freight_value       DECIMAL(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

-- ============================================================
-- TABLE 4: payments
-- ============================================================
CREATE TABLE payments (
    order_id                VARCHAR(50),
    payment_sequential      INT,
    payment_type            VARCHAR(30),
    payment_installments    INT,
    payment_value           DECIMAL(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);

-- ============================================================
-- TABLE 5: reviews
-- ============================================================
CREATE TABLE reviews (
    review_id               VARCHAR(50),
    order_id                VARCHAR(50),
    review_score            INT,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    DATETIME,
    review_answer_timestamp DATETIME,
    PRIMARY KEY (review_id, order_id)
);

SELECT 'All tables created successfully!' AS status;
