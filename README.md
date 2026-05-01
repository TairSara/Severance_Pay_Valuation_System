<div dir="ltr">

# IAS 19 Severance Pay Valuation System

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red?logo=streamlit)](https://streamlit.io/)
[![Standard](https://img.shields.io/badge/Standard-IAS%2019-gold)](https://www.ifrs.org/)
[![Status](https://img.shields.io/badge/Status-Final%20Submission-brightgreen)]()

---

## Project Description

A full actuarial system for calculating a company's **severance pay liability** under the international accounting standard **IAS 19 – Employee Benefits**.

The system computes the **Present Value of the Defined Benefit Obligation (DBO)** for each employee individually, using the **Projected Unit Credit (PUC)** method with demographic, employment, and financial data.

---

## What the System Does

- Reads employee data from a single Excel source file
- Calculates the DBO for each active employee as of **31/12/2023**
- Employees who terminated employment receive a liability of **0**
- Produces a summary results file and an **interactive dashboard**

---

## Actuarial Methodology

### Valuation Formula

$$DBO = \sum_{t=1}^{T} \; p_t \;\cdot\; B_t \;\cdot\; v_t$$

| Symbol | Meaning |
|--------|---------|
| $t$ | Future projection year |
| $p_t$ | Cumulative survival probability to year $t$ |
| $B_t$ | Expected benefit payment upon exit in year $t$ |
| $v_t$ | Discount factor for year $t$ |

### Exit Probabilities

$$p_t = \prod_{s=1}^{t-1}(1 - q_s^{dismissal} - q_s^{resignation} - q_s^{mortality})$$

- **Dismissal** — age-band rates from the assumptions sheet
- **Resignation** — age-band rates from the assumptions sheet
- **Mortality** — official mortality tables (male / female)

### Benefits by Exit Type

| Event | Benefit (tenure < 5 yrs) | Benefit (tenure >= 5 yrs) |
|-------|--------------------------|---------------------------|
| Dismissal | Salary x tenure x Section 14 factor | max(legal severance, plan assets) |
| Resignation | Plan assets | Plan assets |
| Death | Salary x tenure x Section 14 factor | max(legal severance, plan assets) |
| Retirement | Salary x tenure x Section 14 factor | max(legal severance, plan assets) |

### Discount Curve
The discount rate is taken from an annual yield curve in the assumptions sheet — a different rate is applied for each projection year.

### Section 14 Treatment
A Section 14 factor is calculated per employee based on:
- Coverage percentage
- Section 14 start date relative to employment start date
- Existence of plan assets

---

## Project Structure

```
Severance_Pay_Valuation_System/
│
├── input/
│   ├── data10.xlsx          # Employee data + assumptions sheet
│   └── mortality_table.xlsx # Mortality tables (male / female)
│
├── output/
│   └── results_ias19.xlsx   # Calculation results
│
├── src/
│   ├── ias19_project.py     # Actuarial calculation engine
│   └── ias19_dashboard.py   # Streamlit dashboard
│
└── README.md
```

---

## Running the System

### Requirements

```bash
pip install pandas openpyxl streamlit plotly
```

### Step 1 – Run the Calculation

```bash
python src/ias19_project.py
```

Output is saved to `output/results_ias19.xlsx`

### Step 2 – Open the Dashboard

```bash
streamlit run src/ias19_dashboard.py
```

---

## Dashboard

The dashboard displays:

- **KPI Cards** — total liability, plan assets, net liability, average per employee
- **Bar Chart** — liability by employee (split by gender)
- **Pie Chart** — gender breakdown
- **Histograms** — age and tenure distributions
- **Scatter Plot** — salary vs. liability
- **Age Group Analysis** — liability aggregated by age band
- **Employee Cards** — full detail per employee with search and filter
- **Full Data Table** — all columns with export to Excel

---

## Submission Details

| Field | Value |
|-------|-------|
| Standard | IAS 19 – Employee Benefits |
| Method | Projected Unit Credit (PUC) |
| Valuation Date | 31/12/2023 |
| Reporting Date | 31/12/2024 |

</div>
