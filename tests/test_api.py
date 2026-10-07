import json

import pytest
from fastapi.testclient import TestClient

from conftest import sample_analysis
from features import location_for
from schemas import LocationResult

pytest.importorskip("fastapi")

from api.main import app


def _payload(**listing_overrides):
    listing = {
        "locality": "Whitefield",
        "total_sqft": 1200,
        "bhk": 2,
        "bath": 2,
        "area_type": "Super built-up Area",
        "ready_to_move": True,
        "first_sale": False,
        "asking_price_inr": 8_000_000,
        "carpet_sqft": None,
    }
    listing.update(listing_overrides)
    return {
        "listing": listing,
        "buyer": {
            "net_monthly_income_inr": 123456,
            "existing_monthly_emi_inr": 0,
            "down_payment_fraction": 0.2,
            "annual_interest_rate": 0.08,
            "tenure_years": 20,
            "emi_ratio_cap": 0.4,
        },
        "office_address": "Manyata Tech Park, Bengaluru",
        "assumptions": {
            "appreciation": 0.05,
            "rent_growth": 0.05,
            "investment_return": 0.07,
            "maintenance_rate": 0.005,
            "gross_yield": None,
        },
    }


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETRUTH_LOG_PATH", str(tmp_path / "predictions.jsonl"))

    def unavailable(*_args, **_kwargs):
        return LocationResult(
            available=False,
            note=(
                "Location data is unavailable, so there is no locality score or commute time. "
                "The price and cost figures are unaffected."
            ),
        )

    monkeypatch.setattr("predict.location_for", unavailable)
    monkeypatch.setattr(location_for, "__wrapped__", unavailable, raising=False)
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_negative_area_is_rejected(client):
    response = client.post("/analyze", json=_payload(total_sqft=-5))
    assert response.status_code == 422


def test_analyze_compare_and_pdf(client, tmp_path, monkeypatch):
    monkeypatch.setenv("HOMETRUTH_LOG_PATH", str(tmp_path / "predictions.jsonl"))
    analyzed = client.post("/analyze", json=_payload())
    assert analyzed.status_code == 200, analyzed.text
    body = analyzed.json()
    assert body["price"]["p10_inr"] <= body["price"]["p50_inr"] <= body["price"]["p90_inr"]
    assert body["costs"]["stamp_duty_inr"] == 448_000
    assert body["costs"]["registration_inr"] == 160_000
    assert body["costs"]["gst_inr"] == 0
    assert "123456" not in (tmp_path / "predictions.jsonl").read_text()
    assert "Manyata" not in (tmp_path / "predictions.jsonl").read_text()

    second = _payload()
    second["listing"]["locality"] = "Hebbal"
    second["listing"]["asking_price_inr"] = 9_000_000
    compared = client.post(
        "/compare",
        json={
            "listings": [_payload()["listing"], second["listing"]],
            "buyer": _payload()["buyer"],
            "office_address": None,
            "assumptions": _payload()["assumptions"],
        },
    )
    assert compared.status_code == 200, compared.text
    assert len(compared.json()["results"]) == 2

    pdf = client.post("/report", json=body)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")

    lone = client.post(
        "/compare",
        json={"listings": [_payload()["listing"]], "buyer": _payload()["buyer"]},
    )
    assert lone.status_code == 422


def test_chat_flood_question_on_the_api(client):
    response = client.post(
        "/chat",
        json={
            "analysis": sample_analysis().model_dump(mode="json"),
            "messages": [],
            "user_message": "Is it safe from floods?",
        },
    )
    assert response.status_code == 200
    assert response.json()["text"] == "I don't have that information."
    assert response.json()["refused"] is True
