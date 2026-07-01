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


def test_alert_api_crud_check_and_history(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "alert_api.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    asset_id = seed_api_fixture(database_path)
    client = TestClient(app)

    create_response = client.post(
        "/api/alert-rules",
        json={
            "asset_id": asset_id,
            "name": "AAPL upper",
            "rule_type": "anchor",
            "anchor_date": "2026-06-02",
            "latest_basis": "latest_close",
            "upper_threshold_pct": "0.10",
        },
    )
    rule = create_response.json()
    list_response = client.get("/api/alert-rules", params={"enabled_only": True})
    get_response = client.get(f"/api/alert-rules/{rule['id']}")
    check_response = client.post("/api/alerts/check")
    duplicate_response = client.post("/api/alerts/check")
    events_response = client.get("/api/alert-events", params={"rule_id": rule["id"]})
    update_response = client.put(
        f"/api/alert-rules/{rule['id']}",
        json={
            "asset_id": asset_id,
            "name": "AAPL upper updated",
            "rule_type": "anchor",
            "anchor_date": "2026-06-02",
            "latest_basis": "latest_close",
            "upper_threshold_pct": "0.20",
        },
    )
    delete_response = client.delete(f"/api/alert-rules/{rule['id']}")
    enabled_after_delete = client.get("/api/alert-rules", params={"enabled_only": True})

    assert create_response.status_code == 200
    assert rule["id"] > 0
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "AAPL upper"
    assert get_response.status_code == 200
    assert get_response.json()["id"] == rule["id"]
    assert check_response.status_code == 200
    assert check_response.json()["triggered_event_count"] == 1
    assert duplicate_response.json()["triggered_event_count"] == 0
    assert duplicate_response.json()["skipped_rules"][0]["reason"] == "duplicate_event"
    assert events_response.status_code == 200
    assert len(events_response.json()) == 1
    assert events_response.json()[0]["trigger_direction"] == "upper"
    assert update_response.status_code == 200
    assert update_response.json()["upper_threshold_pct"] == "0.20"
    assert delete_response.status_code == 200
    assert enabled_after_delete.json() == []


def test_alert_api_returns_errors_for_invalid_requests(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "alert_api.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    asset_id = seed_api_fixture(database_path)
    client = TestClient(app)

    invalid_rule = client.post(
        "/api/alert-rules",
        json={
            "asset_id": asset_id,
            "name": "bad threshold",
            "rule_type": "anchor",
            "anchor_date": "2026-06-02",
            "upper_threshold_pct": "-0.10",
        },
    )
    missing_asset = client.post(
        "/api/alert-rules",
        json={
            "asset_id": 999,
            "name": "missing asset",
            "rule_type": "anchor",
            "anchor_date": "2026-06-02",
            "upper_threshold_pct": "0.10",
        },
    )
    missing_rule = client.get("/api/alert-rules/999")

    assert invalid_rule.status_code == 400
    assert missing_asset.status_code == 404
    assert missing_rule.status_code == 404


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
    return asset.id


def make_record(
    trade_date: date,
    open_price: str,
    high_price: str | None,
    low_price: str | None,
    close_price: str | None,
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
        volume=Decimal("1000"),
        currency="USD",
        is_complete=True,
        fetched_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )
