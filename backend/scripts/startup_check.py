from __future__ import annotations

import argparse
import json

from app.services.startup_check_service import StartupCheckReport, StartupCheckService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local database and data freshness.")
    parser.add_argument("--database-path", default=None)
    parser.add_argument("--market", default=None)
    parser.add_argument("--stale-days", type=int, default=3)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = StartupCheckService(database_path=args.database_path).run(
        stale_days=args.stale_days,
        market=args.market,
    )

    if args.as_json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_text_report(report)

    return 0 if report.ok else 1


def print_text_report(report: StartupCheckReport) -> None:
    print("Stock Reminder startup check")
    print(f"Checked at: {report.checked_at}")
    print(f"Database: {report.database_path}")
    print(f"Database exists: {yes_no(report.database_exists)}")
    print(f"Schema OK: {yes_no(report.schema_ok)}")

    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"- {error}")

    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings:
            print(f"- {warning}")

    print("\nSummary:")
    print(f"- Total assets: {report.total_asset_count}")
    print(f"- Active assets: {report.active_asset_count}")
    print(f"- Assets without prices: {report.assets_without_prices}")
    print(f"- Stale assets: {report.stale_asset_count}")
    print(f"- Today open-only records: {report.today_open_only_count}")
    print(f"- Recent failed sync jobs: {len(report.recent_failed_sync_jobs)}")

    if report.asset_statuses:
        print("\nAsset freshness:")
        for item in report.asset_statuses:
            latest_complete = item.latest_complete_date or "none"
            latest_open = item.latest_open_date or "none"
            stale = "stale" if item.is_stale else "fresh"
            print(
                f"- {item.symbol:<12} {item.market:<6} "
                f"complete={latest_complete:<10} open={latest_open:<10} "
                f"rows={item.price_count:<5} {stale}"
            )

    if report.recent_failed_sync_jobs:
        print("\nRecent failed sync jobs:")
        for job in report.recent_failed_sync_jobs[:5]:
            print(
                f"- #{job['id']} {job['job_type']} {job['provider_symbol']} "
                f"started={job['started_at']} error={job['error_message']}"
            )


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())
