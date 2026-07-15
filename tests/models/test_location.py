"""
Tests for the Location domain model.
"""

import pytest
from speedtest.models import Location


def test_location_from_dict() -> None:
    """Test that Location correctly parses and casts dictionary data."""

    raw_api_data = {
        "latitude": "40.0",
        "longitude": "-74.0",
        "cityName": "New York",
        "countryCode": "US",
        "countryName": "United States",
        "regionCode": "NY",
        "regionName": "New York",
    }

    location = Location.from_dict(raw_api_data)

    assert location.latitude == pytest.approx(40.0)
    assert location.longitude == pytest.approx(-74.0)
    assert location.city_name == "New York"
    assert location.country_code == "US"
    assert location.country_name == "United States"
    assert location.region_code == "NY"
    assert location.region_name == "New York"

    assert isinstance(location.latitude, float)
    assert isinstance(location.longitude, float)


def test_location_from_dict_with_float_inputs() -> None:
    """Test that from_dict works even if the lat/lon are already floats."""

    raw_api_data = {
        "latitude": 51.5074,
        "longitude": -0.1278,
        "cityName": "London",
        "countryCode": "GB",
        "countryName": "United Kingdom",
        "regionCode": "ENG",
        "regionName": "England",
    }

    location = Location.from_dict(raw_api_data)

    assert location.latitude == pytest.approx(51.5074)
    assert location.longitude == pytest.approx(-0.1278)
    assert location.city_name == "London"
