"""
Defines core models of the service.
"""

import argparse
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


@dataclass(kw_only=True)
class SpeedtestConfig:
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


@dataclass(kw_only=True)
class RunContext:
    # Execution modes
    list_servers_only: bool
    debug_mode: bool
    is_quiet: bool

    # Test parameters
    target_server_id: int | None
    no_download: bool
    no_upload: bool
    threads: int

    # Output
    share: bool
    json_output: bool
    units: tuple[str, int]  # e.g., ("bit", 1) or ("byte", 8)

    # Connection options
    # source_ip: str | None = None
    # timeout: float = 10.0

    # API payload
    api_config: SpeedtestConfig | None = None

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "RunContext":
        """
        Consumes the raw argparse namespace and reconciles the final application state.
        """

        if args.single:
            threads = 1
        elif getattr(args, "threads", None) is not None:
            threads = args.threads
        else:
            threads = 4

        return cls(
            list_servers_only=args.list,
            debug_mode=args.debug,
            is_quiet=args.json,
            target_server_id=args.server,
            no_download=args.no_download,
            no_upload=args.no_upload,
            threads=threads,
            share=args.share,
            json_output=args.json,
            units=args.units,
            # source_ip=getattr(args, "source", None),
            # timeout=getattr(args, "timeout", 10.0),
        )


@dataclass(kw_only=True)
class TestResult:
    # Populated after ping phase
    server: Server | None = None
    ping_ms: float | None = None

    # Populated after transfer phases
    download_bps: float | None = None
    download_bytes: int | None = None

    upload_bps: float | None = None
    upload_bytes: int | None = None

    share_url: str | None = None

    @property
    def is_complete(self) -> bool:
        """Helper to check if all tests ran."""

        return all(x is not None for x in (self.ping_ms, self.download_bps, self.upload_bps))
