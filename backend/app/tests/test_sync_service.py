from datetime import date, datetime, timezone
from decimal import Decimal

from app.db.repositories import AssetRepository, DailyPriceRepository, SyncJobRepository
from app.models.asset import SeedAsset
from app.providers.models import OhlcvRecord
from app.services.sync_service import SyncService


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


def test_sync_history_writes_prices_and_job(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"
    service = SyncService(database_path=database_path, providers={"fake": FakeProvider()})
    try:
        AssetRepository(service.connection).upsert_seed_asset(
            SeedAsset(
                symbol="FAKE.US",
                name="Fake Asset",
                asset_type="stock",
                market="US",
                currency="USD",
                timezone="America/New_York",
                default_provider="fake",
                provider_symbol="FAKE",
            )
        )

        results = service.sync_history(years=1, end_date=date(2026, 6, 30))
        asset = AssetRepository(service.connection).get_by_symbol("FAKE.US")
        assert asset is not None
        price_count = DailyPriceRepository(service.connection).count_for_asset(asset.id)
        jobs = SyncJobRepository(service.connection).list_jobs()
    finally:
        service.close()

    assert results[0].status == "success"
    assert price_count == 1
    assert jobs[0].status == "success"
    assert jobs[0].row_count == 1


def test_sync_open_writes_incomplete_open_only_record(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"
    service = SyncService(database_path=database_path, providers={"fake": FakeProvider()})
    try:
        asset = AssetRepository(service.connection).upsert_seed_asset(
            SeedAsset(
                symbol="FAKE.US",
                name="Fake Asset",
                asset_type="stock",
                market="US",
                currency="USD",
                timezone="America/New_York",
                default_provider="fake",
                provider_symbol="FAKE",
            )
        )
        results = service.sync_open(target_date=date(2026, 6, 30))
        stored = DailyPriceRepository(service.connection).get_by_asset_date_provider(
            asset.id,
            "2026-06-30",
            "fake",
        )
    finally:
        service.close()

    assert results[0].status == "success"
    assert stored is not None
    assert stored.open == "10"
    assert stored.close is None
    assert stored.is_complete is False
