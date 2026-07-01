from __future__ import annotations

import argparse
from pathlib import Path

from app.services.data_source_spike import (
    result_counts,
    run_validation,
    write_json_results,
    write_markdown_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate free market-data providers for the current watchlist.",
    )
    parser.add_argument("--years", type=int, default=5, help="History span to request.")
    parser.add_argument(
        "--provider",
        choices=("all", "yfinance", "akshare", "ccxt"),
        default="all",
        help="Provider to validate.",
    )
    parser.add_argument(
        "--asset-type",
        choices=("all", "stock", "etf", "crypto"),
        default="all",
        help="Asset type to validate.",
    )
    parser.add_argument(
        "--output",
        default="data/spike_results/latest.json",
        help="JSON output path, relative to backend/ when run from backend.",
    )
    parser.add_argument(
        "--report",
        default="../docs/current_data_source_validation_report.md",
        help="Markdown report output path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = run_validation(
        years=args.years,
        provider=args.provider,
        asset_type=args.asset_type,
    )

    for result in results:
        message = (
            f"{result.asset_symbol:<12} "
            f"{result.provider:<8} "
            f"{result.provider_symbol:<12} "
            f"{result.status.value:<22} "
            f"rows={result.row_count}"
        )
        if result.error_message:
            message += f" error={result.error_message}"
        print(message)

    write_json_results(results, Path(args.output))
    write_markdown_report(results, Path(args.report))

    counts = result_counts(results)
    print(f"Summary: {counts}")
    print(f"JSON output: {args.output}")
    print(f"Markdown report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
