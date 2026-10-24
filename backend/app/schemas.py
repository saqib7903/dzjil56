"""API response models (serialised as camelCase JSON)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ErrorStats(ApiModel):
    count: int
    mean_actual: float | None = None
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    wape_pct: float | None = None
    p50_abs_error: float | None = None
    p90_abs_error: float | None = None
    p99_abs_error: float | None = None
    max_abs_error: float | None = None
    residual_p10: float | None = None
    residual_p90: float | None = None


class SeriesPoint(ApiModel):
    time: datetime
    actual: float | None
    forecast: float | None
    forecast_publish_time: datetime | None
    horizon_hours: float | None
    band_low: float | None = None
    band_high: float | None = None


class Band(ApiModel):
    """Empirical P10-P90 residual band applied around the forecast."""

    residual_p10: float | None
    residual_p90: float | None
    sample_size: int
    basis: str


class HourlyError(ApiModel):
    hour: int  # local (market) hour of day
    mae: float | None
    bias: float | None
    count: int


class GenerationResponse(ApiModel):
    start: datetime
    end: datetime
    horizon_hours: float
    points: list[SeriesPoint]
    summary: ErrorStats
    band: Band
    hourly: list[HourlyError]


class HorizonAccuracy(ApiModel):
    horizon_hours: float
    count: int
    mae: float | None
    rmse: float | None
    bias: float | None
    p90_abs_error: float | None


class HorizonCurveResponse(ApiModel):
    start: datetime
    end: datetime
    points: list[HorizonAccuracy]


class DayAheadEnergy(ApiModel):
    hours: float
    forecast_mwh: float | None
    actual_mwh: float | None
    error_mwh: float | None
    # Daily-energy view across every delivery day in the window under the same gate rule.
    firm_wind_p10_mwh: float | None
    upside_wind_p90_mwh: float | None
    daily_residual_p10_mwh: float | None
    daily_residual_p90_mwh: float | None
    days_in_sample: int


class DayAheadResponse(ApiModel):
    delivery_date: date
    gate_closure_local: str
    gate_closure_utc: datetime
    forecast_publish_time: datetime | None
    points: list[SeriesPoint]
    summary: ErrorStats
    band: Band
    energy: DayAheadEnergy


class DailyAccuracy(ApiModel):
    delivery_date: date
    forecast_mwh: float | None
    actual_mwh: float | None
    error_mwh: float | None
    mae: float | None
    count: int


class DailyAccuracyResponse(ApiModel):
    gate_closure_local: str
    days: list[DailyAccuracy]
    summary: ErrorStats


class MetaResponse(ApiModel):
    window_start: datetime
    window_end: datetime
    first_delivery_date: date
    last_delivery_date: date
    max_horizon_hours: float
    default_gate_closure: str
    market_timezone: str
    data_source: str
    loaded_at: datetime
    actual_count: int
    forecast_count: int
    actual_resolution_minutes: int = 30
    forecast_resolution_minutes: int = 60


class Health(ApiModel):
    status: str
