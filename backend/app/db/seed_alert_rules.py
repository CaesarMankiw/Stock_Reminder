from __future__ import annotations

import sqlite3

from app.db.repositories import AssetRepository, utc_now_iso


def seed_default_alert_rules(connection: sqlite3.Connection) -> int:
    assets = AssetRepository(connection).list_assets(active_only=True)
    created_count = 0
    for asset in assets:
        created_count += upsert_default_rule(
            connection,
            asset_id=asset.id,
            name=f"{asset.symbol} 1m drawdown -10%",
            period="1m",
            trigger_metric="max_drawdown_pct",
            upper_threshold_pct=None,
            lower_threshold_pct="-0.10",
        )
        created_count += upsert_default_rule(
            connection,
            asset_id=asset.id,
            name=f"{asset.symbol} 3m change +/-20%",
            period="3m",
            trigger_metric="change_pct",
            upper_threshold_pct="0.20",
            lower_threshold_pct="-0.20",
        )
    return created_count


def disable_rules_for_inactive_assets(connection: sqlite3.Connection) -> int:
    now = utc_now_iso()
    cursor = connection.execute(
        """
        UPDATE alert_rules
        SET is_enabled = 0, updated_at = ?
        WHERE is_enabled = 1
          AND asset_id IN (
            SELECT id FROM assets WHERE is_active = 0
          )
        """,
        (now,),
    )
    connection.commit()
    return cursor.rowcount


def disable_legacy_verification_rules(connection: sqlite3.Connection) -> int:
    now = utc_now_iso()
    cursor = connection.execute(
        """
        UPDATE alert_rules
        SET is_enabled = 0, updated_at = ?
        WHERE is_enabled = 1
          AND name LIKE 'phase%-verify-%'
        """,
        (now,),
    )
    connection.commit()
    return cursor.rowcount


def upsert_default_rule(
    connection: sqlite3.Connection,
    asset_id: int,
    name: str,
    period: str,
    trigger_metric: str,
    upper_threshold_pct: str | None,
    lower_threshold_pct: str | None,
) -> int:
    now = utc_now_iso()
    cursor = connection.execute(
        """
        INSERT INTO alert_rules (
          asset_id, name, rule_type, anchor_date, period, start_date, end_date,
          latest_basis, trigger_metric, upper_threshold_pct, lower_threshold_pct,
          frequency, is_enabled, created_at, updated_at
        )
        SELECT ?, ?, 'period', NULL, ?, NULL, NULL,
               'latest_close', ?, ?, ?, 'once_per_data_date', 1, ?, ?
        WHERE NOT EXISTS (
          SELECT 1 FROM alert_rules
          WHERE asset_id = ? AND name = ?
        )
        """,
        (
            asset_id,
            name,
            period,
            trigger_metric,
            upper_threshold_pct,
            lower_threshold_pct,
            now,
            now,
            asset_id,
            name,
        ),
    )
    connection.commit()
    return cursor.rowcount
