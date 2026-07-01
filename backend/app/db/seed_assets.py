from __future__ import annotations

from app.models.asset import SeedAsset


DEFAULT_SEED_ASSETS: tuple[SeedAsset, ...] = (
    SeedAsset("513180.SH", "恒生科技ETF华夏", "etf", "CN", "CNY", "Asia/Shanghai", "yfinance", "513180.SS"),
    SeedAsset("159915.SZ", "创业板ETF易方达", "etf", "CN", "CNY", "Asia/Shanghai", "yfinance", "159915.SZ"),
    SeedAsset("588000.SH", "科创50ETF华夏", "etf", "CN", "CNY", "Asia/Shanghai", "yfinance", "588000.SS"),
    SeedAsset("510500.SH", "中证500ETF南方", "etf", "CN", "CNY", "Asia/Shanghai", "yfinance", "510500.SS"),
    SeedAsset("510300.SH", "沪深300ETF华泰柏瑞", "etf", "CN", "CNY", "Asia/Shanghai", "yfinance", "510300.SS"),
    SeedAsset("159941.SZ", "纳指ETF广发", "etf", "CN", "CNY", "Asia/Shanghai", "yfinance", "159941.SZ"),
    SeedAsset("513500.SH", "标普500ETF博时", "etf", "CN", "CNY", "Asia/Shanghai", "yfinance", "513500.SS"),
    SeedAsset("BTC-USD", "Bitcoin USD", "crypto", "CRYPTO", "USD", "UTC", "yfinance", "BTC-USD"),
    SeedAsset("ETH-USD", "Ethereum USD", "crypto", "CRYPTO", "USD", "UTC", "yfinance", "ETH-USD"),
    SeedAsset("BNB-USD", "BNB USD", "crypto", "CRYPTO", "USD", "UTC", "yfinance", "BNB-USD"),
)
