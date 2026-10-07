"""Locality and commute scores from OpenStreetMap, with a disk cache.

Weights (they sum to 100): metro 35, IT parks 25, schools 20, hospitals 20.
Each category is scored 0–100 from the nearest place and the count inside 2 km,
then combined with those weights. Commute time is the shortest drive path at
25 km/h. It excludes live traffic.
"""

import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

from paths import CACHE_DIR
from rates import COMMUTE_SPEED_KMH, LOCALITY_RADIUS_M, LOCALITY_WEIGHTS
from schemas import LocationComponent, LocationResult

logger = logging.getLogger("hometruth.features")

_GEOCODE_PATH = CACHE_DIR / "geocode.json"
_SCORE_PATH = CACHE_DIR / "locality_scores.json"
_COMMUTE_PATH = CACHE_DIR / "commutes.json"
_LOCATION_TIMEOUT_SECONDS = 75
_UNAVAILABLE = (
    "Location data is unavailable, so there is no locality score or commute time. "
    "The price and cost figures are unaffected."
)


def component_score(count: int, nearest_m: float | None, radius_m: float = LOCALITY_RADIUS_M) -> float:
    if count <= 0 or nearest_m is None:
        return 0.0
    distance_score = 100.0 * (1.0 - min(max(nearest_m, 0.0), radius_m) / radius_m)
    count_score = 100.0 * min(count, 5) / 5.0
    return 0.6 * distance_score + 0.4 * count_score


