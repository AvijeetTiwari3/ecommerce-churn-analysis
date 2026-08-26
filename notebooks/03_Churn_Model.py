"""
=============================================================
03_Churn_Model.py — ML Churn Prediction (SQL Server version)
=============================================================
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pyodbc
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, RocCurveDisplay

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
# Feature Engineering from SQL Server
# ============================================================
print("  Loading feature data from SQL Server...")
conn = pyodbc.connect(CONN_STR)
feature_query = """
SELECT
    c.customer_unique_id,
    c.customer_state,
    COUNT(DISTINCT o.order_id)                                                   AS total_orders,
    ROUND(SUM(p.payment_value), 2)                                               AS total_revenue,
    ROUND(AVG(p.payment_value), 2)                                               AS avg_order_value,
    ROUND(AVG(CAST(r.review_score AS FLOAT)), 2)                                 AS avg_review_score,
    DATEDIFF(day, MIN(o.order_purchase_timestamp), MAX(o.order_purchase_timestamp)) AS customer_lifespan_days,
    ROUND(AVG(CAST(DATEDIFF(day, o.order_estimated_delivery_date,
                   o.order_delivered_customer_date) AS FLOAT)), 2)               AS avg_delivery_delay,
    COUNT(DISTINCT p.payment_type)                                               AS unique_payment_methods,
    SUM(CASE WHEN p.payment_type = 'credit_card' THEN 1 ELSE 0 END)             AS credit_card_orders,
    ROUND(AVG(CAST(p.payment_installments AS FLOAT)), 2)                         AS avg_installments,
    MAX(o.order_purchase_timestamp)                                              AS last_order_date
FROM customers c
JOIN orders o   ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id    = p.order_id
LEFT JOIN reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_unique_id, c.customer_state
"""
df = pd.read_sql(feature_query, conn)
conn.close()
print(f"  Features loaded for {len(df):,} customers")

# ============================================================
# Target Variable
# ============================================================
df['last_order_date']       = pd.to_datetime(df['last_order_date'])
df['days_since_last_order'] = (REFERENCE_DATE - df['last_order_date']).dt.days
df['churn']                 = (df['days_since_last_order'] > CHURN_DAYS).astype(int)
print(f"  Churn Rate: {df['churn'].mean():.2%}  |  Churned: {df['churn'].sum():,}  |  Active: {(df['churn']==0).sum():,}")

# ============================================================
# Model Training
# ============================================================
feature_cols = [
    'total_orders','total_revenue','avg_order_value','avg_review_score',
    'customer_lifespan_days','avg_delivery_delay','unique_payment_methods',
    'credit_card_orders','avg_installments'
    # NOTE: days_since_last_order excluded — it directly encodes churn label (data leakage)
]
X = df[feature_cols].fillna(0)
y = df['churn']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

print("  Training Gradient Boosting Classifier...")
model = GradientBoostingClassifier(n_estimators=200, learning_rate=0.1, max_depth=4,
                                    min_samples_split=50, random_state=42)
model.fit(X_train, y_train)

y_pred  = model.predict(X_test)
y_prob  = model.predict_proba(X_test)[:, 1]
auc     = roc_auc_score(y_test, y_prob)
cv_auc  = cross_val_score(model, X, y, cv=StratifiedKFold(5), scoring='roc_auc')

print(f"\n  Classification Report:")
print(classification_report(y_test, y_pred))
print(f"  AUC-ROC      : {auc:.4f}")
print(f"  CV AUC (5-fold): {cv_auc.mean():.4f} +/- {cv_auc.std():.4f}")

# ============================================================
# CHART 7: Feature Importance + ROC Curve
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle('Churn Prediction Model — Gradient Boosting', fontweight='bold', fontsize=14)

imp_df = pd.DataFrame({'Feature': feature_cols, 'Importance': model.feature_importances_}).sort_values('Importance')
clrs   = ['#E74C3C' if x > imp_df['Importance'].median() else '#3498DB' for x in imp_df['Importance']]
axes[0].barh(imp_df['Feature'], imp_df['Importance'], color=clrs, edgecolor='white')
axes[0].set_title('Feature Importance', fontweight='bold')
axes[0].set_xlabel('Importance Score')

RocCurveDisplay.from_predictions(y_test, y_prob, name=f'GBM (AUC={auc:.3f})', ax=axes[1], color='#E74C3C')
axes[1].plot([0,1],[0,1],'k--',alpha=0.5,label='Random (AUC=0.500)')
axes[1].set_title('ROC Curve', fontweight='bold'); axes[1].legend()

plt.tight_layout()
plt.savefig(f'{OUTPUT}/07_model_performance.png', bbox_inches='tight')
plt.close()
print("  Saved: 07_model_performance.png")

# ============================================================
# CHART 8: Confusion Matrix
# ============================================================
cm = confusion_matrix(y_test, y_pred)
fig, ax = plt.subplots(figsize=(7, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='RdYlGn',
            xticklabels=['Pred Active','Pred Churned'],
            yticklabels=['Act Active','Act Churned'], ax=ax)
ax.set_title('Confusion Matrix', fontweight='bold', fontsize=13)
plt.tight_layout()
plt.savefig(f'{OUTPUT}/08_confusion_matrix.png', bbox_inches='tight')
plt.close()
print("  Saved: 08_confusion_matrix.png")

# ============================================================
# Risk Segmentation + Business Impact
# ============================================================
df['churn_probability'] = model.predict_proba(X)[:, 1]
df['risk_category'] = pd.cut(df['churn_probability'], bins=[0,0.30,0.60,1.0],
                               labels=['Low Risk','Medium Risk','High Risk'])

at_risk_active  = df[(df['churn']==0) & (df['risk_category']=='High Risk')]
avg_revenue     = df['total_revenue'].mean()
revenue_at_risk = len(at_risk_active) * avg_revenue

print(f"\n  HIGH RISK ACTIVE USERS    : {len(at_risk_active):,}")
print(f"  REVENUE AT RISK           : R${revenue_at_risk:,.0f}")
print(f"  AVG CUSTOMER LTV          : R${avg_revenue:,.2f}")

# CHART 9: Risk Segments
risk_counts = df['risk_category'].value_counts().reset_index()
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(risk_counts['risk_category'].astype(str), risk_counts['count'],
              color=['#2ECC71','#F39C12','#E74C3C'], edgecolor='white')
ax.bar_label(bars, fmt='%d', padding=4, fontweight='bold')
ax.set_title('Customer Risk Segmentation (Churn Model)', fontweight='bold', fontsize=13)
ax.set_xlabel('Risk Category'); ax.set_ylabel('Number of Customers')
plt.tight_layout()
plt.savefig(f'{OUTPUT}/09_risk_segments.png', bbox_inches='tight')
plt.close()
print("  Saved: 09_risk_segments.png")

# ============================================================
# Save predictions CSV (for Power BI)
# ============================================================
output_df = df[[
    'customer_unique_id','customer_state','total_orders','total_revenue',
    'avg_review_score','avg_delivery_delay','days_since_last_order',
    'churn','churn_probability','risk_category'
]]
output_df.to_csv(f'{DASH_DIR}/churn_predictions.csv', index=False)
print(f"  Predictions saved: {len(output_df):,} rows")

# Store globally
import builtins
builtins._model_df          = df
builtins._model_auc         = auc
builtins._model_at_risk_n   = len(at_risk_active)
builtins._model_revenue_risk= revenue_at_risk
builtins._model_avg_revenue = avg_revenue

print("  Churn Model Complete!")
