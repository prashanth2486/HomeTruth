import pytest

from schemas import AnalyzeRequest, Assumptions, BuyerInput, CompareRequest, ListingInput
from validation import InputError, validate_compare, validate_request


def _listing(**overrides) -> ListingInput:
    payload = dict(
        locality="Whitefield",
        total_sqft=1200,
        bhk=2,
        bath=2,
        asking_price_inr=8_000_000,
    )
    payload.update(overrides)
    return ListingInput(**payload)


def _buyer(**overrides) -> BuyerInput:
    payload = dict(net_monthly_income_inr=150_000)
    payload.update(overrides)
    return BuyerInput(**payload)


def test_negative_area_empty_locality_and_absurd_price_are_rejected():
    with pytest.raises(InputError, match="Area must be positive"):
        validate_request(AnalyzeRequest(listing=_listing(total_sqft=-10), buyer=_buyer()))
    with pytest.raises(InputError, match="locality"):
        validate_request(AnalyzeRequest(listing=_listing(locality="   "), buyer=_buyer()))
    with pytest.raises(InputError, match="Asking price must be positive"):
        validate_request(AnalyzeRequest(listing=_listing(asking_price_inr=-1), buyer=_buyer()))
    with pytest.raises(InputError, match="500 crore"):
        validate_request(AnalyzeRequest(listing=_listing(asking_price_inr=6_000_000_000), buyer=_buyer()))


def test_emi_cap_stays_between_40_and_50_percent():
    with pytest.raises(InputError, match="EMI cap"):
        validate_request(AnalyzeRequest(listing=_listing(), buyer=_buyer(emi_ratio_cap=0.3)))


def test_compare_requires_two_or_three_listings():
    buyer = _buyer()
    with pytest.raises(InputError, match="2 or 3"):
        validate_compare(CompareRequest(listings=[_listing()], buyer=buyer))
    cleaned = validate_compare(
        CompareRequest(
            listings=[_listing(), _listing(locality=" Hebbal ")],
            buyer=buyer,
            assumptions=Assumptions(),
            office_address="  ",
        )
    )
    assert cleaned.listings[1].locality == "Hebbal"
    assert cleaned.office_address is None
