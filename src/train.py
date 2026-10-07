"""Train the Ridge baseline and five LightGBM quantile models.

Grouped cross-validation holds out whole localities, then maps any locality that
was not frequent in the training fold to "other". That is the unseen-area score.
A shuffled K-fold is stored beside it for buyers who pick a known locality.
There is no listing date, so there is no time split.
"""

import json

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from costs import fold_locality
from data_cleaning import clean_listings, group_rare_localities, localities_meeting_threshold
from metrics import interval_coverage, mape_pct, median_absolute_error
from model_frame import as_lgbm_frame, as_model_frame
from paths import ARTIFACT_PATH, METRICS_PATH, RAW_CSV
from quantiles import QUANTILE_KEYS, enforce_quantile_rows

LGBM_PARAMS = {
    "n_estimators": 250,
    "learning_rate": 0.06,
    "num_leaves": 31,
    "min_child_samples": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "verbosity": -1,
    "n_jobs": -1,
}
QUANTILES = ((0.10, "p10"), (0.40, "p40"), (0.50, "p50"), (0.60, "p60"), (0.90, "p90"))


def fit_quantile_models(frame: pd.DataFrame, y_log: np.ndarray) -> dict:
    models = {}
    for alpha, name in QUANTILES:
        model = LGBMRegressor(objective="quantile", alpha=alpha, **LGBM_PARAMS)
        model.fit(frame, y_log)
        models[name] = model
    return models


def fit_ridge(frame: pd.DataFrame, y_log: np.ndarray) -> Pipeline:
    transform = ColumnTransformer(
        [
            ("num", StandardScaler(), ["total_sqft", "bhk", "bath", "ready_to_move"]),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ["location", "area_type"],
            ),
        ]
    )
    pipeline = Pipeline([("transform", transform), ("model", Ridge(alpha=1.0))])
    pipeline.fit(frame, y_log)
    return pipeline


def _frames(train_df: pd.DataFrame, test_df: pd.DataFrame):
    kept = localities_meeting_threshold(train_df["location"])
    train_grouped = group_rare_localities(train_df, kept)
    test_grouped = group_rare_localities(test_df, kept)
    area_types = sorted(train_grouped["area_type"].unique())
    localities = sorted(kept)
    train_strings = as_model_frame(train_grouped, localities, area_types)
    test_strings = as_model_frame(test_grouped, localities, area_types)
    train_lgbm = as_lgbm_frame(train_strings, localities, area_types)
    test_lgbm = as_lgbm_frame(test_strings, localities, area_types)
    return train_strings, test_strings, train_lgbm, test_lgbm


def _predict_lakhs(models: dict, frame: pd.DataFrame) -> dict[str, np.ndarray]:
    columns = {name: np.exp(model.predict(frame)).tolist() for name, model in models.items()}
    ordered = enforce_quantile_rows({key: columns[key] for key in QUANTILE_KEYS})
    return {key: np.asarray(values, dtype=float) for key, values in ordered.items()}


def _oof_predictions(cleaned: pd.DataFrame, splitter) -> dict[str, np.ndarray]:
    y = cleaned["price_lakhs"].to_numpy()
    groups = cleaned["location"].to_numpy()
    p10 = np.zeros(len(cleaned))
    p50 = np.zeros(len(cleaned))
    p90 = np.zeros(len(cleaned))
    ridge_pred = np.zeros(len(cleaned))
    splits = splitter.split(cleaned, y, groups) if isinstance(splitter, GroupKFold) else splitter.split(cleaned, y)
    for fold, (train_idx, test_idx) in enumerate(splits, start=1):
        print(f"  fold {fold}: train {len(train_idx)} test {len(test_idx)}", flush=True)
        train_df = cleaned.iloc[train_idx]
        test_df = cleaned.iloc[test_idx]
        train_strings, test_strings, train_lgbm, test_lgbm = _frames(train_df, test_df)
        y_log = np.log(train_df["price_lakhs"].to_numpy())
        models = fit_quantile_models(train_lgbm, y_log)
        predicted = _predict_lakhs(models, test_lgbm)
        p10[test_idx] = predicted["p10"]
        p50[test_idx] = predicted["p50"]
        p90[test_idx] = predicted["p90"]
        ridge = fit_ridge(train_strings, y_log)
        ridge_pred[test_idx] = np.exp(ridge.predict(test_strings))
    return {"y": y, "p10": p10, "p50": p50, "p90": p90, "ridge": ridge_pred}


