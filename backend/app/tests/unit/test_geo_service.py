import math

from app.services.geo_service import (
    bounding_box,
    haversine_m,
    is_within_radius,
    speed_kmh,
)


def test_haversine_zero_distance() -> None:
    assert haversine_m(37.5, 127.0, 37.5, 127.0) == 0


def test_haversine_known_distance() -> None:
    # Seoul City Hall -> Gangnam Station, ~8.5km as the crow flies.
    d = haversine_m(37.5663, 126.9779, 37.4979, 127.0276)
    assert 8000 < d < 9500


def test_is_within_radius() -> None:
    # ~30m north
    assert is_within_radius(37.56430, 126.9770, 37.5642, 126.9770, 50)
    assert not is_within_radius(37.5652, 126.9770, 37.5642, 126.9770, 50)


def test_bounding_box_contains_point() -> None:
    min_lat, max_lat, min_lng, max_lng = bounding_box(37.5, 127.0, 1000)
    assert min_lat < 37.5 < max_lat
    assert min_lng < 127.0 < max_lng


def test_speed_kmh() -> None:
    assert speed_kmh(37.5, 127.0, 37.5, 127.0, 0) == math.inf
    v = speed_kmh(37.5663, 126.9779, 37.4979, 127.0276, 3600)
    assert 8 < v < 10
