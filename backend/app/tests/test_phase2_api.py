from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository, SyncJobRepository
from app.db.schema import initialize_schema
from app.main import app
from app.models.asset import SeedAsset
from app.providers.models import OhlcvRecord


def test_phase2_read_apis_use_database(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "api.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))

    with connect(database_path) as connection:
        initialize_schema(connection)
        asset = AssetRepository(connection).upsert_seed_asset(
            SeedAsset(
                symbol="AAPL.US",
                name="Apple Inc.",
                asset_type="stock",
                market="US",
                currency="USD",
                timezone="America/New_York",
                default_provider="yfinance",
                provider_symbol="AAPL",
            )
        )
        DailyPriceRepository(connection).upsert_ohlcv_record(
            asset_id=asset.id,
            provider_key="yfinance",
            record=OhlcvRecord(
                asset_symbol="AAPL",
                provider="Yahoo Finance via yfinance",
                provider_symbol="AAPL",
                trade_date=date(2026, 6, 29),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
                volume=Decimal("1000"),
                currency="USD",
                is_complete=True,
                fetched_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
            ),
        )
        jobs = SyncJobRepository(connection)
        job_id = jobs.start_job("init_history", asset.id, "yfinance", "AAPL")
        jobs.finish_job(job_id, "success", 1)

    client = TestClient(app)

    assets_response = client.get("/api/assets")
    prices_response = client.get(f"/api/assets/{asset.id}/prices")
    jobs_response = client.get("/api/sync-jobs")

    assert assets_response.status_code == 200
    assert assets_response.json()[0]["symbol"] == "AAPL.US"
    assert prices_response.status_code == 200
    assert prices_response.json()[0]["close"] == "100.5"
    assert jobs_response.status_code == 200
    assert jobs_response.json()[0]["status"] == "success"
