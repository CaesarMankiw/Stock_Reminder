from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.db.connection import connect
from app.db.repositories import (
    AlertEventRepository,
    AlertRuleRepository,
    AssetRepository,
)
from app.db.schema import initialize_schema
from app.models.alert import (
    AlertCheckSummary,
    AlertEvent,
    AlertEventInput,
    AlertRule,
    AlertRuleInput,
    AlertSkippedRule,
)
from app.models.statistics import AnchorStatistics, PeriodStatistics
from app.services.statistics_service import LATEST_CLOSE, TODAY_OPEN, StatisticsService


VALID_RULE_TYPES = {"anchor", "period"}
VALID_PERIODS = {"1w", "1m", "3m", "1y", "custom"}
VALID_LATEST_BASIS = {LATEST_CLOSE, TODAY_OPEN}
VALID_FREQUENCIES = {"once_per_data_date"}
CHANGE_PCT = "change_pct"
MAX_DRAWDOWN_PCT = "max_drawdown_pct"
VALID_TRIGGER_METRICS = {CHANGE_PCT, MAX_DRAWDOWN_PCT}
PERIOD_CHANGE_BASIS = "period_change"
PERIOD_DRAWDOWN_BASIS = "period_drawdown"


class AlertRuleNotFoundError(ValueError):
    pass


class AlertAssetNotFoundError(ValueError):
    pass


class InvalidAlertRuleError(ValueError):
    pass


