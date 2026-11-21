"""
Tests for the geographic helpers.
"""

import pytest
from speedtest.api.geo import great_circle_km


def test_same_point_is_zero() -> None:
    assert great_circle_km(52.37, 4.89, 52.37, 4.89) == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("origin", "destination", "expected_km"),
    [
        # Published great-circle distances between city centres.
        ((51.5074, -0.1278), (48.8566, 2.3522), 344),  # London -> Paris
        ((40.7128, -74.0060), (34.0522, -118.2437), 3936),  # New York -> Los Angeles
        ((35.6762, 139.6503), (43.0618, 141.3545), 832),  # Tokyo -> Sapporo
        ((-33.8688, 151.2093), (51.5074, -0.1278), 16993),  # Sydney -> London
    ],
)
def test_matches_known_city_distances(
    origin: tuple[float, float], destination: tuple[float, float], expected_km: float
) -> None:
    assert great_circle_km(*origin, *destination) == pytest.approx(expected_km, rel=0.01)


def test_distance_is_symmetric() -> None:
    forward = great_circle_km(51.5074, -0.1278, 35.6762, 139.6503)
    backward = great_circle_km(35.6762, 139.6503, 51.5074, -0.1278)

    assert forward == pytest.approx(backward)


def test_antipodal_points_do_not_raise() -> None:
    """Rounding can push the haversine term slightly above 1; that must not crash asin."""

    assert great_circle_km(0.0, 0.0, 0.0, 180.0) == pytest.approx(20015, rel=0.001)


def test_crossing_the_antimeridian_takes_the_short_way() -> None:
    assert great_circle_km(0.0, 179.0, 0.0, -179.0) == pytest.approx(222, rel=0.01)
