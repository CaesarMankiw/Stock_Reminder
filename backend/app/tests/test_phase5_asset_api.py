from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository
from app.db.schema import initialize_schema
from app.main import app
from app.models.asset import SeedAsset
from app.providers.models import OhlcvRecord


def test_asset_detail_and_summary_api(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "asset_summary.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    asset_id = seed_asset_with_prices(database_path)
    client = TestClient(app)

    detail_response = client.get(f"/api/assets/{asset_id}")
    summary_response = client.get("/api/assets/summary")

    assert detail_response.status_code == 200
    assert detail_response.json()["symbol"] == "AAPL.US"
    assert summary_response.status_code == 200
    assert summary_response.json()[0]["asset"]["id"] == asset_id
    assert summary_response.json()[0]["latest_complete_date"] == "2026-06-10"
    assert summary_response.json()[0]["latest_complete_close"] == "125"
    assert summary_response.json()[0]["latest_open_date"] == "2026-06-11"
    assert summary_response.json()[0]["latest_open"] == "140"
    assert summary_response.json()[0]["latest_open_is_complete"] is False
    assert summary_response.json()[0]["price_count"] == 2


def test_asset_detail_returns_404(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "asset_summary.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    seed_asset_with_prices(database_path)
    client = TestClient(app)

    response = client.get("/api/assets/999")

    assert response.status_code == 404


def seed_asset_with_prices(database_path) -> int:
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
        prices = DailyPriceRepository(connection)
        prices.upsert_ohlcv_record(
            asset_id=asset.id,
            record=make_record(date(2026, 6, 10), "86", "130", "84", "125"),
            provider_key="yfinance",
        )
        prices.upsert_ohlcv_record(
            asset_id=asset.id,
            record=make_record(
                date(2026, 6, 11),
                "140",
                None,
                None,
                None,
                is_complete=False,
            ),
            provider_key="yfinance",
            open_only=True,
        )
    return asset.id


def make_record(
    trade_date: date,
    open_price: str,
    high_price: str | None,
    low_price: str | None,
    close_price: str | None,
    is_complete: bool = True,
) -> OhlcvRecord:
    return OhlcvRecord(
        asset_symbol="AAPL",
        provider="Yahoo Finance via yfinance",
        provider_symbol="AAPL",
        trade_date=trade_date,
        open=Decimal(open_price),
        high=Decimal(high_price) if high_price else None,
        low=Decimal(low_price) if low_price else None,
        close=Decimal(close_price) if close_price else None,
        volume=Decimal("1000") if is_complete else None,
        currency="USD",
        is_complete=is_complete,
        fetched_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )
