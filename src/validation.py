"""Reject listings and buyer inputs the calculator should not run."""

from schemas import AnalyzeRequest, Assumptions, BuyerInput, CompareRequest, ListingInput


class InputError(ValueError):
    """The user sent a value the app will not estimate."""


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_listing(listing: ListingInput) -> None:
    errors: list[str] = []
    locality = (listing.locality or "").strip()
    _require(bool(locality), "Enter a locality.", errors)
    _require(listing.total_sqft > 0, "Area must be positive.", errors)
    _require(listing.total_sqft <= 50_000, "Area above 50,000 sqft is outside the range this model can estimate.", errors)
    _require(listing.asking_price_inr > 0, "Asking price must be positive.", errors)
    _require(
        listing.asking_price_inr <= 5_000_000_000,
        "Asking price above ₹500 crore is outside the range this model can estimate.",
        errors,
    )
    _require(1 <= listing.bhk <= 20, "BHK must be between 1 and 20.", errors)
    _require(0 < listing.bath <= 20, "Bathrooms must be greater than 0 and at most 20.", errors)
    if listing.carpet_sqft is not None:
        _require(listing.carpet_sqft > 0, "Carpet area must be positive.", errors)
        _require(listing.carpet_sqft <= 50_000, "Carpet area above 50,000 sqft is not accepted.", errors)
    if errors:
        raise InputError(" ".join(errors))


def validate_buyer(buyer: BuyerInput) -> None:
    errors: list[str] = []
    _require(buyer.net_monthly_income_inr > 0, "Net monthly income must be positive.", errors)
    _require(buyer.existing_monthly_emi_inr >= 0, "Existing EMI cannot be negative.", errors)
    _require(
        0 <= buyer.down_payment_fraction <= 0.95,
        "Down payment must be between 0% and 95% of the price.",
        errors,
    )
    _require(
        0 <= buyer.annual_interest_rate <= 0.25,
        "Interest rate must be between 0% and 25%.",
        errors,
    )
    _require(1 <= buyer.tenure_years <= 30, "Loan tenure must be between 1 and 30 years.", errors)
    _require(
        0.40 <= buyer.emi_ratio_cap <= 0.50,
        "The EMI cap must be between 40% and 50% of net income.",
        errors,
    )
    if errors:
        raise InputError(" ".join(errors))


def validate_assumptions(assumptions: Assumptions) -> None:
    errors: list[str] = []
    _require(-0.10 <= assumptions.appreciation <= 0.20, "Appreciation must be between -10% and 20%.", errors)
    _require(-0.10 <= assumptions.rent_growth <= 0.20, "Rent growth must be between -10% and 20%.", errors)
    _require(
        0 <= assumptions.investment_return <= 0.20,
        "Investment return must be between 0% and 20%.",
        errors,
    )
    _require(
        0 <= assumptions.maintenance_rate <= 0.05,
        "Maintenance must be between 0% and 5% of the property value per year.",
        errors,
    )
    if assumptions.gross_yield is not None:
        _require(
            0 <= assumptions.gross_yield <= 0.15,
            "Gross yield must be between 0% and 15%.",
            errors,
        )
    if errors:
        raise InputError(" ".join(errors))


def validate_request(request: AnalyzeRequest) -> AnalyzeRequest:
    listing = request.listing.model_copy(update={"locality": request.listing.locality.strip()})
    office = (request.office_address or "").strip() or None
    cleaned = request.model_copy(update={"listing": listing, "office_address": office})
    validate_listing(cleaned.listing)
    validate_buyer(cleaned.buyer)
    validate_assumptions(cleaned.assumptions)
    return cleaned


def validate_compare(request: CompareRequest) -> CompareRequest:
    if not 2 <= len(request.listings) <= 3:
        raise InputError("Compare 2 or 3 listings.")
    office = (request.office_address or "").strip() or None
    listings = [item.model_copy(update={"locality": item.locality.strip()}) for item in request.listings]
    cleaned = request.model_copy(update={"listings": listings, "office_address": office})
    for listing in cleaned.listings:
        validate_listing(listing)
    validate_buyer(cleaned.buyer)
    validate_assumptions(cleaned.assumptions)
    return cleaned
