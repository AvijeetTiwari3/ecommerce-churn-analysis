"""
=============================================================
01_EDA.py — Exploratory Data Analysis (SQL Server version)
=============================================================
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pyodbc
import warnings
warnings.filterwarnings('ignore')

SERVER   = r'ASUS\MSSQL'
DRIVER   = 'ODBC Driver 17 for SQL Server'
CONN_STR = f'DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE=ecommerce_churn;Trusted_Connection=yes;'
OUTPUT   = r'C:\Users\invin\OneDrive\Desktop\PRT2\dashboard\screenshots'
DASH_DIR = r'C:\Users\invin\OneDrive\Desktop\PRT2\dashboard'
REFERENCE_DATE = pd.Timestamp('2018-10-01')
CHURN_DAYS = 90

sns.set_style("whitegrid")
plt.rcParams.update({'font.size': 11, 'figure.dpi': 150})

# ============================================================
# Load data
# ============================================================
print("  Loading data from SQL Server...")
conn = pyodbc.connect(CONN_STR)
orders_df    = pd.read_sql("SELECT * FROM orders",    conn)
customers_df = pd.read_sql("SELECT * FROM customers", conn)
payments_df  = pd.read_sql("SELECT * FROM payments",  conn)
reviews_df   = pd.read_sql("SELECT * FROM reviews",   conn)
conn.close()

for c in ['order_purchase_timestamp','order_delivered_customer_date','order_estimated_delivery_date']:
    orders_df[c] = pd.to_datetime(orders_df[c], errors='coerce')

delivered = orders_df[orders_df['order_status'] == 'delivered'].copy()
delivered = delivered.merge(customers_df[['customer_id','customer_unique_id']], on='customer_id')

# ============================================================
# Churn Labels
# ============================================================
last_purchase = (
    delivered.groupby('customer_unique_id')['order_purchase_timestamp']
    .max().reset_index().rename(columns={'order_purchase_timestamp':'last_order_date'})
)
last_purchase['days_since_last_order'] = (REFERENCE_DATE - last_purchase['last_order_date']).dt.days
last_purchase['churn_label']  = (last_purchase['days_since_last_order'] > CHURN_DAYS).astype(int)
last_purchase['churn_status'] = last_purchase['churn_label'].map({0:'Active', 1:'Churned'})

total_churned = int(last_purchase['churn_label'].sum())
total_active  = int((last_purchase['churn_label'] == 0).sum())
churn_rate    = last_purchase['churn_label'].mean() * 100

print(f"  Churn Rate: {churn_rate:.1f}%  |  Churned: {total_churned:,}  |  Active: {total_active:,}")

# ============================================================
# CHART 1: Churn Distribution + Monthly Trend
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle('E-commerce Customer Churn Overview', fontsize=16, fontweight='bold')

wedges, texts, autotexts = axes[0].pie(
    [total_active, total_churned], labels=['Active','Churned'],
    colors=['#2ECC71','#E74C3C'], autopct='%1.1f%%', startangle=90,
    pctdistance=0.75, wedgeprops=dict(width=0.5)
)
for at in autotexts: at.set_fontweight('bold')
axes[0].set_title(f'Customer Churn Distribution\n(Total: {len(last_purchase):,} customers)', fontweight='bold')

delivered['month'] = delivered['order_purchase_timestamp'].dt.to_period('M')
monthly = delivered.groupby('month').size().reset_index(name='order_count')
monthly['month_str'] = monthly['month'].astype(str)
axes[1].plot(monthly['month_str'], monthly['order_count'], marker='o', color='#3498DB', linewidth=2, markersize=4)
axes[1].fill_between(monthly['month_str'], monthly['order_count'], alpha=0.15, color='#3498DB')
axes[1].set_title('Monthly Order Trend', fontweight='bold')
axes[1].set_xlabel('Month'); axes[1].set_ylabel('Number of Orders')
axes[1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig(f'{OUTPUT}/01_churn_overview.png', bbox_inches='tight')
plt.close()
print("  Saved: 01_churn_overview.png")

# ============================================================
# Revenue Segmentation
# ============================================================
customer_revenue = (
    delivered.merge(payments_df, on='order_id')
    .groupby('customer_unique_id')
    .agg(total_orders=('order_id','count'), total_revenue=('payment_value','sum'),
         avg_order_val=('payment_value','mean')).reset_index()
)
customer_revenue['revenue_quartile'] = pd.qcut(
    customer_revenue['total_revenue'], q=4,
    labels=['Bottom 25%','Mid-Low 25%','Mid-High 25%','Top 25% (VIP)']
)

# CHART 2: Revenue by Segment
seg_revenue = customer_revenue.groupby('revenue_quartile')['total_revenue'].sum().reset_index()
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(seg_revenue['revenue_quartile'].astype(str), seg_revenue['total_revenue'],
              color=['#E74C3C','#E67E22','#3498DB','#2ECC71'], edgecolor='white', linewidth=1.2)
ax.bar_label(bars, fmt='R$%.0f', padding=5)
ax.set_title('Total Revenue by Customer Segment', fontsize=14, fontweight='bold')
ax.set_xlabel('Customer Segment'); ax.set_ylabel('Total Revenue (BRL)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'R${x:,.0f}'))
plt.tight_layout()
plt.savefig(f'{OUTPUT}/02_revenue_segments.png', bbox_inches='tight')
plt.close()
print("  Saved: 02_revenue_segments.png")

# ============================================================
# Review Score vs Churn
# ============================================================
reviews_merged = (
    reviews_df.groupby('order_id')['review_score'].mean().reset_index()
    .merge(orders_df[['order_id','customer_id']], on='order_id')
    .merge(customers_df[['customer_id','customer_unique_id']], on='customer_id')
    .groupby('customer_unique_id')['review_score'].mean().reset_index()
    .merge(last_purchase[['customer_unique_id','churn_status']], on='customer_unique_id')
)

# CHART 3: Review Score vs Churn
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.boxplot(data=reviews_merged, x='churn_status', y='review_score',
            palette={'Active':'#2ECC71','Churned':'#E74C3C'}, ax=axes[0])
axes[0].set_title('Review Score vs Churn Status', fontweight='bold')
axes[0].set_xlabel('Churn Status'); axes[0].set_ylabel('Avg Review Score')

avg_scores = reviews_merged.groupby('churn_status')['review_score'].mean().reset_index()
bars2 = axes[1].bar(avg_scores['churn_status'], avg_scores['review_score'],
                    color=['#2ECC71','#E74C3C'], edgecolor='white')
axes[1].bar_label(bars2, fmt='%.2f', padding=3)
axes[1].set_title('Avg Review Score by Churn Status', fontweight='bold')
axes[1].set_ylim(0, 5.5); axes[1].set_ylabel('Avg Review Score (out of 5)')
plt.tight_layout()
plt.savefig(f'{OUTPUT}/03_review_vs_churn.png', bbox_inches='tight')
plt.close()
print("  Saved: 03_review_vs_churn.png")

# ============================================================
# Delivery Delay vs Churn
# ============================================================
delivered['delivery_delay_days'] = (
    delivered['order_delivered_customer_date'] - delivered['order_estimated_delivery_date']
).dt.days
delay_churn = (
    delivered.groupby('customer_unique_id')['delivery_delay_days'].mean().reset_index()
    .merge(last_purchase[['customer_unique_id','churn_status']], on='customer_unique_id').dropna()
)

# CHART 4: Delivery Delay Distribution
fig, ax = plt.subplots(figsize=(10, 5))
for status, color in [('Active','#2ECC71'),('Churned','#E74C3C')]:
    data = delay_churn[delay_churn['churn_status']==status]['delivery_delay_days']
    ax.hist(data.clip(-10,20), bins=30, alpha=0.6, color=color, label=status, density=True)
ax.axvline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.7, label='On-Time Line')
ax.set_title('Delivery Delay Distribution vs Churn Status', fontweight='bold', fontsize=13)
ax.set_xlabel('Avg Delivery Delay (days) — Positive = Late')
ax.set_ylabel('Density'); ax.legend()
plt.tight_layout()
plt.savefig(f'{OUTPUT}/04_delay_vs_churn.png', bbox_inches='tight')
plt.close()
print("  Saved: 04_delay_vs_churn.png")

# ============================================================
# Save Master Dataset for Power BI
# ============================================================
master = (
    last_purchase
    .merge(customer_revenue, on='customer_unique_id', how='left')
    .merge(reviews_merged.rename(columns={'review_score':'avg_review_score'}),
           on=['customer_unique_id','churn_status'], how='left')
    .merge(delay_churn.rename(columns={'delivery_delay_days':'avg_delay_days'}),
           on=['customer_unique_id','churn_status'], how='left')
    .merge(customers_df[['customer_unique_id','customer_state']].drop_duplicates(),
           on='customer_unique_id', how='left')
)
master.to_csv(f'{DASH_DIR}/master_dataset.csv', index=False)
print(f"  Master dataset saved: {master.shape[0]:,} rows")

# Store globally for next scripts
import builtins
builtins._eda_last_purchase = last_purchase
builtins._eda_customer_revenue = customer_revenue
builtins._eda_delivered = delivered
builtins._eda_customers_df = customers_df
builtins._eda_payments_df  = payments_df
builtins._eda_reviews_df   = reviews_df

print("  EDA Complete!")
