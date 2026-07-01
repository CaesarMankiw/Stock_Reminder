from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone

from app.models.alert import AlertEvent, AlertEventInput, AlertRule, AlertRuleInput
from app.models.asset import Asset, SeedAsset
from app.models.price import DailyPrice
from app.models.sync_job import SyncJob
from app.providers.models import OhlcvRecord, decimal_to_json


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AssetRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert_seed_asset(self, asset: SeedAsset) -> Asset:
        now = utc_now_iso()
        self.connection.execute(
            """
            INSERT INTO assets (
              symbol, name, asset_type, market, currency, timezone,
              default_provider, provider_symbol, is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
              name = excluded.name,
              asset_type = excluded.asset_type,
              market = excluded.market,
              currency = excluded.currency,
              timezone = excluded.timezone,
              default_provider = excluded.default_provider,
              provider_symbol = excluded.provider_symbol,
              is_active = excluded.is_active,
              updated_at = excluded.updated_at
            """,
            (
                asset.symbol,
                asset.name,
                asset.asset_type,
                asset.market,
                asset.currency,
                asset.timezone,
                asset.default_provider,
                asset.provider_symbol,
                1 if asset.is_active else 0,
                now,
                now,
            ),
        )
        self.connection.commit()
        found = self.get_by_symbol(asset.symbol)
        if found is None:
            raise RuntimeError(f"Failed to upsert asset {asset.symbol}")
        return found

    def seed_assets(self, assets: Iterable[SeedAsset]) -> list[Asset]:
        return [self.upsert_seed_asset(asset) for asset in assets]

    def list_assets(
        self,
        active_only: bool = False,
        market: str | None = None,
    ) -> list[Asset]:
        sql = "SELECT * FROM assets"
        conditions: list[str] = []
        params: list[object] = []
        if active_only:
            conditions.append("is_active = 1")
        if market:
            conditions.append("market = ?")
            params.append(market)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY market, asset_type, symbol"
        rows = self.connection.execute(sql, params).fetchall()
        return [asset_from_row(row) for row in rows]

    def get_by_symbol(self, symbol: str) -> Asset | None:
        row = self.connection.execute(
            "SELECT * FROM assets WHERE symbol = ?",
            (symbol,),
        ).fetchone()
        return asset_from_row(row) if row else None

    def deactivate_assets_except(self, symbols: Iterable[str]) -> int:
        active_symbols = tuple(symbols)
        now = utc_now_iso()
        if not active_symbols:
            cursor = self.connection.execute(
                "UPDATE assets SET is_active = 0, updated_at = ? WHERE is_active = 1",
                (now,),
            )
            self.connection.commit()
            return cursor.rowcount
        placeholders = ", ".join("?" for _ in active_symbols)
        cursor = self.connection.execute(
            f"""
            UPDATE assets SET is_active = 0, updated_at = ?
            WHERE is_active = 1 AND symbol NOT IN ({placeholders})
            """,
            (now, *active_symbols),
        )
        self.connection.commit()
        return cursor.rowcount

    def get_by_id(self, asset_id: int) -> Asset | None:
        row = self.connection.execute(
            "SELECT * FROM assets WHERE id = ?",
            (asset_id,),
        ).fetchone()
        return asset_from_row(row) if row else None


class DailyPriceRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert_ohlcv_record(
        self,
        asset_id: int,
        record: OhlcvRecord,
        provider_key: str,
        force_complete: bool | None = None,
        open_only: bool = False,
    ) -> bool:
        is_complete = record.is_complete if force_complete is None else force_complete
        values = price_values_from_record(record, is_complete=is_complete, open_only=open_only)
        existing = self.get_by_asset_date_provider(asset_id, record.trade_date.isoformat(), provider_key)
        now = utc_now_iso()

        if existing and existing.is_complete and not is_complete:
            return False

        if existing is None:
            self.connection.execute(
                """
                INSERT INTO daily_prices (
                  asset_id, trade_date, open, high, low, close, volume, currency,
                  is_complete, provider, provider_symbol, fetched_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    record.trade_date.isoformat(),
                    values["open"],
                    values["high"],
                    values["low"],
                    values["close"],
                    values["volume"],
                    record.currency,
                    1 if is_complete else 0,
                    provider_key,
                    record.provider_symbol,
                    record.fetched_at.isoformat(),
                    now,
                    now,
                ),
            )
        else:
            self.connection.execute(
                """
                UPDATE daily_prices SET
                  open = ?,
                  high = ?,
                  low = ?,
                  close = ?,
                  volume = ?,
                  currency = ?,
                  is_complete = ?,
                  provider_symbol = ?,
                  fetched_at = ?,
                  updated_at = ?
                WHERE id = ?
                """,
                (
                    values["open"],
                    values["high"],
                    values["low"],
                    values["close"],
                    values["volume"],
                    record.currency,
                    1 if is_complete else 0,
                    record.provider_symbol,
                    record.fetched_at.isoformat(),
                    now,
                    existing.id,
                ),
            )

        self.connection.commit()
        return True

    def bulk_upsert_records(
        self,
        asset_id: int,
        records: Iterable[OhlcvRecord],
        provider_key: str,
        force_complete: bool | None = None,
        open_only: bool = False,
    ) -> int:
        count = 0
        for record in records:
            if self.upsert_ohlcv_record(
                asset_id=asset_id,
                record=record,
                provider_key=provider_key,
                force_complete=force_complete,
                open_only=open_only,
            ):
                count += 1
        return count

    def list_prices(
        self,
        asset_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailyPrice]:
        sql = "SELECT * FROM daily_prices WHERE asset_id = ?"
        params: list[object] = [asset_id]
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
        sql += " ORDER BY trade_date"
        rows = self.connection.execute(sql, params).fetchall()
        return [price_from_row(row) for row in rows]

    def list_complete_prices(
        self,
        asset_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailyPrice]:
        sql = "SELECT * FROM daily_prices WHERE asset_id = ? AND is_complete = 1"
        params: list[object] = [asset_id]
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
        sql += " ORDER BY trade_date, id"
        rows = self.connection.execute(sql, params).fetchall()
        return [price_from_row(row) for row in rows]

    def get_first_complete_on_or_after(
        self,
        asset_id: int,
        target_date: str,
    ) -> DailyPrice | None:
        row = self.connection.execute(
            """
            SELECT * FROM daily_prices
            WHERE asset_id = ? AND is_complete = 1 AND trade_date >= ?
            ORDER BY trade_date ASC, id ASC
            LIMIT 1
            """,
            (asset_id, target_date),
        ).fetchone()
        return price_from_row(row) if row else None

    def get_last_complete_on_or_before(
        self,
        asset_id: int,
        target_date: str,
    ) -> DailyPrice | None:
        row = self.connection.execute(
            """
            SELECT * FROM daily_prices
            WHERE asset_id = ? AND is_complete = 1 AND trade_date <= ?
            ORDER BY trade_date DESC, id DESC
            LIMIT 1
            """,
            (asset_id, target_date),
        ).fetchone()
        return price_from_row(row) if row else None

    def get_latest_complete(self, asset_id: int) -> DailyPrice | None:
        row = self.connection.execute(
            """
            SELECT * FROM daily_prices
            WHERE asset_id = ? AND is_complete = 1
            ORDER BY trade_date DESC, id DESC
            LIMIT 1
            """,
            (asset_id,),
        ).fetchone()
        return price_from_row(row) if row else None

    def get_latest_open_record(self, asset_id: int) -> DailyPrice | None:
        row = self.connection.execute(
            """
            SELECT * FROM daily_prices
            WHERE asset_id = ? AND open IS NOT NULL
            ORDER BY trade_date DESC, id DESC
            LIMIT 1
            """,
            (asset_id,),
        ).fetchone()
        return price_from_row(row) if row else None

    def count_for_asset(self, asset_id: int) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM daily_prices WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()
        return int(row["count"])

    def get_by_asset_date_provider(
        self,
        asset_id: int,
        trade_date: str,
        provider: str,
    ) -> DailyPrice | None:
        row = self.connection.execute(
            """
            SELECT * FROM daily_prices
            WHERE asset_id = ? AND trade_date = ? AND provider = ?
            """,
            (asset_id, trade_date, provider),
        ).fetchone()
        return price_from_row(row) if row else None


class SyncJobRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def start_job(
        self,
        job_type: str,
        asset_id: int | None,
        provider: str | None,
        provider_symbol: str | None,
    ) -> int:
        now = utc_now_iso()
        cursor = self.connection.execute(
            """
            INSERT INTO sync_jobs (
              job_type, asset_id, provider, provider_symbol, status,
              started_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'running', ?, ?, ?)
            """,
            (job_type, asset_id, provider, provider_symbol, now, now, now),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def finish_job(
        self,
        job_id: int,
        status: str,
        row_count: int,
        error_message: str | None = None,
    ) -> None:
        now = utc_now_iso()
        self.connection.execute(
            """
            UPDATE sync_jobs SET
              status = ?,
              finished_at = ?,
              row_count = ?,
              error_message = ?,
              updated_at = ?
            WHERE id = ?
            """,
            (status, now, row_count, error_message, now, job_id),
        )
        self.connection.commit()

    def list_jobs(
        self,
        job_type: str | None = None,
        status: str | None = None,
        asset_id: int | None = None,
        limit: int = 100,
    ) -> list[SyncJob]:
        sql = "SELECT * FROM sync_jobs"
        conditions: list[str] = []
        params: list[object] = []
        if job_type:
            conditions.append("job_type = ?")
            params.append(job_type)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if asset_id is not None:
            conditions.append("asset_id = ?")
            params.append(asset_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = self.connection.execute(sql, params).fetchall()
        return [sync_job_from_row(row) for row in rows]


class AlertRuleRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_rule(self, rule: AlertRuleInput) -> AlertRule:
        now = utc_now_iso()
        cursor = self.connection.execute(
            """
            INSERT INTO alert_rules (
              asset_id, name, rule_type, anchor_date, period, start_date, end_date,
              latest_basis, trigger_metric, upper_threshold_pct, lower_threshold_pct, frequency,
              is_enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule.asset_id,
                rule.name or default_rule_name(rule),
                rule.rule_type,
                rule.anchor_date,
                rule.period,
                rule.start_date,
                rule.end_date,
                rule.latest_basis,
                rule.trigger_metric,
                rule.upper_threshold_pct,
                rule.lower_threshold_pct,
                rule.frequency,
                1 if rule.is_enabled else 0,
                now,
                now,
            ),
        )
        self.connection.commit()
        created = self.get_by_id(int(cursor.lastrowid))
        if created is None:
            raise RuntimeError("Failed to create alert rule")
        return created

    def update_rule(self, rule_id: int, rule: AlertRuleInput) -> AlertRule | None:
        now = utc_now_iso()
        self.connection.execute(
            """
            UPDATE alert_rules SET
              asset_id = ?,
              name = ?,
              rule_type = ?,
              anchor_date = ?,
              period = ?,
              start_date = ?,
              end_date = ?,
              latest_basis = ?,
              trigger_metric = ?,
              upper_threshold_pct = ?,
              lower_threshold_pct = ?,
              frequency = ?,
              is_enabled = ?,
              updated_at = ?
            WHERE id = ?
            """,
            (
                rule.asset_id,
                rule.name or default_rule_name(rule),
                rule.rule_type,
                rule.anchor_date,
                rule.period,
                rule.start_date,
                rule.end_date,
                rule.latest_basis,
                rule.trigger_metric,
                rule.upper_threshold_pct,
                rule.lower_threshold_pct,
                rule.frequency,
                1 if rule.is_enabled else 0,
                now,
                rule_id,
            ),
        )
        self.connection.commit()
        return self.get_by_id(rule_id)

    def disable_rule(self, rule_id: int) -> bool:
        now = utc_now_iso()
        cursor = self.connection.execute(
            """
            UPDATE alert_rules SET is_enabled = 0, updated_at = ?
            WHERE id = ?
            """,
            (now, rule_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def get_by_id(self, rule_id: int) -> AlertRule | None:
        row = self.connection.execute(
            "SELECT * FROM alert_rules WHERE id = ?",
            (rule_id,),
        ).fetchone()
        return alert_rule_from_row(row) if row else None

    def list_rules(
        self,
        asset_id: int | None = None,
        enabled_only: bool = False,
    ) -> list[AlertRule]:
        sql = "SELECT * FROM alert_rules"
        conditions: list[str] = []
        params: list[object] = []
        if asset_id is not None:
            conditions.append("asset_id = ?")
            params.append(asset_id)
        if enabled_only:
            conditions.append("is_enabled = 1")
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id DESC"
        rows = self.connection.execute(sql, params).fetchall()
        return [alert_rule_from_row(row) for row in rows]


class AlertEventRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_event(self, event: AlertEventInput) -> AlertEvent | None:
        now = utc_now_iso()
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO alert_events (
              rule_id, asset_id, rule_type, trigger_direction, data_date,
              trigger_value_pct, threshold_pct, price_basis, statistics_payload,
              message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.rule_id,
                event.asset_id,
                event.rule_type,
                event.trigger_direction,
                event.data_date,
                event.trigger_value_pct,
                event.threshold_pct,
                event.price_basis,
                event.statistics_payload,
                event.message,
                now,
            ),
        )
        self.connection.commit()
        if cursor.rowcount == 0:
            return None
        created = self.get_by_id(int(cursor.lastrowid))
        if created is None:
            raise RuntimeError("Failed to create alert event")
        return created

    def get_by_id(self, event_id: int) -> AlertEvent | None:
        row = self.connection.execute(
            "SELECT * FROM alert_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        return alert_event_from_row(row) if row else None

    def list_events(
        self,
        asset_id: int | None = None,
        rule_id: int | None = None,
        limit: int = 100,
    ) -> list[AlertEvent]:
        sql = "SELECT * FROM alert_events"
        conditions: list[str] = []
        params: list[object] = []
        if asset_id is not None:
            conditions.append("asset_id = ?")
            params.append(asset_id)
        if rule_id is not None:
            conditions.append("rule_id = ?")
            params.append(rule_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = self.connection.execute(sql, params).fetchall()
        return [alert_event_from_row(row) for row in rows]


def price_values_from_record(
    record: OhlcvRecord,
    is_complete: bool,
    open_only: bool,
) -> dict[str, str | None]:
    if open_only or not is_complete:
        return {
            "open": decimal_to_json(record.open),
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
        }
    return {
        "open": decimal_to_json(record.open),
        "high": decimal_to_json(record.high),
        "low": decimal_to_json(record.low),
        "close": decimal_to_json(record.close),
        "volume": decimal_to_json(record.volume),
    }


def default_rule_name(rule: AlertRuleInput) -> str:
    if rule.rule_type == "anchor":
        return f"Asset {rule.asset_id} anchor alert"
    return f"Asset {rule.asset_id} period alert"


def asset_from_row(row: sqlite3.Row) -> Asset:
    return Asset(
        id=int(row["id"]),
        symbol=row["symbol"],
        name=row["name"] or "",
        asset_type=row["asset_type"],
        market=row["market"],
        currency=row["currency"] or "",
        timezone=row["timezone"],
        default_provider=row["default_provider"],
        provider_symbol=row["provider_symbol"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def alert_rule_from_row(row: sqlite3.Row) -> AlertRule:
    return AlertRule(
        id=int(row["id"]),
        asset_id=int(row["asset_id"]),
        name=row["name"],
        rule_type=row["rule_type"],
        anchor_date=row["anchor_date"],
        period=row["period"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        latest_basis=row["latest_basis"],
        trigger_metric=row["trigger_metric"] if "trigger_metric" in row.keys() else "change_pct",
        upper_threshold_pct=row["upper_threshold_pct"],
        lower_threshold_pct=row["lower_threshold_pct"],
        frequency=row["frequency"],
        is_enabled=bool(row["is_enabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def alert_event_from_row(row: sqlite3.Row) -> AlertEvent:
    return AlertEvent(
        id=int(row["id"]),
        rule_id=int(row["rule_id"]),
        asset_id=int(row["asset_id"]),
        rule_type=row["rule_type"],
        trigger_direction=row["trigger_direction"],
        data_date=row["data_date"],
        trigger_value_pct=row["trigger_value_pct"],
        threshold_pct=row["threshold_pct"],
        price_basis=row["price_basis"],
        statistics_payload=row["statistics_payload"],
        message=row["message"],
        created_at=row["created_at"],
    )


def price_from_row(row: sqlite3.Row) -> DailyPrice:
    return DailyPrice(
        id=int(row["id"]),
        asset_id=int(row["asset_id"]),
        trade_date=row["trade_date"],
        open=row["open"],
        high=row["high"],
        low=row["low"],
        close=row["close"],
        volume=row["volume"],
        currency=row["currency"],
        is_complete=bool(row["is_complete"]),
        provider=row["provider"],
        provider_symbol=row["provider_symbol"],
        fetched_at=row["fetched_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def sync_job_from_row(row: sqlite3.Row) -> SyncJob:
    return SyncJob(
        id=int(row["id"]),
        job_type=row["job_type"],
        asset_id=row["asset_id"],
        provider=row["provider"],
        provider_symbol=row["provider_symbol"],
        status=row["status"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        row_count=int(row["row_count"]),
        error_message=row["error_message"],
        retry_count=int(row["retry_count"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
