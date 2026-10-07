import pytest

from costs import (
    buy_vs_rent,
    gst_on_property,
    loan_balance,
    monthly_emi,
    stamp_duty_breakdown,
)


def test_emi_matches_the_closed_form():
    assert monthly_emi(1_000_000, 0.10, 1) == pytest.approx(87915.88723000959, rel=1e-9)
    assert monthly_emi(5_000_000, 0.08, 20) == pytest.approx(41822.00344967314, rel=1e-9)
    assert monthly_emi(0, 0.08, 20) == 0
    assert monthly_emi(1200, 0, 1) == 100


def test_loan_balance_endpoints():
    assert loan_balance(80, 0, 2, 0) == 80
    assert loan_balance(80, 0, 2, 1) == pytest.approx(40)
    assert loan_balance(80, 0, 2, 2) == 0


def test_resale_stamp_duty_on_50_lakh():
    duty = stamp_duty_breakdown(5_000_000, first_sale=False)
    assert duty["rate"] == 0.05
    assert duty["base_inr"] == 250_000
    assert duty["cess_inr"] == 25_000
    assert duty["surcharge_inr"] == 5_000
    assert duty["total_stamp_inr"] == 280_000
    assert duty["registration_inr"] == 100_000


def test_first_sale_slabs_apply_to_the_whole_price():
    small = stamp_duty_breakdown(1_500_000, True)
    assert small["rate"] == 0.02
    assert small["base_inr"] == 30_000
    assert small["cess_inr"] == 3_000
    assert small["surcharge_inr"] == 600
    assert small["registration_inr"] == 30_000

    middle = stamp_duty_breakdown(3_000_000, True)
    assert middle["rate"] == 0.03
    assert middle["base_inr"] == 90_000

    large = stamp_duty_breakdown(6_000_000, True)
    assert large["rate"] == 0.05
    assert large["base_inr"] == 300_000

    assert stamp_duty_breakdown(2_000_000, True)["rate"] == 0.02
    assert stamp_duty_breakdown(4_500_000, True)["rate"] == 0.03


def test_gst_bands():
    ready = gst_on_property(4_000_000, False, 1000, "Super built-up Area", None)
    assert ready["gst_inr"] == 0
    assert ready["gst_rate"] == 0

    carpet_50_sqm = 50 * 10.76391041671
    affordable = gst_on_property(4_000_000, True, 1000, "Super built-up Area", carpet_50_sqm)
    assert affordable["gst_rate"] == 0.01
    assert affordable["gst_inr"] == 40_000
    assert affordable["carpet_assumed"] is False

    carpet_80_sqm = 80 * 10.76391041671
    larger = gst_on_property(4_000_000, True, 1000, "Super built-up Area", carpet_80_sqm)
    assert larger["gst_rate"] == 0.05
    assert larger["gst_inr"] == 200_000

    expensive = gst_on_property(5_000_000, True, 400, "Carpet Area", None)
    assert expensive["gst_rate"] == 0.05
    assert expensive["carpet_assumed"] is False


def test_buy_versus_rent_hand_worked_cases():
    tie = buy_vs_rent(
        price_inr=100,
        upfront_inr=20,
        loan_inr=80,
        annual_interest_rate=0,
        tenure_years=1,
        annual_rent_inr=0,
        appreciation=0,
        rent_growth=0,
        investment_return=0,
        maintenance_rate=0,
        horizons=(1,),
    )[0]
    assert tie["cheaper"] == "tie"
    assert tie["buyer_net_worth_inr"] == pytest.approx(100)
    assert tie["renter_net_worth_inr"] == pytest.approx(100)

    renting_wins = buy_vs_rent(
        price_inr=100,
        upfront_inr=20,
        loan_inr=80,
        annual_interest_rate=0,
        tenure_years=1,
        annual_rent_inr=0,
        appreciation=0,
        rent_growth=0,
        investment_return=1,
        maintenance_rate=0,
        horizons=(1,),
    )[0]
    assert renting_wins["cheaper"] == "rent"
    assert renting_wins["renter_net_worth_inr"] == pytest.approx(200)

    buying_wins = buy_vs_rent(
        price_inr=100,
        upfront_inr=20,
        loan_inr=80,
        annual_interest_rate=0,
        tenure_years=1,
        annual_rent_inr=0,
        appreciation=1,
        rent_growth=0,
        investment_return=0,
        maintenance_rate=0,
        horizons=(1,),
    )[0]
    assert buying_wins["cheaper"] == "buy"
    assert buying_wins["buyer_net_worth_inr"] == pytest.approx(200)
