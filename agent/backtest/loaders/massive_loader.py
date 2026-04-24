"""Massive.com-backed loader for US equity OHLCV data.

Requires a Massive.com API key set via the MASSIVE_API_KEY environment variable.
Install the client with: pip install massive>=2.0.0
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from backtest.loaders.base import validate_date_range
from backtest.loaders.registry import register

_OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]

# Map project interval strings to Massive timespan + multiplier
_INTERVAL_MAP: dict[str, tuple[int, str]] = {
    "1m":  (1,  "minute"),
    "5m":  (5,  "minute"),
    "15m": (15, "minute"),
    "30m": (30, "minute"),
    "1H":  (1,  "hour"),
    "4H":  (4,  "hour"),
    "1D":  (1,  "day"),
    "1W":  (1,  "week"),
}


def _to_massive_ticker(code: str) -> str:
    """Convert project symbol to Massive ticker.

    Args:
        code: Project symbol such as ``AAPL.US``.

    Returns:
        Massive-compatible ticker string.
    """
    upper = code.strip().upper()
    if upper.endswith(".US"):
        return upper[:-3]
    return upper


def _parse_interval(interval: str) -> tuple[int, str]:
    """Resolve an interval string to (multiplier, timespan).

    Args:
        interval: Backtest interval such as ``1D`` or ``15m``.

    Returns:
        Tuple of (multiplier, timespan) for the Massive aggregates API.
    """
    normalized = str(interval or "1D").strip()
    return _INTERVAL_MAP.get(normalized, (1, "day"))


@register
class DataLoader:
    """Fetch US equity OHLCV bars from Massive.com via the massive Python client."""

    name = "massive"
    markets = {"us_equity"}
    requires_auth = True

    def is_available(self) -> bool:
        """Return True when a Massive API key is configured.

        Returns:
            True if MASSIVE_API_KEY is set, False otherwise.
        """
        return bool(os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY"))

    def _get_client(self):
        """Create and return a massive RESTClient.

        Returns:
            Configured RESTClient instance.
        """
        from massive import RESTClient  # type: ignore[import]

        api_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY", "")
        return RESTClient(api_key=api_key)

    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        fields: Optional[List[str]] = None,
        interval: str = "1D",
    ) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV history keyed by the original project symbols.

        Args:
            codes: Project symbols such as ``AAPL.US``.
            start_date: Start date in ``YYYY-MM-DD`` format.
            end_date: End date in ``YYYY-MM-DD`` format.
            fields: Ignored; included for interface compatibility.
            interval: Backtest interval such as ``1D`` or ``1H``.

        Returns:
            Mapping of input symbol to normalized OHLCV dataframe.
        """
        del fields
        if not codes:
            return {}
        validate_date_range(start_date, end_date)

        multiplier, timespan = _parse_interval(interval)
        client = self._get_client()
        results: Dict[str, pd.DataFrame] = {}

        for code in codes:
            ticker = _to_massive_ticker(code)
            try:
                aggs = list(
                    client.list_aggs(
                        ticker=ticker,
                        multiplier=multiplier,
                        timespan=timespan,
                        from_=start_date,
                        to=end_date,
                        adjusted=True,
                        sort="asc",
                        limit=50000,
                    )
                )
                if not aggs:
                    print(f"[WARN] massive returned no data for {ticker}")
                    continue

                rows = [
                    {
                        "trade_date": pd.Timestamp(a.timestamp, unit="ms"),
                        "open":   float(a.open),
                        "high":   float(a.high),
                        "low":    float(a.low),
                        "close":  float(a.close),
                        "volume": float(a.volume) if a.volume is not None else None,
                    }
                    for a in aggs
                ]
                df = pd.DataFrame(rows).set_index("trade_date")
                df.index = pd.DatetimeIndex(df.index)
                df.index.name = "trade_date"
                df = df.sort_index()
                df["volume"] = df["volume"].fillna(0.0)
                df = df.dropna(subset=["open", "high", "low", "close"])
                results[code] = df[_OHLCV_COLUMNS]
            except Exception as exc:
                print(f"[WARN] massive fetch failed for {ticker}: {exc}")
                continue

        return results
