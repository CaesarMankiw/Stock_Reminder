# Stock Reminder

本项目是一个只在本地 Mac 上运行的股票、ETF 与虚拟货币涨跌幅提醒网页。当前版本聚焦 10 个固定关注资产，使用免费行情源同步最多 5 年日线 OHLCV 数据，并在本地 SQLite 中计算锚点涨跌幅、区间涨跌幅、区间高低点、振幅和最大回撤。

当前不部署到公网服务器，不包含账户系统，也不写入任何云端数据库。

## 当前关注资产

| 资产 | 内部 symbol | 免费数据源 | provider symbol |
| --- | --- | --- | --- |
| 恒生科技ETF华夏 | `513180.SH` | Yahoo Finance via yfinance | `513180.SS` |
| 创业板ETF易方达 | `159915.SZ` | Yahoo Finance via yfinance | `159915.SZ` |
| 科创50ETF华夏 | `588000.SH` | Yahoo Finance via yfinance | `588000.SS` |
| 中证500ETF南方 | `510500.SH` | Yahoo Finance via yfinance | `510500.SS` |
| 沪深300ETF华泰柏瑞 | `510300.SH` | Yahoo Finance via yfinance | `510300.SS` |
| 纳指ETF广发 | `159941.SZ` | Yahoo Finance via yfinance | `159941.SZ` |
| 标普500ETF博时 | `513500.SH` | Yahoo Finance via yfinance | `513500.SS` |
| BTC | `BTC-USD` | Yahoo Finance via yfinance | `BTC-USD` |
| ETH | `ETH-USD` | Yahoo Finance via yfinance | `ETH-USD` |
| BNB | `BNB-USD` | Yahoo Finance via yfinance | `BNB-USD` |

`AKShare` / 东方财富在当前本地网络环境中出现代理断开，因此当前默认同步全部使用 `yfinance`。项目仍保留 AKShare 和 CCXT provider 代码，作为后续免费源切换或比对时的备选能力。

## 已实现功能

- 本地 FastAPI 后端、React 前端、SQLite 数据库。
- 10 个固定关注资产 seed，其他旧样例资产会被软停用。
- 免费源 5 年历史日线同步，字段包含 open、high、low、close、volume。
- 当日 open-only 数据写入，收盘后可补齐完整 OHLCV。
- K 线图支持 `1日`、`3日`、`5日`、`一周`、`一月`、`一季度`、`一年`蜡烛周期。这里的周期表示单根蜡烛覆盖的时间跨度，整体可见时间跨度通过放大、缩小和横向拉宽查看。
- Y 轴显示最高点到最低点之间 5 档刻度，包含至少 3 个中间刻度。
- 默认锚点日期为 `2026-01-01`。
- 主动“更新数据”按钮会对当前选中资产重新同步 5 年历史数据。
- 默认提醒策略：
  - 单月内从最高点回撤 `10%` 及以上。
  - 三个月内起止涨跌幅达到 `20%` 及以上。
- 手动提醒检查、提醒历史、同步任务状态、启动检查、日志、SQLite 备份和恢复脚本。

## 本地运行

建议使用 Python 3.11+、Node.js 20+、SQLite。首次运行：

```bash
cd /Users/liuxiang/Programme/Self_Play/Stock_Reminder

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/init_db.py
python scripts/seed_assets.py
python scripts/sync_history.py --years 5

cd ../frontend
npm install

cd ..
./scripts/start_local.sh
```

启动后访问：

- 前端工作台：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/health`

`scripts/start_local.sh` 会同时启动后端和前端，并把日志写入 `logs/backend.log` 与 `logs/frontend.log`。如果端口已被占用，脚本会提示先停止已有进程或改用环境变量：

```bash
BACKEND_PORT=8001 FRONTEND_PORT=5174 ./scripts/start_local.sh
```

## 常用命令

初始化或刷新关注资产和默认提醒：

```bash
cd backend
source .venv/bin/activate
python scripts/seed_assets.py
```

同步全部关注资产 5 年历史：

```bash
cd backend
source .venv/bin/activate
python scripts/sync_history.py --years 5
```

只同步某个资产：

```bash
cd backend
source .venv/bin/activate
python scripts/sync_history.py --asset-id 1 --years 5
```

执行开盘、收盘和提醒检查：

```bash
./scripts/run_daily_sync.sh open
./scripts/run_daily_sync.sh close
./scripts/run_daily_sync.sh alerts
```

启动前检查：

```bash
cd backend
source .venv/bin/activate
python scripts/startup_check.py
```

备份与恢复 SQLite：

```bash
./scripts/backup_db.sh
./scripts/restore_db.sh backend/data/backups/<backup-file>.sqlite3
```

运行测试和前端构建：

```bash
cd backend
source .venv/bin/activate
python -m pytest -q

cd ../frontend
npm run build
```

## 当前文档

- [关注资产调整与验证报告](docs/watchlist_update_validation_report.md)
- [开盘同步 launchd 样例](docs/launchd/stock-reminder-open-sync.plist.example)
- [收盘同步 launchd 样例](docs/launchd/stock-reminder-close-sync.plist.example)
- [提醒检查 launchd 样例](docs/launchd/stock-reminder-alert-check.plist.example)

`launchd` 文件只是样例，项目不会自动注册系统任务。

## 已知限制

- 免费行情源稳定性取决于本地网络和 provider 可用性；当前 `AKShare` / 东方财富不可作为默认源。
- 前端 K 线是本地 SVG 图，不是专业交易软件级别的拖拽缩放、十字光标和技术指标系统。
- 默认提醒检查需要手动点击或通过本地脚本触发，当前不弹出 macOS 原生通知。
- 主动更新按钮会等待当前资产同步完成，数据源响应慢时页面会短暂等待。
- 数据库、日志、备份和构建产物都属于本地运行文件，不提交到 Git。
