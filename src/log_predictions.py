"""Append locality, size, and the predicted range. Never write income or office location."""

import json
import os
from datetime import datetime, timezone

from paths import PREDICTION_LOG
from schemas import AnalysisResult


def prediction_log_path():
    override = os.environ.get("HOMETRUTH_LOG_PATH")
    if override:
        return override if hasattr(override, "open") else __import__("pathlib").Path(override)
    return PREDICTION_LOG


def log_prediction(result: AnalysisResult) -> None:
    record = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "locality": result.price.locality_used,
        "locality_unseen": result.price.locality_unseen,
        "total_sqft": result.total_sqft,
        "bhk": result.bhk,
        "bath": result.bath,
        "area_type": result.area_type,
        "ready_to_move": result.ready_to_move,
        "p10_inr": result.price.p10_inr,
        "p50_inr": result.price.p50_inr,
        "p90_inr": result.price.p90_inr,
        "verdict": result.price.verdict,
    }
    path = prediction_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def summarize_log(path=None) -> dict:
    path = path or prediction_log_path()
    if not path.exists():
        return {"count": 0, "median_p50_inr": None, "localities": {}}
    p50_values = []
    localities: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        p50_values.append(float(row["p50_inr"]))
        name = row["locality"]
        localities[name] = localities.get(name, 0) + 1
    p50_values.sort()
    mid = len(p50_values) // 2
    if not p50_values:
        median = None
    elif len(p50_values) % 2:
        median = p50_values[mid]
    else:
        median = (p50_values[mid - 1] + p50_values[mid]) / 2
    return {"count": len(p50_values), "median_p50_inr": median, "localities": localities}
