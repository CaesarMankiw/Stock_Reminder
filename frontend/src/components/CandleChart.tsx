import { useMemo, useState } from "react";

import type { DailyPrice } from "../types/api";
import { formatPrice } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type CandleChartProps = {
  prices: DailyPrice[];
  interval: CandleInterval;
};

type CandleInterval = "1D" | "3D" | "5D" | "1W" | "1M" | "1Q" | "1Y";

type CandlePoint = {
  key: string;
  startDate: string;
  endDate: string;
  open: number;
  high: number;
  low: number;
  close: number;
  currency?: string;
  provider: string;
  providerSymbol: string;
};

const WIDTH = 920;
const HEIGHT = 320;
const PADDING = {
  top: 26,
  right: 78,
  bottom: 28,
  left: 24,
};
const ZOOM_LEVELS = [1, 0.72, 0.48, 0.28] as const;
const WIDTH_LEVELS = [1, 1.4, 1.8, 2.4] as const;

export function CandleChart({ prices, interval }: CandleChartProps) {
  const [zoomIndex, setZoomIndex] = useState(0);
  const [widthIndex, setWidthIndex] = useState(0);
  const candles = useMemo(() => aggregateCandles(prices, interval), [prices, interval]);
  const openOnly = [...prices].reverse().find((price) => !price.is_complete && price.open !== null);
  const zoomRatio = ZOOM_LEVELS[zoomIndex];
  const visible = useMemo(() => {
    const visibleCount = Math.max(1, Math.ceil(candles.length * zoomRatio));
    return candles.slice(-visibleCount);
  }, [candles, zoomRatio]);
  const widthScale = WIDTH_LEVELS[widthIndex];

  if (candles.length === 0) {
    return (
      <section className="surface chart-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Chart</p>
            <h2>K 线</h2>
          </div>
        </div>
        <p className="empty-state">没有可绘制的完整日线。</p>
      </section>
    );
  }

  const lows = visible.map((price) => price.low);
  const highs = visible.map((price) => price.high);
  const minLow = Math.min(...lows);
  const maxHigh = Math.max(...highs);
  const span = maxHigh - minLow || 1;
  const chartLeft = PADDING.left;
  const chartRight = WIDTH - PADDING.right;
  const chartTop = PADDING.top;
  const chartBottom = HEIGHT - PADDING.bottom;
  const candleGap = (chartRight - chartLeft) / visible.length;
  const candleWidth = Math.max(2, Math.min(10, candleGap * 0.58));
  const yFor = (value: number) => chartBottom - ((value - minLow) / span) * (chartBottom - chartTop);
  const yTicks = Array.from({ length: 5 }, (_, index) => maxHigh - (span / 4) * index);
  const last = visible[visible.length - 1];
  const scaledWidth = WIDTH * widthScale;

  return (
    <section className="surface chart-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Chart</p>
          <h2>K 线</h2>
        </div>
        <div className="chart-legend">
          <StatusBadge tone="good">{visible.length}/{candles.length} candles</StatusBadge>
          {openOnly ? <StatusBadge tone="warn">Open only {openOnly.trade_date}</StatusBadge> : null}
        </div>
      </div>
      <div className="chart-toolbar" aria-label="图表缩放">
        <button type="button" onClick={() => setZoomIndex((current) => Math.min(current + 1, ZOOM_LEVELS.length - 1))}>
          放大
        </button>
        <button type="button" onClick={() => setZoomIndex((current) => Math.max(current - 1, 0))}>
          缩小
        </button>
        <button type="button" onClick={() => setZoomIndex(0)}>
          重置
        </button>
        <button type="button" onClick={() => setWidthIndex((current) => Math.min(current + 1, WIDTH_LEVELS.length - 1))}>
          拉宽
        </button>
        <button type="button" onClick={() => setWidthIndex((current) => Math.max(current - 1, 0))}>
          收窄
        </button>
      </div>
      <div className="chart-wrap" role="img" aria-label="日线 K 线图">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" style={{ width: `${scaledWidth}px` }}>
          {yTicks.map((tick) => {
            const y = yFor(tick);
            return (
              <g key={tick}>
                <line x1={chartLeft} x2={chartRight} y1={y} y2={y} className="grid-line" />
                <text x={WIDTH - 8} y={y + 4} textAnchor="end" className="axis-label">
                  {formatPrice(String(tick))}
                </text>
              </g>
            );
          })}
          <line x1={chartRight} x2={chartRight} y1={chartTop} y2={chartBottom} className="axis-line" />
          {visible.map((price, index) => {
            const { open, high, low, close } = price;
            const x = chartLeft + index * candleGap + candleGap / 2;
            const yHigh = yFor(high);
            const yLow = yFor(low);
            const yOpen = yFor(open);
            const yClose = yFor(close);
            const rising = close >= open;
            const bodyTop = Math.min(yOpen, yClose);
            const bodyHeight = Math.max(1, Math.abs(yOpen - yClose));
            return (
              <g className={rising ? "candle candle-up" : "candle candle-down"} key={price.key}>
                <line x1={x} x2={x} y1={yHigh} y2={yLow} />
                <rect x={x - candleWidth / 2} y={bodyTop} width={candleWidth} height={bodyHeight} rx={1} />
              </g>
            );
          })}
        </svg>
      </div>
      <dl className="chart-footer">
        <div>
          <dt>起始</dt>
          <dd>{visible[0].startDate}</dd>
        </div>
        <div>
          <dt>结束</dt>
          <dd>{last.endDate}</dd>
        </div>
        <div>
          <dt>最新收盘</dt>
          <dd>{formatPrice(String(last.close), last.currency)}</dd>
        </div>
        <div>
          <dt>Provider</dt>
          <dd>{last.provider} / {last.providerSymbol}</dd>
        </div>
      </dl>
    </section>
  );
}

