import type { AssetSummary } from "../types/api";
import { formatPrice } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type AssetListProps = {
  summaries: AssetSummary[];
  selectedAssetId: number | null;
  query: string;
  market: string;
  onQueryChange: (query: string) => void;
  onMarketChange: (market: string) => void;
  onSelect: (assetId: number) => void;
};

export function AssetList({
  summaries,
  selectedAssetId,
  query,
  market,
  onQueryChange,
  onMarketChange,
  onSelect,
}: AssetListProps) {
  const markets = Array.from(new Set(summaries.map((summary) => summary.asset.market))).sort();
  const normalizedQuery = query.trim().toLowerCase();
  const filtered = summaries.filter((summary) => {
    const asset = summary.asset;
    const matchesQuery =
      !normalizedQuery ||
      asset.symbol.toLowerCase().includes(normalizedQuery) ||
      asset.name.toLowerCase().includes(normalizedQuery);
    const matchesMarket = market === "ALL" || asset.market === market;
    return matchesQuery && matchesMarket;
  });

  return (
    <section className="surface asset-list">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Assets</p>
          <h2>关注资产</h2>
        </div>
        <StatusBadge>{filtered.length}</StatusBadge>
      </div>
      <div className="filter-row">
        <input
          aria-label="过滤资产"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Symbol / name"
        />
        <select aria-label="市场过滤" value={market} onChange={(event) => onMarketChange(event.target.value)}>
          <option value="ALL">All</option>
          {markets.map((item) => (
            <option value={item} key={item}>
              {item}
            </option>
          ))}
        </select>
      </div>
      <div className="asset-items">
        {filtered.map((summary) => {
          const asset = summary.asset;
          const isSelected = selectedAssetId === asset.id;
          const openOnly =
            summary.latest_open_date !== null &&
            summary.latest_open_date !== summary.latest_complete_date &&
            summary.latest_open_is_complete === false;
          return (
            <button
              className={`asset-row ${isSelected ? "asset-row-selected" : ""}`}
              type="button"
              onClick={() => onSelect(asset.id)}
              key={asset.id}
            >
              <span>
                <strong>{asset.symbol}</strong>
                <small>{asset.name}</small>
              </span>
              <span className="asset-meta">
                <StatusBadge tone={openOnly ? "warn" : "good"}>
                  {openOnly ? "Open only" : "Complete"}
                </StatusBadge>
                <span>{formatPrice(summary.latest_complete_close, asset.currency)}</span>
              </span>
            </button>
          );
        })}
        {filtered.length === 0 ? <p className="empty-state">没有匹配资产。</p> : null}
      </div>
    </section>
  );
}
