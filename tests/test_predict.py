import json

import pytest

from explain import build_sentence
from paths import METRICS_PATH
from schemas import AnalyzeRequest, BuyerInput, ListingInput


def test_explanation_sentence_joins_three_factors():
    sentence = build_sentence(["the locality Whitefield raises the estimate", "floor area lowers the estimate", "bedrooms raise the estimate"])
    assert sentence.startswith("The estimate is driven mainly by")
    assert sentence.endswith(".")
    assert ", and " in sentence


def test_saved_metrics_include_coverage():
    if not METRICS_PATH.exists():
        pytest.skip("train the model before checking coverage")
    metrics = json.loads(METRICS_PATH.read_text())
    coverage = metrics["grouped_cv"]["interval_10_90_coverage"]
    assert 0 <= coverage <= 1
    assert "mape_pct" in metrics["grouped_cv"]["lightgbm_p50"]
    assert "mape_pct" in metrics["grouped_cv"]["ridge_baseline"]


def test_live_model_orders_quantiles_and_hides_income(monkeypatch, tmp_path):
    pytest.importorskip("lightgbm")
    import predict

    if not predict.ARTIFACT_PATH.exists():
        pytest.skip("model artifact is missing")
    monkeypatch.setenv("HOMETRUTH_LOG_PATH", str(tmp_path / "predictions.jsonl"))
    from schemas import LocationResult

    monkeypatch.setattr(
        predict,
        "location_for",
        lambda *_args, **_kwargs: LocationResult(
            available=False,
            note="Location data is unavailable, so there is no locality score or commute time. The price and cost figures are unaffected.",
        ),
    )
    result = predict.analyze(
        AnalyzeRequest(
            listing=ListingInput(
                locality="Whitefield",
                total_sqft=1200,
                bhk=2,
                bath=2,
                asking_price_inr=8_000_000,
                ready_to_move=True,
                first_sale=False,
            ),
            buyer=BuyerInput(net_monthly_income_inr=123456),
            office_address="Secret Office, Bengaluru",
        )
    )
    price = result.price
    assert price.p10_inr <= price.p40_inr <= price.p50_inr <= price.p60_inr <= price.p90_inr
    assert price.verdict in {"great_deal", "fair", "overpriced"}
    assert price.explanation
    assert price.locality_unseen is False
    unseen = predict.analyze(
        AnalyzeRequest(
            listing=ListingInput(
                locality="A locality the model has never heard of",
                total_sqft=1200,
                bhk=2,
                bath=2,
                asking_price_inr=8_000_000,
            ),
            buyer=BuyerInput(net_monthly_income_inr=123456),
        )
    )
    assert unseen.price.locality_unseen is True
    assert unseen.price.locality_used == "other"
    assert "less reliable" in unseen.price.explanation
    text = (tmp_path / "predictions.jsonl").read_text()
    assert "123456" not in text
    assert "Secret Office" not in text
    assert "income" not in text
