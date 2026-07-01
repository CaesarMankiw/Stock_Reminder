from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DailyPrice:
    id: int
    asset_id: int
    trade_date: str
    open: str | None
    high: str | None
    low: str | None
    close: str | None
    volume: str | None
    currency: str | None
    is_complete: bool
    provider: str
    provider_symbol: str
    fetched_at: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "trade_date": self.trade_date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "currency": self.currency,
            "is_complete": self.is_complete,
            "provider": self.provider,
            "provider_symbol": self.provider_symbol,
            "fetched_at": self.fetched_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

