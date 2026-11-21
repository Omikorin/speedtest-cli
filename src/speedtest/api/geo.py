"""
Geographic helpers.
"""

from math import asin, cos, radians, sin, sqrt

__all__ = ["great_circle_km"]

EARTH_RADIUS_KM = 6371.0088


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two coordinates, in kilometres."""

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2

    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(a)))
