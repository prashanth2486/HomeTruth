from metrics import interval_coverage, mape_pct, median_absolute_error
from quantiles import enforce_quantile_order
from verdict import offer_band, price_verdict


def test_crossing_quantiles_are_sorted():
    ordered = enforce_quantile_order({"p10": 90, "p40": 10, "p50": 50, "p60": 40, "p90": 80})
    assert ordered == {"p10": 10.0, "p40": 40.0, "p50": 50.0, "p60": 80.0, "p90": 90.0}


def test_verdict_boundaries():
    assert price_verdict(90, 100, 200) == "great_deal"
    assert price_verdict(100, 100, 200) == "fair"
    assert price_verdict(150, 100, 200) == "fair"
    assert price_verdict(200, 100, 200) == "fair"
    assert price_verdict(201, 100, 200) == "overpriced"
    assert offer_band(40, 60) == (40.0, 60.0)


def test_interval_coverage_counts_closed_endpoints():
    coverage = interval_coverage([1, 2, 3], [0, 2, 0], [2, 2, 1])
    assert coverage == 2 / 3
    assert mape_pct([100, 200], [110, 200]) == 5
    assert median_absolute_error([10, 20, 30], [10, 23, 30]) == 0
