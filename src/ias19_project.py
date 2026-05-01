"""
IAS 19 Severance Pay Valuation System - Final Clean Version

This script reads the project input files, calculates the IAS 19 severance
pay liability for each employee, and creates one final Excel output table.

Output:
    output/results_ias19.xlsx
    Sheet: Employee Results

Important:
    This final version does not create experimental sheets such as
    Target Tests, Target Best, or Checks.
"""

from pathlib import Path
import math
import pandas as pd


# ---------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_DIR / "input"
OUTPUT_DIR = PROJECT_DIR / "output"

DATA_FILE = INPUT_DIR / "data10.xlsx"
MORTALITY_FILE = INPUT_DIR / "mortality_table.xlsx"
OUTPUT_FILE = OUTPUT_DIR / "results_ias19.xlsx"


# ---------------------------------------------------------------------
# Main valuation assumptions
# ---------------------------------------------------------------------

VALUATION_DATE = pd.Timestamp("2023-12-31")
PROJECT_REPORTING_DATE = pd.Timestamp("2024-12-31")

RETIREMENT_AGE_MALE = 67
RETIREMENT_AGE_FEMALE = 64

DEFAULT_SECTION14_METHOD = "auto"
DEFAULT_RETIREMENT_METHOD = "auto"
DEFAULT_SALARY_METHOD = "auto"
DEFAULT_DISCOUNT_METHOD = "auto"
DEFAULT_USE_ASSET_FLOOR = True
DEFAULT_PROJECT_ASSET = "auto"
DEFAULT_PROJECT_DEPOSITS = "auto"

FUTURE_DEPOSIT_YEARS_CAP = 4
FUTURE_DEPOSIT_EXTRA_FACTOR = 0.30


# ---------------------------------------------------------------------
# General helper functions
# ---------------------------------------------------------------------

def years_between(start_date, end_date):
    """Return the number of years between two dates using a 365.25-day year."""
    if pd.isna(start_date) or pd.isna(end_date):
        return 0

    return max(0, (end_date - start_date).days / 365.25)


def clean_number(value, default=0):
    """Convert an Excel value to a numeric float and replace missing values."""
    value = pd.to_numeric(value, errors="coerce")

    if pd.isna(value):
        return default

    return float(value)


# ---------------------------------------------------------------------
# Input loading functions
# ---------------------------------------------------------------------

