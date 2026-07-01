from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from app.db.connection import connect, get_database_path
from app.db.repositories import AssetRepository, DailyPriceRepository
from app.db.schema import initialize_schema
from app.models.asset import Asset
from app.models.statistics import AnchorStatistics, PeriodStatistics
from app.services.statistics_service import StatisticsService, subtract_period


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "current_statistics_validation_report.md"
DEFAULT_SYMBOLS = ["513180.SH", "BTC-USD"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify local statistics calculations.")
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Asset symbol to verify. Can be provided multiple times.",
    )
    parser.add_argument("--period", default="1y", choices=["1w", "1m", "3m", "1y"])
    parser.add_argument("--anchor-date", default=None, help="Anchor date in YYYY-MM-DD format.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbols = args.symbol or DEFAULT_SYMBOLS
    anchor_date = date.fromisoformat(args.anchor_date) if args.anchor_date else None

    with connect() as connection:
        initialize_schema(connection)
        assets = AssetRepository(connection)
        prices = DailyPriceRepository(connection)
        selected_assets = [assets.get_by_symbol(symbol) for symbol in symbols]
        latest_dates = {
            asset.symbol: latest.trade_date
            for asset in selected_assets
            if asset is not None
            if (latest := prices.get_latest_complete(asset.id)) is not None
        }

    service = StatisticsService()
    try:
        sections = [
            "# 当前统计计算验证报告",
            "",
            f"生成日期：{date.today().isoformat()}",
            "",
            "## 验证范围",
            "",
            "- 默认验证样例为一个 ETF 和一个虚拟货币，均来自当前关注资产。",
            "- 数据来源：本地 SQLite `daily_prices` 表，价格数据来自资产默认免费 provider。",
            f"- 数据库：`{get_database_path()}`",
            "- 统计默认只使用 `is_complete=1` 的完整日线。",
            "- `today_open` 只在锚点统计中作为临时最新价口径使用。",
            "",
            "## 样例结果",
            "",
        ]
        for symbol, asset in zip(symbols, selected_assets, strict=False):
            if asset is None:
                sections.extend(missing_asset_section(symbol))
                continue
            latest_date_value = latest_dates.get(asset.symbol)
            if latest_date_value is None:
                sections.extend(no_complete_data_section(asset))
                continue
            latest_date = date.fromisoformat(latest_date_value)
            requested_anchor = anchor_date or subtract_period(latest_date, "1y")
            anchor = service.get_anchor_statistics(asset.id, requested_anchor)
            today_open = service.get_anchor_statistics(asset.id, requested_anchor, "today_open")
            period = service.get_period_statistics(asset.id, args.period)
            sections.extend(asset_section(asset, anchor, today_open, period))
    finally:
        service.close()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote statistics validation report: {output_path}")
    return 0


def missing_asset_section(symbol: str) -> list[str]:
    return [
        f"### 未找到资产：{symbol}",
        "",
        "本地 `assets` 表没有该 symbol，请先执行 `python scripts/seed_assets.py`。",
        "",
    ]


def no_complete_data_section(asset: Asset) -> list[str]:
    return [
        f"### {asset.symbol}",
        "",
        "本地 `daily_prices` 表没有该资产的完整日线，统计状态会是 `insufficient_data`。",
        "",
    ]


def asset_section(
    asset: Asset,
    anchor: AnchorStatistics,
    today_open: AnchorStatistics,
    period: PeriodStatistics,
) -> list[str]:
    return [
        f"### {asset.symbol}",
        "",
        f"- 名称：{asset.name}",
        f"- 市场/类型：{asset.market} / {asset.asset_type}",
        f"- 免费数据源：`{asset.default_provider}`，provider symbol：`{asset.provider_symbol}`",
        "",
        "#### 锚点统计：latest_close",
        "",
        anchor_table(anchor),
        "",
        "#### 锚点统计：today_open",
        "",
        anchor_table(today_open),
        "",
        f"#### 区间统计：{period.period}",
        "",
        period_table(period),
        "",
    ]


def anchor_table(statistics: AnchorStatistics) -> str:
    rows = [
        ("data_status", statistics.data_status),
        ("requested_anchor_date", statistics.requested_anchor_date),
        ("actual_anchor_date", statistics.actual_anchor_date),
        ("anchor_price", statistics.anchor_price),
        ("latest_date", statistics.latest_date),
        ("latest_price", statistics.latest_price),
        ("latest_basis", statistics.latest_basis),
        ("latest_is_complete", statistics.latest_is_complete),
        ("change_amount", statistics.change_amount),
        ("change_pct", statistics.change_pct),
        ("record_count", statistics.record_count),
    ]
    return markdown_table(rows)


def period_table(statistics: PeriodStatistics) -> str:
    rows = [
        ("data_status", statistics.data_status),
        ("requested_start_date", statistics.requested_start_date),
        ("requested_end_date", statistics.requested_end_date),
        ("actual_start_date", statistics.actual_start_date),
        ("actual_end_date", statistics.actual_end_date),
        ("start_price", statistics.start_price),
        ("end_price", statistics.end_price),
        ("change_amount", statistics.change_amount),
        ("change_pct", statistics.change_pct),
        ("period_high", statistics.period_high),
        ("period_high_date", statistics.period_high_date),
        ("period_low", statistics.period_low),
        ("period_low_date", statistics.period_low_date),
        ("amplitude", statistics.amplitude),
        ("max_drawdown_pct", statistics.max_drawdown_pct),
        ("max_drawdown_peak_date", statistics.max_drawdown_peak_date),
        ("max_drawdown_trough_date", statistics.max_drawdown_trough_date),
        ("record_count", statistics.record_count),
    ]
    return markdown_table(rows)


def markdown_table(rows: list[tuple[str, object]]) -> str:
    lines = ["| 字段 | 值 |", "| --- | --- |"]
    for key, value in rows:
        lines.append(f"| `{key}` | {'' if value is None else value} |")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
