"""Geographic helpers — GPS radius checks (F-CONQ-01) and abuse speed math (F-CONQ-09)."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in meters."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def is_within_radius(
    lat1: float, lng1: float, lat2: float, lng2: float, radius_m: float
) -> bool:
    return haversine_m(lat1, lng1, lat2, lng2) <= radius_m


def bounding_box(
    lat: float, lng: float, radius_m: float
) -> tuple[float, float, float, float]:
    """Rough lat/lng box for a first-pass SQL filter before exact haversine.

    Returns (min_lat, max_lat, min_lng, max_lng).
    """
    lat_delta = math.degrees(radius_m / EARTH_RADIUS_M)
    lng_delta = math.degrees(
        radius_m / (EARTH_RADIUS_M * math.cos(math.radians(lat)) or 1e-9)
    )
    return lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta


def speed_kmh(
    lat1: float, lng1: float, lat2: float, lng2: float, seconds: float
) -> float:
    if seconds <= 0:
        return math.inf
    meters = haversine_m(lat1, lng1, lat2, lng2)
    return (meters / seconds) * 3.6
