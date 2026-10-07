"""Feature frames shared by training and prediction."""

import pandas as pd

FEATURE_COLUMNS = ["total_sqft", "bhk", "bath", "ready_to_move", "location", "area_type"]


def default_area_type(area_types: list[str]) -> str:
    for name in area_types:
        if name.casefold() == "super built-up area":
            return name
    return area_types[0]


def as_model_frame(
    df: pd.DataFrame,
    locality_categories: list[str],
    area_types: list[str],
    location_column: str = "location_grouped",
) -> pd.DataFrame:
    locations = df[location_column].astype(str)
    known_locations = set(locality_categories)
    locations = locations.where(locations.isin(known_locations | {"other"}), "other")
    areas = df["area_type"].astype(str)
    fallback = default_area_type(area_types)
    areas = areas.where(areas.isin(area_types), fallback)
    frame = pd.DataFrame(
        {
            "total_sqft": df["total_sqft"].astype(float),
            "bhk": df["bhk"].astype(float),
            "bath": df["bath"].astype(float),
            "ready_to_move": df["ready_to_move"].astype(int),
            "location": locations,
            "area_type": areas,
        }
    )
    return frame[FEATURE_COLUMNS]


def as_lgbm_frame(frame: pd.DataFrame, locality_categories: list[str], area_types: list[str]) -> pd.DataFrame:
    out = frame.copy()
    out["location"] = pd.Categorical(out["location"], categories=list(locality_categories) + ["other"])
    out["area_type"] = pd.Categorical(out["area_type"], categories=list(area_types))
    return out
