from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.providers.models import OhlcvRecord, to_decimal


class YFinanceProvider:
    name = "yfinance"
    source_label = "Yahoo Finance via yfinance"

    def fetch_daily_ohlcv(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
        asset_type: str | None = None,
    ) -> list[OhlcvRecord]:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("yfinance is not installed") from exc

        # yfinance treats end as exclusive; add one day to include end_date.
        frame = yf.download(
            provider_symbol,
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            progress=False,
            group_by="column",
            threads=False,
        )

        if frame is None or frame.empty:
            return []

        frame = _normalize_yfinance_columns(frame)
        fetched_at = datetime.now(timezone.utc)
        today = fetched_at.date()
        records: list[OhlcvRecord] = []

        for index, row in frame.iterrows():
            trade_date = _index_to_date(index)
            records.append(
                OhlcvRecord(
                    asset_symbol=provider_symbol,
                    provider=self.source_label,
                    provider_symbol=provider_symbol,
                    trade_date=trade_date,
                    open=to_decimal(row.get("Open")),
                    high=to_decimal(row.get("High")),
                    low=to_decimal(row.get("Low")),
                    close=to_decimal(row.get("Close")),
                    volume=to_decimal(row.get("Volume")),
                    currency=None,
                    is_complete=trade_date < today,
                    fetched_at=fetched_at,
                )
            )

        return records


def _normalize_yfinance_columns(frame: Any) -> Any:
    if not hasattr(frame.columns, "nlevels") or frame.columns.nlevels == 1:
        return frame

    # yfinance may return a MultiIndex even for a single ticker. Prefer the
    # price-field level when present, otherwise flatten to the first level.
    known_fields = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    for level in range(frame.columns.nlevels):
        level_values = set(str(value) for value in frame.columns.get_level_values(level))
        if known_fields.intersection(level_values):
            normalized = frame.copy()
            normalized.columns = frame.columns.get_level_values(level)
            return normalized

    normalized = frame.copy()
    normalized.columns = frame.columns.get_level_values(0)
    return normalized


def _index_to_date(index: Any) -> date:
    if hasattr(index, "date"):
        return index.date()
    return date.fromisoformat(str(index)[:10])

