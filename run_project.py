"""
=============================================================
MASTER RUNNER — Runs the ENTIRE project end to end
SQL Server 2019 | Windows Authentication
=============================================================
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

import pyodbc
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIG
# ============================================================
SERVER   = r'ASUS\MSSQL'
DATABASE = 'ecommerce_churn'
DRIVER   = 'ODBC Driver 17 for SQL Server'
DATASET  = r'C:\Users\invin\OneDrive\Desktop\PRT2\Dataset'
OUTPUT   = r'C:\Users\invin\OneDrive\Desktop\PRT2\dashboard'

CONN_STR = (
    f'DRIVER={{{DRIVER}}};SERVER={SERVER};'
    f'DATABASE={DATABASE};Trusted_Connection=yes;'
)

def get_conn():
    return pyodbc.connect(CONN_STR)

def run_sql(cursor, sql, description=""):
    try:
        cursor.execute(sql)
        if description:
            print(f"  OK  {description}")
    except Exception as e:
        print(f"  ERR {description}: {e}")

def bulk_insert(conn, df, table, chunk=5000):
    df = df.where(pd.notnull(df), None)
    cols   = list(df.columns)
    ph     = ','.join(['?'] * len(cols))
    col_str= ','.join([f'[{c}]' for c in cols])
    sql    = f"INSERT INTO [{table}] ({col_str}) VALUES ({ph})"
    cursor = conn.cursor()
    cursor.fast_executemany = True
    total  = len(df)
    for i in range(0, total, chunk):
        rows = [tuple(r) for r in df.iloc[i:i+chunk].itertuples(index=False)]
        cursor.executemany(sql, rows)
        conn.commit()
        pct = min(i+chunk, total)
        print(f"    {table}: {pct:>7,}/{total:,} rows", end='\r')
    print(f"    {table}: {total:,}/{total:,} rows - DONE      ")
    cursor.close()

print("="*60)
print("  E-COMMERCE CHURN ANALYSIS — FULL PROJECT RUNNER")
print("="*60)

# ============================================================
# STEP 1: Create Database & Tables
# ============================================================
print("\n[STEP 1] Creating Database and Tables...")

# Connect to master first to create DB
conn0 = pyodbc.connect(
    f'DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE=master;Trusted_Connection=yes;'
)
conn0.autocommit = True
cur0 = conn0.cursor()

cur0.execute("""
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'ecommerce_churn')
BEGIN
    CREATE DATABASE ecommerce_churn
    PRINT 'Database created'
END
ELSE
    PRINT 'Database already exists'
