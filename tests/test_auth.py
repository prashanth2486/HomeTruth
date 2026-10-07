import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from api.main import app
from db import reset_engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMETRUTH_JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("HOMETRUTH_DATABASE_URL", f"sqlite:///{tmp_path / 'auth.db'}")
    reset_engine()
    return TestClient(app)


def _register(client, email="buyer@example.com", password="secretpass", name="Asha"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": name},
    )


def test_register_login_me_and_shortlist_sync(client):
    created = _register(client)
    assert created.status_code == 200
    body = created.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "buyer@example.com"
    assert "income" not in body["user"]
    token = body["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["name"] == "Asha"

    updated = client.put(
        "/auth/me/shortlist",
        headers={"Authorization": f"Bearer {token}"},
        json={"listing_ids": ["ht-09061", "ht-09067"]},
    )
    assert updated.status_code == 200
    assert updated.json()["shortlist"] == ["ht-09061", "ht-09067"]

    prefs = client.put(
        "/auth/me/buyer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "net_monthly_income_inr": 180000,
            "office_address": "Manyata Tech Park, Bengaluru",
            "annual_interest_rate": 0.08,
            "down_payment_fraction": 0.2,
            "tenure_years": 20,
            "emi_ratio_cap": 0.4,
            "existing_monthly_emi_inr": 0,
        },
    )
    assert prefs.status_code == 200
    assert prefs.json()["buyer_prefs"]["net_monthly_income_inr"] == 180000

    again = client.post(
        "/auth/login",
        json={"email": "buyer@example.com", "password": "secretpass"},
    )
    assert again.status_code == 200
    assert again.json()["user"]["shortlist"] == ["ht-09061", "ht-09067"]


def test_duplicate_email_and_bad_password(client):
    assert _register(client).status_code == 200
    clash = _register(client)
    assert clash.status_code == 409

    bad = client.post(
        "/auth/login",
        json={"email": "buyer@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401


def test_me_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
