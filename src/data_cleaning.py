"""Turn the Bengaluru listings file into a model-ready table.

Price in the source file is lakhs of rupees. Locality names keep their most
common spelling. Rare localities stay intact here; training maps them to
"other" with a threshold fit on each training fold.
"""

import math
import re

import numpy as np
import pandas as pd

from rates import MIN_LOCALITY_COUNT

_SQM = 10.76391041671
_SQ_YARD = 9.0
_ACRE = 43560.0
_GUNTHA = 1089.0
_CENT = 435.6
_PERCH = 272.25
_GROUND = 2400.0
_MIN_SQFT_PER_BHK = 300
_MIN_PRICE_PER_SQFT = 1000
_MAX_PRICE_PER_SQFT = 100_000


def parse_total_sqft(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    unit_text = text.lower()
    multiplier = 1.0
    if "sq. meter" in unit_text or "sq.meter" in unit_text or "sqmeter" in unit_text:
        multiplier = _SQM
    elif "sq. yard" in unit_text or "sq.yard" in unit_text or "sq yard" in unit_text:
        multiplier = _SQ_YARD
    elif "acre" in unit_text:
        multiplier = _ACRE
    elif "guntha" in unit_text:
        multiplier = _GUNTHA
    elif "cent" in unit_text:
        multiplier = _CENT
    elif "perch" in unit_text:
        multiplier = _PERCH
    elif "ground" in unit_text:
        multiplier = _GROUND
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None
    if len(numbers) >= 2 and "-" in text:
        number = (numbers[0] + numbers[1]) / 2.0
    else:
        number = numbers[0]
    return number * multiplier


def parse_bhk(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    match = re.search(r"\d+", str(value))
    if match is None:
        return None
    return float(match.group())


def _collapse_ws(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def _canonical_spelling(names: pd.Series) -> pd.Series:
    keys = names.str.casefold()
    frame = pd.DataFrame({"key": keys, "display": names})
    chosen = frame.groupby("key")["display"].agg(lambda values: values.value_counts().index[0])
    return keys.map(chosen)


def localities_meeting_threshold(locations: pd.Series, min_count: int = MIN_LOCALITY_COUNT) -> list[str]:
    counts = locations.value_counts()
    return sorted(counts[counts >= min_count].index.tolist())


def group_rare_localities(
    df: pd.DataFrame,
    kept: list[str] | None = None,
    min_count: int = MIN_LOCALITY_COUNT,
) -> pd.DataFrame:
    """Map localities outside `kept` to other. Fit `kept` on the training fold only."""
    out = df.copy()
    if kept is None:
        kept = localities_meeting_threshold(out["location"], min_count)
    kept_set = set(kept)
    out["location_grouped"] = np.where(out["location"].isin(kept_set), out["location"], "other")
    return out


def clean_listings(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {"rows_in": int(len(df))}
    work = df.copy()
    work["location"] = _collapse_ws(work["location"])
    work.loc[work["location"].str.casefold().isin({"", "nan", "none"}), "location"] = np.nan
    work = work.dropna(subset=["location"])
    work["location"] = _canonical_spelling(work["location"])
    work["area_type"] = _collapse_ws(work["area_type"])
    work["total_sqft_num"] = work["total_sqft"].map(parse_total_sqft)
    work["bhk"] = work["size"].map(parse_bhk)
    work["bath"] = pd.to_numeric(work["bath"], errors="coerce")
    work["price_lakhs"] = pd.to_numeric(work["price"], errors="coerce")
    availability = _collapse_ws(work["availability"]).str.casefold()
    work["ready_to_move"] = availability.eq("ready to move")

    before = len(work)
    work = work.dropna(subset=["location", "area_type", "total_sqft_num", "bhk", "bath", "price_lakhs"])
    stats["dropped_missing"] = int(before - len(work))

    work = work[(work["total_sqft_num"] > 0) & (work["price_lakhs"] > 0) & (work["bhk"] > 0)]
    work = work[work["bath"] >= 1]
    work = work[work["bath"] <= work["bhk"] + 2]
    work = work[work["total_sqft_num"] / work["bhk"] >= _MIN_SQFT_PER_BHK]
    stats["rows_after_structure_filters"] = int(len(work))

    work["price_per_sqft"] = work["price_lakhs"] * 100_000 / work["total_sqft_num"]
    work = work[
        (work["price_per_sqft"] >= _MIN_PRICE_PER_SQFT) & (work["price_per_sqft"] <= _MAX_PRICE_PER_SQFT)
    ]

    kept_parts = []
    for _, group in work.groupby("location", sort=False):
        if len(group) < MIN_LOCALITY_COUNT:
            kept_parts.append(group)
            continue
        mean = group["price_per_sqft"].mean()
        std = group["price_per_sqft"].std()
        if std is None or math.isnan(std) or std == 0:
            kept_parts.append(group)
            continue
        kept_parts.append(group[(group["price_per_sqft"] > mean - std) & (group["price_per_sqft"] < mean + std)])
    work = pd.concat(kept_parts, ignore_index=True) if kept_parts else work.iloc[0:0]
    work = work.drop_duplicates(
        subset=["location", "area_type", "total_sqft_num", "bhk", "bath", "ready_to_move", "price_lakhs"]
    )

    cleaned = pd.DataFrame(
        {
            "location": work["location"].astype(str),
            "area_type": work["area_type"].astype(str),
            "total_sqft": work["total_sqft_num"].astype(float),
            "bhk": work["bhk"].astype(float),
            "bath": work["bath"].astype(float),
            "ready_to_move": work["ready_to_move"].astype(bool),
            "price_lakhs": work["price_lakhs"].astype(float),
            "price_per_sqft": work["price_per_sqft"].astype(float),
        }
    )
    stats["rows_out"] = int(len(cleaned))
    stats["localities"] = int(cleaned["location"].nunique()) if len(cleaned) else 0
    return cleaned, stats
