from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnchorStatistics:
    asset_id: int
    requested_anchor_date: str
    actual_anchor_date: str | None
    anchor_price: str | None
    latest_date: str | None
    latest_price: str | None
    latest_basis: str
    latest_is_complete: bool | None
    change_amount: str | None
    change_pct: str | None
    record_count: int
    data_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "requested_anchor_date": self.requested_anchor_date,
            "actual_anchor_date": self.actual_anchor_date,
            "anchor_price": self.anchor_price,
            "latest_date": self.latest_date,
            "latest_price": self.latest_price,
            "latest_basis": self.latest_basis,
            "latest_is_complete": self.latest_is_complete,
            "change_amount": self.change_amount,
            "change_pct": self.change_pct,
            "record_count": self.record_count,
            "data_status": self.data_status,
        }


@dataclass(frozen=True)
class PeriodStatistics:
    asset_id: int
    period: str
    requested_start_date: str
    requested_end_date: str
    actual_start_date: str | None
    actual_end_date: str | None
    start_price: str | None
    end_price: str | None
    change_amount: str | None
    change_pct: str | None
    period_high: str | None
    period_high_date: str | None
    period_low: str | None
    period_low_date: str | None
    amplitude: str | None
    max_drawdown_pct: str | None
    max_drawdown_peak_date: str | None
    max_drawdown_trough_date: str | None
    record_count: int
    data_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "period": self.period,
            "requested_start_date": self.requested_start_date,
            "requested_end_date": self.requested_end_date,
            "actual_start_date": self.actual_start_date,
            "actual_end_date": self.actual_end_date,
            "start_price": self.start_price,
            "end_price": self.end_price,
            "change_amount": self.change_amount,
            "change_pct": self.change_pct,
            "period_high": self.period_high,
            "period_high_date": self.period_high_date,
            "period_low": self.period_low,
            "period_low_date": self.period_low_date,
            "amplitude": self.amplitude,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_drawdown_peak_date": self.max_drawdown_peak_date,
            "max_drawdown_trough_date": self.max_drawdown_trough_date,
            "record_count": self.record_count,
            "data_status": self.data_status,
        }
