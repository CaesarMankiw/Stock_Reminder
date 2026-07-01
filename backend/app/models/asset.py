from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeedAsset:
    symbol: str
    name: str
    asset_type: str
    market: str
    currency: str
    timezone: str
    default_provider: str
    provider_symbol: str
    is_active: bool = True


@dataclass(frozen=True)
class Asset(SeedAsset):
    id: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "market": self.market,
            "currency": self.currency,
            "timezone": self.timezone,
            "default_provider": self.default_provider,
            "provider_symbol": self.provider_symbol,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

