from datetime import date, datetime, timezone
from decimal import Decimal

from app.providers.models import AssetValidationTarget, OhlcvRecord, ValidationStatus
from app.services.data_source_spike import (
    classify_exception,
    run_validation,
    select_targets,
    validate_records,
)


class FakeProvider:
    name = "fake"
    source_label = "Fake Provider"

    def fetch_daily_ohlcv(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
        asset_type: str | None = None,
    ) -> list[OhlcvRecord]:
        return [
            OhlcvRecord(
                asset_symbol=provider_symbol,
                provider=self.source_label,
                provider_symbol=provider_symbol,
                trade_date=start_date,
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10.5"),
                volume=Decimal("1000"),
                currency="USD",
                is_complete=True,
                fetched_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
            )
        ]


def test_select_targets_filters_provider_and_asset_type() -> None:
    targets = (
        AssetValidationTarget("AAPL.US", "stock", "yfinance", "AAPL"),
        AssetValidationTarget("SPY.US", "etf", "yfinance", "SPY"),
        AssetValidationTarget("BTC/USDT", "crypto", "ccxt", "BTC/USDT"),
    )

    selected = select_targets(provider="yfinance", asset_type="stock", targets=targets)

    assert selected == [targets[0]]


def test_validate_records_marks_history_insufficient() -> None:
    target = AssetValidationTarget("AAPL.US", "stock", "fake", "AAPL")
    record = OhlcvRecord(
        asset_symbol="AAPL",
        provider="Fake Provider",
        provider_symbol="AAPL",
        trade_date=date(2022, 1, 1),
        open=Decimal("10"),
        high=Decimal("11"),
        low=Decimal("9"),
        close=Decimal("10.5"),
        volume=Decimal("1000"),
        currency="USD",
        is_complete=True,
        fetched_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

    result = validate_records(
        target=target,
        records=[record],
        requested_start_date=date(2021, 1, 1),
        requested_end_date=date(2026, 6, 30),
    )

    assert result.status == ValidationStatus.HISTORY_INSUFFICIENT
    assert result.row_count == 1
    assert result.has_open is True


def test_run_validation_uses_registered_provider() -> None:
    target = AssetValidationTarget("AAPL.US", "stock", "fake", "AAPL")

    results = run_validation(
        years=1,
        end_date=date(2026, 6, 30),
        targets=(target,),
        registry={"fake": FakeProvider()},
    )

    assert len(results) == 1
    assert results[0].provider == "fake"
    assert results[0].row_count == 1


def test_classify_exception_detects_network_error() -> None:
    assert classify_exception(TimeoutError("connection timeout")) == ValidationStatus.NETWORK_ERROR
    assert classify_exception(ValueError("bad symbol")) == ValidationStatus.PROVIDER_ERROR
