from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.providers.models import OhlcvRecord, to_decimal


class AkShareProvider:
    name = "akshare"
    source_label = "东方财富 via AKShare"

    def fetch_daily_ohlcv(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
        asset_type: str | None = None,
    ) -> list[OhlcvRecord]:
        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError("akshare is not installed") from exc

        symbol = _strip_market_suffix(provider_symbol)
        start = start_date.strftime("%Y%m%d")
        end = end_date.strftime("%Y%m%d")

        if asset_type == "etf":
            frame = ak.fund_etf_hist_em(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="",
            )
        elif asset_type == "stock":
            frame = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="",
            )
        else:
            raise ValueError(f"AKShare provider does not support asset_type={asset_type!r}")

        if frame is None or frame.empty:
            return []

        fetched_at = datetime.now(timezone.utc)
        today = fetched_at.date()
        records: list[OhlcvRecord] = []

        for _, row in frame.iterrows():
            trade_date = _row_date(row.get("日期"))
            records.append(
                OhlcvRecord(
                    asset_symbol=provider_symbol,
                    provider=self.source_label,
                    provider_symbol=provider_symbol,
                    trade_date=trade_date,
                    open=to_decimal(row.get("开盘")),
                    high=to_decimal(row.get("最高")),
                    low=to_decimal(row.get("最低")),
                    close=to_decimal(row.get("收盘")),
                    volume=to_decimal(row.get("成交量")),
                    currency="CNY",
                    is_complete=trade_date < today,
                    fetched_at=fetched_at,
                )
            )

        return records


def _strip_market_suffix(provider_symbol: str) -> str:
    return provider_symbol.split(".", maxsplit=1)[0]


def _row_date(value: Any) -> date:
    if hasattr(value, "date"):
        return value.date()
    return date.fromisoformat(str(value)[:10])

