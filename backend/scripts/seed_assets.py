from __future__ import annotations

from app.db.seed_alert_rules import (
    disable_legacy_verification_rules,
    disable_rules_for_inactive_assets,
    seed_default_alert_rules,
)
from app.services.sync_service import SyncService


def main() -> int:
    service = SyncService()
    try:
        assets = service.seed_default_assets()
        deactivated_count = service.deactivate_assets_except_default()
        disabled_rule_count = disable_rules_for_inactive_assets(service.connection)
        disabled_verification_count = disable_legacy_verification_rules(service.connection)
        default_rule_count = seed_default_alert_rules(service.connection)
    finally:
        service.close()

    print(f"Seeded {len(assets)} assets")
    print(f"Deactivated {deactivated_count} non-watchlist assets")
    print(f"Disabled {disabled_rule_count} rules for inactive assets")
    print(f"Disabled {disabled_verification_count} verification rules")
    print(f"Created {default_rule_count} default alert rules")
    for asset in assets:
        print(f"{asset.id:>3} {asset.symbol:<12} {asset.default_provider:<8} {asset.provider_symbol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
