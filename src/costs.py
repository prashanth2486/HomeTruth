"""Stamp duty, GST, EMI, and the buy-versus-rent comparison."""

import json

from paths import RENT_YIELDS_PATH
from rates import (
    AFFORDABLE_CARPET_SQM,
    AFFORDABLE_PRICE_CAP_INR,
    BBMP_SURCHARGE_ON_DUTY,
    CARPET_SHARE_OF_SUPER_BUILTUP,
    CESS_ON_DUTY,
    DEFAULT_GROSS_YIELD,
    FIRST_SALE_BAND_20_LAKH_INR,
    FIRST_SALE_BAND_45_LAKH_INR,
    GST_AFFORDABLE,
    GST_STANDARD,
    GUIDANCE_VALUE_NOTE,
    RATE_NOTES,
    REGISTRATION_FEE,
    SQFT_PER_SQM,
    STAMP_DUTY_STANDARD,
    STAMP_FIRST_SALE_UP_TO_20_LAKH,
    STAMP_FIRST_SALE_UP_TO_45_LAKH,
)


def monthly_emi(principal: float, annual_interest_rate: float, tenure_years: int) -> float:
    """EMI = P * r * (1+r)^n / ((1+r)^n - 1), with r the monthly rate."""
    months = int(tenure_years) * 12
    if principal <= 0 or months <= 0:
        return 0.0
    if annual_interest_rate == 0:
        return float(principal) / months
    monthly_rate = annual_interest_rate / 12
    growth = (1 + monthly_rate) ** months
    return float(principal) * monthly_rate * growth / (growth - 1)


def loan_balance(principal: float, annual_interest_rate: float, tenure_years: int, years_paid: int) -> float:
    months = int(tenure_years) * 12
    paid = min(max(int(years_paid), 0) * 12, months)
    if principal <= 0 or paid <= 0:
        return max(float(principal), 0.0)
    if paid >= months:
        return 0.0
    if annual_interest_rate == 0:
        return float(principal) * (1 - paid / months)
    monthly_rate = annual_interest_rate / 12
    factor_n = (1 + monthly_rate) ** months
    factor_k = (1 + monthly_rate) ** paid
    return float(principal) * (factor_n - factor_k) / (factor_n - 1)


def stamp_duty_rate(price_inr: float, first_sale: bool) -> float:
    if not first_sale:
        return STAMP_DUTY_STANDARD
    if price_inr <= FIRST_SALE_BAND_20_LAKH_INR:
        return STAMP_FIRST_SALE_UP_TO_20_LAKH
    if price_inr <= FIRST_SALE_BAND_45_LAKH_INR:
        return STAMP_FIRST_SALE_UP_TO_45_LAKH
    return STAMP_DUTY_STANDARD


def stamp_duty_breakdown(price_inr: float, first_sale: bool) -> dict:
    rate = stamp_duty_rate(price_inr, first_sale)
    base = price_inr * rate
    cess = base * CESS_ON_DUTY
    surcharge = base * BBMP_SURCHARGE_ON_DUTY
    registration = price_inr * REGISTRATION_FEE
    return {
        "rate": rate,
        "base_inr": base,
        "cess_inr": cess,
        "surcharge_inr": surcharge,
        "total_stamp_inr": base + cess + surcharge,
        "registration_inr": registration,
    }


def carpet_sqm_for_gst(total_sqft: float, area_type: str, carpet_sqft: float | None) -> tuple[float, bool]:
    if carpet_sqft is not None and carpet_sqft > 0:
        return carpet_sqft / SQFT_PER_SQM, False
    if area_type.casefold() == "carpet area":
        return total_sqft / SQFT_PER_SQM, False
    return total_sqft * CARPET_SHARE_OF_SUPER_BUILTUP / SQFT_PER_SQM, True


def gst_on_property(
    price_inr: float,
    under_construction: bool,
    total_sqft: float,
    area_type: str,
    carpet_sqft: float | None,
) -> dict:
    carpet_sqm, assumed = carpet_sqm_for_gst(total_sqft, area_type, carpet_sqft)
    if not under_construction:
        return {
            "gst_inr": 0.0,
            "gst_rate": 0.0,
            "carpet_sqm": carpet_sqm,
            "carpet_assumed": assumed,
            "gst_note": "GST is not added because the property is treated as ready to move.",
        }
    affordable = carpet_sqm <= AFFORDABLE_CARPET_SQM and price_inr <= AFFORDABLE_PRICE_CAP_INR
    rate = GST_AFFORDABLE if affordable else GST_STANDARD
    if affordable:
        note = "GST at 1% because the carpet area is within 60 sq m and the price is within ₹45 lakh."
    else:
        note = "GST at 5% because the apartment is under construction and outside the affordable band."
    if assumed:
        note += " Carpet area is assumed at 70% of the entered area because carpet sqft was not provided."
    return {
        "gst_inr": price_inr * rate,
        "gst_rate": rate,
        "carpet_sqm": carpet_sqm,
        "carpet_assumed": assumed,
        "gst_note": note,
    }


def resolve_first_sale(ready_to_move: bool, first_sale: bool | None) -> bool:
    if first_sale is None:
        return not ready_to_move
    return first_sale


