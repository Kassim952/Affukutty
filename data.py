"""
data.py — Market data fetching via yfinance
Fetches OHLCV data for multiple timeframes per symbol.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

from config import YFINANCE_SYMBOL_MAP

logger = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    "15m": "15m",
    "5m":  "5m",
    "1m":  "1m",
}

LOOKBACK_DAYS = {
    "15m": 7,
    "5m":  3,
    "1m":  1,
}


def get_ticker(symbol: str) -> str:
    return YFINANCE_SYMBOL_MAP.get(symbol, symbol)


def fetch_ohlcv(symbol: str, timeframe: str, bars: int = 200) -> pd.DataFrame | None:
    """
    Fetch OHLCV candles for a symbol/timeframe.
    Returns a DataFrame with columns: open, high, low, close, volume
    Returns None on failure.
    """
    ticker = get_ticker(symbol)
    tf = TIMEFRAME_MAP.get(timeframe, timeframe)
    days = LOOKBACK_DAYS.get(timeframe, 3)

    end = datetime.utcnow()
    start = end - timedelta(days=days)

    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval=tf,
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty:
            logger.warning(f"No data returned for {symbol} {timeframe}")
            return None

        # yfinance >=0.2.x returns MultiIndex columns — flatten them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]

        # Normalise column names
        rename_map = {}
        for col in df.columns:
            col_lower = col.strip().lower()
            if col_lower in ("open", "high", "low", "close", "volume"):
                rename_map[col] = col_lower
        df = df.rename(columns=rename_map)

        for required in ("open", "high", "low", "close", "volume"):
            if required not in df.columns:
                logger.warning(f"{symbol} {timeframe}: missing column '{required}'")
                return None

        df = df[["open", "high", "low", "close", "volume"]].dropna()
        df = df.tail(bars)
        return df

    except Exception as e:
        logger.error(f"Error fetching {symbol} {timeframe}: {e}")
        return None


def fetch_all_timeframes(symbol: str) -> dict[str, pd.DataFrame | None]:
    """Return dict with keys '15m', '5m', '1m' for a symbol."""
    return {
        "15m": fetch_ohlcv(symbol, "15m"),
        "5m":  fetch_ohlcv(symbol, "5m"),
        "1m":  fetch_ohlcv(symbol, "1m"),
    }
