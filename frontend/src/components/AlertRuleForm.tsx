import { useEffect, useState } from "react";

import { createAlertRule, updateAlertRule } from "../api/alerts";
import type { AlertRule, Asset } from "../types/api";
import { decimalToPctInput, pctInputToDecimal, subtractMonths } from "../utils/format";

const DEFAULT_ANCHOR_DATE = "2026-01-01";

type AlertRuleFormProps = {
  asset: Asset | null;
  latestCompleteDate: string | null;
  editingRule: AlertRule | null;
  onSaved: () => void;
  onCancelEdit: () => void;
};

export function AlertRuleForm({ asset, latestCompleteDate, editingRule, onSaved, onCancelEdit }: AlertRuleFormProps) {
  const [name, setName] = useState("");
  const [ruleType, setRuleType] = useState<"anchor" | "period">("anchor");
  const [anchorDate, setAnchorDate] = useState("");
  const [latestBasis, setLatestBasis] = useState<"latest_close" | "today_open">("latest_close");
  const [triggerMetric, setTriggerMetric] = useState<"change_pct" | "max_drawdown_pct">("max_drawdown_pct");
  const [period, setPeriod] = useState<"1w" | "1m" | "3m" | "1y" | "custom">("1y");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [upperPct, setUpperPct] = useState("");
  const [lowerPct, setLowerPct] = useState("");
  const [isEnabled, setIsEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editingRule) {
      setName(editingRule.name ?? "");
      setRuleType(editingRule.rule_type);
      setAnchorDate(editingRule.anchor_date ?? latestCompleteDate ?? "");
      setLatestBasis(editingRule.latest_basis);
      setTriggerMetric(editingRule.trigger_metric ?? "change_pct");
      setPeriod(editingRule.period ?? "1y");
      setStartDate(editingRule.start_date ?? "");
      setEndDate(editingRule.end_date ?? "");
      setUpperPct(decimalToPctInput(editingRule.upper_threshold_pct));
      setLowerPct(decimalToPctInput(editingRule.lower_threshold_pct));
      setIsEnabled(editingRule.is_enabled);
      return;
    }
    setName("");
    setRuleType("period");
    setAnchorDate(DEFAULT_ANCHOR_DATE);
    setLatestBasis("latest_close");
    setTriggerMetric("max_drawdown_pct");
    setPeriod("1m");
    setStartDate(latestCompleteDate ? subtractMonths(latestCompleteDate, 1) : "");
    setEndDate(latestCompleteDate ?? "");
    setUpperPct("");
    setLowerPct("-10");
    setIsEnabled(true);
    setError(null);
  }, [editingRule, latestCompleteDate, asset?.id]);

  const save = async () => {
    if (!asset) {
      return;
    }
    const upper = pctInputToDecimal(upperPct);
    const lower = pctInputToDecimal(lowerPct);
    if (!upper && !lower) {
      setError("至少设置一个阈值。");
      return;
    }
    if (upper !== null && Number(upper) <= 0) {
      setError("上涨阈值必须大于 0。");
      return;
    }
    if (lower !== null && Number(lower) >= 0) {
      setError("下跌阈值必须小于 0。");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const payload = {
        asset_id: asset.id,
        name: name.trim() || `${asset.symbol} alert`,
        rule_type: ruleType,
        anchor_date: ruleType === "anchor" ? anchorDate : null,
        period: ruleType === "period" ? period : null,
        start_date: ruleType === "period" && period === "custom" ? startDate : null,
        end_date: ruleType === "period" && period === "custom" ? endDate : null,
        latest_basis: ruleType === "anchor" ? latestBasis : "latest_close",
        trigger_metric: ruleType === "period" ? triggerMetric : "change_pct",
        upper_threshold_pct: upper,
        lower_threshold_pct: lower,
        frequency: "once_per_data_date",
        is_enabled: isEnabled,
      } as const;
      if (editingRule) {
        await updateAlertRule(editingRule.id, payload);
      } else {
        await createAlertRule(payload);
      }
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "保存提醒规则失败");
    } finally {
      setSaving(false);
    }
  };

  if (!asset) {
    return <p className="empty-state">请选择资产后设置提醒。</p>;
  }

  return (
    <div className="alert-form">
      <div className="section-heading tight">
        <h3>{editingRule ? "编辑规则" : "新增规则"}</h3>
        {editingRule ? <button type="button" onClick={onCancelEdit}>取消</button> : null}
      </div>
      {error ? <p className="error-banner">{error}</p> : null}
      <div className="form-grid two-cols">
        <label>
          名称
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder={`${asset.symbol} alert`} />
        </label>
        <label>
          类型
          <select value={ruleType} onChange={(event) => setRuleType(event.target.value as typeof ruleType)}>
            <option value="anchor">anchor</option>
            <option value="period">period</option>
          </select>
        </label>
        {ruleType === "anchor" ? (
          <>
            <label>
              锚点日期
              <input type="date" value={anchorDate} onChange={(event) => setAnchorDate(event.target.value)} />
            </label>
            <label>
              最新口径
              <select value={latestBasis} onChange={(event) => setLatestBasis(event.target.value as typeof latestBasis)}>
                <option value="latest_close">latest_close</option>
                <option value="today_open">today_open</option>
              </select>
            </label>
          </>
        ) : (
          <>
            <label>
              区间
              <select value={period} onChange={(event) => setPeriod(event.target.value as typeof period)}>
                <option value="1w">1w</option>
                <option value="1m">1m</option>
                <option value="3m">3m</option>
                <option value="1y">1y</option>
                <option value="custom">custom</option>
              </select>
            </label>
            <label>
              触发指标
              <select value={triggerMetric} onChange={(event) => setTriggerMetric(event.target.value as typeof triggerMetric)}>
                <option value="max_drawdown_pct">区间高点回撤</option>
                <option value="change_pct">区间起止涨跌幅</option>
              </select>
            </label>
            {period === "custom" ? (
              <>
                <label>
                  起点
                  <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
                </label>
                <label>
                  终点
                  <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
                </label>
              </>
            ) : null}
          </>
        )}
        <label>
          上涨阈值 %
          <input value={upperPct} onChange={(event) => setUpperPct(event.target.value)} placeholder="10" />
        </label>
        <label>
          下跌阈值 %
          <input value={lowerPct} onChange={(event) => setLowerPct(event.target.value)} placeholder="-10" />
        </label>
      </div>
      <label className="checkbox-line">
        <input type="checkbox" checked={isEnabled} onChange={(event) => setIsEnabled(event.target.checked)} />
        启用规则
      </label>
      <button className="primary-action" type="button" onClick={save} disabled={saving}>
        {saving ? "保存中" : editingRule ? "保存修改" : "创建规则"}
      </button>
    </div>
  );
}
