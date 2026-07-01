from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import sqlite3

from app.db.connection import get_database_path
from app.db.repositories import AssetRepository, DailyPriceRepository, SyncJobRepository


EXPECTED_TABLES = {
    "assets",
    "daily_prices",
    "sync_jobs",
    "alert_rules",
    "alert_events",
}


@dataclass(frozen=True)
class AssetFreshness:
    asset_id: int
    symbol: str
    market: str
    price_count: int
    latest_complete_date: str | None
    latest_open_date: str | None
    is_stale: bool
    days_since_latest_complete: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "symbol": self.symbol,
            "market": self.market,
            "price_count": self.price_count,
            "latest_complete_date": self.latest_complete_date,
            "latest_open_date": self.latest_open_date,
            "is_stale": self.is_stale,
            "days_since_latest_complete": self.days_since_latest_complete,
        }


@dataclass(frozen=True)
class StartupCheckReport:
    checked_at: str
    database_path: str
    database_exists: bool
    schema_ok: bool
    total_asset_count: int
    active_asset_count: int
    asset_statuses: list[AssetFreshness]
    today_open_only_count: int
    recent_failed_sync_jobs: list[dict[str, object]]
    recent_sync_jobs: list[dict[str, object]]
    warnings: list[str]
    errors: list[str]

    @property
    def assets_without_prices(self) -> int:
        return sum(1 for item in self.asset_statuses if item.price_count == 0)

    @property
    def stale_asset_count(self) -> int:
        return sum(1 for item in self.asset_statuses if item.is_stale)

    @property
    def ok(self) -> bool:
        return self.database_exists and self.schema_ok and not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "checked_at": self.checked_at,
            "database_path": self.database_path,
            "database_exists": self.database_exists,
            "schema_ok": self.schema_ok,
            "total_asset_count": self.total_asset_count,
            "active_asset_count": self.active_asset_count,
            "assets_without_prices": self.assets_without_prices,
            "stale_asset_count": self.stale_asset_count,
            "today_open_only_count": self.today_open_only_count,
            "asset_statuses": [item.to_dict() for item in self.asset_statuses],
            "recent_failed_sync_jobs": self.recent_failed_sync_jobs,
            "recent_sync_jobs": self.recent_sync_jobs,
            "warnings": self.warnings,
            "errors": self.errors,
            "ok": self.ok,
        }


class StartupCheckService:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = get_database_path(database_path)

    def run(
        self,
        stale_days: int = 3,
        market: str | None = None,
        today: date | None = None,
    ) -> StartupCheckReport:
        checked_at = datetime.now(timezone.utc).isoformat()
        target_today = today or datetime.now(timezone.utc).date()
        warnings: list[str] = []
        errors: list[str] = []

        if not self.database_path.exists():
            errors.append("Database file does not exist.")
            return StartupCheckReport(
                checked_at=checked_at,
                database_path=str(self.database_path),
                database_exists=False,
                schema_ok=False,
                total_asset_count=0,
                active_asset_count=0,
                asset_statuses=[],
                today_open_only_count=0,
                recent_failed_sync_jobs=[],
                recent_sync_jobs=[],
                warnings=warnings,
                errors=errors,
            )

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            missing_tables = missing_schema_tables(connection)
            if missing_tables:
                errors.append(f"Missing database tables: {', '.join(missing_tables)}.")
                return StartupCheckReport(
                    checked_at=checked_at,
                    database_path=str(self.database_path),
                    database_exists=True,
                    schema_ok=False,
                    total_asset_count=0,
                    active_asset_count=0,
                    asset_statuses=[],
                    today_open_only_count=0,
                    recent_failed_sync_jobs=[],
                    recent_sync_jobs=[],
                    warnings=warnings,
                    errors=errors,
                )

            assets = AssetRepository(connection)
            prices = DailyPriceRepository(connection)
            jobs = SyncJobRepository(connection)
            total_assets = assets.list_assets(active_only=False, market=market)
            active_assets = assets.list_assets(active_only=True, market=market)
            asset_statuses = [
                build_asset_freshness(prices, asset.id, asset.symbol, asset.market, target_today, stale_days)
                for asset in active_assets
            ]
            today_open_only_count = count_today_open_only(connection, target_today, market)
            failed_jobs = [job.to_dict() for job in jobs.list_jobs(status="failed", limit=10)]
            recent_jobs = [job.to_dict() for job in jobs.list_jobs(limit=10)]

            if not active_assets:
                warnings.append("No active assets found.")
            if any(item.price_count == 0 for item in asset_statuses):
                warnings.append("Some active assets do not have price data.")
            if any(item.is_stale for item in asset_statuses):
                warnings.append("Some active assets have stale complete daily prices.")
            if failed_jobs:
                warnings.append("Recent failed sync jobs exist.")

            return StartupCheckReport(
                checked_at=checked_at,
                database_path=str(self.database_path),
                database_exists=True,
                schema_ok=True,
                total_asset_count=len(total_assets),
                active_asset_count=len(active_assets),
                asset_statuses=asset_statuses,
                today_open_only_count=today_open_only_count,
                recent_failed_sync_jobs=failed_jobs,
                recent_sync_jobs=recent_jobs,
                warnings=warnings,
                errors=errors,
            )
        finally:
            connection.close()


def missing_schema_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()
    existing = {str(row["name"]) for row in rows}
    return sorted(EXPECTED_TABLES - existing)


def build_asset_freshness(
    prices: DailyPriceRepository,
    asset_id: int,
    symbol: str,
    market: str,
    today: date,
    stale_days: int,
) -> AssetFreshness:
    latest_complete = prices.get_latest_complete(asset_id)
    latest_open = prices.get_latest_open_record(asset_id)
    price_count = prices.count_for_asset(asset_id)
    latest_complete_date = latest_complete.trade_date if latest_complete else None
    days_since_latest_complete = (
        (today - date.fromisoformat(latest_complete_date)).days
        if latest_complete_date
        else None
    )
    is_stale = (
        days_since_latest_complete is None
        or days_since_latest_complete > stale_days
    )

    return AssetFreshness(
        asset_id=asset_id,
        symbol=symbol,
        market=market,
        price_count=price_count,
        latest_complete_date=latest_complete_date,
        latest_open_date=latest_open.trade_date if latest_open else None,
        is_stale=is_stale,
        days_since_latest_complete=days_since_latest_complete,
    )


def count_today_open_only(
    connection: sqlite3.Connection,
    today: date,
    market: str | None,
) -> int:
    sql = """
        SELECT COUNT(*) AS count
        FROM daily_prices dp
        JOIN assets a ON a.id = dp.asset_id
        WHERE dp.trade_date = ?
          AND dp.open IS NOT NULL
          AND dp.is_complete = 0
          AND a.is_active = 1
    """
    params: list[object] = [today.isoformat()]
    if market:
        sql += " AND a.market = ?"
        params.append(market)
    row = connection.execute(sql, params).fetchone()
    return int(row["count"])
