from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.alerts import router as alerts_router
from app.api.assets import router as assets_router
from app.api.health import router as health_router
from app.api.prices import router as prices_router
from app.api.statistics import router as statistics_router
from app.api.sync_jobs import router as sync_jobs_router
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title="Stock Reminder API",
    version="0.1.0",
    description="Local API for the Stock Reminder app.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(assets_router)
app.include_router(prices_router)
app.include_router(statistics_router)
app.include_router(alerts_router)
app.include_router(sync_jobs_router)
