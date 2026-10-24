from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.forecasting import (
    ForecastIndex,
    align,
    delivery_day_bounds,
    gate_closure_utc,
    half_hours,
    horizon_cutoff,
)
from app.models import ForecastPoint

UTC = timezone.utc
LONDON = ZoneInfo("Europe/London")
T = datetime(2026, 1, 10, 12, tzinfo=UTC)


def fc(hours_before: float, value: float, target: datetime = T) -> ForecastPoint:
    return ForecastPoint(target, target - timedelta(hours=hours_before), value)


def test_index_drops_forecasts_outside_horizon_limits():
    index = ForecastIndex([fc(-1, 1), fc(0, 2), fc(48, 3), fc(49, 4)], max_horizon_hours=48)
    assert len(index) == 2
    assert index.latest_before(T, T).generation == 2


def test_latest_before_picks_most_recent_publish_at_or_before_cutoff():
    index = ForecastIndex([fc(30, 30), fc(10, 10), fc(4, 4), fc(1, 1)], 48)
    assert index.latest_before(T, T - timedelta(hours=4)).generation == 4  # inclusive boundary
    assert index.latest_before(T, T - timedelta(hours=5)).generation == 10
    assert index.latest_before(T, T - timedelta(hours=31)) is None
    assert index.latest_before(T + timedelta(hours=1), T) is None  # unknown target


def test_horizon_cutoff_applies_lead_time_per_target():
    index = ForecastIndex([fc(6, 6), fc(2, 2)], 48)
    points = align({T: 1.0}, index, T, T + timedelta(minutes=30), horizon_cutoff(3))
    assert len(points) == 1
    assert points[0].forecast.generation == 6
    assert points[0].is_pair


def test_gate_closure_is_previous_day_local_time():
    # Winter: London == UTC
    assert gate_closure_utc(date(2026, 1, 15), time(9, 50), LONDON) == datetime(2026, 1, 14, 9, 50, tzinfo=UTC)
    # Summer: BST is UTC+1
    assert gate_closure_utc(date(2026, 7, 15), time(9, 50), LONDON) == datetime(2026, 7, 14, 8, 50, tzinfo=UTC)


def test_delivery_day_bounds_handle_clock_changes():
    start, end = delivery_day_bounds(date(2026, 3, 29), LONDON)  # clocks go forward
    assert (end - start) == timedelta(hours=23)
    start, end = delivery_day_bounds(date(2026, 10, 25), LONDON)  # clocks go back
    assert (end - start) == timedelta(hours=25)


def test_half_hours_snaps_to_grid():
    slots = half_hours(datetime(2026, 1, 1, 0, 10, tzinfo=UTC), datetime(2026, 1, 1, 1, 30, tzinfo=UTC))
    assert slots == [datetime(2026, 1, 1, 0, 30, tzinfo=UTC), datetime(2026, 1, 1, 1, 0, tzinfo=UTC)]
