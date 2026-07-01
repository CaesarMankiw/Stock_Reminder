from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.providers.akshare_provider import AkShareProvider
from app.providers.base import MarketDataProvider
from app.providers.ccxt_provider import CcxtProvider
from app.providers.models import (
    AssetValidationTarget,
    OhlcvRecord,
    ProviderValidationResult,
    ValidationStatus,
)
from app.providers.yfinance_provider import YFinanceProvider


DEFAULT_ASSET_TARGETS: tuple[AssetValidationTarget, ...] = (
    AssetValidationTarget("513180.SH", "etf", "yfinance", "513180.SS", "CNY"),
    AssetValidationTarget("159915.SZ", "etf", "yfinance", "159915.SZ", "CNY"),
    AssetValidationTarget("588000.SH", "etf", "yfinance", "588000.SS", "CNY"),
    AssetValidationTarget("510500.SH", "etf", "yfinance", "510500.SS", "CNY"),
    AssetValidationTarget("510300.SH", "etf", "yfinance", "510300.SS", "CNY"),
    AssetValidationTarget("159941.SZ", "etf", "yfinance", "159941.SZ", "CNY"),
    AssetValidationTarget("513500.SH", "etf", "yfinance", "513500.SS", "CNY"),
    AssetValidationTarget("BTC-USD", "crypto", "yfinance", "BTC-USD", "USD"),
    AssetValidationTarget("ETH-USD", "crypto", "yfinance", "ETH-USD", "USD"),
    AssetValidationTarget("BNB-USD", "crypto", "yfinance", "BNB-USD", "USD"),
)


def subtract_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year - years)


def provider_registry() -> dict[str, MarketDataProvider]:
    return {
        "yfinance": YFinanceProvider(),
        "akshare": AkShareProvider(),
        "ccxt": CcxtProvider(),
    }


def select_targets(
    provider: str = "all",
    asset_type: str = "all",
    targets: Iterable[AssetValidationTarget] = DEFAULT_ASSET_TARGETS,
) -> list[AssetValidationTarget]:
    selected: list[AssetValidationTarget] = []
    for target in targets:
        if provider != "all" and target.provider != provider:
            continue
        if asset_type != "all" and target.asset_type != asset_type:
            continue
        selected.append(target)
    return selected


def run_validation(
    years: int = 5,
    provider: str = "all",
    asset_type: str = "all",
    end_date: date | None = None,
    targets: Iterable[AssetValidationTarget] = DEFAULT_ASSET_TARGETS,
    registry: dict[str, MarketDataProvider] | None = None,
) -> list[ProviderValidationResult]:
    requested_end_date = end_date or datetime.now(timezone.utc).date()
    requested_start_date = subtract_years(requested_end_date, years)
    providers = registry or provider_registry()
    results: list[ProviderValidationResult] = []

    for target in select_targets(provider, asset_type, targets):
        market_provider = providers.get(target.provider)
        if market_provider is None:
            results.append(
                failure_result(
                    target,
                    requested_start_date,
                    requested_end_date,
                    ValidationStatus.PROVIDER_ERROR,
                    f"Provider {target.provider!r} is not registered",
                )
            )
            continue

        try:
            records = market_provider.fetch_daily_ohlcv(
                provider_symbol=target.provider_symbol,
                start_date=requested_start_date,
                end_date=requested_end_date,
                asset_type=target.asset_type,
            )
        except Exception as exc:  # noqa: BLE001 - spike must record all provider failures.
            results.append(
                failure_result(
                    target,
                    requested_start_date,
                    requested_end_date,
                    classify_exception(exc),
                    str(exc),
                )
            )
            continue

        results.append(
            validate_records(
                target=target,
                records=records,
                requested_start_date=requested_start_date,
                requested_end_date=requested_end_date,
            )
        )

    return results


