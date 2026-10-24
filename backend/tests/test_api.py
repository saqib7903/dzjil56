import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.store import WindDataStore


@pytest.fixture
def client(snapshot_settings):
    app = create_app(snapshot_settings, WindDataStore(snapshot_settings))
    app.dependency_overrides[get_settings] = lambda: snapshot_settings
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["dataSource"] == "snapshot"
    assert body["firstDeliveryDate"] == "2026-01-01"
    assert body["lastDeliveryDate"] == "2026-01-03"
    assert body["actualCount"] == 3 * 48


def test_generation_selects_forecast_respecting_horizon(client):
    body = client.get(
        "/api/generation",
        params={"start": "2026-01-02T00:00:00Z", "end": "2026-01-03T00:00:00Z", "horizon": 5},
    ).json()
    assert len(body["points"]) == 48
    paired = [p for p in body["points"] if p["forecast"] is not None]
    assert len(paired) == 24  # hourly forecasts vs half-hourly actuals
    for p in paired:
        assert p["horizonHours"] >= 5
        # synthetic forecasts over-forecast by 10 MW per hour of lead time
        assert p["forecast"] - p["actual"] == pytest.approx(10 * p["horizonHours"])
    assert body["summary"]["bias"] > 0
    assert len(body["hourly"]) == 24


def test_horizon_curve_error_grows_with_lead_time(client):
    points = client.get("/api/accuracy/horizons", params={"step": 6}).json()["points"]
    maes = [p["mae"] for p in points if p["mae"] is not None]
    assert maes == sorted(maes)
    assert points[0]["horizonHours"] == 0


def test_day_ahead_uses_gate_closure_on_previous_day(client):
    body = client.get("/api/day-ahead", params={"date": "2026-01-02", "gate": "10:00"}).json()
    assert body["gateClosureUtc"] == "2026-01-01T10:00:00Z"
    assert body["forecastPublishTime"] <= body["gateClosureUtc"]
    assert body["energy"]["hours"] == 24
    assert body["energy"]["actualMwh"] == 24000


def test_daily_accuracy(client):
    body = client.get("/api/accuracy/daily").json()
    assert [d["deliveryDate"] for d in body["days"]] == ["2026-01-01", "2026-01-02", "2026-01-03"]


@pytest.mark.parametrize(
    "path,params",
    [
        ("/api/generation", {"start": "2025-12-01T00:00:00Z"}),
        ("/api/generation", {"start": "2026-01-02T00:00:00Z", "end": "2026-01-01T00:00:00Z"}),
        ("/api/generation", {"horizon": 60}),
        ("/api/generation", {"horizon": -1}),
        ("/api/day-ahead", {"date": "2026-03-01"}),
        ("/api/day-ahead", {"date": "2026-01-02", "gate": "late"}),
    ],
)
def test_validation_errors(client, path, params):
    assert client.get(path, params=params).status_code == 422
