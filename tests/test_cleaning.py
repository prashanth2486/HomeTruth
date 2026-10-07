import math

import pandas as pd
import pytest

from data_cleaning import (
    clean_listings,
    group_rare_localities,
    localities_meeting_threshold,
    parse_bhk,
    parse_total_sqft,
)
from paths import RAW_CSV


def test_range_and_unit_conversions():
    assert parse_total_sqft("2100 - 2850") == 2475
    assert parse_total_sqft("34.46Sq. Meter") == pytest.approx(34.46 * 10.76391041671)
    assert parse_total_sqft("1574Sq. Yards") == 1574 * 9
    assert parse_total_sqft("1.5Acres") == pytest.approx(1.5 * 43560)
    assert parse_bhk("2 BHK") == 2
    assert parse_bhk("4 Bedroom") == 4
    assert parse_bhk("1 RK") == 1


def test_tiny_homes_and_double_spaces_are_removed():
    frame = pd.DataFrame(
        [
            {
                "area_type": "Super built-up  Area",
                "availability": "Ready To Move",
                "location": " Whitefield ",
                "size": "2 BHK",
                "society": "",
                "total_sqft": "100",
                "bath": 2,
                "balcony": 1,
                "price": 10,
            },
            {
                "area_type": "Plot  Area",
                "availability": "Ready To Move",
                "location": "Whitefield",
                "size": "2 BHK",
                "society": "",
                "total_sqft": "1200",
                "bath": 2,
                "balcony": 1,
                "price": 80,
            },
        ]
    )
    cleaned, stats = clean_listings(frame)
    assert stats["rows_out"] == 1
    assert cleaned.iloc[0]["location"] == "Whitefield"
    assert cleaned.iloc[0]["area_type"] == "Super built-up Area" or cleaned.iloc[0]["area_type"] == "Plot Area"
    assert math.isclose(cleaned.iloc[0]["total_sqft"], 1200)


def test_rare_localities_use_a_supplied_keep_list():
    frame = pd.DataFrame({"location": ["Whitefield", "Rare Place"]})
    grouped = group_rare_localities(frame, kept=["Whitefield"])
    assert grouped["location_grouped"].tolist() == ["Whitefield", "other"]
    assert localities_meeting_threshold(pd.Series(["A"] * 10 + ["B"] * 2)) == ["A"]


def test_public_csv_cleans():
    if not RAW_CSV.exists():
        pytest.skip("listings file is not downloaded")
    cleaned, stats = clean_listings(pd.read_csv(RAW_CSV))
    assert stats["rows_in"] > 10_000
    assert stats["rows_out"] > 5_000
    assert cleaned["price_lakhs"].gt(0).all()
    assert cleaned["total_sqft"].gt(0).all()
