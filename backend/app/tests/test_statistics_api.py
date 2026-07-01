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


def test_statistics_apis_return_anchor_and_period_results(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "statistics_api.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    asset_id = seed_api_fixture(database_path)
    client = TestClient(app)

    anchor_response = client.get(
        f"/api/assets/{asset_id}/statistics/anchor",
        params={"anchor_date": "2026-06-02"},
    )
    period_response = client.get(
        f"/api/assets/{asset_id}/statistics/period",
        params={
            "period": "custom",
            "start_date": "2026-06-02",
            "end_date": "2026-06-11",
        },
    )

    assert anchor_response.status_code == 200
    assert anchor_response.json()["actual_anchor_date"] == "2026-06-03"
    assert anchor_response.json()["latest_price"] == "125"
    assert period_response.status_code == 200
    assert period_response.json()["actual_end_date"] == "2026-06-10"
    assert period_response.json()["period_high"] == "130"
    assert period_response.json()["max_drawdown_peak_date"] == "2026-06-03"


def test_statistics_api_supports_today_open_basis(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "statistics_api.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    asset_id = seed_api_fixture(database_path)
    client = TestClient(app)

    response = client.get(
        f"/api/assets/{asset_id}/statistics/anchor",
        params={"anchor_date": "2026-06-03", "latest_basis": "today_open"},
    )

    assert response.status_code == 200
    assert response.json()["latest_date"] == "2026-06-11"
    assert response.json()["latest_is_complete"] is False


def test_statistics_api_returns_404_for_missing_asset(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "statistics_api.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    seed_api_fixture(database_path)
    client = TestClient(app)

    response = client.get(
        "/api/assets/999/statistics/anchor",
        params={"anchor_date": "2026-06-01"},
    )

    assert response.status_code == 404


def test_statistics_api_returns_400_for_invalid_period(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "statistics_api.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    asset_id = seed_api_fixture(database_path)
    client = TestClient(app)

    response = client.get(
        f"/api/assets/{asset_id}/statistics/period",
        params={"period": "2w"},
    )

    assert response.status_code == 400


def seed_api_fixture(database_path) -> int:
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
        for record in [
            make_record(date(2026, 6, 3), "106", "115", "100", "112"),
            make_record(date(2026, 6, 5), "110", "120", "90", "95"),
            make_record(date(2026, 6, 8), "96", "100", "80", "85"),
            make_record(date(2026, 6, 10), "86", "130", "84", "125"),
        ]:
            prices.upsert_ohlcv_record(asset.id, record, "yfinance")
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
