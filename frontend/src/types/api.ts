export type Asset = {
  id: number;
  symbol: string;
  name: string;
  asset_type: "stock" | "etf" | "crypto";
  market: string;
  currency: string;
  timezone: string;
  default_provider: string;
  provider_symbol: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AssetSummary = {
  asset: Asset;
  latest_complete_date: string | null;
  latest_complete_close: string | null;
  latest_open_date: string | null;
  latest_open: string | null;
  latest_open_is_complete: boolean | null;
  latest_fetched_at: string | null;
  price_count: number;
};

export type DailyPrice = {
  id: number;
  asset_id: number;
  trade_date: string;
  open: string | null;
  high: string | null;
  low: string | null;
  close: string | null;
  volume: string | null;
  currency: string | null;
  is_complete: boolean;
  provider: string;
  provider_symbol: string;
  fetched_at: string;
  created_at: string;
  updated_at: string;
};

export type AnchorStatistics = {
  asset_id: number;
  requested_anchor_date: string;
  actual_anchor_date: string | null;
  anchor_price: string | null;
  latest_date: string | null;
  latest_price: string | null;
  latest_basis: "latest_close" | "today_open";
  latest_is_complete: boolean | null;
  change_amount: string | null;
  change_pct: string | null;
  record_count: number;
  data_status: string;
};

export type PeriodStatistics = {
  asset_id: number;
  period: "1w" | "1m" | "3m" | "1y" | "custom";
  requested_start_date: string;
  requested_end_date: string;
  actual_start_date: string | null;
  actual_end_date: string | null;
  start_price: string | null;
  end_price: string | null;
  change_amount: string | null;
  change_pct: string | null;
  period_high: string | null;
  period_high_date: string | null;
  period_low: string | null;
  period_low_date: string | null;
  amplitude: string | null;
  max_drawdown_pct: string | null;
  max_drawdown_peak_date: string | null;
  max_drawdown_trough_date: string | null;
  record_count: number;
  data_status: string;
};

export type AlertRule = {
  id: number;
  asset_id: number;
  name: string | null;
  rule_type: "anchor" | "period";
  anchor_date: string | null;
  period: "1w" | "1m" | "3m" | "1y" | "custom" | null;
  start_date: string | null;
  end_date: string | null;
  latest_basis: "latest_close" | "today_open";
  trigger_metric: "change_pct" | "max_drawdown_pct";
  upper_threshold_pct: string | null;
  lower_threshold_pct: string | null;
  frequency: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type AlertRulePayload = {
  asset_id: number;
  name?: string | null;
  rule_type: "anchor" | "period";
  anchor_date?: string | null;
  period?: "1w" | "1m" | "3m" | "1y" | "custom" | null;
  start_date?: string | null;
  end_date?: string | null;
  latest_basis?: "latest_close" | "today_open";
  trigger_metric?: "change_pct" | "max_drawdown_pct";
  upper_threshold_pct?: string | null;
  lower_threshold_pct?: string | null;
  frequency?: string;
  is_enabled?: boolean;
};

export type AlertEvent = {
  id: number;
  rule_id: number;
  asset_id: number;
  rule_type: "anchor" | "period";
  trigger_direction: "upper" | "lower";
  data_date: string;
  trigger_value_pct: string;
  threshold_pct: string;
  price_basis: string;
  statistics_payload: string;
  message: string;
  created_at: string;
};

export type AlertCheckSummary = {
  checked_rule_count: number;
  triggered_event_count: number;
  skipped_rule_count: number;
  created_events: AlertEvent[];
  skipped_rules: Array<{
    rule_id: number;
    asset_id: number;
    reason: string;
  }>;
};

export type SyncJob = {
  id: number;
  job_type: string;
  asset_id: number | null;
  provider: string | null;
  provider_symbol: string | null;
  status: "pending" | "running" | "success" | "failed";
  started_at: string;
  finished_at: string | null;
  row_count: number;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
};

export type RunSyncPayload = {
  job_type: "init_history" | "open_sync" | "close_sync";
  asset_id?: number | null;
  market?: string | null;
  target_date?: string | null;
  years?: number;
};

export type AssetSyncResult = {
  asset_symbol: string;
  job_type: string;
  status: "success" | "failed";
  row_count: number;
  error_message: string | null;
};
