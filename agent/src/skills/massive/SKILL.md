---
name: massive
description: Massive.com (formerly Polygon.io) market data — US stocks, options chains, real-time quotes, trades, fundamentals, and more. Requires MASSIVE_API_KEY.
category: data-source
---
# massive

## Overview

[Massive.com](https://massive.com) (formerly Polygon.io) provides institutional-grade financial market data for US stocks, options, forex, crypto, and indices. The official Python client `massive` (`pip install massive`) exposes both a REST API and WebSocket streams.

**Requires:** `MASSIVE_API_KEY` environment variable set to your Massive.com API key.

```bash
pip install massive>=2.0.0
```

```python
from massive import RESTClient

client = RESTClient(api_key="YOUR_MASSIVE_API_KEY")
```

The project has a built-in Massive DataLoader (`backtest/loaders/massive_loader.py`). When backtesting US equities, set `source: "massive"` to use it directly, or `source: "auto"` (Massive is tried first when `MASSIVE_API_KEY` is set).

---

## Quick Start

### Stocks — Historical OHLCV (Aggregates)

```python
from massive import RESTClient

client = RESTClient(api_key="YOUR_MASSIVE_API_KEY")

# Daily bars for AAPL — paginated, returns all results
aggs = []
for a in client.list_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="day",
    from_="2024-01-01",
    to="2025-01-01",
    adjusted=True,
    sort="asc",
    limit=50000,
):
    aggs.append(a)

import pandas as pd
df = pd.DataFrame([vars(a) for a in aggs])
df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
df = df.set_index("date")[["open", "high", "low", "close", "volume"]]
print(df.tail())
```

### Stocks — Last Quote / Trade

```python
# Latest trade
trade = client.get_last_trade(ticker="AAPL")
print(f"AAPL last price: {trade.price}, size: {trade.size}")

# Latest NBBO quote
quote = client.get_last_quote(ticker="AAPL")
print(f"AAPL bid: {quote.bid_price}  ask: {quote.ask_price}")

# Current snapshot (includes day stats, minute bar, last trade/quote)
snapshot = client.get_snapshot_ticker("stocks", "AAPL")
print(snapshot)
```

### Stocks — Real-Time WebSocket Stream

```python
import asyncio
from massive import WebSocketClient, Feed, Market

async def handle(msgs):
    for m in msgs:
        print(m)

ws = WebSocketClient(
    feed=Feed.RealTime,
    market=Market.Stocks,
    api_key="YOUR_MASSIVE_API_KEY",
    subscriptions=["T.AAPL", "Q.AAPL"],  # T=trades, Q=quotes
    handle_msg=handle,
)
asyncio.run(ws.connect())
```

---

## Options Data

### Options Chain Snapshot

```python
# Full options chain snapshot for AAPL (all expirations)
chain = client.list_snapshot_options_chain(
    underlying_asset="AAPL",
    params={"limit": 250},
)
rows = []
for contract in chain:
    d = contract.details
    g = contract.greeks
    rows.append({
        "ticker":       d.ticker,
        "expiration":   d.expiration_date,
        "strike":       d.strike_price,
        "type":         d.contract_type,   # "call" / "put"
        "iv":           contract.implied_volatility,
        "delta":        g.delta if g else None,
        "gamma":        g.gamma if g else None,
        "theta":        g.theta if g else None,
        "vega":         g.vega  if g else None,
        "open_interest": contract.open_interest,
        "day_volume":   contract.day.volume if contract.day else None,
    })
df = pd.DataFrame(rows)
print(df.head(10))
```

### Filter by Expiration Date and Strike

```python
# AAPL calls expiring 2025-06-20 with strike between 180–220
chain = client.list_snapshot_options_chain(
    underlying_asset="AAPL",
    params={
        "expiration_date": "2025-06-20",
        "contract_type":   "call",
        "strike_price.gte": 180,
        "strike_price.lte": 220,
        "limit": 100,
    },
)
for c in chain:
    d = c.details
    print(f"{d.ticker}  strike={d.strike_price}  IV={c.implied_volatility:.2%}")
```

### Options OHLCV Bars

```python
# Intraday 1-minute bars for a specific option contract
option_ticker = "O:AAPL250620C00200000"  # format: O:<UNDERLYING><YYMMDD><C/P><STRIKE×1000 padded to 8 digits>
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
df = pd.DataFrame([vars(a) for a in aggs])
if not df.empty:
    df["time"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("time")[["open", "high", "low", "close", "volume"]]
    print(df.head())
```

### Last Trade / Quote for an Option

```python
trade = client.get_last_trade(option_ticker="O:AAPL250620C00200000")
print(f"Last trade: price={trade.price}, size={trade.size}")
```

### Unusual Options Activity — High-Volume Contracts

```python
# Scan for AAPL options with open interest > 1000 and volume spike
chain = client.list_snapshot_options_chain(
    underlying_asset="AAPL",
    params={
        "open_interest.gt": 1000,
        "order": "desc",
        "sort": "day.volume",
        "limit": 50,
    },
)
for c in chain:
    d = c.details
    day = c.day
    print(f"{d.ticker}  oi={c.open_interest}  vol={day.volume if day else 'N/A'}")
```

---

## Reference Data

### Ticker Details

```python
details = client.get_ticker_details("AAPL")
print(details.name, details.market_cap, details.description)
```

### Options Contract Reference

```python
contracts = client.list_options_contracts(
    underlying_ticker="AAPL",
    expiration_date_gte="2025-06-01",
    expiration_date_lte="2025-07-01",
    contract_type="call",
    limit=100,
)
for c in contracts:
    print(c.ticker, c.expiration_date, c.strike_price, c.contract_type)
```

### Dividends and Splits

```python
for div in client.list_dividends("AAPL"):
    print(div.cash_amount, div.ex_dividend_date, div.pay_date)

for split in client.list_splits("AAPL"):
    print(split.split_from, split.split_to, split.execution_date)
```

### Market Status and Holidays

```python
status = client.get_market_status()
print("Market open:", status.market)

holidays = client.get_market_holidays()
for h in holidays:
    print(h.name, h.date, h.status)
```

---

## Backtest Integration

### config.json — Use Massive as Data Source

```json
{
  "source": "massive",
  "codes": ["AAPL.US", "MSFT.US", "NVDA.US"],
  "start_date": "2023-01-01",
  "end_date": "2025-01-01",
  "initial_cash": 1000000,
  "commission": 0.001,
  "extra_fields": null
}
```

### config.json — Auto Mode (Massive First for US Equities)

```json
{
  "source": "auto",
  "codes": ["AAPL.US", "BTC-USDT"],
  "start_date": "2024-01-01",
  "end_date": "2025-06-01",
  "initial_cash": 500000,
  "commission": 0.001
}
```

`source: "auto"` routes by ticker format: US equities → Massive (if `MASSIVE_API_KEY` is set) → yfinance → akshare; crypto → OKX → ccxt; A-shares → tushare → akshare.

---

## Options Ticker Format

Massive uses the OCC option symbol convention:

```
O:<UNDERLYING><YY><MM><DD><C|P><STRIKE padded to 8 digits, ×1000>
```

Examples:

| Contract | Ticker |
|----------|--------|
| AAPL call, exp 2025-06-20, strike $200 | `O:AAPL250620C00200000` |
| SPY put, exp 2025-12-19, strike $500 | `O:SPY251219P00500000` |
| TSLA call, exp 2026-01-16, strike $350 | `O:TSLA260116C00350000` |

Helper to build option tickers:

```python
def option_ticker(underlying: str, expiry: str, call_put: str, strike: float) -> str:
    """Build a Massive option ticker string.

    Args:
        underlying: e.g. "AAPL"
        expiry:     "YYYY-MM-DD"
        call_put:   "C" or "P"
        strike:     strike price as a float

    Returns:
        OCC-format option ticker prefixed with "O:".
    """
    yy, mm, dd = expiry[2:4], expiry[5:7], expiry[8:10]
    strike_int = int(round(strike * 1000))
    return f"O:{underlying.upper()}{yy}{mm}{dd}{call_put.upper()}{strike_int:08d}"

print(option_ticker("AAPL", "2025-06-20", "C", 200))  # O:AAPL250620C00200000
```

---

## MCP Server Integration (`@massive-com/mcp_massive`)

Massive also provides an MCP server for LLM-native access to the full API surface. Add it to your Claude / MCP client config:

```bash
# Install once
uv tool install "mcp_massive @ git+https://github.com/massive-com/mcp_massive@v0.9.1"

# Register with Claude Code
claude mcp add massive -e MASSIVE_API_KEY=your_api_key_here -- mcp_massive
```

Or in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "massive": {
      "command": "mcp_massive",
      "env": {
        "MASSIVE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

MCP tools exposed: `search_endpoints`, `call_api`, `query_data` — covers the entire Massive REST API including stocks, options, forex, crypto, fundamentals, news.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MASSIVE_API_KEY` | Yes | Your Massive.com API key |
| `POLYGON_API_KEY` | No | Legacy alias (still accepted) |

```bash
# .env
MASSIVE_API_KEY=your-api-key-here
```

---

## Notes

- **Subscription tiers:** Real-time data (WebSocket) and full historical depth require a paid Stocks and/or Options subscription. The free tier offers delayed data and limited history.
- **Rate limits:** Respect the rate limits for your subscription tier. The REST client does not auto-throttle by default.
- **Options coverage:** All US-listed equity options (CBOE, C2, AMEX, ISE, MIAX, etc.).
- **Stocks coverage:** All US exchanges (NYSE, NASDAQ, BATS, IEX, etc.).
- **Pagination:** `list_*` methods return Python iterators and handle pagination automatically — no manual `next_url` needed.
- **Adjusted prices:** Pass `adjusted=True` to `list_aggs` for split- and dividend-adjusted OHLCV.
- **Ticker format:** Project format `AAPL.US` is automatically converted to `AAPL` by the backtest loader.
