from datetime import date, datetime, timezone
from decimal import Decimal

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository, SyncJobRepository
from app.db.schema import initialize_schema
from app.models.asset import SeedAsset
from app.providers.models import OhlcvRecord


def test_seed_asset_is_idempotent(tmp_path) -> None:
    with connect(tmp_path / "test.sqlite3") as connection:
        initialize_schema(connection)
        repo = AssetRepository(connection)
        asset = SeedAsset(
            symbol="AAPL.US",
            name="Apple Inc.",
            asset_type="stock",
            market="US",
            currency="USD",
            timezone="America/New_York",
            default_provider="yfinance",
            provider_symbol="AAPL",
        )

        first = repo.upsert_seed_asset(asset)
        second = repo.upsert_seed_asset(asset)
        assets = repo.list_assets()

    assert first.id == second.id
    assert len(assets) == 1


def test_incomplete_price_does_not_overwrite_complete_record(tmp_path) -> None:
    with connect(tmp_path / "test.sqlite3") as connection:
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
        repo = DailyPriceRepository(connection)
        complete = make_record(date(2026, 6, 29), close=Decimal("101"), is_complete=True)
        incomplete = make_record(date(2026, 6, 29), close=None, is_complete=False)

        assert repo.upsert_ohlcv_record(asset.id, complete, "yfinance") is True
        assert repo.upsert_ohlcv_record(asset.id, incomplete, "yfinance") is False
        stored = repo.get_by_asset_date_provider(asset.id, "2026-06-29", "yfinance")

    assert stored is not None
    assert stored.is_complete is True
    assert stored.close == "101"


def test_incomplete_record_can_be_completed(tmp_path) -> None:
    with connect(tmp_path / "test.sqlite3") as connection:
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
        repo = DailyPriceRepository(connection)
        incomplete = make_record(date(2026, 6, 30), close=None, is_complete=False)
        complete = make_record(date(2026, 6, 30), close=Decimal("102"), is_complete=True)

        repo.upsert_ohlcv_record(asset.id, incomplete, "yfinance", open_only=True)
        repo.upsert_ohlcv_record(asset.id, complete, "yfinance")
        stored = repo.get_by_asset_date_provider(asset.id, "2026-06-30", "yfinance")

    assert stored is not None
    assert stored.is_complete is True
    assert stored.close == "102"


def test_sync_job_repository_records_success_and_failure(tmp_path) -> None:
    with connect(tmp_path / "test.sqlite3") as connection:
        initialize_schema(connection)
        repo = SyncJobRepository(connection)

        success_id = repo.start_job("init_history", None, "yfinance", "AAPL")
        repo.finish_job(success_id, "success", 10)
        failure_id = repo.start_job("init_history", None, "yfinance", "BAD")
        repo.finish_job(failure_id, "failed", 0, "bad symbol")
        jobs = repo.list_jobs(limit=10)

    assert [job.status for job in jobs] == ["failed", "success"]
    assert jobs[0].error_message == "bad symbol"


def make_record(
    trade_date: date,
    close: Decimal | None,
    is_complete: bool,
) -> OhlcvRecord:
    return OhlcvRecord(
        asset_symbol="AAPL",
        provider="Yahoo Finance via yfinance",
        provider_symbol="AAPL",
        trade_date=trade_date,
        open=Decimal("100"),
        high=Decimal("103") if is_complete else None,
        low=Decimal("99") if is_complete else None,
        close=close,
        volume=Decimal("1000") if is_complete else None,
        currency="USD",
        is_complete=is_complete,
        fetched_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