def _score_block(predictions: dict) -> dict:
    return {
        "lightgbm_p50": {
            "mape_pct": round(mape_pct(predictions["y"], predictions["p50"]), 2),
            "median_ae_lakhs": round(median_absolute_error(predictions["y"], predictions["p50"]), 3),
        },
        "ridge_baseline": {
            "mape_pct": round(mape_pct(predictions["y"], predictions["ridge"]), 2),
            "median_ae_lakhs": round(median_absolute_error(predictions["y"], predictions["ridge"]), 3),
        },
        "interval_10_90_coverage": round(
            interval_coverage(predictions["y"], predictions["p10"], predictions["p90"]),
            4,
        ),
    }


def _artifact(cleaned: pd.DataFrame) -> dict:
    kept = localities_meeting_threshold(cleaned["location"])
    grouped = group_rare_localities(cleaned, kept)
    area_types = sorted(grouped["area_type"].unique())
    localities = sorted(kept)
    strings = as_model_frame(grouped, localities, area_types)
    frame = as_lgbm_frame(strings, localities, area_types)
    y_log = np.log(grouped["price_lakhs"].to_numpy())
    print("Fitting the final models on all cleaned rows", flush=True)
    models = fit_quantile_models(frame, y_log)
    return {
        "models": models,
        "locality_categories": localities,
        "locality_lookup": {fold_locality(name): name for name in localities},
        "area_types": area_types,
        "area_lookup": {name.casefold(): name for name in area_types},
        "medians": {
            "total_sqft": float(grouped["total_sqft"].median()),
            "bhk": float(grouped["bhk"].median()),
            "bath": float(grouped["bath"].median()),
            "ready_to_move": float(grouped["ready_to_move"].astype(float).mean()),
        },
        "min_count": 10,
    }


def train_and_save(csv_path=None) -> dict:
    csv_path = csv_path or RAW_CSV
    raw = pd.read_csv(csv_path)
    cleaned, stats = clean_listings(raw)
    cleaned = cleaned.reset_index(drop=True)
    print(f"Cleaned {stats['rows_out']} rows from {stats['rows_in']}", flush=True)
    print("Grouped cross-validation", flush=True)
    grouped = _oof_predictions(cleaned, GroupKFold(n_splits=5))
    print("Random K-fold", flush=True)
    random_split = _oof_predictions(cleaned, KFold(n_splits=5, shuffle=True, random_state=42))
    metrics = {
        "rows_in": stats["rows_in"],
        "rows_out": stats["rows_out"],
        "dropped_missing": stats["dropped_missing"],
        "localities_after_cleaning": stats["localities"],
        "localities_kept": len(localities_meeting_threshold(cleaned["location"])),
        "target": "log(price in lakhs of rupees)",
        "model": "LightGBM quantile regression at the 10th, 40th, 50th, 60th, and 90th percentiles",
        "baseline": "Ridge regression on the same features",
        "grouped_cv": _score_block(grouped),
        "random_kfold": _score_block(random_split),
        "notes": (
            "Grouped CV holds out whole localities and maps them to other, so it measures unseen areas. "
            "Random K-fold lets a known locality appear in both train and test. "
            "Interval coverage is the share of held-out asking prices inside the 10th-90th prediction. "
            "The design target is about 80%. There is no listing date, so there is no time split. "
            "The model learns asking prices, not registered sale prices."
        ),
    }
    artifact = _artifact(cleaned)
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump(artifact, ARTIFACT_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2), flush=True)
    return metrics


if __name__ == "__main__":
    train_and_save()
