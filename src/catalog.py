"""Scored catalog of historical Bengaluru asking prices.

The file is rebuilt by scripts/build_catalog.py. These rows are old listings
from the public dataset, not homes for sale today.
"""

import json
import math
from functools import lru_cache

import numpy as np
import pandas as pd

from costs import fold_locality
from model_frame import as_lgbm_frame, as_model_frame
from paths import CATALOG_PATH
from quantiles import enforce_quantile_rows
from verdict import price_verdict

CATALOG_NOTE = (
    "These are historical Bengaluru asking prices from the public listings file, "
    "scored by the HomeTruth model. They are not homes for sale today."
)


class CatalogUnavailable(FileNotFoundError):
    pass


def score_listings(cleaned: pd.DataFrame, artifact: dict) -> pd.DataFrame:
    """Attach quantile prices and a verdict. No map calls."""
    lookup = artifact["locality_lookup"]
    grouped = [lookup.get(fold_locality(name), "other") for name in cleaned["location"]]
    source = cleaned.copy()
    source["location_grouped"] = grouped
    strings = as_model_frame(source, artifact["locality_categories"], artifact["area_types"])
    frame = as_lgbm_frame(strings, artifact["locality_categories"], artifact["area_types"])
    raw = {}
    for name, model in artifact["models"].items():
        lakhs = np.exp(model.predict(frame))
        raw[name] = (lakhs * 100_000.0).tolist()
    ordered = enforce_quantile_rows(raw)
    scored = cleaned.copy()
    for key, values in ordered.items():
        scored[key] = values
    asking = scored["price_lakhs"].to_numpy() * 100_000.0
    scored["asking_inr"] = asking
    scored["verdict"] = [
        price_verdict(ask, low, high)
        for ask, low, high in zip(asking, scored["p10"], scored["p90"], strict=True)
    ]
    scored["locality_grouped"] = grouped
    return scored


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2)


def build_payload(scored: pd.DataFrame, coordinates: dict[str, tuple[float, float] | None]) -> dict:
    scored = scored.sort_values(
        ["location", "total_sqft", "bhk", "asking_inr"],
        kind="mergesort",
    ).reset_index(drop=True)
    listings = []
    for index, row in scored.iterrows():
        listings.append(
            {
                "id": f"ht-{index + 1:05d}",
                "locality": str(row["location"]),
                "total_sqft": round(float(row["total_sqft"]), 1),
                "bhk": int(row["bhk"]),
                "bath": float(row["bath"]),
                "area_type": str(row["area_type"]),
                "ready_to_move": bool(row["ready_to_move"]),
                "asking_inr": round(float(row["asking_inr"])),
                "p10_inr": round(float(row["p10"])),
                "p50_inr": round(float(row["p50"])),
                "p90_inr": round(float(row["p90"])),
                "verdict": row["verdict"],
                "price_per_sqft": round(float(row["price_per_sqft"])),
            }
        )
    by_name: dict[str, list[dict]] = {}
    for item in listings:
        by_name.setdefault(item["locality"], []).append(item)
    localities = []
    for name in sorted(by_name):
        rows = by_name[name]
        coords = coordinates.get(name)
        overpriced = sum(1 for item in rows if item["verdict"] == "overpriced")
        localities.append(
            {
                "name": name,
                "count": len(rows),
                "median_asking_inr": round(_median([item["asking_inr"] for item in rows])),
                "median_model_inr": round(_median([item["p50_inr"] for item in rows])),
                "share_overpriced": round(overpriced / len(rows), 3),
                "lat": None if not coords else round(coords[0], 5),
                "lon": None if not coords else round(coords[1], 5),
            }
        )
    return {
        "note": CATALOG_NOTE,
        "listing_count": len(listings),
        "locality_count": len(localities),
        "localities": localities,
        "listings": listings,
    }


def write_catalog(payload: dict, path=CATALOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")))


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        raise CatalogUnavailable(
            f"Catalog not found at {CATALOG_PATH}. Run python scripts/build_catalog.py."
        )
    return json.loads(CATALOG_PATH.read_text())


def clear_catalog_cache() -> None:
    load_catalog.cache_clear()


def search_localities(catalog: dict, query: str = "", limit: int = 24) -> list[dict]:
    needle = " ".join(query.strip().casefold().split())
    matches = []
    for item in catalog["localities"]:
        if needle and needle not in item["name"].casefold():
            continue
        matches.append(item)
    matches.sort(key=lambda item: (-item["count"], item["name"]))
    return matches[:limit]


def locality_by_name(catalog: dict, name: str) -> dict | None:
    key = fold_locality(name)
    for item in catalog["localities"]:
        if fold_locality(item["name"]) == key:
            return item
    return None


def _gap(item: dict) -> float:
    mid = item["p50_inr"] or 1
    return (item["asking_inr"] - mid) / mid


def filter_listings(
    catalog: dict,
    *,
    locality: str | None = None,
    bhk: int | None = None,
    verdict: str | None = None,
    max_price: float | None = None,
    sort: str = "price",
    limit: int = 40,
    offset: int = 0,
) -> dict:
    locality_key = fold_locality(locality) if locality else ""
    rows = []
    for item in catalog["listings"]:
        if locality_key and fold_locality(item["locality"]) != locality_key:
            continue
        if bhk is not None and int(item["bhk"]) != int(bhk):
            continue
        if verdict and item["verdict"] != verdict:
            continue
        if max_price is not None and item["asking_inr"] > max_price:
            continue
        rows.append(item)
    if sort == "gap":
        rows.sort(key=_gap)
    else:
        rows.sort(key=lambda item: item["asking_inr"])
    total = len(rows)
    start = max(offset, 0)
    end = start + max(limit, 1)
    return {"total": total, "listings": rows[start:end]}


def listing_by_id(catalog: dict, listing_id: str) -> dict | None:
    for item in catalog["listings"]:
        if item["id"] == listing_id:
            return item
    return None


def map_localities(catalog: dict) -> list[dict]:
    return [
        item
        for item in catalog["localities"]
        if item.get("lat") is not None and item.get("lon") is not None and not math.isnan(item["lat"])
    ]