class AlertService:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.connection = connect(database_path)
        initialize_schema(self.connection)
        self.assets = AssetRepository(self.connection)
        self.rules = AlertRuleRepository(self.connection)
        self.events = AlertEventRepository(self.connection)
        self.statistics = StatisticsService(database_path)

    def close(self) -> None:
        self.statistics.close()
        self.connection.close()

    def create_rule(self, rule_input: AlertRuleInput) -> AlertRule:
        normalized = self._validate_rule_input(rule_input)
        return self.rules.create_rule(normalized)

    def update_rule(self, rule_id: int, rule_input: AlertRuleInput) -> AlertRule:
        if self.rules.get_by_id(rule_id) is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        normalized = self._validate_rule_input(rule_input)
        updated = self.rules.update_rule(rule_id, normalized)
        if updated is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        return updated

    def delete_rule(self, rule_id: int) -> bool:
        if not self.rules.disable_rule(rule_id):
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        return True

    def get_rule(self, rule_id: int) -> AlertRule:
        rule = self.rules.get_by_id(rule_id)
        if rule is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        return rule

    def list_rules(
        self,
        asset_id: int | None = None,
        enabled_only: bool = False,
    ) -> list[AlertRule]:
        if asset_id is not None:
            self._ensure_asset_exists(asset_id)
        return self.rules.list_rules(asset_id=asset_id, enabled_only=enabled_only)

    def list_events(
        self,
        asset_id: int | None = None,
        rule_id: int | None = None,
        limit: int = 100,
    ) -> list[AlertEvent]:
        if asset_id is not None:
            self._ensure_asset_exists(asset_id)
        if rule_id is not None and self.rules.get_by_id(rule_id) is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        return self.events.list_events(
            asset_id=asset_id,
            rule_id=rule_id,
            limit=max(1, min(limit, 500)),
        )

    def check_alerts(self, asset_id: int | None = None) -> AlertCheckSummary:
        if asset_id is not None:
            self._ensure_asset_exists(asset_id)
        rules = self.rules.list_rules(asset_id=asset_id, enabled_only=True)
        created_events: list[AlertEvent] = []
        skipped_rules: list[AlertSkippedRule] = []

        for rule in rules:
            events, skipped = self.check_rule(rule)
            created_events.extend(events)
            skipped_rules.extend(skipped)

        return AlertCheckSummary(
            checked_rule_count=len(rules),
            triggered_event_count=len(created_events),
            skipped_rule_count=len(skipped_rules),
            created_events=created_events,
            skipped_rules=skipped_rules,
        )

    def check_rule(self, rule: AlertRule) -> tuple[list[AlertEvent], list[AlertSkippedRule]]:
        if not rule.is_enabled:
            return [], [skipped(rule, "rule_disabled")]

        try:
            statistics = self._statistics_for_rule(rule)
        except ValueError as exc:
            return [], [skipped(rule, str(exc))]

        if statistics.data_status != "ok":
            return [], [skipped(rule, f"statistics_{statistics.data_status}")]

        trigger_value = parse_decimal(trigger_metric_value(rule, statistics))
        if trigger_value is None:
            return [], [skipped(rule, "statistics_trigger_metric_missing")]

        data_date = statistics.latest_date if isinstance(statistics, AnchorStatistics) else statistics.actual_end_date
        if data_date is None:
            return [], [skipped(rule, "statistics_data_date_missing")]

        created_events: list[AlertEvent] = []
        duplicate_count = 0
        upper_threshold = parse_decimal(rule.upper_threshold_pct)
        lower_threshold = parse_decimal(rule.lower_threshold_pct)

        if upper_threshold is not None and trigger_value >= upper_threshold:
            event = self._create_event(
                rule=rule,
                statistics=statistics,
                trigger_direction="upper",
                data_date=data_date,
                trigger_value_pct=trigger_value,
                threshold_pct=upper_threshold,
            )
            if event is None:
                duplicate_count += 1
            else:
                created_events.append(event)

        if lower_threshold is not None and trigger_value <= lower_threshold:
            event = self._create_event(
                rule=rule,
                statistics=statistics,
                trigger_direction="lower",
                data_date=data_date,
                trigger_value_pct=trigger_value,
                threshold_pct=lower_threshold,
            )
            if event is None:
                duplicate_count += 1
            else:
                created_events.append(event)

        if created_events:
            return created_events, []
        if duplicate_count:
            return [], [skipped(rule, "duplicate_event")]
        return [], [skipped(rule, "threshold_not_reached")]

    def _create_event(
        self,
        rule: AlertRule,
        statistics: AnchorStatistics | PeriodStatistics,
        trigger_direction: str,
        data_date: str,
        trigger_value_pct: Decimal,
        threshold_pct: Decimal,
    ) -> AlertEvent | None:
        asset = self.assets.get_by_id(rule.asset_id)
        if asset is None:
            raise AlertAssetNotFoundError(f"Asset {rule.asset_id} not found")
        if isinstance(statistics, AnchorStatistics):
            price_basis = statistics.latest_basis
        elif rule.trigger_metric == MAX_DRAWDOWN_PCT:
            price_basis = PERIOD_DRAWDOWN_BASIS
        else:
            price_basis = PERIOD_CHANGE_BASIS
        message = format_alert_message(
            symbol=asset.symbol,
            price_basis=price_basis,
            trigger_value_pct=trigger_value_pct,
            trigger_direction=trigger_direction,
            threshold_pct=threshold_pct,
            rule=rule,
        )
        return self.events.create_event(
            AlertEventInput(
                rule_id=rule.id,
                asset_id=rule.asset_id,
                rule_type=rule.rule_type,
                trigger_direction=trigger_direction,
                data_date=data_date,
                trigger_value_pct=decimal_to_output(trigger_value_pct),
                threshold_pct=decimal_to_output(threshold_pct),
                price_basis=price_basis,
                statistics_payload=json.dumps(statistics.to_dict(), ensure_ascii=False, sort_keys=True),
                message=message,
            )
        )

    def _statistics_for_rule(self, rule: AlertRule) -> AnchorStatistics | PeriodStatistics:
        if rule.rule_type == "anchor":
            if rule.anchor_date is None:
                raise InvalidAlertRuleError("anchor_date_missing")
            return self.statistics.get_anchor_statistics(
                asset_id=rule.asset_id,
                anchor_date=date.fromisoformat(rule.anchor_date),
                latest_basis=rule.latest_basis,
            )
        if rule.rule_type == "period":
            if rule.period is None:
                raise InvalidAlertRuleError("period_missing")
            return self.statistics.get_period_statistics(
                asset_id=rule.asset_id,
                period=rule.period,
                start_date=parse_date(rule.start_date),
                end_date=parse_date(rule.end_date),
            )
        raise InvalidAlertRuleError(f"Unsupported rule_type {rule.rule_type}")

    def _validate_rule_input(self, rule_input: AlertRuleInput) -> AlertRuleInput:
        self._ensure_asset_exists(rule_input.asset_id)
        if rule_input.rule_type not in VALID_RULE_TYPES:
            raise InvalidAlertRuleError("rule_type must be anchor or period")
        if rule_input.frequency not in VALID_FREQUENCIES:
            raise InvalidAlertRuleError("frequency must be once_per_data_date")
        if rule_input.latest_basis not in VALID_LATEST_BASIS:
            raise InvalidAlertRuleError("latest_basis must be latest_close or today_open")
        if rule_input.trigger_metric not in VALID_TRIGGER_METRICS:
            raise InvalidAlertRuleError("trigger_metric must be change_pct or max_drawdown_pct")

        upper_threshold = parse_decimal(rule_input.upper_threshold_pct)
        lower_threshold = parse_decimal(rule_input.lower_threshold_pct)
        if rule_input.upper_threshold_pct is not None and upper_threshold is None:
            raise InvalidAlertRuleError("upper_threshold_pct must be a decimal string")
        if rule_input.lower_threshold_pct is not None and lower_threshold is None:
            raise InvalidAlertRuleError("lower_threshold_pct must be a decimal string")
        if upper_threshold is None and lower_threshold is None:
            raise InvalidAlertRuleError("at least one threshold is required")
        if upper_threshold is not None and upper_threshold <= 0:
            raise InvalidAlertRuleError("upper_threshold_pct must be greater than 0")
        if lower_threshold is not None and lower_threshold >= 0:
            raise InvalidAlertRuleError("lower_threshold_pct must be less than 0")

        if rule_input.rule_type == "anchor":
            if rule_input.anchor_date is None:
                raise InvalidAlertRuleError("anchor_date is required for anchor rules")
            parse_required_date(rule_input.anchor_date, "anchor_date")
            return AlertRuleInput(
                asset_id=rule_input.asset_id,
                name=rule_input.name,
                rule_type="anchor",
                anchor_date=rule_input.anchor_date,
                period=None,
                start_date=None,
                end_date=None,
                latest_basis=rule_input.latest_basis,
                trigger_metric=CHANGE_PCT,
                upper_threshold_pct=decimal_to_output(upper_threshold),
                lower_threshold_pct=decimal_to_output(lower_threshold),
                frequency=rule_input.frequency,
                is_enabled=rule_input.is_enabled,
            )

        period = rule_input.period
        if period not in VALID_PERIODS:
            raise InvalidAlertRuleError("period must be 1w, 1m, 3m, 1y, or custom")
        if period == "custom" and rule_input.start_date is None:
            raise InvalidAlertRuleError("start_date is required when period=custom")
        if rule_input.start_date is not None:
            parse_required_date(rule_input.start_date, "start_date")
        if rule_input.end_date is not None:
            parse_required_date(rule_input.end_date, "end_date")
        if (
            rule_input.start_date is not None
            and rule_input.end_date is not None
            and rule_input.start_date > rule_input.end_date
        ):
            raise InvalidAlertRuleError("start_date must be earlier than or equal to end_date")

        return AlertRuleInput(
            asset_id=rule_input.asset_id,
            name=rule_input.name,
            rule_type="period",
            anchor_date=None,
            period=period,
            start_date=rule_input.start_date,
            end_date=rule_input.end_date,
            latest_basis=LATEST_CLOSE,
            trigger_metric=rule_input.trigger_metric,
            upper_threshold_pct=decimal_to_output(upper_threshold),
            lower_threshold_pct=decimal_to_output(lower_threshold),
            frequency=rule_input.frequency,
            is_enabled=rule_input.is_enabled,
        )

    def _ensure_asset_exists(self, asset_id: int) -> None:
        if self.assets.get_by_id(asset_id) is None:
            raise AlertAssetNotFoundError(f"Asset {asset_id} not found")


