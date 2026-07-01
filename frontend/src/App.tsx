import { useEffect, useMemo, useState } from "react";

import { checkAlerts, fetchAlertEvents, fetchAlertRules } from "./api/alerts";
import { fetchAssetSummaries } from "./api/assets";
import { fetchHealth, type HealthResponse } from "./api/health";
import { fetchPrices } from "./api/prices";
import { fetchSyncJobs, runSyncJob } from "./api/syncJobs";
import { AlertEventList } from "./components/AlertEventList";
import { AlertRuleForm } from "./components/AlertRuleForm";
import { AlertRuleList } from "./components/AlertRuleList";
import { AssetDetailHeader } from "./components/AssetDetailHeader";
import { AssetList } from "./components/AssetList";
import { CandleChart } from "./components/CandleChart";
import { StatisticsPanel } from "./components/StatisticsPanel";
import { StatusBadge } from "./components/StatusBadge";
import { SyncJobPanel } from "./components/SyncJobPanel";
import type { AlertCheckSummary, AlertEvent, AlertRule, AssetSummary, DailyPrice, SyncJob } from "./types/api";
import { addDays } from "./utils/format";

type ConnectionState = "checking" | "online" | "offline";
type CandleInterval = "1D" | "3D" | "5D" | "1W" | "1M" | "1Q" | "1Y";

const MAX_HISTORY_DAYS = 366 * 5;

const intervalLabels: Record<CandleInterval, string> = {
  "1D": "1日",
  "3D": "3日",
  "5D": "5日",
  "1W": "一周",
  "1M": "一月",
  "1Q": "一季度",
  "1Y": "一年",
};

