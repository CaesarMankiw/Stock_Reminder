from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlertRuleInput:
    asset_id: int
    name: str | None
    rule_type: str
    anchor_date: str | None = None
    period: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    latest_basis: str = "latest_close"
    trigger_metric: str = "change_pct"
    upper_threshold_pct: str | None = None
    lower_threshold_pct: str | None = None
    frequency: str = "once_per_data_date"
    is_enabled: bool = True


@dataclass(frozen=True)
class AlertRule(AlertRuleInput):
    id: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "anchor_date": self.anchor_date,
            "period": self.period,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "latest_basis": self.latest_basis,
            "trigger_metric": self.trigger_metric,
            "upper_threshold_pct": self.upper_threshold_pct,
            "lower_threshold_pct": self.lower_threshold_pct,
            "frequency": self.frequency,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class AlertEventInput:
    rule_id: int
    asset_id: int
    rule_type: str
    trigger_direction: str
    data_date: str
    trigger_value_pct: str
    threshold_pct: str
    price_basis: str
    statistics_payload: str
    message: str


@dataclass(frozen=True)
class AlertEvent(AlertEventInput):
    id: int = 0
    created_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "asset_id": self.asset_id,
            "rule_type": self.rule_type,
            "trigger_direction": self.trigger_direction,
            "data_date": self.data_date,
            "trigger_value_pct": self.trigger_value_pct,
            "threshold_pct": self.threshold_pct,
            "price_basis": self.price_basis,
            "statistics_payload": self.statistics_payload,
            "message": self.message,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class AlertSkippedRule:
    rule_id: int
    asset_id: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "asset_id": self.asset_id,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class AlertCheckSummary:
    checked_rule_count: int
    triggered_event_count: int
    skipped_rule_count: int
    created_events: list[AlertEvent]
    skipped_rules: list[AlertSkippedRule]

    def to_dict(self) -> dict[str, object]:
        return {
            "checked_rule_count": self.checked_rule_count,
            "triggered_event_count": self.triggered_event_count,
            "skipped_rule_count": self.skipped_rule_count,
            "created_events": [event.to_dict() for event in self.created_events],
            "skipped_rules": [skipped.to_dict() for skipped in self.skipped_rules],
        }
