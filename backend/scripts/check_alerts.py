from __future__ import annotations

import argparse

from app.services.alert_service import AlertService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run alert checks once.")
    parser.add_argument("--asset-id", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = AlertService()
    try:
        summary = service.check_alerts(asset_id=args.asset_id)
    finally:
        service.close()

    print(f"checked_rule_count={summary.checked_rule_count}")
    print(f"triggered_event_count={summary.triggered_event_count}")
    print(f"skipped_rule_count={summary.skipped_rule_count}")
    for event in summary.created_events:
        print(
            f"event id={event.id} rule={event.rule_id} "
            f"direction={event.trigger_direction} data_date={event.data_date} "
            f"value={event.trigger_value_pct} threshold={event.threshold_pct}"
        )
    for skipped in summary.skipped_rules:
        print(f"skipped rule={skipped.rule_id} reason={skipped.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
