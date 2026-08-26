"""
=============================================================
02_AB_Testing.py — Statistical A/B Test (SQL Server version)
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
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.power import NormalIndPower
import warnings
warnings.filterwarnings('ignore')

SERVER   = r'ASUS\MSSQL'
DRIVER   = 'ODBC Driver 17 for SQL Server'
CONN_STR = f'DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE=ecommerce_churn;Trusted_Connection=yes;'
OUTPUT   = r'C:\Users\invin\OneDrive\Desktop\PRT2\dashboard\screenshots'
DASH_DIR = r'C:\Users\invin\OneDrive\Desktop\PRT2\dashboard'

sns.set_style("whitegrid")
plt.rcParams.update({'font.size': 11, 'figure.dpi': 150})

# ============================================================
# Load A/B Data from SQL Server
# ============================================================
print("  Loading A/B test data...")
conn = pyodbc.connect(CONN_STR)
query = """
SELECT
    c.customer_unique_id,
    COUNT(DISTINCT o.order_id)                              AS total_orders,
    SUM(p.payment_value)                                    AS total_revenue,
    AVG(p.payment_value)                                    AS avg_order_value,
    AVG(DATEDIFF(day,
        o.order_estimated_delivery_date,
        o.order_delivered_customer_date))                   AS avg_delay_days
FROM customers c
JOIN orders o   ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id    = p.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_unique_id
"""
df = pd.read_sql(query, conn)
conn.close()

df = df.dropna(subset=['avg_delay_days'])
df['ab_group'] = df['avg_delay_days'].apply(
    lambda x: 'Control (Late Delivery)' if x > 0 else 'Treatment (On-Time Delivery)'
)
df['is_repeat_buyer'] = (df['total_orders'] > 1).astype(int)

control   = df[df['ab_group'] == 'Control (Late Delivery)']
treatment = df[df['ab_group'] == 'Treatment (On-Time Delivery)']

control_rate   = control['is_repeat_buyer'].mean()
treatment_rate = treatment['is_repeat_buyer'].mean()
lift           = (treatment_rate - control_rate) / max(control_rate, 0.0001) * 100

# ============================================================
# Statistical Test
# ============================================================
count = np.array([treatment['is_repeat_buyer'].sum(), control['is_repeat_buyer'].sum()])
nobs  = np.array([len(treatment), len(control)])
z_stat, p_value = proportions_ztest(count, nobs)
significant = p_value < 0.05

# Power Analysis
denom = (control_rate*(1-control_rate) + treatment_rate*(1-treatment_rate)) / 2
effect_size = abs(treatment_rate - control_rate) / max(np.sqrt(denom), 0.0001)
required_n = NormalIndPower().solve_power(effect_size=effect_size, alpha=0.05, power=0.80, alternative='two-sided')

# Business Impact
avg_ltv        = df['total_revenue'].mean()
extra_repeats  = int((treatment_rate - control_rate) * len(treatment))
revenue_impact = extra_repeats * avg_ltv

print(f"  Control   Repeat Rate: {control_rate:.2%}  (n={len(control):,})")
print(f"  Treatment Repeat Rate: {treatment_rate:.2%}  (n={len(treatment):,})")
print(f"  Lift: {lift:+.2f}%  |  Z={z_stat:.3f}  |  p={p_value:.4f}  |  Significant: {'YES' if significant else 'NO'}")
print(f"  Extra Repeat Buyers: {extra_repeats:,}  |  Revenue Uplift: R${revenue_impact:,.0f}")

# ============================================================
# CHART 5: A/B Test Results
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(15, 6))
fig.suptitle('A/B Test: On-Time Delivery Impact on Repeat Purchase Rate', fontweight='bold', fontsize=13)

groups = ['Control\n(Late Delivery)', 'Treatment\n(On-Time Delivery)']
rates  = [control_rate*100, treatment_rate*100]
bars   = axes[0].bar(groups, rates, color=['#E74C3C','#2ECC71'], edgecolor='white', width=0.5)
axes[0].bar_label(bars, fmt='%.2f%%', padding=4, fontweight='bold')
axes[0].set_ylabel('Repeat Purchase Rate (%)')
axes[0].set_title(f'Repeat Purchase Rate by Group (Lift: {lift:+.2f}%)')
axes[0].set_ylim(0, max(rates)*1.3)
sig_text = f"p = {p_value:.4f}\n{'Statistically Significant' if significant else 'Not Significant'}"
axes[0].text(0.5, max(rates)*1.15, sig_text, ha='center', fontsize=9,
             bbox=dict(boxstyle='round,pad=0.4', fc='lightyellow', ec='orange', alpha=0.9),
             transform=axes[0].get_xaxis_transform())

axes[1].hist(control['total_orders'].clip(upper=8), bins=range(1,10), alpha=0.6, color='#E74C3C', label='Control (Late)', density=True)
axes[1].hist(treatment['total_orders'].clip(upper=8), bins=range(1,10), alpha=0.6, color='#2ECC71', label='Treatment (On-Time)', density=True)
axes[1].set_xlabel('Number of Orders per Customer'); axes[1].set_ylabel('Density')
axes[1].set_title('Order Count Distribution by Group'); axes[1].legend()

plt.tight_layout()
plt.savefig(f'{OUTPUT}/05_ab_test_results.png', bbox_inches='tight')
plt.close()
print("  Saved: 05_ab_test_results.png")

# ============================================================
# Save A/B summary CSV
# ============================================================
ab_summary = pd.DataFrame({
    'Metric': ['Control Group Size','Treatment Group Size','Control Repeat Rate',
               'Treatment Repeat Rate','Lift (%)','Z-Statistic','P-Value',
               'Statistically Significant','Extra Repeat Buyers','Revenue Uplift (BRL)'],
    'Value': [f"{len(control):,}", f"{len(treatment):,}",
              f"{control_rate:.2%}", f"{treatment_rate:.2%}",
              f"{lift:+.2f}%", f"{z_stat:.4f}", f"{p_value:.6f}",
              'YES' if significant else 'NO',
              f"{extra_repeats:,}", f"R${revenue_impact:,.0f}"]
})
ab_summary.to_csv(f'{DASH_DIR}/ab_test_summary.csv', index=False)

# Store globally
import builtins
builtins._ab_df            = df
builtins._ab_control_rate  = control_rate
builtins._ab_treatment_rate= treatment_rate
builtins._ab_lift          = lift
builtins._ab_pvalue        = p_value

print("  A/B Testing Complete!")
