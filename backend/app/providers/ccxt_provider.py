from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.providers.models import OhlcvRecord, to_decimal


class CcxtProvider:
    name = "ccxt"

    def __init__(self, exchange_id: str = "binance") -> None:
        self.exchange_id = exchange_id
        self.source_label = f"{exchange_id.title()} via CCXT"

    def fetch_daily_ohlcv(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
        asset_type: str | None = None,
    ) -> list[OhlcvRecord]:
        try:
            import ccxt
        except ImportError as exc:
            raise RuntimeError("ccxt is not installed") from exc

        exchange_class = getattr(ccxt, self.exchange_id)
        exchange = exchange_class({"enableRateLimit": True, "timeout": 15000})
        since = _date_to_millis(start_date)
        end_millis = _date_to_millis(end_date + timedelta(days=1))
        fetched_at = datetime.now(timezone.utc)
        today = fetched_at.date()
        records: list[OhlcvRecord] = []

        while since < end_millis:
            batch = exchange.fetch_ohlcv(
                provider_symbol,
                timeframe="1d",
                since=since,
                limit=1000,
            )
            if not batch:
                break

            for item in batch:
                timestamp, open_, high, low, close, volume = item
                if timestamp >= end_millis:
                    continue
                trade_date = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date()
                records.append(
                    OhlcvRecord(
                        asset_symbol=provider_symbol,
                        provider=self.source_label,
                        provider_symbol=provider_symbol,
                        trade_date=trade_date,
                        open=_decimal_from_ccxt(open_),
                        high=_decimal_from_ccxt(high),
                        low=_decimal_from_ccxt(low),
                        close=_decimal_from_ccxt(close),
                        volume=_decimal_from_ccxt(volume),
                        currency=_quote_currency(provider_symbol),
                        is_complete=trade_date < today,
                        fetched_at=fetched_at,
                    )
                )

            next_since = int(batch[-1][0]) + 24 * 60 * 60 * 1000
            if next_since <= since:
                break
            since = next_since

        return records


def _date_to_millis(value: date) -> int:
    dt = datetime.combine(value, time.min, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _decimal_from_ccxt(value: Any) -> Decimal | None:
    return to_decimal(value)


def _quote_currency(symbol: str) -> str | None:
    if "/" not in symbol:
        return None
    return symbol.split("/", maxsplit=1)[1]

