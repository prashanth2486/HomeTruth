"""One analysis JSON for a listing, a buyer, and an optional office."""

import logging
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from affordability import assess_affordability
from costs import assumptions_text, buy_vs_rent, fold_locality, indicative_gross_yield, purchase_costs
from explain import explain_row
from features import location_for
from log_predictions import log_prediction
from model_frame import as_lgbm_frame, as_model_frame, default_area_type
from paths import ARTIFACT_PATH
from quantiles import enforce_quantile_order
from rates import DISCLAIMER
from schemas import (
    Affordability,
    AnalysisResult,
    AnalyzeRequest,
    CompareRequest,
    CompareResult,
    CostBreakdown,
    HorizonResult,
    PriceEstimate,
)
from validation import validate_compare, validate_request
from verdict import offer_band, price_verdict

logger = logging.getLogger("hometruth.predict")


@lru_cache(maxsize=1)
def load_artifact():
    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(f"Model file not found at {ARTIFACT_PATH}. Run python scripts/retrain.py.")
    return joblib.load(ARTIFACT_PATH)


def frame_for_listing(listing, artifact) -> tuple[pd.DataFrame, str, bool]:
    key = fold_locality(listing.locality)
    if key in artifact["locality_lookup"]:
        location = artifact["locality_lookup"][key]
        unseen = False
    else:
        location = "other"
        unseen = True
    area = artifact["area_lookup"].get(listing.area_type.casefold(), default_area_type(artifact["area_types"]))
    source = pd.DataFrame(
        [
            {
                "total_sqft": listing.total_sqft,
                "bhk": listing.bhk,
                "bath": listing.bath,
                "ready_to_move": int(listing.ready_to_move),
                "location_grouped": location,
                "area_type": area,
            }
        ]
    )
    frame = as_model_frame(source, artifact["locality_categories"], artifact["area_types"])
    return as_lgbm_frame(frame, artifact["locality_categories"], artifact["area_types"]), location, unseen


def predict_range_inr(artifact, frame: pd.DataFrame) -> dict[str, float]:
    raw = {}
    for name, model in artifact["models"].items():
        lakhs = float(np.exp(model.predict(frame)[0]))
        raw[name] = lakhs * 100_000
    return enforce_quantile_order(raw)


