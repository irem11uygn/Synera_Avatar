"""FastAPI uygulaması: router kaydı, hata biçimi ve günlük ayarı."""

import logging

from fastapi import FastAPI

from app import __version__
from app.api import auth, health, lots, master, production, purchases, sync, transfers
from app.api.errors import register_error_handlers
from app.config import get_settings

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = FastAPI(
        title="AVATAR — Synera",
        description="Üretim, maliyet, satış ve lot izlenebilirliği API'si",
        version=__version__,
    )
    register_error_handlers(app)
    routers = (
        health.router,
        auth.router,
        master.router,
        purchases.router,
        lots.router,
        transfers.router,
        production.router,
        sync.router,
    )
    for router in routers:
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
