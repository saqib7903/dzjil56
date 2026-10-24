"""HTTP routes. All timestamps are ISO-8601; naive values are treated as UTC."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from . import analytics, schemas
from .config import Settings, get_settings
from .store import DataUnavailableError, WindDataset, WindDataStore

router = APIRouter(prefix="/api")


def get_store(request: Request) -> WindDataStore:
    return request.app.state.store


def get_dataset(store: Annotated[WindDataStore, Depends(get_store)]) -> WindDataset:
    try:
        return store.get()
    except DataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Wind data is temporarily unavailable: {exc}") from exc


SettingsDep = Annotated[Settings, Depends(get_settings)]
DatasetDep = Annotated[WindDataset, Depends(get_dataset)]


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _window(settings: Settings, start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    start = _utc(start) if start else settings.window_start
    end = _utc(end) if end else settings.window_end
    if start >= end:
        raise HTTPException(status_code=422, detail="'start' must be earlier than 'end'.")
    if start < settings.window_start or end > settings.window_end:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Requested range must lie within {settings.window_start:%Y-%m-%d %H:%M} and "
                f"{settings.window_end:%Y-%m-%d %H:%M} UTC."
            ),
        )
    return start, end


def _gate(value: str | None, settings: Settings) -> time:
    raw = value or settings.default_gate_closure
    try:
        return time.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="'gate' must be a local time in HH:MM format.") from exc


@router.get("/health", response_model=schemas.Health)
def health() -> schemas.Health:
    return schemas.Health(status="ok")


@router.get("/meta", response_model=schemas.MetaResponse)
def meta(settings: SettingsDep, ds: DatasetDep) -> schemas.MetaResponse:
    days = analytics.delivery_days(settings)
    return schemas.MetaResponse(
        window_start=settings.window_start,
        window_end=settings.window_end,
        first_delivery_date=days[0],
        last_delivery_date=days[-1],
        max_horizon_hours=settings.max_horizon_hours,
        default_gate_closure=settings.default_gate_closure,
        market_timezone=settings.market_timezone,
        data_source=ds.source,
        loaded_at=ds.loaded_at,
        actual_count=len(ds.actuals),
        forecast_count=ds.raw_forecast_count,
    )


@router.get("/generation", response_model=schemas.GenerationResponse)
def generation(
    settings: SettingsDep,
    ds: DatasetDep,
    start: Annotated[datetime | None, Query(description="Inclusive start of the target window")] = None,
    end: Annotated[datetime | None, Query(description="Exclusive end of the target window")] = None,
    horizon: Annotated[float, Query(ge=0, description="Minimum forecast lead time in hours")] = 4.0,
) -> schemas.GenerationResponse:
    if horizon > settings.max_horizon_hours:
        raise HTTPException(status_code=422, detail=f"'horizon' must be at most {settings.max_horizon_hours:g} hours.")
    start, end = _window(settings, start, end)
    return analytics.generation_view(ds, settings, start, end, horizon)


@router.get("/accuracy/horizons", response_model=schemas.HorizonCurveResponse)
def accuracy_by_horizon(
    settings: SettingsDep,
    ds: DatasetDep,
    start: datetime | None = None,
    end: datetime | None = None,
    step: Annotated[float, Query(ge=0.5, le=12)] = 1.0,
) -> schemas.HorizonCurveResponse:
    start, end = _window(settings, start, end)
    return analytics.horizon_curve(ds, start, end, settings.max_horizon_hours, step)


@router.get("/day-ahead", response_model=schemas.DayAheadResponse)
def day_ahead(
    settings: SettingsDep,
    ds: DatasetDep,
    delivery_date: Annotated[date, Query(alias="date", description="Delivery day (market local date)")],
    gate: Annotated[str | None, Query(description="Gate closure on D-1, local HH:MM")] = None,
) -> schemas.DayAheadResponse:
    days = analytics.delivery_days(settings)
    if not days[0] <= delivery_date <= days[-1]:
        raise HTTPException(status_code=422, detail=f"'date' must be between {days[0]} and {days[-1]}.")
    return analytics.day_ahead_view(ds, settings, delivery_date, _gate(gate, settings))


@router.get("/accuracy/daily", response_model=schemas.DailyAccuracyResponse)
def accuracy_daily(settings: SettingsDep, ds: DatasetDep, gate: str | None = None) -> schemas.DailyAccuracyResponse:
    return analytics.daily_accuracy(ds, settings, _gate(gate, settings))
