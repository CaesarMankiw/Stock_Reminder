import { apiRequest, toQuery } from "./client";
import type { AlertCheckSummary, AlertEvent, AlertRule, AlertRulePayload } from "../types/api";

export function fetchAlertRules(params: { assetId?: number; enabledOnly?: boolean } = {}): Promise<AlertRule[]> {
  return apiRequest<AlertRule[]>(
    `/api/alert-rules${toQuery({
      asset_id: params.assetId,
      enabled_only: params.enabledOnly,
    })}`,
  );
}

export function createAlertRule(payload: AlertRulePayload): Promise<AlertRule> {
  return apiRequest<AlertRule>("/api/alert-rules", { method: "POST", body: payload });
}

export function updateAlertRule(ruleId: number, payload: AlertRulePayload): Promise<AlertRule> {
  return apiRequest<AlertRule>(`/api/alert-rules/${ruleId}`, { method: "PUT", body: payload });
}

export function disableAlertRule(ruleId: number): Promise<{ deleted: boolean; rule_id: number }> {
  return apiRequest<{ deleted: boolean; rule_id: number }>(`/api/alert-rules/${ruleId}`, { method: "DELETE" });
}

export function checkAlerts(assetId?: number): Promise<AlertCheckSummary> {
  return apiRequest<AlertCheckSummary>(`/api/alerts/check${toQuery({ asset_id: assetId })}`, { method: "POST" });
}

export function fetchAlertEvents(params: { assetId?: number; ruleId?: number; limit?: number } = {}): Promise<AlertEvent[]> {
  return apiRequest<AlertEvent[]>(
    `/api/alert-events${toQuery({
      asset_id: params.assetId,
      rule_id: params.ruleId,
      limit: params.limit ?? 100,
    })}`,
  );
}
