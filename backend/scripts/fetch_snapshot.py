"""Download the configured window from Elexon and write the bundled snapshot.

Usage (from the backend/ directory):

    python -m scripts.fetch_snapshot
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.elexon import ElexonClient
from app.snapshot import snapshot_path, write_snapshot


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    with ElexonClient(settings.elexon_base_url, timeout=settings.http_timeout_seconds) as client:
        actuals = client.fetch_wind_actuals(settings.window_start, settings.window_end)
        forecasts = client.fetch_wind_forecasts(
            settings.window_start - timedelta(hours=settings.max_horizon_hours), settings.window_end
        )
    path = snapshot_path(settings.snapshot_dir)
    write_snapshot(path, actuals, forecasts, datetime.now(timezone.utc), settings.elexon_base_url)
    logging.info("Wrote %d actuals and %d forecasts to %s", len(actuals), len(forecasts), path)


if __name__ == "__main__":
    main()
