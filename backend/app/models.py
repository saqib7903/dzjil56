"""Domain records shared by the data layer and the analytics layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ActualPoint:
    """Outturn wind generation (MW) for the half hour starting at ``start_time``."""

    start_time: datetime
    generation: float


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    """A wind forecast (MW) for ``start_time`` issued at ``publish_time``."""

    start_time: datetime
    publish_time: datetime
    generation: float

    @property
    def horizon_hours(self) -> float:
        return (self.start_time - self.publish_time).total_seconds() / 3600.0
