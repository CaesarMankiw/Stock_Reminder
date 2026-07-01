from __future__ import annotations

import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL UNIQUE,
  name TEXT,
  asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'etf', 'crypto')),
  market TEXT NOT NULL,
  currency TEXT,
  timezone TEXT NOT NULL,
  default_provider TEXT NOT NULL,
  provider_symbol TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL,
  trade_date TEXT NOT NULL,
  open TEXT,
  high TEXT,
  low TEXT,
  close TEXT,
  volume TEXT,
  currency TEXT,
  is_complete INTEGER NOT NULL DEFAULT 0 CHECK (is_complete IN (0, 1)),
  provider TEXT NOT NULL,
  provider_symbol TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (asset_id) REFERENCES assets(id),
  UNIQUE (asset_id, trade_date, provider)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_asset_date
ON daily_prices(asset_id, trade_date);

CREATE INDEX IF NOT EXISTS idx_daily_prices_provider
ON daily_prices(provider, provider_symbol);

CREATE TABLE IF NOT EXISTS sync_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_type TEXT NOT NULL CHECK (job_type IN ('init_history', 'open_sync', 'close_sync')),
  asset_id INTEGER,
  provider TEXT,
  provider_symbol TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed')),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  row_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE INDEX IF NOT EXISTS idx_sync_jobs_status
ON sync_jobs(status);

CREATE INDEX IF NOT EXISTS idx_sync_jobs_asset
ON sync_jobs(asset_id);

CREATE TABLE IF NOT EXISTS alert_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  rule_type TEXT NOT NULL CHECK (rule_type IN ('anchor', 'period')),
  anchor_date TEXT,
  period TEXT CHECK (period IS NULL OR period IN ('1w', '1m', '3m', '1y', 'custom')),
  start_date TEXT,
  end_date TEXT,
  latest_basis TEXT NOT NULL DEFAULT 'latest_close'
    CHECK (latest_basis IN ('latest_close', 'today_open')),
  trigger_metric TEXT NOT NULL DEFAULT 'change_pct'
    CHECK (trigger_metric IN ('change_pct', 'max_drawdown_pct')),
  upper_threshold_pct TEXT,
  lower_threshold_pct TEXT,
  frequency TEXT NOT NULL DEFAULT 'once_per_data_date'
    CHECK (frequency IN ('once_per_data_date')),
  is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_asset
ON alert_rules(asset_id);

CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled
ON alert_rules(is_enabled);

CREATE TABLE IF NOT EXISTS alert_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_id INTEGER NOT NULL,
  asset_id INTEGER NOT NULL,
  rule_type TEXT NOT NULL CHECK (rule_type IN ('anchor', 'period')),
  trigger_direction TEXT NOT NULL CHECK (trigger_direction IN ('upper', 'lower')),
  data_date TEXT NOT NULL,
  trigger_value_pct TEXT NOT NULL,
  threshold_pct TEXT NOT NULL,
  price_basis TEXT NOT NULL,
  statistics_payload TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (rule_id) REFERENCES alert_rules(id),
  FOREIGN KEY (asset_id) REFERENCES assets(id),
  UNIQUE (rule_id, data_date, trigger_direction)
);

CREATE INDEX IF NOT EXISTS idx_alert_events_asset
ON alert_events(asset_id);

CREATE INDEX IF NOT EXISTS idx_alert_events_rule
ON alert_events(rule_id);

CREATE INDEX IF NOT EXISTS idx_alert_events_data_date
ON alert_events(data_date);
"""


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    ensure_column(
        connection,
        table_name="alert_rules",
        column_name="trigger_metric",
        definition="TEXT NOT NULL DEFAULT 'change_pct'",
    )
    connection.commit()


def ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    if any(row[1] == column_name for row in rows):
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
