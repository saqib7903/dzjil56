"""Turns the raw dataset into the views served by the API."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from . import schemas
from .config import Settings
from .forecasting import (
    AlignedPoint,
    align,
    delivery_day_bounds,
    gate_closure_utc,
    horizon_cutoff,
)
from .metrics import ErrorSummary, percentile, summarize
from .store import WindDataset


def _r(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


def to_stats(summary: ErrorSummary) -> schemas.ErrorStats:
    return schemas.ErrorStats(
        count=summary.count,
        mean_actual=_r(summary.mean_actual),
        mae=_r(summary.mae),
        rmse=_r(summary.rmse),
        bias=_r(summary.bias),
        wape_pct=_r(summary.wape_pct, 2),
        p50_abs_error=_r(summary.p50_abs_error),
        p90_abs_error=_r(summary.p90_abs_error),
        p99_abs_error=_r(summary.p99_abs_error),
        max_abs_error=_r(summary.max_abs_error),
        residual_p10=_r(summary.residual_p10),
        residual_p90=_r(summary.residual_p90),
    )


def pairs_of(points: list[AlignedPoint]) -> list[tuple[float, float]]:
    return [(p.actual, p.forecast.generation) for p in points if p.is_pair]  # type: ignore[union-attr]


def to_series(points: list[AlignedPoint], band: schemas.Band | None = None) -> list[schemas.SeriesPoint]:
    out = []
    for p in points:
        fc = p.forecast
        low = high = None
        if fc is not None and band is not None and band.residual_p10 is not None:
            low = max(0.0, fc.generation + band.residual_p10)
            high = max(0.0, fc.generation + (band.residual_p90 or 0.0))
        out.append(
            schemas.SeriesPoint(
                time=p.time,
                actual=p.actual,
                forecast=fc.generation if fc else None,
                forecast_publish_time=fc.publish_time if fc else None,
                horizon_hours=_r((p.time - fc.publish_time).total_seconds() / 3600, 2) if fc else None,
                band_low=_r(low),
                band_high=_r(high),
            )
        )
    return out


def hourly_errors(points: list[AlignedPoint], tz: ZoneInfo) -> list[schemas.HourlyError]:
    buckets: dict[int, list[float]] = defaultdict(list)
    for p in points:
        if p.is_pair:
            buckets[p.time.astimezone(tz).hour].append(p.forecast.generation - p.actual)  # type: ignore[union-attr,operator]
    out = []
    for hour in range(24):
        errs = buckets.get(hour, [])
        out.append(
            schemas.HourlyError(
                hour=hour,
                mae=_r(sum(abs(e) for e in errs) / len(errs)) if errs else None,
                bias=_r(sum(errs) / len(errs)) if errs else None,
                count=len(errs),
            )
        )
    return out


# --------------------------------------------------------------- horizon view
def horizon_band(ds: WindDataset, settings: Settings, horizon: float) -> schemas.Band:
    """Residual spread for a given horizon across the whole delivery window."""

    def compute() -> schemas.Band:
        aligned = align(ds.actuals, ds.forecasts, settings.window_start, settings.window_end, horizon_cutoff(horizon))
        s = summarize(pairs_of(aligned))
        return schemas.Band(
            residual_p10=_r(s.residual_p10),
            residual_p90=_r(s.residual_p90),
            sample_size=s.count,
            basis=f"All January target periods at a {horizon:g}h minimum lead time",
        )

    return ds.memo(("horizon_band", horizon), compute)  # type: ignore[return-value]


def generation_view(
    ds: WindDataset, settings: Settings, start: datetime, end: datetime, horizon: float
) -> schemas.GenerationResponse:
    aligned = align(ds.actuals, ds.forecasts, start, end, horizon_cutoff(horizon))
    band = horizon_band(ds, settings, horizon)
    return schemas.GenerationResponse(
        start=start,
        end=end,
        horizon_hours=horizon,
        points=to_series(aligned, band),
        summary=to_stats(summarize(pairs_of(aligned))),
        band=band,
        hourly=hourly_errors(aligned, ZoneInfo(settings.market_timezone)),
    )


def horizon_curve(
    ds: WindDataset, start: datetime, end: datetime, max_horizon: float, step: float
) -> schemas.HorizonCurveResponse:
    points = []
    h = 0.0
    while h <= max_horizon + 1e-9:
        s = summarize(pairs_of(align(ds.actuals, ds.forecasts, start, end, horizon_cutoff(h))))
        points.append(
            schemas.HorizonAccuracy(
                horizon_hours=round(h, 2),
                count=s.count,
                mae=_r(s.mae),
                rmse=_r(s.rmse),
                bias=_r(s.bias),
                p90_abs_error=_r(s.p90_abs_error),
            )
        )
        h += step
    return schemas.HorizonCurveResponse(start=start, end=end, points=points)


# ------------------------------------------------------------- day-ahead view
def delivery_days(settings: Settings) -> list[date]:
    tz = ZoneInfo(settings.market_timezone)
    first = settings.window_start.astimezone(tz).date()
    last = (settings.window_end - timedelta(seconds=1)).astimezone(tz).date()
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def _day_points(ds: WindDataset, day: date, gate: time, tz: ZoneInfo) -> tuple[datetime, list[AlignedPoint]]:
    cutoff = gate_closure_utc(day, gate, tz)
    start, end = delivery_day_bounds(day, tz)
    return cutoff, align(ds.actuals, ds.forecasts, start, end, lambda _t: cutoff)


def day_energy(points: list[AlignedPoint]) -> tuple[float, float | None, float | None]:
    """(hours, forecast MWh, actual MWh) using mean MW x day length.

    Forecasts are hourly and actuals half-hourly, so averaging MW before
    multiplying by the day length compares like with like.
    """
    hours = len(points) * 0.5
    fc = [p.forecast.generation for p in points if p.forecast is not None]
    ac = [p.actual for p in points if p.actual is not None]
    return (
        hours,
        sum(fc) / len(fc) * hours if fc else None,
        sum(ac) / len(ac) * hours if ac else None,  # type: ignore[arg-type]
    )


def daily_records(ds: WindDataset, settings: Settings, gate: time) -> list[tuple[date, datetime, list[AlignedPoint]]]:
    tz = ZoneInfo(settings.market_timezone)

    def compute():
        return [(day, *_day_points(ds, day, gate, tz)) for day in delivery_days(settings)]

    return ds.memo(("daily", gate.isoformat()), compute)  # type: ignore[return-value]


def gate_band(ds: WindDataset, settings: Settings, gate: time) -> schemas.Band:
    def compute() -> schemas.Band:
        pairs = [pair for _, _, pts in daily_records(ds, settings, gate) for pair in pairs_of(pts)]
        s = summarize(pairs)
        return schemas.Band(
            residual_p10=_r(s.residual_p10),
            residual_p90=_r(s.residual_p90),
            sample_size=s.count,
            basis=f"All January delivery periods using the forecast available at {gate:%H:%M} on D-1",
        )

    return ds.memo(("gate_band", gate.isoformat()), compute)  # type: ignore[return-value]


def _daily_energy_errors(ds: WindDataset, settings: Settings, gate: time) -> list[float]:
    def compute() -> list[float]:
        errors = []
        for _, _, pts in daily_records(ds, settings, gate):
            _, fc, ac = day_energy(pts)
            if fc is not None and ac is not None:
                errors.append(ac - fc)
        return errors

    return ds.memo(("daily_energy_residuals", gate.isoformat()), compute)  # type: ignore[return-value]


def day_ahead_view(ds: WindDataset, settings: Settings, day: date, gate: time) -> schemas.DayAheadResponse:
    tz = ZoneInfo(settings.market_timezone)
    cutoff, points = _day_points(ds, day, gate, tz)
    band = gate_band(ds, settings, gate)
    hours, fc_mwh, ac_mwh = day_energy(points)
    residuals = _daily_energy_errors(ds, settings, gate)
    r10, r90 = percentile(residuals, 10), percentile(residuals, 90)
    publish_times = {p.forecast.publish_time for p in points if p.forecast is not None}
    day_start, day_end = delivery_day_bounds(day, tz)
    runs_from = day_start - timedelta(days=1)
    runs = sorted(
        {
            published
            for p in points
            for published in ds.forecasts.publish_times_for(p.time)
            if runs_from <= published < day_end
        }
    )
    return schemas.DayAheadResponse(
        delivery_date=day,
        gate_closure_local=gate.strftime("%H:%M"),
        gate_closure_utc=cutoff,
        forecast_publish_time=max(publish_times) if publish_times else None,
        forecast_runs=runs,
        points=to_series(points, band),
        summary=to_stats(summarize(pairs_of(points))),
        band=band,
        energy=schemas.DayAheadEnergy(
            hours=hours,
            forecast_mwh=_r(fc_mwh, 0),
            actual_mwh=_r(ac_mwh, 0),
            error_mwh=_r(fc_mwh - ac_mwh, 0) if fc_mwh is not None and ac_mwh is not None else None,
            firm_wind_p10_mwh=_r(max(0.0, fc_mwh + r10), 0) if fc_mwh is not None and r10 is not None else None,
            upside_wind_p90_mwh=_r(max(0.0, fc_mwh + r90), 0) if fc_mwh is not None and r90 is not None else None,
            daily_residual_p10_mwh=_r(r10, 0),
            daily_residual_p90_mwh=_r(r90, 0),
            days_in_sample=len(residuals),
        ),
    )


def daily_accuracy(ds: WindDataset, settings: Settings, gate: time) -> schemas.DailyAccuracyResponse:
    days = []
    all_pairs: list[tuple[float, float]] = []
    for day, _, pts in daily_records(ds, settings, gate):
        pairs = pairs_of(pts)
        all_pairs.extend(pairs)
        _, fc, ac = day_energy(pts)
        s = summarize(pairs)
        days.append(
            schemas.DailyAccuracy(
                delivery_date=day,
                forecast_mwh=_r(fc, 0),
                actual_mwh=_r(ac, 0),
                error_mwh=_r(fc - ac, 0) if fc is not None and ac is not None else None,
                mae=_r(s.mae),
                count=s.count,
            )
        )
    return schemas.DailyAccuracyResponse(
        gate_closure_local=gate.strftime("%H:%M"),
        days=days,
        summary=to_stats(summarize(all_pairs)),
    )
