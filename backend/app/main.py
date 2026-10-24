"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import Settings, get_settings
from .routes import router
from .store import WindDataStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, store: WindDataStore | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Wind Forecast Monitor API",
        version="1.0.0",
        description="UK national wind generation: Elexon forecasts vs outturn for day-ahead procurement.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.store = store or WindDataStore(settings)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
