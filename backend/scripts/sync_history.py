from __future__ import annotations

import argparse

from app.services.sync_service import SyncService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize historical OHLCV data.")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--market", default=None)
    parser.add_argument("--asset-id", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = SyncService()
    try:
        results = service.sync_history(years=args.years, market=args.market, asset_id=args.asset_id)
    finally:
        service.close()

    for result in results:
        message = (
            f"{result.asset_symbol:<12} {result.job_type:<12} "
            f"{result.status:<8} rows={result.row_count}"
        )
        if result.error_message:
            message += f" error={result.error_message}"
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
