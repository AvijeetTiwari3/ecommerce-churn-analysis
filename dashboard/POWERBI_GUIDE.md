## Power BI Dashboard Setup Guide
## File: dashboard/POWERBI_GUIDE.md

---

# 📊 Power BI Dashboard Setup

## Step 1: Import Data into Power BI

1. Open **Power BI Desktop**
2. Click **Get Data → Text/CSV**
3. Import these two files from `dashboard/` folder:
   - `master_dataset.csv`
   - `churn_predictions.csv`
4. Also import `ab_test_summary.csv`

---

## Step 2: Connect to MySQL (Optional — for live data)

1. **Get Data → MySQL Database**
2. Server: `localhost`
3. Database: `ecommerce_churn`
4. Import: `customers`, `orders`, `payments`, `reviews`

---

## Step 3: Create These DAX Measures

Go to **Modeling → New Measure** and add these:

```dax
-- 1. Churn Rate
Churn Rate =
DIVIDE(
    CALCULATE(COUNTROWS(churn_predictions), churn_predictions[churn] = 1),
    COUNTROWS(churn_predictions)
) * 100

-- 2. Average Revenue Per User (ARPU)
ARPU =
DIVIDE(
    SUM(churn_predictions[total_revenue]),
    DISTINCTCOUNT(churn_predictions[customer_unique_id])
)

-- 3. Total At-Risk Revenue
Revenue At Risk =
CALCULATE(
    SUM(churn_predictions[total_revenue]),
    churn_predictions[risk_category] = "High Risk",
    churn_predictions[churn] = 0
)

-- 4. Active Customer Count
Active Customers =
CALCULATE(
    COUNTROWS(churn_predictions),
    churn_predictions[churn] = 0
)

-- 5. High Risk Customer Count
High Risk Customers =
CALCULATE(
    COUNTROWS(churn_predictions),
    churn_predictions[risk_category] = "High Risk"
)
```

---

## Step 4: Build the 5 Visuals

### Page 1: Executive Overview

| Visual | Type | Fields |
|---|---|---|
| Churn Rate | KPI Card | [Churn Rate] measure |
| Active Customers | KPI Card | [Active Customers] measure |
| Revenue at Risk | KPI Card | [Revenue At Risk] measure |
| ARPU | KPI Card | [ARPU] measure |
| Churn Distribution | Donut Chart | churn_status → Count |
| Revenue by Risk Segment | Clustered Bar | risk_category → total_revenue |

---

### Page 2: Customer Deep Dive

| Visual | Type | Fields |
|---|---|---|
| Churn by State | Filled Map | customer_state → Churn Rate |
| Review Score vs Churn | Clustered Bar | churn_status → avg_review_score |
| Delivery Delay vs Churn | Box Plot | churn_status → avg_delivery_delay |
| Risk Segment Breakdown | Stacked Bar | risk_category + churn_status |

---

### Page 3: A/B Test Results

| Visual | Type | Fields |
|---|---|---|
| A/B Test Summary Table | Table | All columns from ab_test_summary.csv |
| Repeat Purchase Rate | Clustered Column | ab_group → repeat_purchase_rate |

---

## Step 5: Color Theme

Use these colors consistently:

| Meaning | Color Code |
|---|---|
| Active / Positive | `#2ECC71` (Green) |
| Churned / Negative | `#E74C3C` (Red) |
| High Risk | `#E74C3C` (Red) |
| Medium Risk | `#F39C12` (Orange) |
| Low Risk | `#2ECC71` (Green) |
| Accent / Lines | `#3498DB` (Blue) |

---

## Step 6: Save & Export

1. Save as `dashboard/churn_dashboard.pbix`
2. Take screenshots of each page
3. Save screenshots in `dashboard/screenshots/`
4. Add screenshot to README.md
