"""Compare an asking price with the predicted percentile band."""

from typing import Literal


def price_verdict(asking: float, p10: float, p90: float) -> Literal["great_deal", "fair", "overpriced"]:
    if asking < p10:
        return "great_deal"
    if asking > p90:
        return "overpriced"
    return "fair"


def offer_band(p40: float, p60: float) -> tuple[float, float]:
    return float(p40), float(p60)


VERDICT_LABELS = {
    "great_deal": "Great deal",
    "fair": "Fair",
    "overpriced": "Overpriced",
}