def purchase_costs(
    price_inr: float,
    ready_to_move: bool,
    first_sale: bool | None,
    total_sqft: float,
    area_type: str,
    carpet_sqft: float | None,
) -> dict:
    is_first_sale = resolve_first_sale(ready_to_move, first_sale)
    stamp = stamp_duty_breakdown(price_inr, is_first_sale)
    gst = gst_on_property(price_inr, not ready_to_move, total_sqft, area_type, carpet_sqft)
    return {
        "first_sale": is_first_sale,
        "stamp_duty_rate": stamp["rate"],
        "stamp_duty_base_inr": stamp["base_inr"],
        "cess_inr": stamp["cess_inr"],
        "surcharge_inr": stamp["surcharge_inr"],
        "stamp_duty_inr": stamp["total_stamp_inr"],
        "registration_inr": stamp["registration_inr"],
        "gst_inr": gst["gst_inr"],
        "gst_rate": gst["gst_rate"],
        "gst_note": gst["gst_note"],
        "carpet_sqm": gst["carpet_sqm"],
        "carpet_assumed": gst["carpet_assumed"],
        "transaction_costs_inr": stamp["total_stamp_inr"] + stamp["registration_inr"] + gst["gst_inr"],
        "guidance_value_note": GUIDANCE_VALUE_NOTE,
        "rate_notes": list(RATE_NOTES),
    }


def fold_locality(name: str) -> str:
    return " ".join(name.strip().casefold().split())


def indicative_gross_yield(locality: str, override: float | None = None) -> tuple[float, str]:
    if override is not None:
        return float(override), "Using the gross yield you entered. This rent figure is indicative, not an observed rent."
    payload = json.loads(RENT_YIELDS_PATH.read_text())
    table = {fold_locality(key): float(value) for key, value in payload.get("by_locality", {}).items()}
    matched = table.get(fold_locality(locality))
    if matched is not None:
        return matched, (
            f"Indicative gross yield of {matched:.1%} for this locality. "
            "It is an assumption, not an observed rent."
        )
    default = float(payload.get("default_gross_yield", DEFAULT_GROSS_YIELD))
    return default, (
        f"Indicative city-wide gross yield of {default:.1%}. "
        "It is an assumption, not an observed rent."
    )


def buy_vs_rent(
    price_inr: float,
    upfront_inr: float,
    loan_inr: float,
    annual_interest_rate: float,
    tenure_years: int,
    annual_rent_inr: float,
    appreciation: float,
    rent_growth: float,
    investment_return: float,
    maintenance_rate: float,
    horizons: tuple[int, ...] = (5, 10, 15),
) -> list[dict]:
    """Compare wealth after buying with wealth after renting and investing the gap.

    The renter starts with the buyer's upfront cash (down payment plus stamp duty,
    registration, and GST). Each year the renter adds EMI plus maintenance minus
    rent, then the portfolio compounds. The buyer holds the appreciated home less
    the remaining loan. Equal net worth within one rupee is a tie.
    """
    emi = monthly_emi(loan_inr, annual_interest_rate, tenure_years)
    rows = []
    for years in horizons:
        buyer_cash = upfront_inr
        rent_cash = 0.0
        portfolio = upfront_inr
        for year in range(1, years + 1):
            year_rent = annual_rent_inr * ((1 + rent_growth) ** (year - 1))
            year_maintenance = maintenance_rate * price_inr * ((1 + appreciation) ** (year - 1))
            year_emi = emi * 12 if year <= tenure_years else 0.0
            buyer_cash += year_emi + year_maintenance
            rent_cash += year_rent
            portfolio += year_emi + year_maintenance - year_rent
            portfolio *= 1 + investment_return
        house_value = price_inr * ((1 + appreciation) ** years)
        balance = loan_balance(loan_inr, annual_interest_rate, tenure_years, years)
        buyer_net = house_value - balance
        renter_net = portfolio
        if abs(buyer_net - renter_net) <= 1:
            cheaper = "tie"
        elif buyer_net > renter_net:
            cheaper = "buy"
        else:
            cheaper = "rent"
        rows.append(
            {
                "years": years,
                "buy_cash_outflow_inr": buyer_cash,
                "buy_opportunity_cost_inr": upfront_inr * ((1 + investment_return) ** years - 1),
                "rent_cash_outflow_inr": rent_cash,
                "buyer_net_worth_inr": buyer_net,
                "renter_net_worth_inr": renter_net,
                "cheaper": cheaper,
            }
        )
    return rows


def assumptions_text(
    appreciation: float,
    rent_growth: float,
    investment_return: float,
    maintenance_rate: float,
    gross_yield: float,
) -> str:
    return (
        "Indicative comparison only. "
        f"Price appreciation {appreciation:.0%}, rent growth {rent_growth:.0%}, "
        f"investment return {investment_return:.0%}, "
        f"maintenance {maintenance_rate:.1%} of value per year, "
        f"gross yield {gross_yield:.1%}. "
        "The renter is assumed to invest the upfront cash and each year's gap between "
        "the buyer's EMI plus maintenance and the rent. This is not a forecast."
    )
