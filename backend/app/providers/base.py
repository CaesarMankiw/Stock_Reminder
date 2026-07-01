from datetime import date
from typing import Protocol

from app.providers.models import OhlcvRecord


class MarketDataProvider(Protocol):
    name: str
    source_label: str

    def fetch_daily_ohlcv(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
        asset_type: str | None = None,
    ) -> list[OhlcvRecord]:
        """Fetch daily OHLCV records for a provider-specific symbol."""
        ...
