import type { AssetSummary } from "../types/api";
import { formatDateTime, formatPrice } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type AssetDetailHeaderProps = {
  summary: AssetSummary | null;
};

export function AssetDetailHeader({ summary }: AssetDetailHeaderProps) {
  if (summary === null) {
    return (
      <section className="surface detail-header">
        <p className="empty-state">请选择资产。</p>
      </section>
    );
  }

  const asset = summary.asset;
  const hasOpenOnly =
    summary.latest_open_date !== null &&
    summary.latest_open_date !== summary.latest_complete_date &&
    summary.latest_open_is_complete === false;

  return (
    <section className="surface detail-header">
      <div className="detail-title">
        <div>
          <p className="eyebrow">{asset.market} / {asset.asset_type}</p>
          <h2>{asset.symbol}</h2>
          <p>{asset.name}</p>
        </div>
        <StatusBadge tone={hasOpenOnly ? "warn" : "good"}>{hasOpenOnly ? "今日未完成" : "完整日线"}</StatusBadge>
      </div>
      <dl className="metric-grid">
        <div>
          <dt>最新完整日</dt>
          <dd>{summary.latest_complete_date ?? "N/A"}</dd>
        </div>
        <div>
          <dt>最新收盘</dt>
          <dd>{formatPrice(summary.latest_complete_close, asset.currency)}</dd>
        </div>
        <div>
          <dt>最新开盘记录</dt>
          <dd>{summary.latest_open_date ?? "N/A"}</dd>
        </div>
        <div>
          <dt>开盘价</dt>
          <dd>{formatPrice(summary.latest_open, asset.currency)}</dd>
        </div>
        <div>
          <dt>数据源</dt>
          <dd>{asset.default_provider} / {asset.provider_symbol}</dd>
        </div>
        <div>
          <dt>采集时间</dt>
          <dd>{formatDateTime(summary.latest_fetched_at)}</dd>
        </div>
      </dl>
    </section>
  );
}