""")
conn0.close()
print("  Database: ecommerce_churn - READY")

conn = get_conn()
conn.autocommit = True
cur  = conn.cursor()

# Drop & recreate tables
tables_sql = [
    ("DROP reviews",        "IF OBJECT_ID('reviews','U')     IS NOT NULL DROP TABLE reviews"),
    ("DROP order_items",    "IF OBJECT_ID('order_items','U') IS NOT NULL DROP TABLE order_items"),
    ("DROP payments",       "IF OBJECT_ID('payments','U')    IS NOT NULL DROP TABLE payments"),
    ("DROP orders",         "IF OBJECT_ID('orders','U')      IS NOT NULL DROP TABLE orders"),
    ("DROP customers",      "IF OBJECT_ID('customers','U')   IS NOT NULL DROP TABLE customers"),
    ("CREATE customers", """
        CREATE TABLE customers (
            customer_id         NVARCHAR(50) PRIMARY KEY,
            customer_unique_id  NVARCHAR(50) NOT NULL,
            customer_zip_code   NVARCHAR(10),
            customer_city       NVARCHAR(100),
            customer_state      NVARCHAR(5)
        )"""),
    ("CREATE orders", """
        CREATE TABLE orders (
            order_id                        NVARCHAR(50) PRIMARY KEY,
            customer_id                     NVARCHAR(50),
            order_status                    NVARCHAR(30),
            order_purchase_timestamp        DATETIME2,
            order_approved_at               DATETIME2,
            order_delivered_carrier_date    DATETIME2,
            order_delivered_customer_date   DATETIME2,
            order_estimated_delivery_date   DATETIME2,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )"""),
    ("CREATE order_items", """
        CREATE TABLE order_items (
            order_id            NVARCHAR(50),
            order_item_id       INT,
            product_id          NVARCHAR(50),
            seller_id           NVARCHAR(50),
            shipping_limit_date DATETIME2,
            price               DECIMAL(10,2),
            freight_value       DECIMAL(10,2),
            PRIMARY KEY (order_id, order_item_id)
        )"""),
    ("CREATE payments", """
        CREATE TABLE payments (
            order_id                NVARCHAR(50),
            payment_sequential      INT,
            payment_type            NVARCHAR(30),
            payment_installments    INT,
            payment_value           DECIMAL(10,2),
            PRIMARY KEY (order_id, payment_sequential)
        )"""),
    ("CREATE reviews", """
        CREATE TABLE reviews (
            review_id               NVARCHAR(50),
            order_id                NVARCHAR(50),
            review_score            INT,
            review_comment_title    NVARCHAR(500),
            review_comment_message  NVARCHAR(MAX),
            review_creation_date    DATETIME2,
            review_answer_timestamp DATETIME2,
            PRIMARY KEY (review_id, order_id)
        )"""),
]

for desc, sql in tables_sql:
    run_sql(cur, sql, desc)

conn.close()
print("  All tables created successfully!")

# ============================================================
# STEP 2: Import CSV Data
# ============================================================
print("\n[STEP 2] Importing CSV data into SQL Server...")

conn = get_conn()

# Customers
print("  Loading customers...")
df = pd.read_csv(f'{DATASET}/olist_customers_dataset.csv')
df.columns = ['customer_id','customer_unique_id','customer_zip_code','customer_city','customer_state']
df['customer_zip_code'] = df['customer_zip_code'].astype(str)
bulk_insert(conn, df, 'customers')

# Orders
print("  Loading orders...")
df = pd.read_csv(f'{DATASET}/olist_orders_dataset.csv')
df.columns = [
    'order_id','customer_id','order_status',
    'order_purchase_timestamp','order_approved_at',
    'order_delivered_carrier_date','order_delivered_customer_date',
    'order_estimated_delivery_date'
]
for c in df.columns[3:]:
    df[c] = pd.to_datetime(df[c], errors='coerce')
    df[c] = df[c].astype(object).where(df[c].notnull(), None)
bulk_insert(conn, df, 'orders')

# Order Items
print("  Loading order_items...")
df = pd.read_csv(f'{DATASET}/olist_order_items_dataset.csv')
df.columns = ['order_id','order_item_id','product_id','seller_id','shipping_limit_date','price','freight_value']
df['shipping_limit_date'] = pd.to_datetime(df['shipping_limit_date'], errors='coerce')
df['shipping_limit_date'] = df['shipping_limit_date'].astype(object).where(df['shipping_limit_date'].notnull(), None)
bulk_insert(conn, df, 'order_items')

# Payments
print("  Loading payments...")
df = pd.read_csv(f'{DATASET}/olist_order_payments_dataset.csv')
df.columns = ['order_id','payment_sequential','payment_type','payment_installments','payment_value']
bulk_insert(conn, df, 'payments')

# Reviews
print("  Loading reviews...")
df = pd.read_csv(f'{DATASET}/olist_order_reviews_dataset.csv', encoding='utf-8', on_bad_lines='skip')
df.columns = [
    'review_id','order_id','review_score',
    'review_comment_title','review_comment_message',
    'review_creation_date','review_answer_timestamp'
]
for c in ['review_creation_date','review_answer_timestamp']:
    df[c] = pd.to_datetime(df[c], errors='coerce')
    df[c] = df[c].astype(object).where(df[c].notnull(), None)
bulk_insert(conn, df, 'reviews')

# Verify
print("\n  IMPORT SUMMARY:")
cur = conn.cursor()
for t in ['customers','orders','order_items','payments','reviews']:
    cur.execute(f"SELECT COUNT(*) FROM [{t}]")
    n = cur.fetchone()[0]
    print(f"    {t:<15}: {n:>8,} rows")
conn.close()

# ============================================================
# STEP 3: SQL Analysis (fetch & display)
# ============================================================
print("\n[STEP 3] Running SQL Analysis Queries...")
conn = get_conn()

# Query 1: Churn Rate
print("\n  QUERY 1: Churn Rate")
q1 = """
WITH last_purchase AS (
    SELECT c.customer_unique_id,
           MAX(o.order_purchase_timestamp) AS last_order_date
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
churn_labels AS (
    SELECT customer_unique_id, last_order_date,
           DATEDIFF(day, last_order_date, '2018-10-01') AS days_since,
           CASE WHEN DATEDIFF(day, last_order_date, '2018-10-01') > 90
                THEN 'Churned' ELSE 'Active' END AS churn_status
    FROM last_purchase
)
SELECT churn_status,
       COUNT(*) AS customer_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM churn_labels
GROUP BY churn_status
"""
df_q1 = pd.read_sql(q1, conn)
print(df_q1.to_string(index=False))

# Query 2: Revenue by Segment
print("\n  QUERY 2: Revenue Segments (NTILE Window Function)")
q2 = """
WITH customer_revenue AS (
    SELECT c.customer_unique_id,
           COUNT(DISTINCT o.order_id)     AS total_orders,
           ROUND(SUM(p.payment_value),2)  AS total_revenue,
           ROUND(AVG(p.payment_value),2)  AS avg_order_value
    FROM customers c
    JOIN orders o   ON c.customer_id = o.customer_id
    JOIN payments p ON o.order_id    = p.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
ranked AS (
    SELECT *, NTILE(4) OVER (ORDER BY total_revenue DESC) AS revenue_quartile
    FROM customer_revenue
)
SELECT revenue_quartile,
       CASE revenue_quartile WHEN 1 THEN 'Top 25% (VIP)'
                             WHEN 2 THEN 'Mid-High 25%'
                             WHEN 3 THEN 'Mid-Low 25%'
                             WHEN 4 THEN 'Bottom 25%' END AS segment,
       COUNT(*) AS customers,
       ROUND(SUM(total_revenue),0) AS segment_revenue,
       ROUND(AVG(avg_order_value),2) AS avg_order_value
FROM ranked
GROUP BY revenue_quartile
ORDER BY revenue_quartile
"""
df_q2 = pd.read_sql(q2, conn)
print(df_q2.to_string(index=False))

# Query 3: A/B Test SQL
print("\n  QUERY 3: A/B Test (Late vs On-Time Delivery)")
q3 = """
WITH delivery_groups AS (
    SELECT c.customer_unique_id,
           AVG(DATEDIFF(day, o.order_estimated_delivery_date,
                        o.order_delivered_customer_date)) AS avg_delay_days
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_unique_id
),
ab_groups AS (
    SELECT customer_unique_id, avg_delay_days,
           CASE WHEN avg_delay_days > 0 THEN 'Control (Late)'
                ELSE 'Treatment (On-Time)' END AS ab_group
    FROM delivery_groups
),
purchase_counts AS (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS total_orders
    FROM customers c JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT ab.ab_group,
       COUNT(ab.customer_unique_id) AS total_users,
       SUM(CASE WHEN ISNULL(pc.total_orders,0) > 1 THEN 1 ELSE 0 END) AS repeat_buyers,
       ROUND(SUM(CASE WHEN ISNULL(pc.total_orders,0) > 1 THEN 1.0 ELSE 0 END) /
             COUNT(ab.customer_unique_id) * 100, 2) AS repeat_rate_pct
FROM ab_groups ab
LEFT JOIN purchase_counts pc ON ab.customer_unique_id = pc.customer_unique_id
GROUP BY ab.ab_group
"""
df_q3 = pd.read_sql(q3, conn)
print(df_q3.to_string(index=False))

# Query 4: Monthly Revenue with LAG
print("\n  QUERY 4: Monthly Revenue Trend (LAG Window Function)")
q4 = """
WITH monthly AS (
    SELECT FORMAT(o.order_purchase_timestamp,'yyyy-MM') AS month,
           ROUND(SUM(p.payment_value),2) AS revenue
    FROM orders o JOIN payments p ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY FORMAT(o.order_purchase_timestamp,'yyyy-MM')
)
SELECT month, revenue,
       ROUND(SUM(revenue) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING),2) AS cumulative_revenue,
       ROUND((revenue - LAG(revenue) OVER (ORDER BY month)) * 100.0 /
              NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 2) AS mom_growth_pct
FROM monthly
ORDER BY month
"""
df_q4 = pd.read_sql(q4, conn)
print(df_q4.to_string(index=False))

conn.close()
print("\n  SQL Analysis complete!")

# ============================================================
# STEP 4: Python EDA + Charts
# ============================================================
print("\n[STEP 4] Running EDA and generating charts...")
exec(open(r'C:\Users\invin\OneDrive\Desktop\PRT2\notebooks\01_EDA.py').read())

# ============================================================
# STEP 5: A/B Testing
# ============================================================
print("\n[STEP 5] Running A/B Statistical Test...")
exec(open(r'C:\Users\invin\OneDrive\Desktop\PRT2\notebooks\02_AB_Testing.py').read())

# ============================================================
# STEP 6: Churn Model
# ============================================================
print("\n[STEP 6] Training Churn Prediction Model...")
exec(open(r'C:\Users\invin\OneDrive\Desktop\PRT2\notebooks\03_Churn_Model.py').read())

# ============================================================
# STEP 7: Power BI Dashboard (HTML + pbix data)
# ============================================================
print("\n[STEP 7] Building Interactive Dashboard...")
exec(open(r'C:\Users\invin\OneDrive\Desktop\PRT2\notebooks\04_Dashboard.py').read())

print("\n" + "="*60)
print("  PROJECT COMPLETE!")
print("="*60)
print(f"  Dashboard: {OUTPUT}/churn_dashboard.html")
print(f"  Power BI:  {OUTPUT}/churn_predictions.csv")
print(f"             {OUTPUT}/master_dataset.csv")
print(f"             {OUTPUT}/monthly_revenue.csv")
print(f"             {OUTPUT}/ab_test_summary.csv")
