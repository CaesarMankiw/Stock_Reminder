from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.db.connection import get_database_path
from app.services.alert_service import AlertService


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "current_alert_validation_report.md"


def main() -> int:
    service = AlertService()
    try:
        rules = service.list_rules(enabled_only=True)
        if not rules:
            raise RuntimeError("No enabled alert rules. Run: python scripts/seed_assets.py")
        first_summary = service.check_alerts()
        second_summary = service.check_alerts()
        recent_events = service.list_events(limit=10)
    finally:
        service.close()

    sections = [
        "# 当前提醒验证报告",
        "",
        f"生成日期：{datetime.now(timezone.utc).date().isoformat()}",
        "",
        "## 验证范围",
        "",
        "- 数据来源：本地 SQLite `daily_prices` 表和统计计算服务。",
        f"- 数据库：`{get_database_path()}`",
        "- 验证方式：使用当前已启用提醒规则连续运行两次检查，确认触发和去重。",
        "- 本脚本不创建临时样例规则，不验证前端页面、macOS 原生通知或自动调度。",
        "",
        "## 当前启用规则",
        "",
        rules_table([rule.to_dict() for rule in rules]),
        "",
        "## 第一次检查",
        "",
        summary_table(first_summary.to_dict()),
        "",
        "## 第二次检查",
        "",
        summary_table(second_summary.to_dict()),
        "",
        "说明：同一规则、同一数据日期、同一方向已触发过时会返回 `duplicate_event`，不会重复写入提醒事件。",
        "",
        "## 最近提醒事件",
        "",
        events_table([event.to_dict() for event in recent_events]),
        "",
    ]

    DEFAULT_OUTPUT.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote alert validation report: {DEFAULT_OUTPUT}")
    return 0


def rules_table(rules: list[dict[str, object]]) -> str:
    if not rules:
        return "暂无启用规则。"
    lines = [
        "| id | asset_id | name | type | metric | period | lower | upper |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rule in rules:
        lines.append(
            "| {id} | {asset_id} | {name} | {rule_type} | {trigger_metric} | "
            "{period} | {lower_threshold_pct} | {upper_threshold_pct} |".format(**rule)
        )
    return "\n".join(lines)


def summary_table(summary: dict[str, object]) -> str:
    rows = [
        ("checked_rule_count", summary["checked_rule_count"]),
        ("triggered_event_count", summary["triggered_event_count"]),
        ("skipped_rule_count", summary["skipped_rule_count"]),
    ]
    lines = ["| 字段 | 值 |", "| --- | --- |"]
    lines.extend(f"| `{key}` | {value} |" for key, value in rows)
    skipped = summary["skipped_rules"]
    if skipped:
        lines.append(f"| `skipped_rules` | `{skipped}` |")
    created = summary["created_events"]
    if created:
        lines.append(f"| `created_events` | `{created}` |")
    return "\n".join(lines)


def events_table(events: list[dict[str, object]]) -> str:
    if not events:
        return "暂无提醒事件。"
    lines = [
        "| id | rule_id | asset_id | direction | data_date | basis | value | threshold |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for event in events:
        lines.append(
            "| {id} | {rule_id} | {asset_id} | {trigger_direction} | {data_date} | "
            "{price_basis} | {trigger_value_pct} | {threshold_pct} |".format(**event)
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
