import json

import pytest
from fastapi.testclient import TestClient

from catalog import clear_catalog_cache, filter_listings, map_localities

pytest.importorskip("fastapi")

from api.main import app


def _catalog():
    return {
        "note": "Historical asks, not current inventory.",
        "listing_count": 2,
        "locality_count": 2,
        "localities": [
            {
                "name": "Whitefield",
                "count": 1,
                "median_asking_inr": 8_000_000,
                "median_model_inr": 6_000_000,
                "share_overpriced": 1,
                "lat": 12.97,
                "lon": 77.75,
            },
            {
                "name": "Hebbal",
                "count": 1,
                "median_asking_inr": 5_000_000,
                "median_model_inr": 7_000_000,
                "share_overpriced": 0,
                "lat": None,
                "lon": None,
            },
        ],
        "listings": [
            {
                "id": "ht-00001",
                "locality": "Whitefield",
                "total_sqft": 1200,
                "bhk": 2,
                "bath": 2,
                "area_type": "Super built-up Area",
                "ready_to_move": True,
                "asking_inr": 8_000_000,
                "p10_inr": 4_000_000,
                "p50_inr": 6_000_000,
                "p90_inr": 7_000_000,
                "verdict": "overpriced",
                "price_per_sqft": 6667,
            },
            {
                "id": "ht-00002",
                "locality": "Hebbal",
                "total_sqft": 1000,
                "bhk": 2,
                "bath": 2,
                "area_type": "Super built-up Area",
                "ready_to_move": True,
                "asking_inr": 5_000_000,
                "p10_inr": 5_500_000,
                "p50_inr": 7_000_000,
                "p90_inr": 9_000_000,
                "verdict": "great_deal",
                "price_per_sqft": 5000,
            },
        ],
    }


@pytest.fixture
def client(monkeypatch, tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(_catalog()))
    monkeypatch.setattr("catalog.CATALOG_PATH", path)
    clear_catalog_cache()
    yield TestClient(app)
    clear_catalog_cache()


def test_gap_sort_puts_the_cheaper_ask_first():
    page = filter_listings(_catalog(), bhk=2, sort="gap")
    assert [item["id"] for item in page["listings"]] == ["ht-00002", "ht-00001"]


def test_map_skips_missing_coordinates():
    assert [item["name"] for item in map_localities(_catalog())] == ["Whitefield"]


def test_search_filter_and_listing_id(client):
    found = client.get("/localities", params={"q": "white"})
    assert found.status_code == 200
    body = found.json()
    assert body["localities"][0]["name"] == "Whitefield"
    assert "income" not in json.dumps(body)

    deals = client.get("/listings", params={"verdict": "great_deal", "max_price": 6_000_000})
    assert deals.status_code == 200
    assert deals.json()["listings"][0]["id"] == "ht-00002"
    assert "income" not in json.dumps(deals.json())

    one = client.get("/listings/ht-00001")
    assert one.status_code == 200
    assert one.json()["listing"]["locality"] == "Whitefield"
    assert "income" not in one.json()

    missing = client.get("/listings/ht-99999")
    assert missing.status_code == 404


def test_built_catalog_search_and_known_id():
    from catalog import listing_by_id, load_catalog, search_localities
    from paths import CATALOG_PATH

    if not CATALOG_PATH.exists():
        pytest.skip("catalog not built")
    clear_catalog_cache()
    catalog = load_catalog()
    assert "income" not in json.dumps(catalog)
    found = search_localities(catalog, "whitefield")
    assert found[0]["name"] == "Whitefield"
    known = listing_by_id(catalog, "ht-09065")
    assert known is not None
    assert known["locality"] == "Whitefield"
    assert known["verdict"] in {"great_deal", "fair", "overpriced"}


def test_locality_page_is_case_insensitive(client):
    response = client.get("/localities/whitefield")
    assert response.status_code == 200
    assert response.json()["locality"]["count"] == 1
    assert response.json()["total"] == 1