def validate_records(
    target: AssetValidationTarget,
    records: list[OhlcvRecord],
    requested_start_date: date,
    requested_end_date: date,
) -> ProviderValidationResult:
    if not records:
        return failure_result(
            target,
            requested_start_date,
            requested_end_date,
            ValidationStatus.SYMBOL_NOT_SUPPORTED,
            "Provider returned no daily records",
        )

    sorted_records = sorted(records, key=lambda record: record.trade_date)
    actual_start_date = sorted_records[0].trade_date
    actual_end_date = sorted_records[-1].trade_date
    has_open = any(record.open is not None for record in sorted_records)
    has_high = any(record.high is not None for record in sorted_records)
    has_low = any(record.low is not None for record in sorted_records)
    has_close = any(record.close is not None for record in sorted_records)
    has_volume = any(record.volume is not None for record in sorted_records)
    supports_today_open = any(
        record.trade_date == requested_end_date and record.open is not None
        for record in sorted_records
    )

    status = ValidationStatus.SUCCESS
    error_message = None
    if not all((has_open, has_high, has_low, has_close)):
        status = ValidationStatus.FIELD_MISSING
        error_message = "At least one required OHLC field is missing"
    elif (actual_start_date - requested_start_date).days > 7:
        status = ValidationStatus.HISTORY_INSUFFICIENT
        error_message = (
            f"Actual start date {actual_start_date.isoformat()} is after "
            f"requested start date {requested_start_date.isoformat()}"
        )

    return ProviderValidationResult(
        asset_symbol=target.asset_symbol,
        asset_type=target.asset_type,
        provider=target.provider,
        provider_symbol=target.provider_symbol,
        status=status,
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
        actual_start_date=actual_start_date,
        actual_end_date=actual_end_date,
        row_count=len(sorted_records),
        has_open=has_open,
        has_high=has_high,
        has_low=has_low,
        has_close=has_close,
        has_volume=has_volume,
        supports_today_open=supports_today_open,
        error_message=error_message,
    )


def failure_result(
    target: AssetValidationTarget,
    requested_start_date: date,
    requested_end_date: date,
    status: ValidationStatus,
    error_message: str,
) -> ProviderValidationResult:
    return ProviderValidationResult(
        asset_symbol=target.asset_symbol,
        asset_type=target.asset_type,
        provider=target.provider,
        provider_symbol=target.provider_symbol,
        status=status,
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
        actual_start_date=None,
        actual_end_date=None,
        row_count=0,
        has_open=False,
        has_high=False,
        has_low=False,
        has_close=False,
        has_volume=False,
        supports_today_open=None,
        error_message=error_message,
    )


def classify_exception(exc: Exception) -> ValidationStatus:
    message = f"{type(exc).__name__}: {exc}".lower()
    network_terms = (
        "timeout",
        "connection",
        "network",
        "ssl",
        "proxy",
        "remote disconnected",
        "temporary failure",
    )
    if any(term in message for term in network_terms):
        return ValidationStatus.NETWORK_ERROR
    return ValidationStatus.PROVIDER_ERROR


def write_json_results(results: list[ProviderValidationResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": [result.to_dict() for result in results],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_markdown_report(
    results: list[ProviderValidationResult],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# 当前免费数据源验证报告",
        "",
        f"生成时间：{generated_at}",
        "",
        "## 1. 验证摘要",
        "",
        "| 资产 | 类型 | Provider | Provider Symbol | 状态 | 行数 | 实际日期范围 | 错误 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for result in results:
        actual_range = "-"
        if result.actual_start_date and result.actual_end_date:
            actual_range = (
                f"{result.actual_start_date.isoformat()} ~ "
                f"{result.actual_end_date.isoformat()}"
            )
        lines.append(
            "| "
            f"{result.asset_symbol} | "
            f"{result.asset_type} | "
            f"{result.provider} | "
            f"{result.provider_symbol} | "
            f"{result.status.value} | "
            f"{result.row_count} | "
            f"{actual_range} | "
            f"{_markdown_cell(result.error_message)} |"
        )

    lines.extend(
        [
            "",
            "## 2. 字段完整性",
            "",
            "| 资产 | Provider | Open | High | Low | Close | Volume | Today Open |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for result in results:
        lines.append(
            "| "
            f"{result.asset_symbol} | "
            f"{result.provider} | "
            f"{_yes_no(result.has_open)} | "
            f"{_yes_no(result.has_high)} | "
            f"{_yes_no(result.has_low)} | "
            f"{_yes_no(result.has_close)} | "
            f"{_yes_no(result.has_volume)} | "
            f"{_yes_no(result.supports_today_open)} |"
        )

    lines.extend(
        [
            "",
            "## 3. 说明",
            "",
            "- 本报告由当前免费数据源验证脚本生成。",
            "- 默认验证范围仅包含项目当前关注的 10 个资产。",
            "- 验证结果不写入 SQLite，不代表后续正式同步状态。",
            "- `history_insufficient` 表示免费源返回的实际起始日期晚于请求起始日期。",
            "- `supports_today_open` 只记录本次运行时请求结束日期是否返回 open，不等同于实时行情能力。",
            "",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def result_counts(results: Iterable[ProviderValidationResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status.value] = counts.get(result.status.value, 0) + 1
    return counts


def _yes_no(value: bool | None) -> str:
    if value is None:
        return "-"
    return "yes" if value else "no"


def _markdown_cell(value: Any) -> str:
    if value is None:
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")