def analyze(request: AnalyzeRequest) -> AnalysisResult:
    request = validate_request(request)
    listing = request.listing
    buyer = request.buyer
    artifact = load_artifact()
    frame, locality_used, unseen = frame_for_listing(listing, artifact)
    quantiles = predict_range_inr(artifact, frame)
    explanation, factors = explain_row(artifact["models"]["p50"], frame, artifact["medians"], unseen)
    verdict = price_verdict(listing.asking_price_inr, quantiles["p10"], quantiles["p90"])
    low, high = offer_band(quantiles["p40"], quantiles["p60"])
    purchase = purchase_costs(
        listing.asking_price_inr,
        listing.ready_to_move,
        listing.first_sale,
        listing.total_sqft,
        listing.area_type,
        listing.carpet_sqft,
    )
    budget = assess_affordability(
        price_inr=listing.asking_price_inr,
        net_monthly_income=buyer.net_monthly_income_inr,
        existing_monthly_emi=buyer.existing_monthly_emi_inr,
        down_payment_fraction=buyer.down_payment_fraction,
        annual_interest_rate=buyer.annual_interest_rate,
        tenure_years=buyer.tenure_years,
        emi_ratio_cap=buyer.emi_ratio_cap,
        transaction_costs_inr=purchase["transaction_costs_inr"],
    )
    interest = max(0.0, budget["emi_inr"] * buyer.tenure_years * 12 - budget["loan_inr"])
    gross_yield, rent_note = indicative_gross_yield(listing.locality, request.assumptions.gross_yield)
    annual_rent = listing.asking_price_inr * gross_yield
    horizons = buy_vs_rent(
        price_inr=listing.asking_price_inr,
        upfront_inr=budget["down_payment_inr"] + purchase["transaction_costs_inr"],
        loan_inr=budget["loan_inr"],
        annual_interest_rate=buyer.annual_interest_rate,
        tenure_years=buyer.tenure_years,
        annual_rent_inr=annual_rent,
        appreciation=request.assumptions.appreciation,
        rent_growth=request.assumptions.rent_growth,
        investment_return=request.assumptions.investment_return,
        maintenance_rate=request.assumptions.maintenance_rate,
    )
    try:
        location = location_for(listing.locality, request.office_address)
    except Exception:
        logger.exception("location lookup failed")
        from schemas import LocationResult

        location = LocationResult(
            available=False,
            note=(
                "Location data is unavailable, so there is no locality score or commute time. "
                "The price and cost figures are unaffected."
            ),
        )
    result = AnalysisResult(
        locality_entered=listing.locality,
        total_sqft=listing.total_sqft,
        bhk=listing.bhk,
        bath=listing.bath,
        area_type=listing.area_type,
        ready_to_move=listing.ready_to_move,
        price=PriceEstimate(
            p10_inr=quantiles["p10"],
            p40_inr=quantiles["p40"],
            p50_inr=quantiles["p50"],
            p60_inr=quantiles["p60"],
            p90_inr=quantiles["p90"],
            asking_inr=listing.asking_price_inr,
            verdict=verdict,
            offer_low_inr=low,
            offer_high_inr=high,
            locality_used=locality_used,
            locality_unseen=unseen,
            explanation=explanation,
            factors=factors,
        ),
        costs=CostBreakdown(
            price_inr=listing.asking_price_inr,
            stamp_duty_rate=purchase["stamp_duty_rate"],
            stamp_duty_base_inr=purchase["stamp_duty_base_inr"],
            cess_inr=purchase["cess_inr"],
            surcharge_inr=purchase["surcharge_inr"],
            stamp_duty_inr=purchase["stamp_duty_inr"],
            registration_inr=purchase["registration_inr"],
            gst_inr=purchase["gst_inr"],
            gst_rate=purchase["gst_rate"],
            gst_note=purchase["gst_note"],
            carpet_sqm=purchase["carpet_sqm"],
            carpet_assumed=purchase["carpet_assumed"],
            first_sale=purchase["first_sale"],
            loan_inr=budget["loan_inr"],
            total_interest_inr=interest,
            all_in_cost_inr=listing.asking_price_inr + purchase["transaction_costs_inr"] + interest,
            due_at_purchase_inr=budget["cash_to_close_inr"],
            guidance_value_note=purchase["guidance_value_note"],
            rate_notes=purchase["rate_notes"],
        ),
        affordability=Affordability(
            max_emi_inr=budget["max_emi_inr"],
            max_loan_inr=budget["max_loan_inr"],
            emi_inr=budget["emi_inr"],
            fits=budget["fits"],
            max_affordable_price_inr=budget["max_affordable_price_inr"],
            cash_to_close_inr=budget["cash_to_close_inr"],
            down_payment_inr=budget["down_payment_inr"],
            reason=budget["reason"],
        ),
        buy_vs_rent=[HorizonResult(**row) for row in horizons],
        rent_monthly_inr=annual_rent / 12,
        rent_note=rent_note,
        assumptions_note=assumptions_text(
            request.assumptions.appreciation,
            request.assumptions.rent_growth,
            request.assumptions.investment_return,
            request.assumptions.maintenance_rate,
            gross_yield,
        ),
        location=location,
        disclaimer=DISCLAIMER,
    )
    try:
        log_prediction(result)
    except Exception:
        logger.exception("prediction log failed")
    return result


def compare(request: CompareRequest) -> CompareResult:
    request = validate_compare(request)
    results = [
        analyze(
            AnalyzeRequest(
                listing=listing,
                buyer=request.buyer,
                office_address=request.office_address,
                assumptions=request.assumptions,
            )
        )
        for listing in request.listings
    ]
    return CompareResult(results=results)
