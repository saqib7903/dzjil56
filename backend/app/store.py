"""Loads the wind dataset once and keeps it in memory.

Source selection (``DATA_SOURCE``):

* ``snapshot`` - bundled file only
* ``live``     - Elexon API, refreshed after ``CACHE_TTL_SECONDS``; falls back to
                 the snapshot if Elexon is unavailable
* ``auto``     - snapshot when present, otherwise live (default)
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .config import Settings
from .elexon import ElexonClient, ElexonError
from .forecasting import ForecastIndex
from .models import ActualPoint, ForecastPoint
from .snapshot import read_snapshot, snapshot_path

log = logging.getLogger(__name__)


class DataUnavailableError(RuntimeError):
    pass


@dataclass
class WindDataset:
    actuals: dict[datetime, float]
    forecasts: ForecastIndex
    source: str
    loaded_at: datetime
    raw_forecast_count: int
    _cache: dict = field(default_factory=dict, repr=False)

    def memo(self, key: tuple, compute: Callable[[], object]) -> object:
        """Small per-dataset memo for derived statistics (cleared on reload)."""
        if key not in self._cache:
            self._cache[key] = compute()
        return self._cache[key]


def build_dataset(
    actuals: list[ActualPoint],
    forecasts: list[ForecastPoint],
    settings: Settings,
    source: str,
    loaded_at: datetime | None = None,
) -> WindDataset:
    publish_floor = settings.window_start - timedelta(hours=settings.max_horizon_hours)
    in_window = [
        f
        for f in forecasts
        if settings.window_start <= f.start_time < settings.window_end and f.publish_time >= publish_floor
    ]
    return WindDataset(
        actuals={
            a.start_time: a.generation for a in actuals if settings.window_start <= a.start_time < settings.window_end
        },
        forecasts=ForecastIndex(in_window, settings.max_horizon_hours),
        source=source,
        loaded_at=loaded_at or datetime.now(timezone.utc),
        raw_forecast_count=len(in_window),
    )


class WindDataStore:
    def __init__(self, settings: Settings, client_factory: Callable[[], ElexonClient] | None = None) -> None:
        self._settings = settings
        self._client_factory = client_factory or (
            lambda: ElexonClient(settings.elexon_base_url, timeout=settings.http_timeout_seconds)
        )
        self._lock = threading.Lock()
        self._dataset: WindDataset | None = None
        self._expires_at = 0.0

    # ----------------------------------------------------------------- loaders
    def _load_snapshot(self) -> WindDataset:
        snap = read_snapshot(snapshot_path(self._settings.snapshot_dir))
        return build_dataset(snap.actuals, snap.forecasts, self._settings, "snapshot", snap.fetched_at)

    def _load_live(self) -> WindDataset:
        s = self._settings
        with self._client_factory() as client:
            actuals = client.fetch_wind_actuals(s.window_start, s.window_end)
            forecasts = client.fetch_wind_forecasts(s.window_start - timedelta(hours=s.max_horizon_hours), s.window_end)
        if not actuals or not forecasts:
            raise ElexonError("Elexon returned no data for the configured window")
        return build_dataset(actuals, forecasts, s, "live")

    def _load(self) -> tuple[WindDataset, float]:
        mode = self._settings.data_source
        has_snapshot = snapshot_path(self._settings.snapshot_dir).exists()
        never = float("inf")
        if mode == "snapshot" or (mode == "auto" and has_snapshot):
            if not has_snapshot:
                raise DataUnavailableError("DATA_SOURCE=snapshot but no snapshot file was found")
            return self._load_snapshot(), never
        try:
            return self._load_live(), time.monotonic() + self._settings.cache_ttl_seconds
        except ElexonError as exc:
            if has_snapshot:
                log.warning("Live load failed (%s); serving bundled snapshot", exc)
                # Try live again in a few minutes rather than pinning to the snapshot.
                return self._load_snapshot(), time.monotonic() + 300
            raise DataUnavailableError(str(exc)) from exc

    # ------------------------------------------------------------------ public
    def get(self) -> WindDataset:
        if self._dataset is not None and time.monotonic() < self._expires_at:
            return self._dataset
        with self._lock:
            if self._dataset is None or time.monotonic() >= self._expires_at:
                try:
                    self._dataset, self._expires_at = self._load()
                except DataUnavailableError:
                    if self._dataset is None:
                        raise
                    log.warning("Refresh failed; continuing with data loaded at %s", self._dataset.loaded_at)
                    self._expires_at = time.monotonic() + 300
            return self._dataset
