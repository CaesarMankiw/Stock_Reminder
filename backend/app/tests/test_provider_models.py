from datetime import date, datetime, timezone
from decimal import Decimal

from app.providers.models import OhlcvRecord, ProviderValidationResult, ValidationStatus


def test_ohlcv_record_serializes_dates_and_decimals() -> None:
    record = OhlcvRecord(
        asset_symbol="AAPL.US",
        provider="Yahoo Finance via yfinance",
        provider_symbol="AAPL",
        trade_date=date(2026, 6, 30),
        open=Decimal("100.12"),
        high=Decimal("101.34"),
        low=Decimal("99.98"),
        close=Decimal("100.50"),
        volume=Decimal("123456"),
        currency="USD",
        is_complete=True,
        fetched_at=datetime(2026, 6, 30, 8, 0, tzinfo=timezone.utc),
    )

    payload = record.to_dict()

    assert payload["trade_date"] == "2026-06-30"
    assert payload["open"] == "100.12"
    assert payload["fetched_at"] == "2026-06-30T08:00:00+00:00"


def test_provider_validation_result_serializes_status() -> None:
    result = ProviderValidationResult(
        asset_symbol="AAPL.US",
        asset_type="stock",
        provider="yfinance",
        provider_symbol="AAPL",
        status=ValidationStatus.SUCCESS,
        requested_start_date=date(2021, 6, 30),
        requested_end_date=date(2026, 6, 30),
        actual_start_date=date(2021, 7, 1),
        actual_end_date=date(2026, 6, 29),
        row_count=1234,
        has_open=True,
        has_high=True,
        has_low=True,
        has_close=True,
        has_volume=True,
        supports_today_open=False,
        error_message=None,
    )

    payload = result.to_dict()

    assert payload["status"] == "success"
    assert payload["actual_start_date"] == "2021-07-01"
    assert payload["error_message"] is None

