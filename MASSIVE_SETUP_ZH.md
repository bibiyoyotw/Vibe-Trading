# Massive.com 設定教學與使用指南

> 本文件說明如何在 Vibe-Trading 中設定並使用 [Massive.com](https://massive.com)（原 Polygon.io）的股票與選擇權數據。

---

## 目錄

1. [什麼是 Massive.com](#什麼是-massivecom)
2. [申請 API 金鑰](#申請-api-金鑰)
3. [安裝與設定](#安裝與設定)
4. [數據來源說明](#數據來源說明)
5. [股票數據使用範例](#股票數據使用範例)
6. [選擇權數據使用範例](#選擇權數據使用範例)
7. [回測整合](#回測整合)
8. [MCP 伺服器整合](#mcp-伺服器整合)
9. [常見問題](#常見問題)

---

## 什麼是 Massive.com

[Massive.com](https://massive.com)（原 Polygon.io，於 2025 年 10 月更名）是一個專業級金融市場數據平台，提供：

- **美股** — 全美所有交易所的即時與歷史行情（NYSE、NASDAQ、BATS、IEX 等）
- **選擇權** — 全美掛牌股票選擇權（CBOE、C2、AMEX、ISE、MIAX 等），包含 Greeks、隱含波動率、未平倉量
- **外匯、加密貨幣、指數** — 多資產全覆蓋
- **基本面數據** — 財務報表、股息、股票分割、分析師評級
- **新聞** — Benzinga 即時新聞

Vibe-Trading 已將 Massive 設定為美股與選擇權回測的**預設數據來源**。

---

## 申請 API 金鑰

1. 前往 [https://massive.com](https://massive.com) 建立帳戶（免費方案可用）
2. 登入後，在控制台找到 **API Keys** 頁面
3. 建立一個新的 API Key
4. 訂閱 **Stocks** 和/或 **Options** 方案（免費方案提供延遲數據；付費方案提供即時數據與完整歷史記錄）

> **注意：** 原 Polygon.io 的 API Key 與 Massive.com 完全相容，無需重新申請。

---

## 安裝與設定

### 1. 安裝相依套件

```bash
pip install massive>=2.0.0
```

若使用 Vibe-Trading 完整安裝，`massive` 已包含在 `requirements.txt` 中，無需額外安裝：

```bash
pip install vibe-trading-ai
```

### 2. 設定 API 金鑰

在 `agent/.env` 中加入（複製 `agent/.env.example` 為起點）：

```bash
# 必填：Massive.com API 金鑰
MASSIVE_API_KEY=your-massive-api-key-here

# 舊版相容（Polygon.io 金鑰亦可使用）
# POLYGON_API_KEY=your-polygon-api-key-here
```

或直接在終端機設定環境變數：

```bash
export MASSIVE_API_KEY="your-massive-api-key-here"
```

### 3. 驗證設定

```python
from massive import RESTClient

client = RESTClient(api_key="your-massive-api-key-here")
snapshot = client.get_snapshot_ticker("stocks", "AAPL")
print(f"AAPL 最新價格: {snapshot.day.close}")
```

若無報錯，代表設定成功。

---

## 數據來源說明

Vibe-Trading 支援以下 6 個數據來源：

| 來源 | 適用市場 | 是否需要 Key | 說明 |
|------|---------|------------|------|
| `massive` | 美股、選擇權 | ✅ 需要 `MASSIVE_API_KEY` | **預設**，專業級數據 |
| `tushare` | A 股 | ✅ 需要 `TUSHARE_TOKEN` | A 股深度數據 |
| `yfinance` | 美股、港股 | ❌ 免費 | Yahoo Finance 備援 |
| `okx` | 加密貨幣 | ❌ 免費 | OKX 公開 API |
| `ccxt` | 加密貨幣 | ❌ 免費 | 100+ 交易所 |
| `akshare` | 多市場 | ❌ 免費 | 備援數據源 |

**自動路由（`source: "auto"`）優先順序：**

- 美股 → `massive` → `yfinance` → `akshare`
- 港股 → `yfinance` → `futu` → `akshare`
- A 股 → `tushare` → `akshare`
- 加密貨幣 → `okx` → `ccxt`

---

## 股票數據使用範例

### 取得歷史 OHLCV K 線

```python
import os
from massive import RESTClient
import pandas as pd

os.environ["MASSIVE_API_KEY"] = "your-api-key"
client = RESTClient()

# 取得 AAPL 日線數據
aggs = list(client.list_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="day",
    from_="2024-01-01",
    to="2025-01-01",
    adjusted=True,   # 除權除息調整
    sort="asc",
    limit=50000,
))

df = pd.DataFrame([{
    "date":   pd.Timestamp(a.timestamp, unit="ms"),
    "open":   a.open,
    "high":   a.high,
    "low":    a.low,
    "close":  a.close,
    "volume": a.volume,
} for a in aggs]).set_index("date")

print(df.tail())
```

### 取得即時報價

```python
# 最新成交
trade = client.get_last_trade(ticker="NVDA")
print(f"NVDA 最新成交: ${trade.price}，數量: {trade.size}")

# 最新 NBBO 報價
quote = client.get_last_quote(ticker="TSLA")
print(f"TSLA 買價: ${quote.bid_price}  賣價: ${quote.ask_price}")
```

### 盤面快照（含今日成交量）

```python
snapshot = client.get_snapshot_ticker("stocks", "AAPL")
print(f"今日開盤: {snapshot.day.open}")
print(f"今日最高: {snapshot.day.high}")
print(f"今日成交量: {snapshot.day.volume:,}")
print(f"最新成交: {snapshot.last_trade.price}")
```

### 即時 WebSocket 串流

```python
import asyncio
from massive import WebSocketClient, Feed, Market

async def handle(msgs):
    for m in msgs:
        print(f"[{m.symbol}] 成交: ${m.price}, 量: {m.size}")

ws = WebSocketClient(
    feed=Feed.RealTime,
    market=Market.Stocks,
    api_key="your-api-key",
    subscriptions=["T.AAPL", "T.NVDA", "Q.TSLA"],  # T=成交, Q=報價
    handle_msg=handle,
)
asyncio.run(ws.connect())
```

---

## 選擇權數據使用範例

### 取得選擇權鏈快照（含 Greeks）

```python
import pandas as pd

# 取得 AAPL 完整選擇權鏈
chain = list(client.list_snapshot_options_chain(
    underlying_asset="AAPL",
    params={"limit": 250},
))

rows = []
for contract in chain:
    d = contract.details
    g = contract.greeks
    rows.append({
        "合約代碼":    d.ticker,
        "到期日":      d.expiration_date,
        "履約價":      d.strike_price,
        "類型":        "買權" if d.contract_type == "call" else "賣權",
        "隱含波動率":   f"{contract.implied_volatility:.1%}" if contract.implied_volatility else "N/A",
        "Delta":      round(g.delta, 4) if g else None,
        "Gamma":      round(g.gamma, 6) if g else None,
        "Theta":      round(g.theta, 4) if g else None,
        "Vega":       round(g.vega, 4) if g else None,
        "未平倉量":    contract.open_interest,
        "今日成交量":  contract.day.volume if contract.day else None,
    })

df = pd.DataFrame(rows)
print(df.head(10).to_string(index=False))
```

### 篩選特定到期日與履約價的選擇權

```python
# AAPL 2025-06-20 到期、履約價 180–220 的買權
chain = list(client.list_snapshot_options_chain(
    underlying_asset="AAPL",
    params={
        "expiration_date":   "2025-06-20",
        "contract_type":     "call",
        "strike_price.gte":  180,
        "strike_price.lte":  220,
        "limit": 100,
    },
))

for c in chain:
    d = c.details
    iv = c.implied_volatility
    print(f"{d.ticker}  履約價={d.strike_price}  IV={iv:.1%}  Delta={c.greeks.delta:.3f}")
```

### 異常活躍選擇權掃描

```python
# 掃描 NVDA 未平倉量 > 5000 且按成交量排序的前 20 個合約
chain = list(client.list_snapshot_options_chain(
    underlying_asset="NVDA",
    params={
        "open_interest.gt": 5000,
        "order": "desc",
        "sort": "day.volume",
        "limit": 20,
    },
))

for c in chain:
    d = c.details
    day = c.day
    vol = day.volume if day else "N/A"
    print(f"{d.ticker}  到期={d.expiration_date}  履約價={d.strike_price}  "
          f"未平倉={c.open_interest:,}  今日成交量={vol}")
```

### 選擇權 K 線數據

```python
# 特定選擇權合約的 1 分鐘 K 線
# 合約代碼格式：O:<標的><到期日YYMMDD><C/P><履約價×1000，8位>
option_ticker = "O:AAPL250620C00200000"  # AAPL 2025-06-20 到期 $200 買權

aggs = list(client.list_aggs(
    ticker=option_ticker,
    multiplier=1,
    timespan="minute",
    from_="2025-06-10",
    to="2025-06-11",
    adjusted=False,
    sort="asc",
    limit=50000,
))
df = pd.DataFrame([{
    "time":   pd.Timestamp(a.timestamp, unit="ms"),
    "open":   a.open,
    "high":   a.high,
    "low":    a.low,
    "close":  a.close,
    "volume": a.volume,
} for a in aggs]).set_index("time")
print(df.head())
```

### 選擇權合約代碼產生器

```python
def option_ticker(underlying: str, expiry: str, call_put: str, strike: float) -> str:
    """產生 Massive 選擇權合約代碼（OCC 格式）

    參數：
        underlying: 標的股票代碼，例如 "AAPL"
        expiry:     到期日 "YYYY-MM-DD"
        call_put:   "C"（買權）或 "P"（賣權）
        strike:     履約價（浮點數）

    回傳：
        Massive 選擇權合約代碼，例如 "O:AAPL250620C00200000"
    """
    yy, mm, dd = expiry[2:4], expiry[5:7], expiry[8:10]
    strike_int = int(round(strike * 1000))
    return f"O:{underlying.upper()}{yy}{mm}{dd}{call_put.upper()}{strike_int:08d}"

# 範例
print(option_ticker("AAPL", "2025-06-20", "C", 200))   # O:AAPL250620C00200000
print(option_ticker("SPY",  "2025-12-19", "P", 500))   # O:SPY251219P00500000
print(option_ticker("TSLA", "2026-01-16", "C", 350))   # O:TSLA260116C00350000
```

---

## 回測整合

### config.json — 直接指定 Massive

```json
{
  "source": "massive",
  "codes": ["AAPL.US", "NVDA.US", "MSFT.US"],
  "start_date": "2023-01-01",
  "end_date": "2025-01-01",
  "initial_cash": 1000000,
  "commission": 0.001
}
```

### config.json — 自動路由（美股優先使用 Massive）

```json
{
  "source": "auto",
  "codes": ["AAPL.US", "BTC-USDT", "000001.SZ"],
  "start_date": "2024-01-01",
  "end_date": "2025-06-01",
  "initial_cash": 500000,
  "commission": 0.001
}
```

> `source: "auto"` 的路由規則：
> - `AAPL.US`（美股）→ `massive`（若有 API Key）→ `yfinance` → `akshare`
> - `BTC-USDT`（加密貨幣）→ `okx` → `ccxt`
> - `000001.SZ`（A 股）→ `tushare` → `akshare`

### 選擇權回測引擎

若要使用選擇權回測引擎，在 config.json 中設定 `engine: "options"`：

```json
{
  "source": "massive",
  "engine": "options",
  "codes": ["AAPL.US"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 1000000,
  "commission": 0.001
}
```

### 透過 CLI 執行回測

```bash
# 設定 API Key
export MASSIVE_API_KEY="your-api-key"

# 啟動 Vibe-Trading
vibe-trading

# 在 CLI 中輸入（中文亦可）：
# 「請用 AAPL 日線數據回測一個 20 日移動平均穿越策略，時間範圍 2023-2024，使用 massive 數據來源」
```

---

## MCP 伺服器整合

### 方式一：使用 Vibe-Trading 的內建 MCP 伺服器

Vibe-Trading 已整合 Massive 數據，只需在 `.env` 設定好 `MASSIVE_API_KEY`，啟動 MCP 伺服器即可：

```bash
# 啟動 MCP 伺服器
vibe-trading-mcp
```

在 Claude Desktop 的 `claude_desktop_config.json` 加入：

```json
{
  "mcpServers": {
    "vibe-trading": {
      "command": "vibe-trading-mcp",
      "env": {
        "MASSIVE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### 方式二：獨立安裝 Massive MCP 伺服器

Massive 官方也提供獨立的 MCP 伺服器，直接存取完整 API：

```bash
# 安裝（需要 uv）
uv tool install "mcp_massive @ git+https://github.com/massive-com/mcp_massive@v0.9.1"

# 在 Claude Code 中註冊
claude mcp add massive -e MASSIVE_API_KEY=your-api-key-here -- mcp_massive
```

在 `claude_desktop_config.json` 中設定：

```json
{
  "mcpServers": {
    "massive": {
      "command": "mcp_massive",
      "env": {
        "MASSIVE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Massive MCP 伺服器提供以下工具：

| 工具 | 說明 |
|------|------|
| `search_endpoints` | 用自然語言搜尋 API 端點 |
| `call_api` | 呼叫任何 Massive REST API |
| `query_data` | 用 SQL 查詢已儲存的數據 |

使用範例（對 Claude 輸入）：

```
取得 NVDA 最近 5 天的選擇權鏈，包含 IV 和 Greeks
```

```
掃描 S&P 500 中 put/call 成交量比異常高的股票
```

```
計算 AAPL 過去 20 日的移動平均線
```

---

## 常見問題

### Q: 我有 Polygon.io 的 Key，可以直接用嗎？

**A:** 可以。Polygon.io 已更名為 Massive.com，API Key 完全相容。你可以用 `MASSIVE_API_KEY` 或舊的 `POLYGON_API_KEY` 環境變數設定，兩者都能生效。

### Q: 免費方案有什麼限制？

**A:** 免費方案提供：
- 延遲 15 分鐘的股票數據
- 有限的歷史數據深度
- 每分鐘 API 呼叫次數限制

付費的 Stocks 或 Options 訂閱方案提供即時數據與完整歷史記錄。

### Q: 沒有設定 `MASSIVE_API_KEY` 時會怎樣？

**A:** Vibe-Trading 會自動回退（fallback）到其他免費數據來源：
- 美股 → `yfinance`（Yahoo Finance）
- 港股 → `yfinance`
- 其他市場不受影響

### Q: 如何確認 Massive 正在被使用？

**A:** 執行回測時，終端機會輸出使用的數據來源。你也可以在 `config.json` 明確指定 `"source": "massive"` 來強制使用 Massive。

### Q: 選擇權數據需要特別的訂閱方案嗎？

**A:** 是的，選擇權數據需要訂閱 Massive 的 **Options** 方案（包含在 Stocks + Options Bundle 中）。免費方案不含選擇權數據。

### Q: 支援哪些時間框架？

**A:** Massive 數據來源支援以下時間框架：

| 代碼 | 說明 |
|------|------|
| `1m` | 1 分鐘 |
| `5m` | 5 分鐘 |
| `15m` | 15 分鐘 |
| `30m` | 30 分鐘 |
| `1H` | 1 小時 |
| `4H` | 4 小時 |
| `1D` | 日線（預設） |

在 `config.json` 中設定：

```json
{
  "source": "massive",
  "interval": "1H",
  "codes": ["AAPL.US"],
  ...
}
```

---

## 相關資源

- [Massive.com 官方文件](https://massive.com/docs)
- [massive Python 客戶端 GitHub](https://github.com/massive-com/client-python)
- [Massive MCP 伺服器 GitHub](https://github.com/massive-com/mcp_massive)
- [Vibe-Trading GitHub](https://github.com/HKUDS/Vibe-Trading)
- [Vibe-Trading 中文 README](README_zh.md)
