from __future__ import annotations

import argparse
from datetime import date

from app.services.sync_service import SyncService, yesterday_utc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync complete OHLCV for a target date.")
    parser.add_argument("--market", default=None)
    parser.add_argument("--asset-id", type=int, default=None)
    parser.add_argument(
        "--date",
        dest="target_date",
        default=None,
        help="YYYY-MM-DD; defaults to yesterday UTC to avoid incomplete candles.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_date = date.fromisoformat(args.target_date) if args.target_date else yesterday_utc()
    service = SyncService()
    try:
        results = service.sync_close(target_date=target_date, market=args.market, asset_id=args.asset_id)
    finally:
        service.close()

    for result in results:
        message = (
            f"{result.asset_symbol:<12} {result.job_type:<10} "
            f"{result.status:<8} rows={result.row_count}"
        )
        if result.error_message:
            message += f" error={result.error_message}"
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
