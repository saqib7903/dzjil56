"""Thin client for the Elexon Insights (BMRS) stream endpoints we depend on.

* FUELHH  - half-hourly outturn generation by fuel type (we keep WIND only)
* WINDFOR - national wind generation forecasts, one row per (publishTime, startTime)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .models import ActualPoint, ForecastPoint

log = logging.getLogger(__name__)

WIND_FUEL_TYPE = "WIND"


class ElexonError(RuntimeError):
    """Raised when Elexon cannot be reached or returns an unexpected payload."""


def parse_timestamp(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _chunks(start: datetime, end: datetime, size: timedelta) -> Iterator[tuple[datetime, datetime]]:
    cursor = start
    while cursor < end:
        upper = min(cursor + size, end)
        yield cursor, upper
        cursor = upper


class ElexonClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        chunk: timedelta = timedelta(days=7),
        max_retries: int = 3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._chunk = chunk
        self._max_retries = max_retries
        self._http = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ElexonClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------ http
    def _get(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._http.get(path, params=params)
                if response.status_code >= 500 or response.status_code == 429:
                    raise ElexonError(f"Elexon returned HTTP {response.status_code}")
                response.raise_for_status()
                payload = response.json()
                # Stream endpoints return a bare list; non-stream ones wrap it in {"data": [...]}.
                if isinstance(payload, dict):
                    payload = payload.get("data", [])
                if not isinstance(payload, list):
                    raise ElexonError("Unexpected response shape from Elexon")
                return payload
            except (httpx.HTTPError, ElexonError, ValueError) as exc:
                last_error = exc
                log.warning("Elexon %s attempt %d/%d failed: %s", path, attempt, self._max_retries, exc)
                if attempt < self._max_retries:
                    time.sleep(0.5 * 2 ** (attempt - 1))
        raise ElexonError(f"Failed to fetch {path}: {last_error}") from last_error

    # -------------------------------------------------------------- datasets
    def fetch_wind_actuals(self, start: datetime, end: datetime) -> list[ActualPoint]:
        """Wind outturn with ``start <= startTime < end``.

        FUELHH is filtered by settlement date, so we pad the request by a day on
        each side and trim on ``startTime`` afterwards. If a period was
        republished we keep the most recent value.
        """
        latest: dict[datetime, tuple[datetime, float]] = {}
        padded_start = (start - timedelta(days=1)).date()
        padded_end = (end + timedelta(days=1)).date()
        day = timedelta(days=1)
        cursor = padded_start
        while cursor <= padded_end:
            upper = min(cursor + self._chunk - day, padded_end)
            rows = self._get(
                "/datasets/FUELHH/stream",
                {
                    "settlementDateFrom": cursor.isoformat(),
                    "settlementDateTo": upper.isoformat(),
                    "fuelType": WIND_FUEL_TYPE,
                },
            )
            for row in rows:
                if row.get("fuelType") != WIND_FUEL_TYPE or row.get("generation") is None:
                    continue
                target = parse_timestamp(row["startTime"])
                if not (start <= target < end):
                    continue
                published = parse_timestamp(row.get("publishTime") or row["startTime"])
                previous = latest.get(target)
                if previous is None or published >= previous[0]:
                    latest[target] = (published, float(row["generation"]))
            cursor = upper + day
        return [ActualPoint(t, g) for t, (_, g) in sorted(latest.items())]

    def fetch_wind_forecasts(self, publish_from: datetime, publish_to: datetime) -> list[ForecastPoint]:
        """All WINDFOR rows published in ``[publish_from, publish_to)``."""
        unique: dict[tuple[datetime, datetime], float] = {}
        for lower, upper in _chunks(publish_from, publish_to, self._chunk):
            rows = self._get(
                "/datasets/WINDFOR/stream",
                {"publishDateTimeFrom": _iso(lower), "publishDateTimeTo": _iso(upper)},
            )
            for row in rows:
                if row.get("generation") is None:
                    continue
                published = parse_timestamp(row["publishTime"])
                if not (publish_from <= published < publish_to):
                    continue
                unique[(parse_timestamp(row["startTime"]), published)] = float(row["generation"])
        return [ForecastPoint(start_time=s, publish_time=p, generation=g) for (s, p), g in sorted(unique.items())]
