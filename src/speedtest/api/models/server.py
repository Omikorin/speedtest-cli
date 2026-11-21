from dataclasses import dataclass
from typing import Any, Self


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
            preferred=bool(data.get("preferred")),
            isp_id=int(data["isp_id"]),
            https_functional=bool(data.get("https_functional")),
            force_ping_select=bool(data.get("force_ping_select")),
        )
