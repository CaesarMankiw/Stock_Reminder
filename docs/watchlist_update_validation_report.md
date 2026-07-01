# 关注资产调整与验证报告

生成日期：2026-07-01

## 1. 本次关注资产

当前活跃资产已调整为以下 10 个，其他旧样例资产已软停用：

| 资产 | 内部 symbol | 免费数据源 | provider symbol | 当前验证 |
| --- | --- | --- | --- | --- |
| 恒生科技ETF华夏 | `513180.SH` | Yahoo Finance via yfinance | `513180.SS` | 成功 |
| 创业板ETF易方达 | `159915.SZ` | Yahoo Finance via yfinance | `159915.SZ` | 成功 |
| 科创50ETF华夏 | `588000.SH` | Yahoo Finance via yfinance | `588000.SS` | 成功 |
| 中证500ETF南方 | `510500.SH` | Yahoo Finance via yfinance | `510500.SS` | 成功 |
| 沪深300ETF华泰柏瑞 | `510300.SH` | Yahoo Finance via yfinance | `510300.SS` | 成功 |
| 纳指ETF广发 | `159941.SZ` | Yahoo Finance via yfinance | `159941.SZ` | 成功 |
| 标普500ETF博时 | `513500.SH` | Yahoo Finance via yfinance | `513500.SS` | 成功 |
| BTC | `BTC-USD` | Yahoo Finance via yfinance | `BTC-USD` | 成功 |
| ETH | `ETH-USD` | Yahoo Finance via yfinance | `ETH-USD` | 成功 |
| BNB | `BNB-USD` | Yahoo Finance via yfinance | `BNB-USD` | 成功 |

说明：

- 当前环境下 `AKShare` / 东方财富访问出现代理断开，因此本次将 ETF 默认源切换为 `yfinance`。
- 7 个 ETF 使用 `.SS` 或 `.SZ` 后缀可通过 Yahoo Finance 免费获取日线。
- 3 个虚拟货币继续使用 Yahoo Finance 的 `*-USD` 日线。

## 2. 数据同步结果

执行：

```bash
cd backend
.venv/bin/python scripts/sync_history.py --years 5
```

结果：

| 资产 | 同步结果 | 行数 |
| --- | --- | --- |
| `159915.SZ` | success | 1209 |
| `159941.SZ` | success | 1210 |
| `510300.SH` | success | 1209 |
| `510500.SH` | success | 1209 |
| `513180.SH` | success | 1209 |
| `513500.SH` | success | 1210 |
| `588000.SH` | success | 1209 |
| `BNB-USD` | success | 1826 |
| `BTC-USD` | success | 1826 |
| `ETH-USD` | success | 1826 |

启动检查摘要：

| 指标 | 数值 |
| --- | --- |
| active assets | 10 |
| assets without prices | 0 |
| stale assets | 0 |
| today open-only records | 10 |

## 3. 默认提醒策略

当前已为每个活跃资产创建两条默认启用规则：

| 规则 | trigger metric | period | 阈值 |
| --- | --- | --- | --- |
| 单月高点回撤 | `max_drawdown_pct` | `1m` | `<= -10%` |
| 三月涨跌幅 | `change_pct` | `3m` | `>= 20%` 或 `<= -20%` |

历史验证规则已停用，避免干扰当前提醒检查。

## 4. 前端调整

已实现：

- K 线蜡烛周期：`1日`、`3日`、`5日`、`一周`、`一月`、`一季度`、`一年`，每个按钮表示一根蜡烛覆盖的时间跨度。
- K 线图缩放：放大、缩小、重置；整体可见时间跨度由缩放决定，最多使用当前本地 5 年数据。
- K 线图横向拉宽：支持拉宽、收窄，便于在宽屏或横屏下查看更多蜡烛细节。
- Y 轴价格刻度：最高点到最低点共 5 档，含中间 3 个刻度。
- 初始锚点日期：`2026-01-01`。
- 主动更新数据按钮：对当前选中资产执行 5 年历史同步并刷新页面数据。
- 同步任务状态栏移至左侧资产列表下方。

## 5. 验证结果

| 项目 | 结果 |
| --- | --- |
| 后端测试 | `44 passed, 1 warning` |
| 前端构建 | `npm run build` 通过 |
| yfinance ETF 可用性 | 7/7 成功 |
| yfinance crypto 可用性 | 3/3 成功 |
| 5 年历史同步 | 10/10 成功 |

warning 为 FastAPI/Starlette `TestClient` deprecation warning，不影响当前功能。

## 6. 当前缺陷与重点测试

### 当前缺陷

- `AKShare` / 东方财富在当前网络环境下仍会代理失败，暂不作为默认源。
- `sync_jobs` 中仍保留历史失败记录，启动检查会提示 recent failed sync jobs。
- 前端图表为本地 SVG 聚合与缩放，不是专业图表库级别的拖拽缩放和技术指标系统。
- 主动更新按钮当前同步选中资产的 5 年历史，数据源慢时页面会等待。
- 默认规则会创建在数据库中，但不会自动弹出 macOS 通知。

### 重点测试

- 10 个资产是否都能打开 K 线。
- 1日/3日/5日/一周/一月/一季度/一年是否按单根蜡烛周期聚合。
- 放大、缩小、重置、拉宽、收窄后 Y 轴刻度和可见蜡烛数量是否合理。
- `2026-01-01` 锚点统计是否能正常计算。
- “更新数据”按钮是否能刷新选中资产数据和同步状态。
- 默认 20 条提醒规则是否只针对当前 10 个活跃资产。
- 提醒检查是否能基于 `max_drawdown_pct` 和 `change_pct` 正确触发或跳过去重。
