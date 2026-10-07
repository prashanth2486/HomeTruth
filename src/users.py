"""Account rows. Shortlist and buyer prefs sync for signed-in users only."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base

MAX_SHORTLIST = 3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    shortlist_json: Mapped[str] = mapped_column(Text, default="[]")
    buyer_prefs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def shortlist(self) -> list[str]:
        try:
            raw = json.loads(self.shortlist_json or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(raw, list):
            return []
        return [str(item) for item in raw][:MAX_SHORTLIST]

    def set_shortlist(self, ids: list[str]) -> None:
        cleaned: list[str] = []
        for item in ids:
            value = str(item).strip()
            if value and value not in cleaned:
                cleaned.append(value)
            if len(cleaned) >= MAX_SHORTLIST:
                break
        self.shortlist_json = json.dumps(cleaned)

    def buyer_prefs(self) -> dict | None:
        if not self.buyer_prefs_json:
            return None
        try:
            raw = json.loads(self.buyer_prefs_json)
        except json.JSONDecodeError:
            return None
        return raw if isinstance(raw, dict) else None

    def set_buyer_prefs(self, prefs: dict | None) -> None:
        if prefs is None:
            self.buyer_prefs_json = None
            return
        allowed = {
            "net_monthly_income_inr",
            "existing_monthly_emi_inr",
            "down_payment_fraction",
            "annual_interest_rate",
            "tenure_years",
            "emi_ratio_cap",
            "office_address",
        }
        cleaned = {key: prefs[key] for key in allowed if key in prefs}
        self.buyer_prefs_json = json.dumps(cleaned)