function App() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [summaries, setSummaries] = useState<AssetSummary[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [prices, setPrices] = useState<DailyPrice[]>([]);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [jobs, setJobs] = useState<SyncJob[]>([]);
  const [assetQuery, setAssetQuery] = useState("");
  const [market, setMarket] = useState("ALL");
  const [candleInterval, setCandleInterval] = useState<CandleInterval>("1D");
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [checkSummary, setCheckSummary] = useState<AlertCheckSummary | null>(null);
  const [syncSummary, setSyncSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [syncRunning, setSyncRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedSummary = useMemo(
    () => summaries.find((summary) => summary.asset.id === selectedAssetId) ?? null,
    [selectedAssetId, summaries],
  );
  const selectedAsset = selectedSummary?.asset ?? null;

  const loadShell = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthResult, summaryResult, jobsResult, rulesResult, eventsResult] = await Promise.all([
        fetchHealth(),
        fetchAssetSummaries(true),
        fetchSyncJobs(8),
        fetchAlertRules(),
        fetchAlertEvents({ limit: 50 }),
      ]);
      setHealth(healthResult);
      setConnectionState("online");
      setSummaries(summaryResult);
      setJobs(jobsResult);
      setRules(rulesResult);
      setEvents(eventsResult);
      setSelectedAssetId((current) => current ?? preferredAssetId(summaryResult));
    } catch (caught) {
      setConnectionState("offline");
      setError(caught instanceof Error ? caught.message : "加载工作台失败");
    } finally {
      setLoading(false);
    }
  };

  const loadAssetDetail = async (assetId: number) => {
    const summary = summaries.find((item) => item.asset.id === assetId);
    const latestDate = summary?.latest_complete_date;
    setDetailLoading(true);
    setError(null);
    try {
      const startDate = latestDate ? addDays(latestDate, -MAX_HISTORY_DAYS) : undefined;
      const [priceResult, rulesResult, eventsResult] = await Promise.all([
        fetchPrices(assetId, { startDate }),
        fetchAlertRules({ assetId }),
        fetchAlertEvents({ assetId, limit: 50 }),
      ]);
      setPrices(priceResult);
      setRules((allRules) => mergeRules(allRules, rulesResult, assetId));
      setEvents((allEvents) => mergeEvents(allEvents, eventsResult, assetId));
      setEditingRule(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载资产详情失败");
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    void loadShell();
  }, []);

  useEffect(() => {
    if (selectedAssetId !== null && summaries.length > 0) {
      void loadAssetDetail(selectedAssetId);
    }
  }, [selectedAssetId, summaries.length]);

  const selectedRules = rules.filter((rule) => rule.asset_id === selectedAssetId);
  const selectedEvents = events.filter((event) => event.asset_id === selectedAssetId);

  const refreshAlerts = async () => {
    if (selectedAssetId === null) {
      return;
    }
    const [rulesResult, eventsResult, summariesResult] = await Promise.all([
      fetchAlertRules({ assetId: selectedAssetId }),
      fetchAlertEvents({ assetId: selectedAssetId, limit: 50 }),
      fetchAssetSummaries(true),
    ]);
    setRules((allRules) => mergeRules(allRules, rulesResult, selectedAssetId));
    setEvents((allEvents) => mergeEvents(allEvents, eventsResult, selectedAssetId));
    setSummaries(summariesResult);
    setEditingRule(null);
  };

  const runAlertCheck = async () => {
    setError(null);
    try {
      const summary = await checkAlerts(selectedAssetId ?? undefined);
      setCheckSummary(summary);
      await refreshAlerts();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "提醒检查失败");
    }
  };

  const runDataSync = async () => {
    if (selectedAssetId === null) {
      return;
    }
    setSyncRunning(true);
    setSyncSummary(null);
    setError(null);
    try {
      const results = await runSyncJob({ job_type: "init_history", asset_id: selectedAssetId, years: 5 });
      const successCount = results.filter((result) => result.status === "success").length;
      const failedCount = results.filter((result) => result.status === "failed").length;
      const rows = results.reduce((sum, result) => sum + result.row_count, 0);
      setSyncSummary(`同步完成：${successCount} 成功 / ${failedCount} 失败 / ${rows} 行`);
      await loadShell();
      if (selectedAssetId !== null) {
        await loadAssetDetail(selectedAssetId);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "数据更新失败");
    } finally {
      setSyncRunning(false);
    }
  };

  const statusText =
    connectionState === "checking"
      ? "检查中"
      : connectionState === "online"
        ? "后端连接正常"
        : "后端未连接";

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Local Stock Reminder</p>
          <h1>股票涨跌幅提醒工作台</h1>
        </div>
        <div className="top-actions">
          <button type="button" onClick={() => void loadShell()}>刷新</button>
          <button type="button" onClick={() => void runDataSync()} disabled={syncRunning || selectedAssetId === null}>
            {syncRunning ? "更新中" : "更新数据"}
          </button>
          <button className="primary-action" type="button" onClick={() => void runAlertCheck()}>
            检查提醒
          </button>
          <div className={`status-pill status-${connectionState}`}>{statusText}</div>
        </div>
      </header>

      {error ? <p className="error-banner">{error}</p> : null}
      {syncSummary ? <p className="success-banner">{syncSummary}</p> : null}
      {loading ? <p className="loading-line">正在加载本地工作台...</p> : null}

      <section className="dashboard-grid">
        <aside className="left-column">
          <AssetList
            summaries={summaries}
            selectedAssetId={selectedAssetId}
            query={assetQuery}
            market={market}
            onQueryChange={setAssetQuery}
            onMarketChange={setMarket}
            onSelect={setSelectedAssetId}
          />
          <SyncJobPanel jobs={jobs} />
        </aside>

        <section className="main-column">
          <AssetDetailHeader summary={selectedSummary} />
          <section className="range-bar">
            <div>
              <p className="eyebrow">Candle interval</p>
              <h2>价格走势</h2>
            </div>
            <div className="segmented">
              {(["1D", "3D", "5D", "1W", "1M", "1Q", "1Y"] as const).map((item) => (
                <button
                  className={candleInterval === item ? "active" : ""}
                  type="button"
                  onClick={() => setCandleInterval(item)}
                  key={item}
                >
                  {intervalLabels[item]}
                </button>
              ))}
            </div>
          </section>
          {detailLoading ? <p className="loading-line">正在加载资产数据...</p> : null}
          <CandleChart prices={prices} interval={candleInterval} />
          <StatisticsPanel asset={selectedAsset} latestCompleteDate={selectedSummary?.latest_complete_date ?? null} />
        </section>

        <aside className="side-column">
          <section className="surface alerts-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Alerts</p>
                <h2>提醒规则</h2>
              </div>
              <StatusBadge tone={checkSummary?.triggered_event_count ? "good" : "neutral"}>
                {checkSummary ? `${checkSummary.triggered_event_count} triggered` : `${selectedRules.length} rules`}
              </StatusBadge>
            </div>
            {checkSummary ? (
              <div className="check-summary">
                checked {checkSummary.checked_rule_count} / skipped {checkSummary.skipped_rule_count}
              </div>
            ) : null}
            <AlertRuleForm
              asset={selectedAsset}
              latestCompleteDate={selectedSummary?.latest_complete_date ?? null}
              editingRule={editingRule}
              onSaved={() => void refreshAlerts()}
              onCancelEdit={() => setEditingRule(null)}
            />
            <AlertRuleList rules={selectedRules} onEdit={setEditingRule} onChanged={() => void refreshAlerts()} />
          </section>

          <section className="surface events-panel">
            <AlertEventList events={selectedEvents} rules={rules} summaries={summaries} />
          </section>

          <section className="surface service-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Service</p>
                <h2>本地服务</h2>
              </div>
            </div>
            <dl className="result-list">
              <div>
                <dt>环境</dt>
                <dd>{health?.environment ?? "local"}</dd>
              </div>
              <div>
                <dt>服务</dt>
                <dd>{health?.service ?? "stock-reminder-backend"}</dd>
              </div>
              <div>
                <dt>资产</dt>
                <dd>{summaries.length}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </section>
    </main>
  );
}

function mergeRules(allRules: AlertRule[], selectedRules: AlertRule[], assetId: number): AlertRule[] {
  return [...allRules.filter((rule) => rule.asset_id !== assetId), ...selectedRules];
}

function mergeEvents(allEvents: AlertEvent[], selectedEvents: AlertEvent[], assetId: number): AlertEvent[] {
  return [...allEvents.filter((event) => event.asset_id !== assetId), ...selectedEvents].sort((a, b) => b.id - a.id);
}

function preferredAssetId(summaries: AssetSummary[]): number | null {
  return summaries.find((summary) => summary.price_count > 0)?.asset.id ?? summaries[0]?.asset.id ?? null;
}

export default App;