function aggregateCandles(prices: DailyPrice[], interval: CandleInterval): CandlePoint[] {
  const complete = prices
    .filter(
      (price) =>
        price.is_complete &&
        price.open !== null &&
        price.high !== null &&
        price.low !== null &&
        price.close !== null,
    )
    .sort((a, b) => a.trade_date.localeCompare(b.trade_date));

  if (interval === "1D") {
    return complete.map((price) => ({
      key: price.trade_date,
      startDate: price.trade_date,
      endDate: price.trade_date,
      open: Number(price.open),
      high: Number(price.high),
      low: Number(price.low),
      close: Number(price.close),
      currency: price.currency ?? undefined,
      provider: price.provider,
      providerSymbol: price.provider_symbol,
    }));
  }

  const groups = interval === "3D" || interval === "5D"
    ? groupByTradingDays(complete, interval === "3D" ? 3 : 5)
    : groupByCalendar(complete, interval);

  return groups.map(candleFromGroup);
}

function groupByTradingDays(prices: DailyPrice[], size: number): DailyPrice[][] {
  const groups: DailyPrice[][] = [];
  for (let index = 0; index < prices.length; index += size) {
    groups.push(prices.slice(index, index + size));
  }
  return groups;
}

function groupByCalendar(prices: DailyPrice[], interval: CandleInterval): DailyPrice[][] {
  const groups = new Map<string, DailyPrice[]>();
  for (const price of prices) {
    const key = calendarKey(price.trade_date, interval);
    const group = groups.get(key) ?? [];
    group.push(price);
    groups.set(key, group);
  }
  return [...groups.values()];
}

function calendarKey(tradeDate: string, interval: CandleInterval): string {
  const [year, month, day] = tradeDate.split("-").map(Number);
  if (interval === "1W") {
    const date = new Date(Date.UTC(year, month - 1, day));
    const weekday = date.getUTCDay() || 7;
    date.setUTCDate(date.getUTCDate() - weekday + 1);
    return `${date.getUTCFullYear()}-W-${date.getUTCMonth() + 1}-${date.getUTCDate()}`;
  }
  if (interval === "1M") {
    return `${year}-${month}`;
  }
  if (interval === "1Q") {
    return `${year}-Q${Math.floor((month - 1) / 3) + 1}`;
  }
  return `${year}`;
}

function candleFromGroup(group: DailyPrice[]): CandlePoint {
  const first = group[0];
  const last = group[group.length - 1];
  return {
    key: `${first.trade_date}-${last.trade_date}`,
    startDate: first.trade_date,
    endDate: last.trade_date,
    open: Number(first.open),
    high: Math.max(...group.map((price) => Number(price.high))),
    low: Math.min(...group.map((price) => Number(price.low))),
    close: Number(last.close),
    currency: last.currency ?? undefined,
    provider: last.provider,
    providerSymbol: last.provider_symbol,
  };
}