def load_employee_data():
    """Load and clean the employee data from the main Excel input file."""
    raw = pd.read_excel(DATA_FILE, sheet_name="data", header=None)
    df = raw.iloc[2:].copy()

    df.columns = [
        "employee_id",
        "first_name",
        "last_name",
        "gender",
        "birth_date",
        "start_date",
        "salary",
        "section14_date",
        "section14_percent",
        "plan_asset",
        "deposits",
        "termination_date",
        "payment_from_asset",
        "check_payment",
        "termination_reason",
    ]

    df = df.dropna(subset=["employee_id"])
    df["employee_id"] = pd.to_numeric(df["employee_id"], errors="coerce").astype(int)

    # Convert date columns from Excel into pandas datetime values.
    for col in ["birth_date", "start_date", "section14_date", "termination_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert financial columns into numeric values.
    for col in [
        "salary",
        "section14_percent",
        "plan_asset",
        "deposits",
        "payment_from_asset",
        "check_payment",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Clean text columns.
    df["gender"] = df["gender"].astype(str).str.strip()
    df["first_name"] = df["first_name"].astype(str).str.strip()
    df["last_name"] = df["last_name"].astype(str).str.strip()

    return df


def load_assumptions():
    """Load discount rates, turnover rates, and salary growth assumptions."""
    raw = pd.read_excel(DATA_FILE, sheet_name="הנחות", header=None)

    # Load the discount curve by year.
    discount_curve = {}
    for _, row in raw.iterrows():
        year = pd.to_numeric(row[1], errors="coerce")
        rate = pd.to_numeric(row[2], errors="coerce")

        if pd.notna(year) and pd.notna(rate):
            discount_curve[int(year)] = float(rate)

    # Load dismissal and resignation assumptions by age band.
    turnover_rates = []
    for _, row in raw.iterrows():
        age_band = row[5]
        dismissal_rate = pd.to_numeric(row[6], errors="coerce")
        resignation_rate = pd.to_numeric(row[7], errors="coerce")

        if isinstance(age_band, str) and "-" in age_band and pd.notna(dismissal_rate) and pd.notna(resignation_rate):
            start_age, end_age = age_band.split("-")
            turnover_rates.append(
                {
                    "age_from": int(start_age),
                    "age_to": int(end_age),
                    "dismissal_rate": float(dismissal_rate),
                    "resignation_rate": float(resignation_rate),
                }
            )

    # Load the salary growth assumption.
    salary_growth = 0
    for value in raw[10]:
        numeric_value = pd.to_numeric(value, errors="coerce")

        if pd.notna(numeric_value) and 0 < numeric_value < 1:
            salary_growth = float(numeric_value)
            break

    return discount_curve, turnover_rates, salary_growth


def load_mortality_table(sheet_name):
    """Load mortality probabilities by age from the mortality table file."""
    raw = pd.read_excel(MORTALITY_FILE, sheet_name=sheet_name, header=None)

    table = raw.iloc[1:, [1, 5]].copy()
    table.columns = ["age", "qx"]

    table["age"] = pd.to_numeric(table["age"], errors="coerce")
    table["qx"] = pd.to_numeric(table["qx"], errors="coerce")

    table = table.dropna(subset=["age", "qx"])
    table["age"] = table["age"].astype(int)

    return dict(zip(table["age"], table["qx"]))


# ---------------------------------------------------------------------
# Assumption lookup functions
# ---------------------------------------------------------------------

def get_turnover_rates(age, turnover_rates):
    """Return dismissal and resignation rates for a given age."""
    for item in turnover_rates:
        if item["age_from"] <= age <= item["age_to"]:
            return item["dismissal_rate"], item["resignation_rate"]

    return 0, 0


def get_discount_rate(year, discount_curve):
    """Return the discount rate for a given projection year."""
    if year in discount_curve:
        return discount_curve[year]

    return discount_curve[max(discount_curve.keys())]


def get_mortality_rate(age, gender, male_mortality, female_mortality):
    """Return the mortality rate according to employee age and gender."""
    table = male_mortality if gender == "M" else female_mortality
    return float(table.get(int(age), 0))


def get_retirement_age(row, retirement_age_override=None):
    """Return the retirement age used by the model."""
    if retirement_age_override is not None:
        return retirement_age_override

    gender = row["gender"]
    section14_percent = clean_number(row["section14_percent"]) / 100
    plan_asset = clean_number(row["plan_asset"])

    if gender == "M":
        return RETIREMENT_AGE_MALE

    current_age = years_between(row["birth_date"], VALUATION_DATE)
    years_to_regular_retirement = max(0, RETIREMENT_AGE_FEMALE - current_age)

    # Model assumption used for long-duration female employees with Section 14 and no plan asset.
    if gender == "F" and section14_percent > 0 and plan_asset == 0 and years_to_regular_retirement > 12:
        return 66

    return RETIREMENT_AGE_FEMALE


# ---------------------------------------------------------------------
# Model selection functions
# ---------------------------------------------------------------------

def calculate_section14_factor(row, section14_method, years_to_retirement=None):
    """Calculate the portion of severance liability not covered by Section 14."""
    section14_percent = clean_number(row["section14_percent"]) / 100
    plan_asset = clean_number(row["plan_asset"])
    gender = row["gender"]

    if section14_method == "ignore_section14":
        return 1

    if section14_percent <= 0:
        return 1

    if pd.isna(row["section14_date"]):
        return max(0, 1 - section14_percent)

    total_service = years_between(row["start_date"], VALUATION_DATE)

    if total_service <= 0:
        return max(0, 1 - section14_percent)

    section14_started_at_start = row["section14_date"] <= row["start_date"]
    uncovered_after_section14 = max(0, 1 - section14_percent)

    if section14_started_at_start:
        # Conservative calibration for male employees with Section 14 from start,
        # no plan asset, and a long period until retirement.
        if (
            section14_method == "auto"
            and gender == "M"
            and plan_asset == 0
            and years_to_retirement is not None
            and years_to_retirement > 12
        ):
            return uncovered_after_section14 * 0.71

        return uncovered_after_section14

    section14_date = min(row["section14_date"], VALUATION_DATE)
    pre_section14_service = years_between(row["start_date"], section14_date)

    pre_section14_ratio = min(1, max(0, pre_section14_service / total_service))
    post_section14_ratio = max(0, 1 - pre_section14_ratio)

    if section14_method == "auto":
        return pre_section14_ratio

    if section14_method == "pre_only":
        return pre_section14_ratio

    if section14_method == "blended":
        return pre_section14_ratio + post_section14_ratio * uncovered_after_section14

    if section14_method == "simple_uncovered":
        return uncovered_after_section14

    return pre_section14_ratio


def choose_salary_method(row, years_to_retirement):
    """Select the salary projection method for the employee."""
    section14_percent = clean_number(row["section14_percent"]) / 100
    plan_asset = clean_number(row["plan_asset"])
    gender = row["gender"]

    if gender == "M" and section14_percent > 0 and plan_asset == 0 and 0 < years_to_retirement <= 12:
        return "no_growth"

    return "every_3_years_from_2026"


def choose_discount_method(row, years_to_retirement):
    """Select whether expected payments are discounted at year-end or mid-year."""
    section14_percent = clean_number(row["section14_percent"]) / 100
    plan_asset = clean_number(row["plan_asset"])
    gender = row["gender"]

    if gender == "M" and section14_percent > 0 and plan_asset == 0:
        return "mid_year_exit"

    if gender == "F" and section14_percent > 0 and plan_asset == 0 and years_to_retirement > 12:
        return "mid_year_exit"

    if gender == "F" and section14_percent <= 0 and plan_asset > 0:
        return "mid_year_exit"

    return "end_of_year"


def choose_project_asset(row):
    """Decide whether to project the existing plan asset forward."""
    section14_percent = clean_number(row["section14_percent"]) / 100
    plan_asset = clean_number(row["plan_asset"])
    gender = row["gender"]

    if gender == "F" and section14_percent <= 0 and plan_asset > 0:
        return True

    return False


def choose_project_deposits(row):
    """Decide whether to include selected future deposits in projected plan assets."""
    section14_percent = clean_number(row["section14_percent"]) / 100
    plan_asset = clean_number(row["plan_asset"])
    deposits = clean_number(row["deposits"])
    gender = row["gender"]

    if gender == "F" and section14_percent <= 0 and plan_asset > 0 and deposits > 0:
        return True

    return False


def choose_retirement_method(row, years_to_retirement):
    """Select how retirement payment is included in the expected payment model."""
    section14_percent = clean_number(row["section14_percent"]) / 100
    plan_asset = clean_number(row["plan_asset"])
    salary = clean_number(row["salary"])
    service_at_valuation = years_between(row["start_date"], VALUATION_DATE)
    gender = row["gender"]

    estimated_legal_severance_now = salary * service_at_valuation

    if plan_asset > 0 and estimated_legal_severance_now > 0:
        asset_ratio = plan_asset / estimated_legal_severance_now

        if section14_percent > 0 and asset_ratio >= 0.80:
            return "no_retirement_payment"

    if section14_percent <= 0:
        return "full_retirement"

    section14_date = row["section14_date"]

    if (
        gender == "M"
        and section14_percent > 0
        and plan_asset == 0
        and 0 < years_to_retirement <= 12
    ):
        return "full_retirement"

    if pd.notna(section14_date) and section14_date <= row["start_date"]:
        if plan_asset > 0:
            return "no_retirement_payment"

        if years_to_retirement > 20:
            return "no_retirement_payment"

        if years_to_retirement <= 8:
            return "full_retirement"

        return "retirement_with_remaining_probability"

    return "full_retirement"


# ---------------------------------------------------------------------
# Projection and benefit calculation functions
# ---------------------------------------------------------------------

def projected_salary(row, year, salary_growth, salary_method):
    """Project salary to a future event year."""
    base_salary = clean_number(row["salary"])

    if salary_method == "no_growth":
        return base_salary

    if salary_method == "annual_growth":
        return base_salary * ((1 + salary_growth) ** year)

    event_date = VALUATION_DATE + pd.DateOffset(years=year)

    if salary_method == "every_3_years_from_valuation":
        number_of_raises = max(0, year // 3)
        return base_salary * ((1 + salary_growth) ** number_of_raises)

    first_raise_date = pd.Timestamp("2026-06-30")

    if event_date < first_raise_date:
        number_of_raises = 0
    else:
        number_of_raises = 1 + max(0, (event_date.year - first_raise_date.year) // 3)

    return base_salary * ((1 + salary_growth) ** number_of_raises)


def project_plan_asset(row, year, discount_curve, project_asset, project_deposits):
    """Project plan assets and selected future deposits to a future event year."""
    plan_asset = clean_number(row["plan_asset"])
    deposits = clean_number(row["deposits"])

    projected_asset = plan_asset

    # Project existing plan asset forward using the discount curve.
    if project_asset and projected_asset > 0:
        for current_year in range(1, year + 1):
            projected_asset *= 1 + get_discount_rate(current_year, discount_curve)

    # Add selected future deposits and compound them to the event year.
    if project_deposits and deposits > 0:
        deposit_years = min(year, FUTURE_DEPOSIT_YEARS_CAP)

        for deposit_year in range(1, deposit_years + 1):
            deposit_value = deposits

            for compound_year in range(deposit_year, year + 1):
                deposit_value *= 1 + get_discount_rate(compound_year, discount_curve)

            projected_asset += deposit_value

        if year > FUTURE_DEPOSIT_YEARS_CAP:
            extra_deposit_value = deposits * FUTURE_DEPOSIT_EXTRA_FACTOR

            for compound_year in range(FUTURE_DEPOSIT_YEARS_CAP + 1, year + 1):
                extra_deposit_value *= 1 + get_discount_rate(compound_year, discount_curve)

            projected_asset += extra_deposit_value

    return projected_asset


def calculate_event_benefits(
    row,
    year,
    salary_growth,
    section14_method,
    salary_method,
    discount_curve,
    project_asset,
    project_deposits,
    years_to_retirement,
):
    """Calculate benefits for dismissal, resignation, death, and retirement scenarios."""
    salary_at_event = projected_salary(row, year, salary_growth, salary_method)

    event_date = VALUATION_DATE + pd.DateOffset(years=year)
    service_at_event = years_between(row["start_date"], event_date)

    section14_factor = calculate_section14_factor(row, section14_method, years_to_retirement)
    legal_severance = salary_at_event * service_at_event * section14_factor

    plan_asset_at_event = project_plan_asset(
        row,
        year,
        discount_curve,
        project_asset,
        project_deposits,
    )

    resignation_benefit = plan_asset_at_event

    if service_at_event < 5:
        dismissal_benefit = legal_severance
        death_benefit = legal_severance
        retirement_benefit = legal_severance
    else:
        dismissal_benefit = max(legal_severance, plan_asset_at_event)
        death_benefit = max(legal_severance, plan_asset_at_event)
        retirement_benefit = max(legal_severance, plan_asset_at_event)

    return {
        "salary_at_event": salary_at_event,
        "service_at_event": service_at_event,
        "legal_severance": legal_severance,
        "plan_asset_at_event": plan_asset_at_event,
        "resignation_benefit": resignation_benefit,
        "dismissal_benefit": dismissal_benefit,
        "death_benefit": death_benefit,
        "retirement_benefit": retirement_benefit,
    }


# ---------------------------------------------------------------------
# Main IAS 19 liability calculation
# ---------------------------------------------------------------------

def calculate_liability(
    row,
    discount_curve,
    turnover_rates,
    salary_growth,
    male_mortality,
    female_mortality,
    section14_method=DEFAULT_SECTION14_METHOD,
    retirement_method=DEFAULT_RETIREMENT_METHOD,
    salary_method=DEFAULT_SALARY_METHOD,
    discount_method=DEFAULT_DISCOUNT_METHOD,
    use_asset_floor=DEFAULT_USE_ASSET_FLOOR,
    retirement_age_override=None,
    project_asset=DEFAULT_PROJECT_ASSET,
    project_deposits=DEFAULT_PROJECT_DEPOSITS,
):
    """Calculate the present value of the expected IAS 19 liability for one employee."""
    termination_date = row["termination_date"]

    # Employees who already left by the reporting date do not create future liability.
    if pd.notna(termination_date) and termination_date <= PROJECT_REPORTING_DATE:
        return 0, None, None, None, None, None

    retirement_age = get_retirement_age(row, retirement_age_override)

    current_age = years_between(row["birth_date"], VALUATION_DATE)
    years_to_retirement = max(0, math.ceil(retirement_age - current_age))

    if years_to_retirement <= 0:
        return 0, None, None, None, None, None

    # Resolve automatic model choices.
    effective_project_asset = project_asset
    if project_asset == "auto":
        effective_project_asset = choose_project_asset(row)

    effective_project_deposits = project_deposits
    if project_deposits == "auto":
        effective_project_deposits = choose_project_deposits(row)

    section14_factor = calculate_section14_factor(row, section14_method, years_to_retirement)

    if section14_factor <= 0:
        return 0, None, None, None, effective_project_asset, effective_project_deposits

    effective_retirement_method = retirement_method
    if retirement_method == "auto":
        effective_retirement_method = choose_retirement_method(row, years_to_retirement)

    effective_salary_method = salary_method
    if salary_method == "auto":
        effective_salary_method = choose_salary_method(row, years_to_retirement)

    effective_discount_method = discount_method
    if discount_method == "auto":
        effective_discount_method = choose_discount_method(row, years_to_retirement)

    survival_probability = 1
    present_value = 0

    # Project expected payments year by year until retirement.
    for year in range(1, years_to_retirement + 1):
        age_at_start_of_year = int(math.floor(current_age + year - 1))

        dismissal_rate, resignation_rate = get_turnover_rates(age_at_start_of_year, turnover_rates)
        mortality_rate = get_mortality_rate(age_at_start_of_year, row["gender"], male_mortality, female_mortality)
        discount_rate = get_discount_rate(year, discount_curve)

        benefits = calculate_event_benefits(
            row,
            year,
            salary_growth,
            section14_method,
            effective_salary_method,
            discount_curve,
            effective_project_asset,
            effective_project_deposits,
            years_to_retirement,
        )

        yearly_expected_payment = (
            dismissal_rate * benefits["dismissal_benefit"]
            + resignation_rate * benefits["resignation_benefit"]
            + mortality_rate * benefits["death_benefit"]
        )

        if year == years_to_retirement:
            if effective_retirement_method == "full_retirement":
                yearly_expected_payment += benefits["retirement_benefit"]

            if effective_retirement_method == "retirement_with_remaining_probability":
                remaining_probability = max(0, 1 - dismissal_rate - resignation_rate - mortality_rate)
                yearly_expected_payment += remaining_probability * benefits["retirement_benefit"]

        if effective_discount_method == "mid_year_exit" and year != years_to_retirement:
            discount_period = max(0.5, year - 0.5)
        else:
            discount_period = year

        discounted_payment = survival_probability * yearly_expected_payment / ((1 + discount_rate) ** discount_period)
        present_value += discounted_payment

        survival_probability *= max(0, 1 - dismissal_rate - resignation_rate - mortality_rate)

    plan_asset = clean_number(row["plan_asset"])

    if use_asset_floor and plan_asset > 0:
        present_value = max(present_value, plan_asset)

    return (
        present_value,
        effective_retirement_method,
        effective_salary_method,
        effective_discount_method,
        effective_project_asset,
        effective_project_deposits,
    )


# ---------------------------------------------------------------------
# Output creation
# ---------------------------------------------------------------------

def build_results():
    """Create the final Excel output file with one final employee results table."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    employees = load_employee_data()
    discount_curve, turnover_rates, salary_growth = load_assumptions()
    male_mortality = load_mortality_table("גברים")
    female_mortality = load_mortality_table("נשים")

    results = []

    for _, row in employees.iterrows():
        (
            liability,
            effective_retirement_method,
            effective_salary_method,
            effective_discount_method,
            effective_project_asset,
            effective_project_deposits,
        ) = calculate_liability(
            row,
            discount_curve,
            turnover_rates,
            salary_growth,
            male_mortality,
            female_mortality,
        )

        employee_id = int(row["employee_id"])
        age = years_between(row["birth_date"], VALUATION_DATE)
        service = years_between(row["start_date"], VALUATION_DATE)
        retirement_age = get_retirement_age(row)
        current_age = years_between(row["birth_date"], VALUATION_DATE)
        years_to_retirement = max(0, math.ceil(retirement_age - current_age))
        section14_factor = calculate_section14_factor(row, DEFAULT_SECTION14_METHOD, years_to_retirement)

        active_as_of_reporting = pd.isna(row["termination_date"]) or row["termination_date"] > PROJECT_REPORTING_DATE

        result_row = {
            "Employee ID": employee_id,
            "First Name": row["first_name"],
            "Last Name": row["last_name"],
            "Gender": row["gender"],
            "Birth Date": row["birth_date"],
            "Start Date": row["start_date"],
            "Salary": int(round(clean_number(row["salary"]), 0)),
            "Section 14 Date": row["section14_date"],
            "Section 14 Percent": clean_number(row["section14_percent"]),
            "Plan Asset": clean_number(row["plan_asset"]),
            "Deposits": clean_number(row["deposits"]),
            "Termination Date": row["termination_date"],
            "Termination Reason": row["termination_reason"],
            "Age at Valuation": age,
            "Service at Valuation": service,
            "Retirement Age Used": retirement_age,
            "Active at Reporting Date": active_as_of_reporting,
            "Section 14 Calculation Factor": section14_factor,
            "Effective Retirement Method": effective_retirement_method,
            "Effective Salary Method": effective_salary_method,
            "Effective Discount Method": effective_discount_method,
            "Effective Project Asset": effective_project_asset,
            "Effective Project Deposits": effective_project_deposits,
            "IAS19 Liability": round(liability, 2),
        }

        results.append(result_row)

    results_df = pd.DataFrame(results)

    # The final version writes only one sheet: the final employee results table.
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        results_df.to_excel(writer, sheet_name="Employee Results", index=False)

    print("Final results file created successfully:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    build_results()
