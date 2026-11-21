from dataclasses import dataclass
from typing import Any, Self


@dataclass(kw_only=True)
class Location:
    latitude: float
    longitude: float
    city_name: str
    country_code: str
    country_name: str
    region_code: str
    region_name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            city_name=data["cityName"],
            country_code=data["countryCode"],
            country_name=data["countryName"],
            region_code=data["regionCode"],
            region_name=data["regionName"],
        )
