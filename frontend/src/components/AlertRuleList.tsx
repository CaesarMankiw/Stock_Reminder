import { disableAlertRule } from "../api/alerts";
import type { AlertRule } from "../types/api";
import { formatPct } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type AlertRuleListProps = {
  rules: AlertRule[];
  onEdit: (rule: AlertRule) => void;
  onChanged: () => void;
};

export function AlertRuleList({ rules, onEdit, onChanged }: AlertRuleListProps) {
  const disableRule = async (ruleId: number) => {
    await disableAlertRule(ruleId);
    onChanged();
  };

  return (
    <div className="rule-list">
      <div className="section-heading tight">
        <h3>规则</h3>
        <StatusBadge>{rules.length}</StatusBadge>
      </div>
      {rules.length === 0 ? <p className="empty-state">当前资产没有提醒规则。</p> : null}
      {rules.map((rule) => (
        <article className="rule-item" key={rule.id}>
          <div>
            <strong>{rule.name}</strong>
            <p>
              {rule.rule_type === "anchor"
                ? `anchor ${rule.anchor_date} / ${rule.latest_basis}`
                : `period ${rule.period}${rule.period === "custom" ? ` ${rule.start_date} -> ${rule.end_date ?? "latest"}` : ""}`}
            </p>
            <p>
              Up {formatPct(rule.upper_threshold_pct)} / Down {formatPct(rule.lower_threshold_pct)}
            </p>
          </div>
          <div className="rule-actions">
            <StatusBadge tone={rule.is_enabled ? "good" : "neutral"}>{rule.is_enabled ? "Enabled" : "Disabled"}</StatusBadge>
            <button type="button" onClick={() => onEdit(rule)}>编辑</button>
            {rule.is_enabled ? <button type="button" onClick={() => disableRule(rule.id)}>停用</button> : null}
          </div>
        </article>
      ))}
    </div>
  );
}
