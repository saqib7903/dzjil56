from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.models import ActualPoint, ForecastPoint  # noqa: E402
from app.snapshot import snapshot_path, write_snapshot  # noqa: E402

UTC = timezone.utc
START = datetime(2026, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 4, tzinfo=UTC)


def synthetic_data() -> tuple[list[ActualPoint], list[ForecastPoint]]:
    """Actual = 1000 MW flat. Each forecast run over-forecasts by its lead time
    in hours (x10 MW), so the error grows with horizon in a known way."""
    actuals = []
    t = START
    while t < END:
        actuals.append(ActualPoint(t, 1000.0))
        t += timedelta(minutes=30)
    forecasts = []
    publish = START - timedelta(hours=48)
    while publish < END:
        for step in range(0, 49):
            target = publish + timedelta(hours=step)
            if START <= target < END:
                forecasts.append(ForecastPoint(target, publish, 1000.0 + 10.0 * step))
        publish += timedelta(hours=3)
    return actuals, forecasts


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        window_start=START,
        window_end=END,
        data_source="snapshot",
        snapshot_dir=tmp_path,
    )


@pytest.fixture
def snapshot_settings(settings: Settings) -> Settings:
    actuals, forecasts = synthetic_data()
    write_snapshot(snapshot_path(settings.snapshot_dir), actuals, forecasts, START, "test")
    return settings
