from datetime import datetime, timezone

import httpx
import pytest

from app.elexon import ElexonClient, ElexonError

UTC = timezone.utc


def make_client(handler) -> ElexonClient:
    return ElexonClient("https://example.test/api", transport=httpx.MockTransport(handler), max_retries=2)


def test_actuals_keep_wind_only_trim_window_and_latest_revision():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["fuelType"] == "WIND"
        return httpx.Response(
            200,
            json=[
                {
                    "fuelType": "WIND",
                    "startTime": "2026-01-01T00:00:00Z",
                    "publishTime": "2026-01-01T00:30:00Z",
                    "generation": 100,
                },
                {
                    "fuelType": "WIND",
                    "startTime": "2026-01-01T00:00:00Z",
                    "publishTime": "2026-01-01T01:00:00Z",
                    "generation": 110,
                },
                {
                    "fuelType": "CCGT",
                    "startTime": "2026-01-01T00:30:00Z",
                    "publishTime": "2026-01-01T01:00:00Z",
                    "generation": 999,
                },
                {
                    "fuelType": "WIND",
                    "startTime": "2025-12-31T23:30:00Z",
                    "publishTime": "2026-01-01T00:00:00Z",
                    "generation": 50,
                },
            ],
        )

    with make_client(handler) as client:
        points = client.fetch_wind_actuals(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC))
    assert [(p.start_time.isoformat(), p.generation) for p in points] == [("2026-01-01T00:00:00+00:00", 110.0)]


def test_forecasts_are_deduplicated_and_chunked():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["publishDateTimeFrom"])
        return httpx.Response(
            200,
            json=[
                {"publishTime": "2026-01-01T02:30:00Z", "startTime": "2026-01-01T05:00:00Z", "generation": 1},
                {"publishTime": "2026-01-01T02:30:00Z", "startTime": "2026-01-01T05:00:00Z", "generation": 1},
            ],
        )

    with make_client(handler) as client:
        points = client.fetch_wind_forecasts(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 20, tzinfo=UTC))
    assert len(points) == 1
    assert len(calls) == 3  # 7-day chunks


def test_retries_then_raises():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(503)

    with make_client(handler) as client, pytest.raises(ElexonError):
        client.fetch_wind_forecasts(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC))
    assert len(attempts) == 2
