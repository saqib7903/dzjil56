"""Read/write the bundled data snapshot (gzipped JSON).

The analysis window is historical, so shipping a snapshot makes the app fast,
reproducible and independent of Elexon availability. ``scripts/fetch_snapshot.py``
regenerates it from the live API.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .elexon import parse_timestamp
from .models import ActualPoint, ForecastPoint

SNAPSHOT_FILENAME = "wind_snapshot.json.gz"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Snapshot:
    fetched_at: datetime
    actuals: list[ActualPoint]
    forecasts: list[ForecastPoint]


def snapshot_path(directory: Path) -> Path:
    return directory / SNAPSHOT_FILENAME


def write_snapshot(
    path: Path,
    actuals: list[ActualPoint],
    forecasts: list[ForecastPoint],
    fetched_at: datetime,
    source: str,
) -> None:
    payload = {
        "source": source,
        "fetchedAt": _iso(fetched_at),
        "actualsColumns": ["startTime", "generation"],
        "actuals": [[_iso(a.start_time), a.generation] for a in actuals],
        "forecastsColumns": ["publishTime", "startTime", "generation"],
        "forecasts": [[_iso(f.publish_time), _iso(f.start_time), f.generation] for f in forecasts],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))


def read_snapshot(path: Path) -> Snapshot:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    return Snapshot(
        fetched_at=parse_timestamp(payload["fetchedAt"]),
        actuals=[ActualPoint(parse_timestamp(t), float(g)) for t, g in payload["actuals"]],
        forecasts=[
            ForecastPoint(start_time=parse_timestamp(s), publish_time=parse_timestamp(p), generation=float(g))
            for p, s, g in payload["forecasts"]
        ],
    )
