import math

import pytest

from app.metrics import percentile, summarize


def test_percentile_matches_linear_interpolation():
    values = [1, 2, 3, 4]
    assert percentile(values, 0) == 1
    assert percentile(values, 100) == 4
    assert percentile(values, 50) == 2.5
    assert percentile(values, 90) == pytest.approx(3.7)
    assert percentile([], 50) is None


def test_percentile_rejects_out_of_range_q():
    with pytest.raises(ValueError):
        percentile([1], 101)


def test_summarize_known_values():
    # (actual, forecast): errors are +100, -100, +200, 0
    s = summarize([(1000, 1100), (1000, 900), (2000, 2200), (500, 500)])
    assert s.count == 4
    assert s.mae == pytest.approx(100)
    assert s.bias == pytest.approx(50)
    assert s.rmse == pytest.approx(math.sqrt((100**2 + 100**2 + 200**2) / 4))
    assert s.wape_pct == pytest.approx(400 / 4500 * 100)
    assert s.max_abs_error == 200
    assert s.residual_p10 < 0 < s.residual_p90


def test_summarize_empty():
    s = summarize([])
    assert s.count == 0 and s.mae is None
