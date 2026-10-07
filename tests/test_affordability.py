import pytest

from affordability import assess_affordability, max_loan_from_emi, max_monthly_emi
from costs import monthly_emi


def test_emi_cap_subtracts_existing_loans():
    assert max_monthly_emi(200_000, 0, 0.4) == 80_000
    assert max_monthly_emi(100_000, 20_000, 0.4) == 20_000
    assert max_monthly_emi(50_000, 30_000, 0.4) == 0


def test_max_loan_inverts_the_emi_formula():
    assert max_loan_from_emi(1000, 0, 1) == 12_000
    cap = 80_000
    loan = max_loan_from_emi(cap, 0.08, 20)
    assert monthly_emi(loan, 0.08, 20) == pytest.approx(cap, rel=1e-6)


def test_listing_fit_uses_the_emi_rule_only():
    fits = assess_affordability(
        price_inr=5_000_000,
        net_monthly_income=200_000,
        existing_monthly_emi=0,
        down_payment_fraction=0.2,
        annual_interest_rate=0.08,
        tenure_years=20,
        emi_ratio_cap=0.4,
        transaction_costs_inr=380_000,
    )
    assert fits["fits"] is True
    assert fits["loan_inr"] == 4_000_000
    assert fits["cash_to_close_inr"] == 1_000_000 + 380_000

    too_dear = assess_affordability(
        price_inr=5_000_000,
        net_monthly_income=50_000,
        existing_monthly_emi=0,
        down_payment_fraction=0.2,
        annual_interest_rate=0.08,
        tenure_years=20,
        emi_ratio_cap=0.4,
        transaction_costs_inr=380_000,
    )
    assert too_dear["fits"] is False
    assert too_dear["max_emi_inr"] == 20_000
