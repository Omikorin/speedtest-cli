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


@dataclass(kw_only=True)
class Server:
    id: int
    name: str
    sponsor: str
    country: str
    cc: str
    host: str
    url: str
    lat: float
    lon: float
    distance: int
    preferred: bool
    isp_id: int
    https_functional: bool
    force_ping_select: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            id=int(data["id"]),
            name=data["name"],
            sponsor=data["sponsor"],
            country=data["country"],
            cc=data["cc"],
            host=data["host"],
            url=data["url"],
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            distance=int(data["distance"]),
            preferred=bool(data.get("preferred", 0)),
            isp_id=int(data["isp_id"]),
            https_functional=bool(data.get("https_functional", 0)),
            force_ping_select=bool(data.get("force_ping_select", 0)),
        )
