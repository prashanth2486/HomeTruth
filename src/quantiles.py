"""Order quantile predictions so a lower percentile is never above a higher one."""

QUANTILE_KEYS = ("p10", "p40", "p50", "p60", "p90")


def enforce_quantile_order(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(float(values[key]) for key in QUANTILE_KEYS)
    return dict(zip(QUANTILE_KEYS, ordered, strict=True))


def enforce_quantile_rows(columns: dict[str, list[float]]) -> dict[str, list[float]]:
    rows = list(zip(*(columns[key] for key in QUANTILE_KEYS), strict=True))
    sorted_rows = [tuple(sorted(row)) for row in rows]
    return {
        key: [row[index] for row in sorted_rows]
        for index, key in enumerate(QUANTILE_KEYS)
    }
