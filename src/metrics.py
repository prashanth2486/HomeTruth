"""Score helpers shared by training and tests."""

import numpy as np


def mape_pct(y_true, y_pred) -> float:
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(actual - predicted) / np.clip(actual, 1e-9, None)) * 100)


def median_absolute_error(y_true, y_pred) -> float:
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    return float(np.median(np.abs(actual - predicted)))


def interval_coverage(y_true, low, high) -> float:
    """Share of actual values that fall inside the closed interval."""
    actual = np.asarray(y_true, dtype=float)
    if len(actual) == 0:
        return 0.0
    inside = (actual >= np.asarray(low, dtype=float)) & (actual <= np.asarray(high, dtype=float))
    return float(np.mean(inside))
