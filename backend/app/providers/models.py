from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any


class ValidationStatus(StrEnum):
    SUCCESS = "success"
    HISTORY_INSUFFICIENT = "history_insufficient"
    FIELD_MISSING = "field_missing"
    PROVIDER_ERROR = "provider_error"
    SYMBOL_NOT_SUPPORTED = "symbol_not_supported"
    NETWORK_ERROR = "network_error"


@dataclass(frozen=True)
class AssetValidationTarget:
    asset_symbol: str
    asset_type: str
    provider: str
    provider_symbol: str
    currency: str | None = None


@dataclass(frozen=True)
class OhlcvRecord:
    asset_symbol: str
    provider: str
    provider_symbol: str
    trade_date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: Decimal | None
    currency: str | None
    is_complete: bool
    fetched_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_symbol": self.asset_symbol,
            "provider": self.provider,
            "provider_symbol": self.provider_symbol,
            "trade_date": self.trade_date.isoformat(),
            "open": decimal_to_json(self.open),
            "high": decimal_to_json(self.high),
            "low": decimal_to_json(self.low),
            "close": decimal_to_json(self.close),
            "volume": decimal_to_json(self.volume),
            "currency": self.currency,
            "is_complete": self.is_complete,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass(frozen=True)
class ProviderValidationResult:
    asset_symbol: str
    asset_type: str
    provider: str
    provider_symbol: str
    status: ValidationStatus
    requested_start_date: date
    requested_end_date: date
    actual_start_date: date | None
    actual_end_date: date | None
    row_count: int
    has_open: bool
    has_high: bool
    has_low: bool
    has_close: bool
    has_volume: bool
    supports_today_open: bool | None
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_symbol": self.asset_symbol,
            "asset_type": self.asset_type,
            "provider": self.provider,
            "provider_symbol": self.provider_symbol,
            "status": self.status.value,
            "requested_start_date": self.requested_start_date.isoformat(),
            "requested_end_date": self.requested_end_date.isoformat(),
            "actual_start_date": date_to_json(self.actual_start_date),
            "actual_end_date": date_to_json(self.actual_end_date),
            "row_count": self.row_count,
            "has_open": self.has_open,
            "has_high": self.has_high,
            "has_low": self.has_low,
            "has_close": self.has_close,
            "has_volume": self.has_volume,
            "supports_today_open": self.supports_today_open,
            "error_message": self.error_message,
        }


def date_to_json(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def decimal_to_json(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None

    try:
        import pandas as pd
    except ImportError:
        pd = None

    if pd is not None and pd.isna(value):
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

