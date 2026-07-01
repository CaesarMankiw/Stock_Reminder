import type { AlertEvent, AlertRule, AssetSummary } from "../types/api";
import { formatDateTime, formatPct } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type AlertEventListProps = {
  events: AlertEvent[];
  rules: AlertRule[];
  summaries: AssetSummary[];
};

export function AlertEventList({ events, rules, summaries }: AlertEventListProps) {
  const assetById = new Map(summaries.map((summary) => [summary.asset.id, summary.asset]));
  const ruleById = new Map(rules.map((rule) => [rule.id, rule]));

  return (
    <div className="event-list">
      <div className="section-heading tight">
        <h3>提醒历史</h3>
        <StatusBadge>{events.length}</StatusBadge>
      </div>
      {events.length === 0 ? <p className="empty-state">暂无提醒事件。</p> : null}
      {events.map((event) => {
        const asset = assetById.get(event.asset_id);
        const rule = ruleById.get(event.rule_id);
        return (
          <article className="event-item" key={event.id}>
            <div>
              <strong>{asset?.symbol ?? `Asset ${event.asset_id}`}</strong>
              <p>{rule?.name ?? `Rule ${event.rule_id}`}</p>
              <p>{event.message}</p>
            </div>
            <div className="event-meta">
              <StatusBadge tone={event.trigger_direction === "upper" ? "good" : "bad"}>{event.trigger_direction}</StatusBadge>
              <span>{event.data_date}</span>
              <span>{formatPct(event.trigger_value_pct)} / {formatPct(event.threshold_pct)}</span>
              <span>{formatDateTime(event.created_at)}</span>
            </div>
          </article>
        );
      })}
    </div>
  );
}
