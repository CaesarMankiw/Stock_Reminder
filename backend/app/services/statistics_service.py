from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository
from app.db.schema import initialize_schema
from app.models.price import DailyPrice
from app.models.statistics import AnchorStatistics, PeriodStatistics


LATEST_CLOSE = "latest_close"
TODAY_OPEN = "today_open"
VALID_LATEST_BASIS = {LATEST_CLOSE, TODAY_OPEN}
VALID_PERIODS = {"1w", "1m", "3m", "1y", "custom"}


class AssetNotFoundError(ValueError):
    pass


class InvalidStatisticsRequest(ValueError):
    pass


class StatisticsService:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.connection = connect(database_path)
        initialize_schema(self.connection)
        self.assets = AssetRepository(self.connection)
        self.prices = DailyPriceRepository(self.connection)

    def close(self) -> None:
        self.connection.close()

    def get_anchor_statistics(
        self,
        asset_id: int,
        anchor_date: date,
        latest_basis: str = LATEST_CLOSE,
    ) -> AnchorStatistics:
        if latest_basis not in VALID_LATEST_BASIS:
            raise InvalidStatisticsRequest("latest_basis must be latest_close or today_open")
        self._ensure_asset_exists(asset_id)

        requested_anchor_date = anchor_date.isoformat()
        anchor_record = self.prices.get_first_complete_on_or_after(
            asset_id,
            requested_anchor_date,
        )
        if anchor_record is None:
            return self._empty_anchor_statistics(
                asset_id=asset_id,
                requested_anchor_date=requested_anchor_date,
                latest_basis=latest_basis,
                data_status="anchor_not_found",
            )

        anchor_price = parse_decimal(anchor_record.open)
        if anchor_price is None or anchor_price <= 0:
            return self._empty_anchor_statistics(
                asset_id=asset_id,
                requested_anchor_date=requested_anchor_date,
                latest_basis=latest_basis,
                data_status="insufficient_data",
                actual_anchor_date=anchor_record.trade_date,
                anchor_price=decimal_to_output(anchor_price),
                record_count=1,
            )

        latest_record = self._latest_record(asset_id, latest_basis)
        if latest_record is None:
            return self._empty_anchor_statistics(
                asset_id=asset_id,
                requested_anchor_date=requested_anchor_date,
                latest_basis=latest_basis,
                data_status="latest_not_found",
                actual_anchor_date=anchor_record.trade_date,
                anchor_price=decimal_to_output(anchor_price),
                record_count=1,
            )

        latest_price = parse_decimal(
            latest_record.close if latest_basis == LATEST_CLOSE else latest_record.open
        )
        if latest_price is None:
            return self._empty_anchor_statistics(
                asset_id=asset_id,
                requested_anchor_date=requested_anchor_date,
                latest_basis=latest_basis,
                data_status="insufficient_data",
                actual_anchor_date=anchor_record.trade_date,
                anchor_price=decimal_to_output(anchor_price),
                latest_date=latest_record.trade_date,
                latest_price=None,
                latest_is_complete=latest_record.is_complete,
                record_count=self._complete_record_count(
                    asset_id,
                    anchor_record.trade_date,
                    latest_record.trade_date,
                ),
            )

        if latest_record.trade_date < anchor_record.trade_date:
            return self._empty_anchor_statistics(
                asset_id=asset_id,
                requested_anchor_date=requested_anchor_date,
                latest_basis=latest_basis,
                data_status="insufficient_data",
                actual_anchor_date=anchor_record.trade_date,
                anchor_price=decimal_to_output(anchor_price),
                latest_date=latest_record.trade_date,
                latest_price=decimal_to_output(latest_price),
                latest_is_complete=latest_record.is_complete,
            )

        change_amount = latest_price - anchor_price
        change_pct = change_amount / anchor_price
        return AnchorStatistics(
            asset_id=asset_id,
            requested_anchor_date=requested_anchor_date,
            actual_anchor_date=anchor_record.trade_date,
            anchor_price=decimal_to_output(anchor_price),
            latest_date=latest_record.trade_date,
            latest_price=decimal_to_output(latest_price),
            latest_basis=latest_basis,
            latest_is_complete=latest_record.is_complete,
            change_amount=decimal_to_output(change_amount),
            change_pct=decimal_to_output(change_pct),
            record_count=self._complete_record_count(
                asset_id,
                anchor_record.trade_date,
                latest_record.trade_date,
            ),
            data_status="ok",
        )

    def get_period_statistics(
        self,
        asset_id: int,
        period: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PeriodStatistics:
        if period not in VALID_PERIODS:
            raise InvalidStatisticsRequest("period must be 1w, 1m, 3m, 1y, or custom")
        if period == "custom" and start_date is None:
            raise InvalidStatisticsRequest("start_date is required when period=custom")
        self._ensure_asset_exists(asset_id)

        latest_complete = self.prices.get_latest_complete(asset_id)
        requested_end_date = end_date or (
            date.fromisoformat(latest_complete.trade_date)
            if latest_complete is not None
            else date.today()
        )
        requested_start_date = (
            start_date
            if period == "custom"
            else subtract_period(requested_end_date, period)
        )
        if requested_start_date is None:
            raise InvalidStatisticsRequest("start_date is required")
        if requested_start_date > requested_end_date:
            raise InvalidStatisticsRequest("start_date must be earlier than or equal to end_date")

        requested_start_iso = requested_start_date.isoformat()
        requested_end_iso = requested_end_date.isoformat()
        if latest_complete is None:
            return self._empty_period_statistics(
                asset_id=asset_id,
                period=period,
                requested_start_date=requested_start_iso,
                requested_end_date=requested_end_iso,
                data_status="insufficient_data",
            )

        actual_start = self.prices.get_first_complete_on_or_after(
            asset_id,
            requested_start_iso,
        )
        actual_end = self.prices.get_last_complete_on_or_before(
            asset_id,
            requested_end_iso,
        )
        if actual_start is None or actual_end is None or actual_start.trade_date > actual_end.trade_date:
            return self._empty_period_statistics(
                asset_id=asset_id,
                period=period,
                requested_start_date=requested_start_iso,
                requested_end_date=requested_end_iso,
                data_status="insufficient_data",
                actual_start_date=actual_start.trade_date if actual_start else None,
                actual_end_date=actual_end.trade_date if actual_end else None,
            )

        records = self.prices.list_complete_prices(
            asset_id,
            start_date=actual_start.trade_date,
            end_date=actual_end.trade_date,
        )
        if not records:
            return self._empty_period_statistics(
                asset_id=asset_id,
                period=period,
                requested_start_date=requested_start_iso,
                requested_end_date=requested_end_iso,
                data_status="insufficient_data",
                actual_start_date=actual_start.trade_date,
                actual_end_date=actual_end.trade_date,
            )

        computed = compute_period_values(records)
        if computed is None:
            return self._empty_period_statistics(
                asset_id=asset_id,
                period=period,
                requested_start_date=requested_start_iso,
                requested_end_date=requested_end_iso,
                data_status="insufficient_data",
                actual_start_date=actual_start.trade_date,
                actual_end_date=actual_end.trade_date,
                record_count=len(records),
            )

        return PeriodStatistics(
            asset_id=asset_id,
            period=period,
            requested_start_date=requested_start_iso,
            requested_end_date=requested_end_iso,
            actual_start_date=actual_start.trade_date,
            actual_end_date=actual_end.trade_date,
            start_price=decimal_to_output(computed.start_price),
            end_price=decimal_to_output(computed.end_price),
            change_amount=decimal_to_output(computed.change_amount),
            change_pct=decimal_to_output(computed.change_pct),
            period_high=decimal_to_output(computed.period_high),
            period_high_date=computed.period_high_date,
            period_low=decimal_to_output(computed.period_low),
            period_low_date=computed.period_low_date,
            amplitude=decimal_to_output(computed.amplitude),
            max_drawdown_pct=decimal_to_output(computed.max_drawdown_pct),
            max_drawdown_peak_date=computed.max_drawdown_peak_date,
            max_drawdown_trough_date=computed.max_drawdown_trough_date,
            record_count=len(records),
            data_status="ok",
        )

    def _ensure_asset_exists(self, asset_id: int) -> None:
        if self.assets.get_by_id(asset_id) is None:
            raise AssetNotFoundError(f"Asset {asset_id} not found")

    def _latest_record(self, asset_id: int, latest_basis: str) -> DailyPrice | None:
        if latest_basis == TODAY_OPEN:
            return self.prices.get_latest_open_record(asset_id)
        return self.prices.get_latest_complete(asset_id)

    def _complete_record_count(
        self,
        asset_id: int,
        start_date: str,
        end_date: str,
    ) -> int:
        if start_date > end_date:
            return 0
        return len(
            self.prices.list_complete_prices(
                asset_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

    def _empty_anchor_statistics(
        self,
        asset_id: int,
        requested_anchor_date: str,
        latest_basis: str,
        data_status: str,
        actual_anchor_date: str | None = None,
        anchor_price: str | None = None,
        latest_date: str | None = None,
        latest_price: str | None = None,
        latest_is_complete: bool | None = None,
        record_count: int = 0,
    ) -> AnchorStatistics:
        return AnchorStatistics(
            asset_id=asset_id,
            requested_anchor_date=requested_anchor_date,
            actual_anchor_date=actual_anchor_date,
            anchor_price=anchor_price,
            latest_date=latest_date,
            latest_price=latest_price,
            latest_basis=latest_basis,
            latest_is_complete=latest_is_complete,
            change_amount=None,
            change_pct=None,
            record_count=record_count,
            data_status=data_status,
        )

    def _empty_period_statistics(
        self,
        asset_id: int,
        period: str,
        requested_start_date: str,
        requested_end_date: str,
        data_status: str,
        actual_start_date: str | None = None,
        actual_end_date: str | None = None,
        record_count: int = 0,
    ) -> PeriodStatistics:
        return PeriodStatistics(
            asset_id=asset_id,
            period=period,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            actual_start_date=actual_start_date,
            actual_end_date=actual_end_date,
            start_price=None,
            end_price=None,
            change_amount=None,
            change_pct=None,
            period_high=None,
            period_high_date=None,
            period_low=None,
            period_low_date=None,
            amplitude=None,
            max_drawdown_pct=None,
            max_drawdown_peak_date=None,
            max_drawdown_trough_date=None,
            record_count=record_count,
            data_status=data_status,
        )


@dataclass(frozen=True)
class ComputedPeriodValues:
    start_price: Decimal
    end_price: Decimal
    change_amount: Decimal
    change_pct: Decimal
    period_high: Decimal
    period_high_date: str
    period_low: Decimal
    period_low_date: str
    amplitude: Decimal
    max_drawdown_pct: Decimal
    max_drawdown_peak_date: str
    max_drawdown_trough_date: str


def compute_period_values(records: list[DailyPrice]) -> ComputedPeriodValues | None:
    parsed_records = []
    for record in records:
        open_price = parse_decimal(record.open)
        high_price = parse_decimal(record.high)
        low_price = parse_decimal(record.low)
        close_price = parse_decimal(record.close)
        if None in (open_price, high_price, low_price, close_price):
            return None
        parsed_records.append((record, open_price, high_price, low_price, close_price))

    first_record, start_price, _, _, first_close = parsed_records[0]
    last_record, _, _, _, end_price = parsed_records[-1]
    if start_price <= 0 or first_close <= 0:
        return None

    period_high = parsed_records[0][2]
    period_high_date = first_record.trade_date
    period_low = parsed_records[0][3]
    period_low_date = first_record.trade_date
    peak_close = first_close
    peak_date = first_record.trade_date
    max_drawdown_pct = Decimal("0")
    max_drawdown_peak_date = first_record.trade_date
    max_drawdown_trough_date = first_record.trade_date

    for record, _, high_price, low_price, close_price in parsed_records:
        if high_price > period_high:
            period_high = high_price
            period_high_date = record.trade_date
        if low_price < period_low:
            period_low = low_price
            period_low_date = record.trade_date
        if close_price > peak_close:
            peak_close = close_price
            peak_date = record.trade_date
        if peak_close <= 0:
            return None
        drawdown_pct = (close_price - peak_close) / peak_close
        if drawdown_pct < max_drawdown_pct:
            max_drawdown_pct = drawdown_pct
            max_drawdown_peak_date = peak_date
            max_drawdown_trough_date = record.trade_date

    change_amount = end_price - start_price
    change_pct = change_amount / start_price
    amplitude = (period_high - period_low) / start_price
    return ComputedPeriodValues(
        start_price=start_price,
        end_price=end_price,
        change_amount=change_amount,
        change_pct=change_pct,
        period_high=period_high,
        period_high_date=period_high_date,
        period_low=period_low,
        period_low_date=period_low_date,
        amplitude=amplitude,
        max_drawdown_pct=max_drawdown_pct,
        max_drawdown_peak_date=max_drawdown_peak_date,
        max_drawdown_trough_date=max_drawdown_trough_date,
    )


def parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def decimal_to_output(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def subtract_period(end_date: date, period: str) -> date:
    if period == "1w":
        return end_date - timedelta(days=7)
    if period == "1m":
        return subtract_months(end_date, 1)
    if period == "3m":
        return subtract_months(end_date, 3)
    if period == "1y":
        return subtract_months(end_date, 12)
    raise InvalidStatisticsRequest("custom period requires explicit start_date")


def subtract_months(value: date, months: int) -> date:
    target_year = value.year
    target_month = value.month - months
    while target_month <= 0:
        target_month += 12
        target_year -= 1
    target_day = min(value.day, calendar.monthrange(target_year, target_month)[1])
    return date(target_year, target_month, target_day)
