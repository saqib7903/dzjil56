"""Forecast error statistics.

Sign convention: ``error = forecast - actual`` (positive = wind over-forecast,
i.e. the desk would be *short* if it trusted the forecast). ``residual`` is the
opposite, ``actual - forecast``, and is what we add to a forecast to build an
uncertainty band.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolated percentile (same definition as numpy's default)."""
    if not values:
        return None
    if not 0 <= q <= 100:
        raise ValueError("q must be within [0, 100]")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * q / 100.0
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


@dataclass(frozen=True)
class ErrorSummary:
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


def summarize(pairs: Sequence[tuple[float, float]]) -> ErrorSummary:
    """Summarise ``(actual, forecast)`` pairs."""
    if not pairs:
        return ErrorSummary(count=0)
    errors = [f - a for a, f in pairs]
    abs_errors = [abs(e) for e in errors]
    residuals = [-e for e in errors]
    n = len(pairs)
    total_actual = sum(a for a, _ in pairs)
    return ErrorSummary(
        count=n,
        mean_actual=total_actual / n,
        mae=sum(abs_errors) / n,
        rmse=math.sqrt(sum(e * e for e in errors) / n),
        bias=sum(errors) / n,
        wape_pct=(sum(abs_errors) / total_actual * 100.0) if total_actual > 0 else None,
        p50_abs_error=percentile(abs_errors, 50),
        p90_abs_error=percentile(abs_errors, 90),
        p99_abs_error=percentile(abs_errors, 99),
        max_abs_error=max(abs_errors),
        residual_p10=percentile(residuals, 10),
        residual_p90=percentile(residuals, 90),
    )
