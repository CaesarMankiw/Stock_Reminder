from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository, SyncJobRepository
from app.db.schema import initialize_schema
from app.db.seed_assets import DEFAULT_SEED_ASSETS
from app.models.asset import Asset
from app.providers.base import MarketDataProvider
from app.providers.models import OhlcvRecord
from app.services.data_source_spike import provider_registry, subtract_years


@dataclass(frozen=True)
class AssetSyncResult:
    asset_symbol: str
    job_type: str
    status: str
    row_count: int
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "asset_symbol": self.asset_symbol,
            "job_type": self.job_type,
            "status": self.status,
            "row_count": self.row_count,
            "error_message": self.error_message,
        }


class SyncService:
    def __init__(
        self,
        database_path: str | Path | None = None,
        providers: dict[str, MarketDataProvider] | None = None,
    ) -> None:
        self.connection = connect(database_path)
        initialize_schema(self.connection)
        self.assets = AssetRepository(self.connection)
        self.prices = DailyPriceRepository(self.connection)
        self.jobs = SyncJobRepository(self.connection)
        self.providers = providers or provider_registry()

    def close(self) -> None:
        self.connection.close()

    def seed_default_assets(self) -> list[Asset]:
        return self.assets.seed_assets(DEFAULT_SEED_ASSETS)

    def deactivate_assets_except_default(self) -> int:
        return self.assets.deactivate_assets_except(asset.symbol for asset in DEFAULT_SEED_ASSETS)

    def sync_history(
        self,
        years: int = 5,
        market: str | None = None,
        asset_id: int | None = None,
        end_date: date | None = None,
    ) -> list[AssetSyncResult]:
        requested_end = end_date or datetime.now(timezone.utc).date()
        requested_start = subtract_years(requested_end, years)
        assets = self._selected_assets(market=market, asset_id=asset_id)
        return [
            self._sync_asset_history(asset, requested_start, requested_end)
            for asset in assets
        ]

    def sync_open(
        self,
        target_date: date | None = None,
        market: str | None = None,
        asset_id: int | None = None,
    ) -> list[AssetSyncResult]:
        requested_date = target_date or datetime.now(timezone.utc).date()
        assets = self._selected_assets(market=market, asset_id=asset_id)
        return [
            self._sync_asset_single_date(
                asset=asset,
                target_date=requested_date,
                job_type="open_sync",
                open_only=True,
                force_complete=False,
            )
            for asset in assets
        ]

    def sync_close(
        self,
        target_date: date | None = None,
        market: str | None = None,
        asset_id: int | None = None,
    ) -> list[AssetSyncResult]:
        requested_date = target_date or datetime.now(timezone.utc).date()
        assets = self._selected_assets(market=market, asset_id=asset_id)
        return [
            self._sync_asset_single_date(
                asset=asset,
                target_date=requested_date,
                job_type="close_sync",
                open_only=False,
                force_complete=True,
            )
            for asset in assets
        ]

    def _selected_assets(
        self,
        market: str | None = None,
        asset_id: int | None = None,
    ) -> list[Asset]:
        if asset_id is None:
            return self.assets.list_assets(active_only=True, market=market)
        asset = self.assets.get_by_id(asset_id)
        if asset is None or not asset.is_active:
            return []
        if market is not None and asset.market != market:
            return []
        return [asset]

    def _sync_asset_history(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
    ) -> AssetSyncResult:
        job_id = self.jobs.start_job(
            job_type="init_history",
            asset_id=asset.id,
            provider=asset.default_provider,
            provider_symbol=asset.provider_symbol,
        )
        try:
            provider = self._provider_for_asset(asset)
            records = provider.fetch_daily_ohlcv(
                provider_symbol=asset.provider_symbol,
                start_date=start_date,
                end_date=end_date,
                asset_type=asset.asset_type,
            )
            row_count = self.prices.bulk_upsert_records(
                asset_id=asset.id,
                records=records,
                provider_key=asset.default_provider,
            )
        except Exception as exc:  # noqa: BLE001 - sync jobs must record provider failures.
            self.jobs.finish_job(job_id, "failed", 0, str(exc))
            return AssetSyncResult(asset.symbol, "init_history", "failed", 0, str(exc))

        self.jobs.finish_job(job_id, "success", row_count)
        return AssetSyncResult(asset.symbol, "init_history", "success", row_count)

    def _sync_asset_single_date(
        self,
        asset: Asset,
        target_date: date,
        job_type: str,
        open_only: bool,
        force_complete: bool,
    ) -> AssetSyncResult:
        job_id = self.jobs.start_job(
            job_type=job_type,
            asset_id=asset.id,
            provider=asset.default_provider,
            provider_symbol=asset.provider_symbol,
        )
        try:
            provider = self._provider_for_asset(asset)
            records = provider.fetch_daily_ohlcv(
                provider_symbol=asset.provider_symbol,
                start_date=target_date,
                end_date=target_date,
                asset_type=asset.asset_type,
            )
            record = select_record_for_date(records, target_date)
            if record is None:
                raise RuntimeError(f"No OHLCV record returned for {target_date.isoformat()}")
            if not open_only and not has_complete_ohlc(record):
                raise RuntimeError(f"Incomplete OHLC data returned for {target_date.isoformat()}")
            row_count = 1 if self.prices.upsert_ohlcv_record(
                asset_id=asset.id,
                record=record,
                provider_key=asset.default_provider,
                force_complete=force_complete,
                open_only=open_only,
            ) else 0
        except Exception as exc:  # noqa: BLE001 - sync jobs must record provider failures.
            self.jobs.finish_job(job_id, "failed", 0, str(exc))
            return AssetSyncResult(asset.symbol, job_type, "failed", 0, str(exc))

        self.jobs.finish_job(job_id, "success", row_count)
        return AssetSyncResult(asset.symbol, job_type, "success", row_count)

    def _provider_for_asset(self, asset: Asset) -> MarketDataProvider:
        provider = self.providers.get(asset.default_provider)
        if provider is None:
            raise RuntimeError(f"Provider {asset.default_provider!r} is not registered")
        return provider


def select_record_for_date(
    records: list[OhlcvRecord],
    target_date: date,
) -> OhlcvRecord | None:
    for record in records:
        if record.trade_date == target_date:
            return record
    return None


def has_complete_ohlc(record: OhlcvRecord) -> bool:
    return all(
        value is not None
        for value in (record.open, record.high, record.low, record.close)
    )


def yesterday_utc() -> date:
    return datetime.now(timezone.utc).date() - timedelta(days=1)
