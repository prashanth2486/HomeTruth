import json

from conftest import sample_analysis
from log_predictions import log_prediction


def test_prediction_log_keeps_personal_fields_out(tmp_path, monkeypatch):
    path = tmp_path / "predictions.jsonl"
    monkeypatch.setenv("HOMETRUTH_LOG_PATH", str(path))
    log_prediction(sample_analysis())
    text = path.read_text()
    row = json.loads(text)
    assert row["locality"] == "Whitefield"
    assert row["p50_inr"] == 8_000_000
    assert "income" not in text
    assert "office" not in text
    assert "net_monthly" not in text
    assert set(row) == {
        "logged_at",
        "locality",
        "locality_unseen",
        "total_sqft",
        "bhk",
        "bath",
        "area_type",
        "ready_to_move",
        "p10_inr",
        "p50_inr",
        "p90_inr",
        "verdict",
    }
