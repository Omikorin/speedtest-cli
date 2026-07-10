from dataclasses import dataclass
from typing import Any, Self

from .server import Location, Server


@dataclass(kw_only=True)
class ApiConfig:
    ip_address: str
    isp_name: str
    isp_id: int
    guid: str
    token: str
    location: Location
    servers: list[Server]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            ip_address=data["ipAddress"],
            isp_name=data["ispName"],
            isp_id=int(data["ispId"]),
            guid=data["guid"],
            token=data["clientAuth"]["token"],
            location=Location.from_dict(data["location"]),
            servers=[Server.from_dict(s) for s in data.get("servers", [])],
        )
