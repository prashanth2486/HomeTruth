"""Score cleaned listings and write data/catalog.json. No commute lookups."""

import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from catalog import build_payload, score_listings, write_catalog
from data_cleaning import clean_listings
from features import _GEOCODE_PATH, _place_query, _read_cache, geocode_place
from paths import RAW_CSV
from predict import load_artifact

import pandas as pd

logging.getLogger("hometruth.features").setLevel(logging.CRITICAL)


def _coordinates(names: list[str], keep: set[str]) -> dict[str, tuple[float, float] | None]:
    """Geocode the localities the model kept. Rare names stay on listings without a pin."""
    cache = _read_cache(_GEOCODE_PATH)
    found = {}
    targets = [name for name in names if name in keep]
    print(f"Geocoding {len(targets)} kept localities", flush=True)
    for index, name in enumerate(targets, start=1):
        query = _place_query(name)
        key = " ".join(query.strip().casefold().split())
        cached = key in cache
        if not cached:
            time.sleep(1.1)
        coords = geocode_place(query)
        found[name] = coords
        cache = _read_cache(_GEOCODE_PATH)
        status = "cached" if cached else ("ok" if coords else "miss")
        print(f"  geocode {index}/{len(targets)} {name}: {status}", flush=True)
    return found


def main() -> None:
    if not RAW_CSV.exists():
        raise SystemExit(f"Missing {RAW_CSV}. Run python scripts/download_data.py.")
    frame = pd.read_csv(RAW_CSV)
    cleaned, stats = clean_listings(frame)
    print(f"Cleaned {stats['rows_out']} rows", flush=True)
    artifact = load_artifact()
    scored = score_listings(cleaned, artifact)
    names = sorted(scored["location"].unique())
    payload = build_payload(scored, _coordinates(names, set(artifact["locality_categories"])))
    write_catalog(payload)
    placed = sum(1 for item in payload["localities"] if item["lat"] is not None)
    print(
        f"Wrote {payload['listing_count']} listings, "
        f"{payload['locality_count']} localities, {placed} with coordinates",
        flush=True,
    )


if __name__ == "__main__":
    main()
