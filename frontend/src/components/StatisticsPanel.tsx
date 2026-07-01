import { useEffect, useState } from "react";

import { fetchAnchorStatistics, fetchPeriodStatistics } from "../api/statistics";
import type { AnchorStatistics, Asset, PeriodStatistics } from "../types/api";
import { addDays, formatPct, formatPrice, subtractMonths } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

const DEFAULT_ANCHOR_DATE = "2026-01-01";

type StatisticsPanelProps = {
  asset: Asset | null;
  latestCompleteDate: string | null;
};

export function StatisticsPanel({ asset, latestCompleteDate }: StatisticsPanelProps) {
  const [anchorDate, setAnchorDate] = useState("");
  const [latestBasis, setLatestBasis] = useState<"latest_close" | "today_open">("latest_close");
  const [period, setPeriod] = useState<"1w" | "1m" | "3m" | "1y" | "custom">("1y");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [anchorStats, setAnchorStats] = useState<AnchorStatistics | null>(null);
  const [periodStats, setPeriodStats] = useState<PeriodStatistics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!latestCompleteDate) {
      return;
    }
    setAnchorDate((current) => current || DEFAULT_ANCHOR_DATE);
    setCustomStart((current) => current || subtractMonths(latestCompleteDate, 1));
    setCustomEnd((current) => current || latestCompleteDate);
  }, [latestCompleteDate]);

  useEffect(() => {
    setAnchorStats(null);
    setPeriodStats(null);
    setError(null);
  }, [asset?.id]);

  const runAnchor = async () => {
    if (!asset || !anchorDate) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setAnchorStats(await fetchAnchorStatistics(asset.id, { anchorDate, latestBasis }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "锚点统计失败");
    } finally {
      setLoading(false);
    }
  };

  const runPeriod = async () => {
    if (!asset) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setPeriodStats(
        await fetchPeriodStatistics(asset.id, {
          period,
          startDate: period === "custom" ? customStart : undefined,
          endDate: period === "custom" ? customEnd : undefined,
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "区间统计失败");
    } finally {
      setLoading(false);
    }
  };

  if (!asset) {
    return (
      <section className="surface statistics-panel">
        <p className="empty-state">请选择资产后查看统计。</p>
      </section>
    );
  }

  return (
    <section className="surface statistics-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Statistics</p>
          <h2>涨跌幅统计</h2>
        </div>
        {loading ? <StatusBadge>Loading</StatusBadge> : null}
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      <div className="stats-grid">
        <div className="tool-block">
          <h3>锚点</h3>
          <div className="form-grid compact">
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
            <button type="button" onClick={runAnchor}>查询锚点</button>
          </div>
          {anchorStats ? <AnchorResult stats={anchorStats} currency={asset.currency} /> : null}
        </div>

        <div className="tool-block">
          <h3>区间</h3>
          <div className="segmented" role="group" aria-label="区间选择">
            {(["1w", "1m", "3m", "1y", "custom"] as const).map((item) => (
              <button
                className={period === item ? "active" : ""}
                type="button"
                onClick={() => {
                  setPeriod(item);
                  if (item === "1w" && latestCompleteDate) {
                    setCustomStart(addDays(latestCompleteDate, -7));
                    setCustomEnd(latestCompleteDate);
                  }
                }}
                key={item}
              >
                {item}
              </button>
            ))}
          </div>
          {period === "custom" ? (
            <div className="form-grid compact two-cols">
              <label>
                起点
                <input type="date" value={customStart} onChange={(event) => setCustomStart(event.target.value)} />
              </label>
              <label>
                终点
                <input type="date" value={customEnd} onChange={(event) => setCustomEnd(event.target.value)} />
              </label>
            </div>
          ) : null}
          <button type="button" onClick={runPeriod}>查询区间</button>
          {periodStats ? <PeriodResult stats={periodStats} currency={asset.currency} /> : null}
        </div>
      </div>
    </section>
  );
}

function AnchorResult({ stats, currency }: { stats: AnchorStatistics; currency: string }) {
  return (
    <dl className="result-list">
      <Metric label="状态" value={stats.data_status} />
      <Metric label="实际锚点" value={stats.actual_anchor_date ?? "N/A"} />
      <Metric label="锚点价格" value={formatPrice(stats.anchor_price, currency)} />
      <Metric label="最新日期" value={stats.latest_date ?? "N/A"} />
      <Metric label="最新价格" value={formatPrice(stats.latest_price, currency)} />
      <Metric label="涨跌幅" value={formatPct(stats.change_pct)} highlight={stats.change_pct} />
      <Metric label="记录数" value={String(stats.record_count)} />
    </dl>
  );
}

function PeriodResult({ stats, currency }: { stats: PeriodStatistics; currency: string }) {
  return (
    <dl className="result-list">
      <Metric label="状态" value={stats.data_status} />
      <Metric label="实际起止" value={`${stats.actual_start_date ?? "N/A"} / ${stats.actual_end_date ?? "N/A"}`} />
      <Metric label="涨跌幅" value={formatPct(stats.change_pct)} highlight={stats.change_pct} />
      <Metric label="区间高点" value={`${formatPrice(stats.period_high, currency)} @ ${stats.period_high_date ?? "N/A"}`} />
      <Metric label="区间低点" value={`${formatPrice(stats.period_low, currency)} @ ${stats.period_low_date ?? "N/A"}`} />
      <Metric label="振幅" value={formatPct(stats.amplitude)} />
      <Metric
        label="最大回撤"
        value={`${formatPct(stats.max_drawdown_pct)} (${stats.max_drawdown_peak_date ?? "N/A"} -> ${stats.max_drawdown_trough_date ?? "N/A"})`}
      />
    </dl>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: string | null }) {
  const numeric = highlight ? Number(highlight) : null;
  const tone = numeric === null || !Number.isFinite(numeric) ? "" : numeric >= 0 ? "metric-up" : "metric-down";
  return (
    <div>
      <dt>{label}</dt>
      <dd className={tone}>{value}</dd>
    </div>
  );
}
