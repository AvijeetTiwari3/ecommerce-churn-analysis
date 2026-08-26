"""
=============================================================
SCRIPT: 00_import_to_mysql.py
PURPOSE: Import all CSVs into MySQL using Python (pandas)
         Run this AFTER 01_create_database.sql
=============================================================
"""

import pandas as pd
import mysql.connector
from mysql.connector import Error
import os

# ============================================================
# CONFIG — update password if different
# ============================================================
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': 'your_mysql_password',   # <-- CHANGE THIS
    'database': 'ecommerce_churn'
}

DATASET_PATH = r'C:\Users\invin\OneDrive\Desktop\PRT2\Dataset'

# ============================================================
# Helper function to bulk insert DataFrame into MySQL
# ============================================================
def insert_dataframe(conn, cursor, df, table_name, chunk_size=5000):
    df = df.where(pd.notnull(df), None)  # Replace NaN with None
    cols = ', '.join(df.columns.tolist())
    placeholders = ', '.join(['%s'] * len(df.columns))
    query = f"INSERT IGNORE INTO {table_name} ({cols}) VALUES ({placeholders})"
    
    total = len(df)
    for i in range(0, total, chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        rows = [tuple(row) for row in chunk.itertuples(index=False)]
        cursor.executemany(query, rows)
        conn.commit()
        print(f"  {table_name}: {min(i+chunk_size, total):,}/{total:,} rows inserted")

# ============================================================
# MAIN
# ============================================================
def main():
    print("Connecting to MySQL...")
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("Connected!\n")

    # ---- 1. Customers ----
    print("Importing customers...")
    df = pd.read_csv(os.path.join(DATASET_PATH, 'olist_customers_dataset.csv'))
    df.columns = ['customer_id', 'customer_unique_id', 'customer_zip_code', 'customer_city', 'customer_state']
    insert_dataframe(conn, cursor, df, 'customers')
    print(f"  DONE — {len(df):,} rows\n")

    # ---- 2. Orders ----
    print("Importing orders...")
    df = pd.read_csv(os.path.join(DATASET_PATH, 'olist_orders_dataset.csv'))
    df.columns = [
        'order_id', 'customer_id', 'order_status',
        'order_purchase_timestamp', 'order_approved_at',
        'order_delivered_carrier_date', 'order_delivered_customer_date',
        'order_estimated_delivery_date'
    ]
    datetime_cols = [
        'order_purchase_timestamp', 'order_approved_at',
        'order_delivered_carrier_date', 'order_delivered_customer_date',
        'order_estimated_delivery_date'
    ]
    for col in datetime_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    insert_dataframe(conn, cursor, df, 'orders')
    print(f"  DONE — {len(df):,} rows\n")

    # ---- 3. Order Items ----
    print("Importing order_items...")
    df = pd.read_csv(os.path.join(DATASET_PATH, 'olist_order_items_dataset.csv'))
    df.columns = ['order_id', 'order_item_id', 'product_id', 'seller_id', 'shipping_limit_date', 'price', 'freight_value']
    df['shipping_limit_date'] = pd.to_datetime(df['shipping_limit_date'], errors='coerce')
    insert_dataframe(conn, cursor, df, 'order_items')
    print(f"  DONE — {len(df):,} rows\n")

    # ---- 4. Payments ----
    print("Importing payments...")
    df = pd.read_csv(os.path.join(DATASET_PATH, 'olist_order_payments_dataset.csv'))
    df.columns = ['order_id', 'payment_sequential', 'payment_type', 'payment_installments', 'payment_value']
    insert_dataframe(conn, cursor, df, 'payments')
    print(f"  DONE — {len(df):,} rows\n")

    # ---- 5. Reviews ----
    print("Importing reviews...")
    df = pd.read_csv(os.path.join(DATASET_PATH, 'olist_order_reviews_dataset.csv'))
    df.columns = [
        'review_id', 'order_id', 'review_score',
        'review_comment_title', 'review_comment_message',
        'review_creation_date', 'review_answer_timestamp'
    ]
    df['review_creation_date']    = pd.to_datetime(df['review_creation_date'], errors='coerce')
    df['review_answer_timestamp'] = pd.to_datetime(df['review_answer_timestamp'], errors='coerce')
    insert_dataframe(conn, cursor, df, 'reviews')
    print(f"  DONE — {len(df):,} rows\n")

    # ---- Verify ----
    print("=" * 50)
    print("IMPORT SUMMARY:")
    for table in ['customers', 'orders', 'order_items', 'payments', 'reviews']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:<15}: {count:>8,} rows")

    cursor.close()
    conn.close()
    print("\nAll data imported successfully!")

if __name__ == '__main__':
    main()
