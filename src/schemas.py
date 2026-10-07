"""Request and result models for one HomeTruth analysis."""

from typing import Literal

from pydantic import BaseModel, Field

from rates import (
    DEFAULT_ANNUAL_INTEREST_RATE,
    DEFAULT_APPRECIATION,
    DEFAULT_DOWN_PAYMENT_FRACTION,
    DEFAULT_EMI_RATIO,
    DEFAULT_INVESTMENT_RETURN,
    DEFAULT_MAINTENANCE_RATE,
    DEFAULT_RENT_GROWTH,
    DEFAULT_TENURE_YEARS,
)


class ListingInput(BaseModel):
    locality: str
    total_sqft: float
    bhk: int
    bath: float
    area_type: str = "Super built-up Area"
    ready_to_move: bool = True
    first_sale: bool | None = None
    asking_price_inr: float
    carpet_sqft: float | None = None


class BuyerInput(BaseModel):
    net_monthly_income_inr: float
    existing_monthly_emi_inr: float = 0
    down_payment_fraction: float = DEFAULT_DOWN_PAYMENT_FRACTION
    annual_interest_rate: float = DEFAULT_ANNUAL_INTEREST_RATE
    tenure_years: int = DEFAULT_TENURE_YEARS
    emi_ratio_cap: float = DEFAULT_EMI_RATIO


class Assumptions(BaseModel):
    appreciation: float = DEFAULT_APPRECIATION
    rent_growth: float = DEFAULT_RENT_GROWTH
    investment_return: float = DEFAULT_INVESTMENT_RETURN
    maintenance_rate: float = DEFAULT_MAINTENANCE_RATE
    gross_yield: float | None = None


class AnalyzeRequest(BaseModel):
    listing: ListingInput
    buyer: BuyerInput
    office_address: str | None = None
    assumptions: Assumptions = Field(default_factory=Assumptions)


class CompareRequest(BaseModel):
    listings: list[ListingInput]
    buyer: BuyerInput
    office_address: str | None = None
    assumptions: Assumptions = Field(default_factory=Assumptions)


class PriceEstimate(BaseModel):
    p10_inr: float
    p40_inr: float
    p50_inr: float
    p60_inr: float
    p90_inr: float
    asking_inr: float
    verdict: Literal["great_deal", "fair", "overpriced"]
    offer_low_inr: float
    offer_high_inr: float
    locality_used: str
    locality_unseen: bool
    explanation: str
    factors: list[dict]


class CostBreakdown(BaseModel):
    price_inr: float
    stamp_duty_rate: float
    stamp_duty_base_inr: float
    cess_inr: float
    surcharge_inr: float
    stamp_duty_inr: float
    registration_inr: float
    gst_inr: float
    gst_rate: float
    gst_note: str
    carpet_sqm: float | None
    carpet_assumed: bool
    first_sale: bool
    loan_inr: float
    total_interest_inr: float
    all_in_cost_inr: float
    due_at_purchase_inr: float
    guidance_value_note: str
    rate_notes: list[str]


class Affordability(BaseModel):
    max_emi_inr: float
    max_loan_inr: float
    emi_inr: float
    fits: bool
    max_affordable_price_inr: float
    cash_to_close_inr: float
    down_payment_inr: float
    reason: str


class HorizonResult(BaseModel):
    years: int
    buy_cash_outflow_inr: float
    buy_opportunity_cost_inr: float
    rent_cash_outflow_inr: float
    buyer_net_worth_inr: float
    renter_net_worth_inr: float
    cheaper: Literal["buy", "rent", "tie"]


class LocationComponent(BaseModel):
    count: int
    nearest_m: float | None
    score: float


class LocationResult(BaseModel):
    available: bool
    locality_score: float | None = None
    components: dict[str, LocationComponent] | None = None
    weights: dict[str, int] | None = None
    commute_km: float | None = None
    commute_minutes: float | None = None
    commute_speed_kmh: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    note: str


class AnalysisResult(BaseModel):
    locality_entered: str
    total_sqft: float
    bhk: int
    bath: float
    area_type: str
    ready_to_move: bool
    price: PriceEstimate
    costs: CostBreakdown
    affordability: Affordability
    buy_vs_rent: list[HorizonResult]
    rent_monthly_inr: float
    rent_note: str
    assumptions_note: str
    location: LocationResult
    disclaimer: str


class CompareResult(BaseModel):
    results: list[AnalysisResult]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    analysis: AnalysisResult
    messages: list[ChatMessage] = Field(default_factory=list)
    user_message: str


class ChatResponse(BaseModel):
    text: str
    disabled: bool = False
    capped: bool = False
    refused: bool = False
