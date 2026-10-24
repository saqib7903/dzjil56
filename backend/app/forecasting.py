"""Core selection logic: which forecast would a trader have seen?

For a target half hour ``t`` and a *cutoff* time ``c`` (the moment the
decision is made), the relevant forecast is the most recent one with
``publishTime <= c``. Two ways of choosing ``c`` are supported:

* fixed horizon ``h``:      c = t - h            (uniform lead time)
* day-ahead gate closure:   c = gate on day D-1  (what the desk actually trades on)

Forecasts with a lead time outside ``[0, max_horizon]`` are discarded up front.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import ForecastPoint

Cutoff = Callable[[datetime], datetime]


class ForecastIndex:
    """Forecasts grouped by target time, each group sorted by publish time."""

    def __init__(self, points: Iterable[ForecastPoint], max_horizon_hours: float) -> None:
        self.max_horizon = timedelta(hours=max_horizon_hours)
        grouped: dict[datetime, list[ForecastPoint]] = defaultdict(list)
        for point in points:
            lead = point.start_time - point.publish_time
            if timedelta(0) <= lead <= self.max_horizon:
                grouped[point.start_time].append(point)
        self._publish_times: dict[datetime, list[datetime]] = {}
        self._points: dict[datetime, list[ForecastPoint]] = {}
        for target, items in grouped.items():
            items.sort(key=lambda p: p.publish_time)
            self._points[target] = items
            self._publish_times[target] = [p.publish_time for p in items]

    def __len__(self) -> int:
        return sum(len(items) for items in self._points.values())

    @property
    def targets(self) -> list[datetime]:
        return sorted(self._points)

    def latest_before(self, target: datetime, cutoff: datetime) -> ForecastPoint | None:
        publish_times = self._publish_times.get(target)
        if not publish_times:
            return None
        idx = bisect_right(publish_times, cutoff) - 1
        return self._points[target][idx] if idx >= 0 else None

    def publish_times_for(self, target: datetime) -> list[datetime]:
        return list(self._publish_times.get(target, ()))


def horizon_cutoff(horizon_hours: float) -> Cutoff:
    lead = timedelta(hours=horizon_hours)
    return lambda target: target - lead


def gate_closure_utc(delivery_day: date, gate: time, tz: ZoneInfo) -> datetime:
    """Gate closure (local wall-clock ``gate`` on the day before delivery) in UTC."""
    local = datetime.combine(delivery_day - timedelta(days=1), gate, tzinfo=tz)
    return local.astimezone(timezone.utc)


def delivery_day_bounds(delivery_day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """UTC [start, end) of a local delivery day (handles 23h/25h clock-change days)."""
    start = datetime.combine(delivery_day, time(0), tzinfo=tz).astimezone(timezone.utc)
    end = datetime.combine(delivery_day + timedelta(days=1), time(0), tzinfo=tz).astimezone(timezone.utc)
    return start, end


@dataclass(frozen=True, slots=True)
class AlignedPoint:
    time: datetime
    actual: float | None
    forecast: ForecastPoint | None

    @property
    def is_pair(self) -> bool:
        return self.actual is not None and self.forecast is not None


def half_hours(start: datetime, end: datetime) -> list[datetime]:
    step = timedelta(minutes=30)
    # Snap the first slot up to the half-hour grid.
    minutes = start.minute % 30
    cursor = start.replace(second=0, microsecond=0)
    if minutes or start.second or start.microsecond:
        cursor += timedelta(minutes=30 - minutes)
    out: list[datetime] = []
    while cursor < end:
        out.append(cursor)
        cursor += step
    return out


def align(
    actuals: Mapping[datetime, float],
    index: ForecastIndex,
    start: datetime,
    end: datetime,
    cutoff: Cutoff,
) -> list[AlignedPoint]:
    """Actual and selected forecast for every half hour in ``[start, end)``."""
    return [
        AlignedPoint(time=t, actual=actuals.get(t), forecast=index.latest_before(t, cutoff(t)))
        for t in half_hours(start, end)
    ]
