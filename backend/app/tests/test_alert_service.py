from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository
from app.db.schema import initialize_schema
from app.models.alert import AlertRuleInput
from app.models.asset import SeedAsset
from app.providers.models import OhlcvRecord
from app.services.alert_service import AlertService, InvalidAlertRuleError


def test_alert_service_triggers_upper_threshold_and_deduplicates(tmp_path) -> None:
    database_path, asset_id = seed_alert_fixture(tmp_path)
    service = AlertService(database_path)
    try:
        service.create_rule(
            AlertRuleInput(
                asset_id=asset_id,
                name="AAPL upper",
                rule_type="anchor",
                anchor_date="2026-06-02",
                latest_basis="latest_close",
                upper_threshold_pct="0.10",
            )
        )
        first = service.check_alerts()
        second = service.check_alerts()
    finally:
        service.close()

    assert first.checked_rule_count == 1
    assert first.triggered_event_count == 1
    assert first.created_events[0].trigger_direction == "upper"
    assert first.created_events[0].data_date == "2026-06-10"
    assert first.created_events[0].price_basis == "latest_close"
    assert second.triggered_event_count == 0
    assert second.skipped_rules[0].reason == "duplicate_event"


def test_alert_service_triggers_lower_period_threshold(tmp_path) -> None:
    database_path, asset_id = seed_alert_fixture(tmp_path)
    service = AlertService(database_path)
    try:
        service.create_rule(
            AlertRuleInput(
                asset_id=asset_id,
                name="AAPL lower period",
                rule_type="period",
                period="custom",
                start_date="2026-06-03",
                end_date="2026-06-08",
                lower_threshold_pct="-0.10",
            )
        )
        summary = service.check_alerts()
    finally:
        service.close()

    assert summary.triggered_event_count == 1
    assert summary.created_events[0].trigger_direction == "lower"
    assert summary.created_events[0].price_basis == "period_change"
    assert summary.created_events[0].data_date == "2026-06-08"


def test_alert_service_triggers_period_drawdown_threshold(tmp_path) -> None:
    database_path, asset_id = seed_alert_fixture(tmp_path)
    service = AlertService(database_path)
    try:
        service.create_rule(
            AlertRuleInput(
                asset_id=asset_id,
                name="AAPL drawdown",
                rule_type="period",
                period="custom",
                start_date="2026-06-03",
                end_date="2026-06-08",
                trigger_metric="max_drawdown_pct",
                lower_threshold_pct="-0.10",
            )
        )
        summary = service.check_alerts()
    finally:
        service.close()

    assert summary.triggered_event_count == 1
    assert summary.created_events[0].trigger_direction == "lower"
    assert summary.created_events[0].price_basis == "period_drawdown"
    assert summary.created_events[0].data_date == "2026-06-08"


def test_alert_service_can_trigger_today_open_rule(tmp_path) -> None:
    database_path, asset_id = seed_alert_fixture(tmp_path)
    service = AlertService(database_path)
    try:
        service.create_rule(
            AlertRuleInput(
                asset_id=asset_id,
                name="AAPL today open",
                rule_type="anchor",
                anchor_date="2026-06-02",
                latest_basis="today_open",
                upper_threshold_pct="0.20",
            )
        )
        summary = service.check_alerts()
    finally:
        service.close()

    assert summary.triggered_event_count == 1
    assert summary.created_events[0].data_date == "2026-06-11"
    assert summary.created_events[0].price_basis == "today_open"
    assert '"latest_is_complete": false' in summary.created_events[0].statistics_payload


def test_alert_service_skips_insufficient_statistics(tmp_path) -> None:
    database_path, asset_id = seed_alert_fixture(tmp_path)
    service = AlertService(database_path)
    try:
        service.create_rule(
            AlertRuleInput(
                asset_id=asset_id,
                name="AAPL missing anchor",
                rule_type="anchor",
                anchor_date="2026-07-01",
                upper_threshold_pct="0.01",
            )
        )
        summary = service.check_alerts()
    finally:
        service.close()

    assert summary.triggered_event_count == 0
    assert summary.skipped_rules[0].reason == "statistics_anchor_not_found"


def test_alert_service_does_not_check_disabled_rules(tmp_path) -> None:
    database_path, asset_id = seed_alert_fixture(tmp_path)
    service = AlertService(database_path)
    try:
        service.create_rule(
            AlertRuleInput(
                asset_id=asset_id,
                name="AAPL disabled",
                rule_type="anchor",
                anchor_date="2026-06-02",
                upper_threshold_pct="0.01",
                is_enabled=False,
            )
        )
        summary = service.check_alerts()
    finally:
        service.close()

    assert summary.checked_rule_count == 0
    assert summary.triggered_event_count == 0
    assert summary.skipped_rule_count == 0


def test_alert_service_validates_thresholds(tmp_path) -> None:
    database_path, asset_id = seed_alert_fixture(tmp_path)
    service = AlertService(database_path)
    try:
        with pytest.raises(InvalidAlertRuleError):
            service.create_rule(
                AlertRuleInput(
                    asset_id=asset_id,
                    name="bad upper",
                    rule_type="anchor",
                    anchor_date="2026-06-02",
                    upper_threshold_pct="-0.1",
                )
            )
        with pytest.raises(InvalidAlertRuleError):
            service.create_rule(
                AlertRuleInput(
                    asset_id=asset_id,
                    name="missing threshold",
                    rule_type="anchor",
                    anchor_date="2026-06-02",
                )
            )
    finally:
        service.close()


def seed_alert_fixture(tmp_path) -> tuple[object, int]:
    database_path = tmp_path / "alerts.sqlite3"
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
    return database_path, asset.id


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