def combine_location_scores(parts: dict[str, float]) -> float:
    total_weight = float(sum(LOCALITY_WEIGHTS.values()))
    return sum(parts.get(name, 0.0) * weight for name, weight in LOCALITY_WEIGHTS.items()) / total_weight


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def _read_cache(path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _write_cache(path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _coord_key(lat: float, lon: float) -> str:
    return f"{lat:.4f},{lon:.4f}"


def _configure_osmnx():
    import osmnx as ox

    ox.settings.use_cache = True
    ox.settings.cache_folder = str(CACHE_DIR / "osmnx")
    ox.settings.timeout = 25
    ox.settings.user_agent = "HomeTruth/0.1 (educational buyer-side estimate)"
    (CACHE_DIR / "osmnx").mkdir(parents=True, exist_ok=True)
    return ox


def geocode_place(query: str) -> tuple[float, float] | None:
    key = " ".join(query.strip().casefold().split())
    cache = _read_cache(_GEOCODE_PATH)
    if key in cache:
        lat, lon = cache[key]
        return float(lat), float(lon)
    ox = _configure_osmnx()
    try:
        lat, lon = ox.geocode(query)
    except Exception:
        logger.exception("geocode failed for %s", query)
        return None
    if lat is None or lon is None:
        return None
    cache[key] = [float(lat), float(lon)]
    _write_cache(_GEOCODE_PATH, cache)
    return float(lat), float(lon)


def _place_query(name: str) -> str:
    folded = name.casefold()
    if "bengaluru" in folded or "bangalore" in folded:
        return name
    return f"{name}, Bengaluru, Karnataka, India"


def _nearest_and_count(gdf, lat: float, lon: float) -> dict:
    if gdf is None or len(gdf) == 0:
        return {"count": 0, "nearest_m": None}
    nearest = None
    count = 0
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            continue
        point = geom if geom.geom_type == "Point" else geom.representative_point()
        distance = haversine_m(lat, lon, float(point.y), float(point.x))
        if distance <= LOCALITY_RADIUS_M:
            count += 1
            nearest = distance if nearest is None else min(nearest, distance)
    return {"count": count, "nearest_m": nearest}


def _is_metro(row) -> bool:
    station = str(row.get("station", "")).casefold()
    network = str(row.get("network", "")).casefold()
    name = str(row.get("name", "")).casefold()
    subway = str(row.get("subway", "")).casefold()
    return station == "subway" or subway in {"yes", "true"} or "metro" in network or "metro" in name or "namma" in name


def _is_it_park(row) -> bool:
    office = str(row.get("office", "")).casefold()
    name = str(row.get("name", "")).casefold()
    if office == "it":
        return True
    markers = ("tech park", "it park", "techpark", "techno park", "business park", "itpl", "manyata")
    return any(marker in name for marker in markers)


def _query_features(ox, lat: float, lon: float, tags: dict):
    try:
        gdf = ox.features_from_point((lat, lon), tags, dist=LOCALITY_RADIUS_M)
    except Exception:
        logger.exception("OSM feature query failed for %s", tags)
        return None
    if gdf is None or len(gdf) == 0:
        return None
    return gdf


def _filter_features(gdf, predicate):
    if gdf is None or len(gdf) == 0:
        return gdf
    keep = [predicate(row) for _, row in gdf.iterrows()]
    return gdf.iloc[[index for index, flag in enumerate(keep) if flag]]


def _fetch_components(lat: float, lon: float) -> dict[str, dict]:
    ox = _configure_osmnx()
    schools = _query_features(ox, lat, lon, {"amenity": "school"})
    hospitals = _query_features(ox, lat, lon, {"amenity": "hospital"})
    stations = _filter_features(_query_features(ox, lat, lon, {"railway": "station"}), _is_metro)
    offices = _filter_features(_query_features(ox, lat, lon, {"office": ["it", "company"]}), _is_it_park)
    return {
        "metro": _nearest_and_count(stations, lat, lon),
        "schools": _nearest_and_count(schools, lat, lon),
        "hospitals": _nearest_and_count(hospitals, lat, lon),
        "it_parks": _nearest_and_count(offices, lat, lon),
    }


def _route_length_m(graph, route: list) -> float:
    total = 0.0
    for start, end in zip(route[:-1], route[1:], strict=True):
        edges = graph.get_edge_data(start, end)
        if not edges:
            continue
        total += min(float(data.get("length", 0.0)) for data in edges.values())
    return total


def _commute_km(origin: tuple[float, float], destination: tuple[float, float]) -> float | None:
    ox = _configure_osmnx()
    straight = haversine_m(origin[0], origin[1], destination[0], destination[1])
    dist = min(max(straight * 1.4, 2_000), 12_000)
    midpoint = ((origin[0] + destination[0]) / 2, (origin[1] + destination[1]) / 2)
    graph = ox.graph_from_point(midpoint, dist=dist, network_type="drive", simplify=True)
    origin_node = ox.distance.nearest_nodes(graph, X=origin[1], Y=origin[0])
    dest_node = ox.distance.nearest_nodes(graph, X=destination[1], Y=destination[0])
    route = ox.routing.shortest_path(graph, origin_node, dest_node, weight="length")
    if not route or len(route) < 2:
        return None
    return _route_length_m(graph, route) / 1000


def _score_note(has_commute: bool, office_provided: bool) -> str:
    weights = ", ".join(f"{name.replace('_', ' ')} {weight}" for name, weight in LOCALITY_WEIGHTS.items())
    text = (
        f"Locality score weights: {weights}. "
        "Each part is a 0–100 score from how many places sit inside 2 km and how close the nearest one is. "
    )
    if has_commute:
        text += f"Commute uses the shortest road path at {COMMUTE_SPEED_KMH:.0f} km/h and excludes live traffic."
    elif office_provided:
        text += "A road path to the office could not be built, so there is no commute time. Live traffic is not included either way."
    else:
        text += "No office address was entered, so there is no commute time."
    return text


def _location_uncached(locality: str, office_address: str | None) -> LocationResult:
    import socket

    socket.setdefaulttimeout(20)
    origin = geocode_place(_place_query(locality))
    if origin is None:
        return LocationResult(available=False, note=_UNAVAILABLE)
    lat, lon = origin
    key = _coord_key(lat, lon)
    score_cache = _read_cache(_SCORE_PATH)
    if key in score_cache:
        components = score_cache[key]
    else:
        components = _fetch_components(lat, lon)
        score_cache[key] = components
        _write_cache(_SCORE_PATH, score_cache)
    part_scores = {
        name: component_score(int(components[name]["count"]), components[name]["nearest_m"])
        for name in LOCALITY_WEIGHTS
    }
    built = {
        name: LocationComponent(
            count=int(components[name]["count"]),
            nearest_m=None if components[name]["nearest_m"] is None else float(components[name]["nearest_m"]),
            score=part_scores[name],
        )
        for name in LOCALITY_WEIGHTS
    }
    commute_km = None
    office = (office_address or "").strip()
    if office:
        destination = geocode_place(_place_query(office))
        if destination is not None:
            commute_key = f"{key}|{_coord_key(*destination)}"
            commute_cache = _read_cache(_COMMUTE_PATH)
            if commute_key in commute_cache:
                commute_km = commute_cache[commute_key]
            else:
                try:
                    commute_km = _commute_km(origin, destination)
                except Exception:
                    logger.exception("commute failed")
                    commute_km = None
                if commute_km is not None:
                    commute_cache[commute_key] = commute_km
                    _write_cache(_COMMUTE_PATH, commute_cache)
    minutes = None if commute_km is None else commute_km / COMMUTE_SPEED_KMH * 60
    return LocationResult(
        available=True,
        locality_score=combine_location_scores(part_scores),
        components=built,
        weights=dict(LOCALITY_WEIGHTS),
        commute_km=commute_km,
        commute_minutes=minutes,
        commute_speed_kmh=COMMUTE_SPEED_KMH if commute_km is not None else None,
        latitude=lat,
        longitude=lon,
        note=_score_note(commute_km is not None, bool(office)),
    )


def location_for(locality: str, office_address: str | None = None) -> LocationResult:
    """Return scores, or a clear unavailable result if OSM or geocoding fails.

    The pool is shut down without waiting. Otherwise a timed-out Overpass call
    would keep the request blocked until the network call itself returned.
    """
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_location_uncached, locality, office_address)
    try:
        return future.result(timeout=_LOCATION_TIMEOUT_SECONDS)
    except FuturesTimeout:
        logger.warning("location lookup timed out for %s", locality)
        return LocationResult(available=False, note=_UNAVAILABLE)
    except Exception:
        logger.exception("location lookup failed")
        return LocationResult(available=False, note=_UNAVAILABLE)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