def skipped(rule: AlertRule, reason: str) -> AlertSkippedRule:
    return AlertSkippedRule(rule_id=rule.id, asset_id=rule.asset_id, reason=reason)


def parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def decimal_to_output(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def parse_required_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidAlertRuleError(f"{field_name} must be YYYY-MM-DD") from exc


def trigger_metric_value(
    rule: AlertRule,
    statistics: AnchorStatistics | PeriodStatistics,
) -> str | None:
    if isinstance(statistics, AnchorStatistics):
        return statistics.change_pct
    if rule.trigger_metric == MAX_DRAWDOWN_PCT:
        return statistics.max_drawdown_pct
    return statistics.change_pct


def format_alert_message(
    symbol: str,
    price_basis: str,
    trigger_value_pct: Decimal,
    trigger_direction: str,
    threshold_pct: Decimal,
    rule: AlertRule,
) -> str:
    if rule.rule_type == "anchor":
        context = f"since {rule.anchor_date}"
    elif rule.period == "custom":
        context = f"for {rule.start_date} to {rule.end_date or 'latest'}"
    else:
        context = f"for {rule.period}"
    return (
        f"{symbol} {price_basis} {percent_text(trigger_value_pct)} "
        f"reached {trigger_direction} threshold {percent_text(threshold_pct)} {context}."
    )


def percent_text(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"
