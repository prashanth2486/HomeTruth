from features import combine_location_scores, component_score, location_for
from schemas import LocationResult


def test_component_and_weighting():
    assert component_score(0, None) == 0
    assert component_score(5, 0) == 100
    assert component_score(1, 2000) == 8
    assert combine_location_scores({"metro": 100, "it_parks": 0, "schools": 0, "hospitals": 0}) == 35


def test_geocoder_failure_leaves_price_path_intact(monkeypatch):
    monkeypatch.setattr("features.geocode_place", lambda _query: None)
    result = location_for("Nowhere")
    assert result.available is False
    assert "unaffected" in result.note


def test_lookup_exception_is_an_unavailable_result(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("overpass down")

    monkeypatch.setattr("features._location_uncached", boom)
    result = location_for("Whitefield", "Manyata Tech Park")
    assert isinstance(result, LocationResult)
    assert result.available is False
    assert result.commute_minutes is None
