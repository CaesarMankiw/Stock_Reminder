from datetime import date, datetime, timezone
from decimal import Decimal

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository, SyncJobRepository
from app.db.schema import initialize_schema
from app.models.asset import SeedAsset
from app.providers.models import OhlcvRecord
from app.services.startup_check_service import StartupCheckService


def test_startup_check_reports_missing_database(tmp_path) -> None:
    report = StartupCheckService(tmp_path / "missing.sqlite3").run()

    assert report.database_exists is False
    assert report.schema_ok is False
    assert report.errors == ["Database file does not exist."]


def test_startup_check_reports_empty_assets(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"
    with connect(database_path) as connection:
        initialize_schema(connection)

    report = StartupCheckService(database_path).run(today=date(2026, 7, 1))

    assert report.database_exists is True
    assert report.schema_ok is True
    assert report.active_asset_count == 0
    assert "No active assets found." in report.warnings


def test_startup_check_marks_stale_assets_and_counts_open_only(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"
    with connect(database_path) as connection:
        initialize_schema(connection)
        asset = AssetRepository(connection).upsert_seed_asset(make_asset())
        prices = DailyPriceRepository(connection)
        prices.upsert_ohlcv_record(
            asset.id,
            make_record(date(2026, 6, 28), close=Decimal("102"), complete=True),
            "fake",
        )
        prices.upsert_ohlcv_record(
            asset.id,
            make_record(date(2026, 7, 1), close=None, complete=False),
            "fake",
            open_only=True,
        )

    report = StartupCheckService(database_path).run(stale_days=1, today=date(2026, 7, 1))

    assert report.active_asset_count == 1
    assert report.stale_asset_count == 1
    assert report.today_open_only_count == 1
    assert report.asset_statuses[0].latest_complete_date == "2026-06-28"
    assert report.asset_statuses[0].days_since_latest_complete == 3


def test_startup_check_reports_recent_failed_sync_jobs(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"
    with connect(database_path) as connection:
        initialize_schema(connection)
        jobs = SyncJobRepository(connection)
        job_id = jobs.start_job("close_sync", None, "fake", "BAD")
        jobs.finish_job(job_id, "failed", 0, "bad symbol")

    report = StartupCheckService(database_path).run(today=date(2026, 7, 1))

    assert len(report.recent_failed_sync_jobs) == 1
    assert report.recent_failed_sync_jobs[0]["error_message"] == "bad symbol"
    assert "Recent failed sync jobs exist." in report.warnings


def make_asset() -> SeedAsset:
    return SeedAsset(
        symbol="FAKE.US",
        name="Fake Asset",
        asset_type="stock",
        market="US",
        currency="USD",
        timezone="America/New_York",
        default_provider="fake",
        provider_symbol="FAKE",
    )


def make_record(
    trade_date: date,
    close: Decimal | None,
    complete: bool,
) -> OhlcvRecord:
    return OhlcvRecord(
        asset_symbol="FAKE",
        provider="Fake Provider",
        provider_symbol="FAKE",
        trade_date=trade_date,
        open=Decimal("100"),
        high=Decimal("103") if complete else None,
        low=Decimal("99") if complete else None,
        close=close,
        volume=Decimal("1000") if complete else None,
        currency="USD",
        is_complete=complete,
        fetched_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
