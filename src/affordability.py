"""Income check: EMI at or below 40–50% of net monthly income after existing EMIs."""

from costs import monthly_emi


def max_monthly_emi(net_monthly_income: float, existing_monthly_emi: float, ratio: float) -> float:
    return max(0.0, net_monthly_income * ratio - existing_monthly_emi)


def max_loan_from_emi(max_emi: float, annual_interest_rate: float, tenure_years: int) -> float:
    months = int(tenure_years) * 12
    if max_emi <= 0 or months <= 0:
        return 0.0
    if annual_interest_rate == 0:
        return max_emi * months
    monthly_rate = annual_interest_rate / 12
    growth = (1 + monthly_rate) ** months
    return max_emi * (growth - 1) / (monthly_rate * growth)


def assess_affordability(
    price_inr: float,
    net_monthly_income: float,
    existing_monthly_emi: float,
    down_payment_fraction: float,
    annual_interest_rate: float,
    tenure_years: int,
    emi_ratio_cap: float,
    transaction_costs_inr: float,
) -> dict:
    down_payment = price_inr * down_payment_fraction
    loan = max(0.0, price_inr - down_payment)
    emi = monthly_emi(loan, annual_interest_rate, tenure_years)
    cap = max_monthly_emi(net_monthly_income, existing_monthly_emi, emi_ratio_cap)
    loan_ceiling = max_loan_from_emi(cap, annual_interest_rate, tenure_years)
    if down_payment_fraction >= 1:
        max_price = price_inr
    else:
        max_price = loan_ceiling / (1 - down_payment_fraction)
    fits = emi <= cap + 1e-6
    if fits:
        reason = "The loan EMI is within the share of income you set."
    else:
        reason = "The loan EMI is above the share of income you set."
    return {
        "max_emi_inr": cap,
        "max_loan_inr": loan_ceiling,
        "emi_inr": emi,
        "fits": fits,
        "max_affordable_price_inr": max_price,
        "cash_to_close_inr": down_payment + transaction_costs_inr,
        "down_payment_inr": down_payment,
        "loan_inr": loan,
        "reason": reason,
    }
