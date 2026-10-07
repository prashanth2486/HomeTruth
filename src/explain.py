"""Turn the three largest SHAP contributions into one sentence."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("hometruth.explain")

_explainer = None
_explainer_id: int | None = None


def _shap_row(model, frame: pd.DataFrame) -> np.ndarray | None:
    global _explainer, _explainer_id
    try:
        import shap

        if _explainer is None or _explainer_id != id(model):
            _explainer = shap.TreeExplainer(model)
            _explainer_id = id(model)
        values = _explainer.shap_values(frame)
        if isinstance(values, list):
            values = values[0]
        array = np.asarray(values, dtype=float)
        if array.ndim == 1:
            return array
        return array[0]
    except Exception:
        logger.exception("SHAP failed; trying LightGBM contributions")
    try:
        contrib = np.asarray(model.predict(frame, pred_contrib=True), dtype=float)
        if contrib.ndim == 2:
            return contrib[0, :-1]
        return contrib[:-1]
    except Exception:
        logger.exception("LightGBM contribution fallback failed")
        return None


def _clause(feature: str, value, shap_value: float, medians: dict) -> str:
    verb = "raises" if shap_value >= 0 else "lowers"
    if feature == "total_sqft":
        compared = "larger than" if float(value) >= float(medians["total_sqft"]) else "smaller than"
        return (
            f"floor area of {float(value):.0f} sqft, which is {compared} a typical listing, {verb} the estimate"
        )
    if feature == "bhk":
        return f"a bedroom count of {float(value):.0f} {verb} the estimate"
    if feature == "bath":
        return f"a bathroom count of {float(value):.0f} {verb} the estimate"
    if feature == "ready_to_move":
        state = "ready-to-move status" if int(value) == 1 else "under-construction status"
        return f"the {state} {verb} the estimate"
    if feature == "location":
        return f"the locality {value} {verb} the estimate"
    if feature == "area_type":
        return f"the area type {value} {verb} the estimate"
    return f"{feature} {verb} the estimate"


def build_sentence(clauses: list[str]) -> str:
    if not clauses:
        return "No factor breakdown is available for this listing."
    if len(clauses) == 1:
        return f"The estimate is driven mainly by {clauses[0]}."
    if len(clauses) == 2:
        return f"The estimate is driven mainly by {clauses[0]} and {clauses[1]}."
    head = ", ".join(clauses[:-1])
    return f"The estimate is driven mainly by {head}, and {clauses[-1]}."


def _fallback_factors(frame: pd.DataFrame, medians: dict) -> list[dict]:
    row = frame.iloc[0]
    factors = []
    for feature, label in (("total_sqft", "floor area"), ("bhk", "bedrooms"), ("location", "locality")):
        value = row[feature]
        if feature in medians and feature != "location":
            effect = "raises" if float(value) >= float(medians[feature]) else "lowers"
        else:
            effect = "raises"
        factors.append(
            {
                "feature": feature,
                "label": label,
                "value": str(value),
                "effect": effect,
                "shap": None,
            }
        )
    return factors


def explain_row(model, frame: pd.DataFrame, medians: dict, locality_unseen: bool) -> tuple[str, list[dict]]:
    values = _shap_row(model, frame)
    if values is None or len(values) != len(frame.columns):
        factors = _fallback_factors(frame, medians)
        sentence = build_sentence([_clause(item["feature"], item["value"], 1 if item["effect"] == "raises" else -1, medians) for item in factors])
    else:
        row = frame.iloc[0]
        ranked = sorted(
            zip(frame.columns, values, row.tolist(), strict=True),
            key=lambda item: abs(float(item[1])),
            reverse=True,
        )
        factors = []
        for feature, shap_value, value in ranked[:3]:
            effect = "raises" if float(shap_value) >= 0 else "lowers"
            factors.append(
                {
                    "feature": str(feature),
                    "label": str(feature).replace("_", " "),
                    "value": str(value),
                    "effect": effect,
                    "shap": round(float(shap_value), 4),
                }
            )
        sentence = build_sentence([_clause(item["feature"], item["value"], item["shap"], medians) for item in factors])
    if locality_unseen:
        sentence += (
            " This locality was grouped into 'other' because the model did not see enough listings there, "
            "so the estimate is less reliable."
        )
    return sentence, factors
