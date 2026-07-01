from __future__ import annotations

from app.db.connection import connect
from app.db.repositories import AlertEventRepository, AlertRuleRepository, AssetRepository
from app.db.schema import initialize_schema
from app.models.alert import AlertEventInput, AlertRuleInput
from app.models.asset import SeedAsset


def test_alert_rule_repository_crud_and_soft_delete(tmp_path) -> None:
    with connect(tmp_path / "alerts.sqlite3") as connection:
        initialize_schema(connection)
        asset = seed_asset(connection)
        rules = AlertRuleRepository(connection)

        created = rules.create_rule(
            AlertRuleInput(
                asset_id=asset.id,
                name="AAPL +10%",
                rule_type="anchor",
                anchor_date="2026-06-01",
                upper_threshold_pct="0.10",
            )
        )
        updated = rules.update_rule(
            created.id,
            AlertRuleInput(
                asset_id=asset.id,
                name="AAPL +20%",
                rule_type="anchor",
                anchor_date="2026-06-01",
                upper_threshold_pct="0.20",
                is_enabled=False,
            ),
        )
        enabled = rules.list_rules(enabled_only=True)
        disabled = rules.list_rules(asset_id=asset.id, enabled_only=False)
        deleted = rules.disable_rule(created.id)
        after_delete = rules.get_by_id(created.id)

    assert created.id > 0
    assert updated is not None
    assert updated.upper_threshold_pct == "0.20"
    assert enabled == []
    assert len(disabled) == 1
    assert deleted is True
    assert after_delete is not None
    assert after_delete.is_enabled is False


def test_alert_event_repository_writes_and_deduplicates(tmp_path) -> None:
    with connect(tmp_path / "alerts.sqlite3") as connection:
        initialize_schema(connection)
        asset = seed_asset(connection)
        rule = AlertRuleRepository(connection).create_rule(
            AlertRuleInput(
                asset_id=asset.id,
                name="AAPL +10%",
                rule_type="anchor",
                anchor_date="2026-06-01",
                upper_threshold_pct="0.10",
            )
        )
        events = AlertEventRepository(connection)
        event_input = AlertEventInput(
            rule_id=rule.id,
            asset_id=asset.id,
            rule_type="anchor",
            trigger_direction="upper",
            data_date="2026-06-10",
            trigger_value_pct="0.2",
            threshold_pct="0.1",
            price_basis="latest_close",
            statistics_payload="{}",
            message="AAPL triggered",
        )

        first = events.create_event(event_input)
        duplicate = events.create_event(event_input)
        listed = events.list_events(asset_id=asset.id, rule_id=rule.id)

    assert first is not None
    assert first.id > 0
    assert duplicate is None
    assert len(listed) == 1
    assert listed[0].trigger_direction == "upper"


def seed_asset(connection):
    return AssetRepository(connection).upsert_seed_asset(
        SeedAsset(
            symbol="AAPL.US",
            name="Apple Inc.",
            asset_type="stock",
            market="US",
            currency="USD",
            timezone="America/New_York",
            default_provider="yfinance",
            provider_symbol="AAPL",
        )
    )
