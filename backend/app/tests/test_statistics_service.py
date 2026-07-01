from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository
from app.db.schema import initialize_schema
from app.models.asset import SeedAsset
from app.providers.models import OhlcvRecord
from app.services.statistics_service import (
    AssetNotFoundError,
    StatisticsService,
    subtract_period,
)


def test_anchor_statistics_maps_non_trading_date_to_next_complete_day(tmp_path) -> None:
    database_path, asset_id = seed_price_fixture(tmp_path)
    service = StatisticsService(database_path)
    try:
        statistics = service.get_anchor_statistics(
            asset_id=asset_id,
            anchor_date=date(2026, 6, 2),
        )
    finally:
        service.close()

    assert statistics.data_status == "ok"
    assert statistics.requested_anchor_date == "2026-06-02"
    assert statistics.actual_anchor_date == "2026-06-03"
    assert statistics.anchor_price == "106"
    assert statistics.latest_date == "2026-06-10"
    assert statistics.latest_price == "125"
    assert statistics.change_amount == "19"
    assert statistics.change_pct == "0.1792452830188679245283018868"
    assert statistics.record_count == 4


def test_anchor_statistics_can_use_latest_incomplete_open(tmp_path) -> None:
    database_path, asset_id = seed_price_fixture(tmp_path)
    service = StatisticsService(database_path)
    try:
        statistics = service.get_anchor_statistics(
            asset_id=asset_id,
            anchor_date=date(2026, 6, 2),
            latest_basis="today_open",
        )
    finally:
        service.close()

    assert statistics.data_status == "ok"
    assert statistics.latest_date == "2026-06-11"
    assert statistics.latest_price == "140"
    assert statistics.latest_is_complete is False
    assert statistics.change_amount == "34"
    assert statistics.record_count == 4


def test_anchor_statistics_reports_missing_anchor_without_fake_result(tmp_path) -> None:
    database_path, asset_id = seed_price_fixture(tmp_path)
    service = StatisticsService(database_path)
    try:
        statistics = service.get_anchor_statistics(
            asset_id=asset_id,
            anchor_date=date(2026, 7, 1),
        )
    finally:
        service.close()

    assert statistics.data_status == "anchor_not_found"
    assert statistics.actual_anchor_date is None
    assert statistics.change_pct is None


def test_period_statistics_excludes_incomplete_rows_and_computes_extremes(tmp_path) -> None:
    database_path, asset_id = seed_price_fixture(tmp_path)
    service = StatisticsService(database_path)
    try:
        statistics = service.get_period_statistics(
            asset_id=asset_id,
            period="custom",
            start_date=date(2026, 6, 2),
            end_date=date(2026, 6, 11),
        )
    finally:
        service.close()

    assert statistics.data_status == "ok"
    assert statistics.actual_start_date == "2026-06-03"
    assert statistics.actual_end_date == "2026-06-10"
    assert statistics.start_price == "106"
    assert statistics.end_price == "125"
    assert statistics.change_amount == "19"
    assert statistics.period_high == "130"
    assert statistics.period_high_date == "2026-06-10"
    assert statistics.period_low == "80"
    assert statistics.period_low_date == "2026-06-08"
    assert statistics.amplitude == "0.4716981132075471698113207547"
    assert statistics.max_drawdown_pct == "-0.2410714285714285714285714286"
    assert statistics.max_drawdown_peak_date == "2026-06-03"
    assert statistics.max_drawdown_trough_date == "2026-06-08"
    assert statistics.record_count == 4


def test_period_statistics_supports_calendar_periods(tmp_path) -> None:
    database_path, asset_id = seed_price_fixture(tmp_path)
    service = StatisticsService(database_path)
    try:
        statistics = service.get_period_statistics(
            asset_id=asset_id,
            period="1w",
            end_date=date(2026, 6, 10),
        )
    finally:
        service.close()

    assert statistics.requested_start_date == "2026-06-03"
    assert statistics.actual_start_date == "2026-06-03"
    assert statistics.record_count == 4
    assert subtract_period(date(2026, 3, 31), "1m") == date(2026, 2, 28)
    assert subtract_period(date(2024, 2, 29), "1y") == date(2023, 2, 28)


def test_period_statistics_reports_insufficient_data_for_missing_ohlc(tmp_path) -> None:
    database_path, asset_id = seed_price_fixture(tmp_path, include_bad_complete=True)
    service = StatisticsService(database_path)
    try:
        statistics = service.get_period_statistics(
            asset_id=asset_id,
            period="custom",
            start_date=date(2026, 6, 12),
            end_date=date(2026, 6, 12),
        )
    finally:
        service.close()

    assert statistics.data_status == "insufficient_data"
    assert statistics.actual_start_date == "2026-06-12"
    assert statistics.actual_end_date == "2026-06-12"
    assert statistics.record_count == 1
    assert statistics.change_pct is None


def test_statistics_service_raises_for_missing_asset(tmp_path) -> None:
    database_path, _ = seed_price_fixture(tmp_path)
    service = StatisticsService(database_path)
    try:
        with pytest.raises(AssetNotFoundError):
            service.get_anchor_statistics(asset_id=999, anchor_date=date(2026, 6, 1))
    finally:
        service.close()


def seed_price_fixture(
    tmp_path,
    include_bad_complete: bool = False,
) -> tuple[Path, int]:
    database_path = tmp_path / "statistics.sqlite3"
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
            make_record(date(2026, 6, 1), "100", "110", "95", "105"),
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
        if include_bad_complete:
            prices.upsert_ohlcv_record(
                asset_id=asset.id,
                record=make_record(
                    date(2026, 6, 12),
                    "125",
                    None,
                    "120",
                    "121",
                ),
                provider_key="yfinance",
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
