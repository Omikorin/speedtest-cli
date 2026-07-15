from dataclasses import dataclass

from .server import Server


@dataclass(kw_only=True)
class SpeedtestResult:
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

    def _convert_speed(self, speed_bps: float | None, unit_divisor: int) -> float | None:
        """Convert speed from bits per second to the requested unit (e.g., Mega/s)."""

        if speed_bps is None:
            return None
        return (speed_bps / 1_000_000) / unit_divisor

    def get_download_speed(self, unit_divisor: int) -> float | None:
        """Get the download speed formatted to the requested unit divisor."""

        return self._convert_speed(self.download_bps, unit_divisor)

    def get_upload_speed(self, unit_divisor: int) -> float | None:
        """Get the upload speed formatted to the requested unit divisor."""

        return self._convert_speed(self.upload_bps, unit_divisor)

    def get_downloaded_megabytes(self) -> float | None:
        """Get the total downloaded data MB."""

        if self.download_bytes is None:
            return None

        return self.download_bytes / 1_000_000

    def get_uploaded_megabytes(self) -> float | None:
        """Get the total uploaded data in MB."""

        if self.upload_bytes is None:
            return None

        return self.upload_bytes / 1_000_000
