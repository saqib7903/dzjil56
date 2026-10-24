"""Runtime configuration, read once from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    # Delivery (target) window covered by the product. Purchase decisions made
    # during January 2026 are for delivery between 1 Jan and 1 Feb 2026.
    window_start: datetime = _parse_utc("2026-01-01T00:00:00Z")
    window_end: datetime = _parse_utc("2026-02-02T00:00:00Z")  # exclusive
    max_horizon_hours: float = 48.0
    # "auto" = use the bundled snapshot when present, otherwise call Elexon.
    data_source: str = "auto"
    snapshot_dir: Path = BACKEND_DIR / "data"
    cache_ttl_seconds: int = 6 * 60 * 60
    http_timeout_seconds: float = 30.0
    default_gate_closure: str = "09:50"  # N2EX GB day-ahead auction, UK local time
    market_timezone: str = "Europe/London"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    defaults = Settings()
    return Settings(
        elexon_base_url=os.getenv("ELEXON_BASE_URL", defaults.elexon_base_url).rstrip("/"),
        window_start=_parse_utc(os.getenv("WINDOW_START", defaults.window_start.isoformat())),
        window_end=_parse_utc(os.getenv("WINDOW_END", defaults.window_end.isoformat())),
        max_horizon_hours=float(os.getenv("MAX_HORIZON_HOURS", defaults.max_horizon_hours)),
        data_source=os.getenv("DATA_SOURCE", defaults.data_source).lower(),
        snapshot_dir=Path(os.getenv("SNAPSHOT_DIR", str(defaults.snapshot_dir))),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", defaults.cache_ttl_seconds)),
        http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", defaults.http_timeout_seconds)),
        default_gate_closure=os.getenv("DEFAULT_GATE_CLOSURE", defaults.default_gate_closure),
        market_timezone=os.getenv("MARKET_TIMEZONE", defaults.market_timezone),
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS", "*")),
    )
