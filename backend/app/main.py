"""FastAPI uygulaması: router kaydı, hata biçimi, günlük ayarı ve e-posta göndericisi."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import (
    adjustments,
    ai,
    alarms,
    audit,
    auth,
    calc,
    cutting,
    health,
    lots,
    mail,
    master,
    operations,
    production,
    purchases,
    recalls,
    reports,
    reprocessing,
    returns,
    sales,
    stock,
    sync,
    trace,
    transfers,
    users,
)
from app.api.errors import register_error_handlers
from app.config import get_settings
from app.db import get_sessionmaker
from app.services.mail import MailWorker

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """SMTP tanımlıysa giden kutusu göndericisini başlatır; tanımlı değilse e-postalar kuyrukta bekler."""
    smtp = get_settings().smtp
    worker = MailWorker(smtp, get_sessionmaker()) if smtp else None
    if worker:
        worker.start()
    try:
        yield
    finally:
        if worker:
            worker.stop()


def create_app() -> FastAPI:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = FastAPI(
        title="AVATAR — Synera",
        description="Üretim, maliyet, satış ve lot izlenebilirliği API'si",
        version=__version__,
        lifespan=lifespan,
    )
    register_error_handlers(app)
    routers = (
        health.router,
        auth.router,
        users.router,
        operations.router,
        master.router,
        purchases.router,
        lots.router,
        stock.router,
        transfers.router,
        production.router,
        reprocessing.router,
        cutting.router,
        sales.router,
        returns.router,
        adjustments.router,
        trace.router,
        recalls.router,
        alarms.router,
        alarms.settings_router,
        audit.router,
        mail.router,
        calc.router,
        reports.router,
        ai.router,
        sync.router,
    )
    for router in routers:
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
