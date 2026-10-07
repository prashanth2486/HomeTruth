"""Request and response shapes for accounts. Income never enters the prediction log."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class BuyerPrefs(BaseModel):
    net_monthly_income_inr: float | None = None
    existing_monthly_emi_inr: float | None = None
    down_payment_fraction: float | None = None
    annual_interest_rate: float | None = None
    tenure_years: int | None = None
    emi_ratio_cap: float | None = None
    office_address: str | None = None


class ShortlistUpdate(BaseModel):
    listing_ids: list[str] = Field(default_factory=list, max_length=3)


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    name: str
    shortlist: list[str]
    buyer_prefs: BuyerPrefs | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
