"""
confirmation.py — Entry confirmation on 1M chart
Checks:
  - Price touching support/resistance zone
  - Candlestick pattern (engulfing or pin bar)
  - RSI threshold
"""

import pandas as pd
import numpy as np
import logging

from config import RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT, ZONE_TOUCH_TOLERANCE_PCT

logger = logging.getLogger(__name__)


def compute_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _is_bullish_engulfing(df: pd.DataFrame) -> bool:
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    prev_bearish = prev["close"] < prev["open"]
    curr_bullish = curr["close"] > curr["open"]
    engulfs = curr["open"] <= prev["close"] and curr["close"] >= prev["open"]
    return bool(prev_bearish and curr_bullish and engulfs)


def _is_bearish_engulfing(df: pd.DataFrame) -> bool:
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    prev_bullish = prev["close"] > prev["open"]
    curr_bearish = curr["close"] < curr["open"]
    engulfs = curr["open"] >= prev["close"] and curr["close"] <= prev["open"]
    return bool(prev_bullish and curr_bearish and engulfs)


def _is_bullish_pin_bar(df: pd.DataFrame) -> bool:
    """Long lower wick, small body near the top."""
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    body = abs(c["close"] - c["open"])
    candle_range = c["high"] - c["low"]
    if candle_range == 0:
        return False
    lower_wick = min(c["close"], c["open"]) - c["low"]
    upper_wick = c["high"] - max(c["close"], c["open"])
    return bool(
        lower_wick >= 2 * body
        and lower_wick / candle_range >= 0.6
        and upper_wick / candle_range <= 0.2
    )


def _is_bearish_pin_bar(df: pd.DataFrame) -> bool:
    """Long upper wick, small body near the bottom."""
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    body = abs(c["close"] - c["open"])
    candle_range = c["high"] - c["low"]
    if candle_range == 0:
        return False
    upper_wick = c["high"] - max(c["close"], c["open"])
    lower_wick = min(c["close"], c["open"]) - c["low"]
    return bool(
        upper_wick >= 2 * body
        and upper_wick / candle_range >= 0.6
        and lower_wick / candle_range <= 0.2
    )


def _price_touching_zone(current_price: float, zone_price: float) -> bool:
    tol = zone_price * ZONE_TOUCH_TOLERANCE_PCT
    return abs(current_price - zone_price) <= tol


def check_buy_confirmation(df1m: pd.DataFrame, support_price: float) -> dict:
    result = {"confirmed": False, "rsi": None, "pattern": None, "price_touch": False}

    if df1m is None or len(df1m) < RSI_PERIOD + 2:
        return result

    rsi_series = compute_rsi(df1m["close"])
    rsi = float(rsi_series.iloc[-1])
    result["rsi"] = rsi

    current_price = float(df1m["close"].iloc[-1])
    price_touch = _price_touching_zone(current_price, support_price)
    result["price_touch"] = price_touch

    pattern = None
    if _is_bullish_engulfing(df1m):
        pattern = "bullish_engulfing"
    elif _is_bullish_pin_bar(df1m):
        pattern = "pin_bar_bullish"
    result["pattern"] = pattern

    if price_touch and pattern and rsi < RSI_OVERSOLD:
        result["confirmed"] = True

    return result


def check_sell_confirmation(df1m: pd.DataFrame, resistance_price: float) -> dict:
    result = {"confirmed": False, "rsi": None, "pattern": None, "price_touch": False}

    if df1m is None or len(df1m) < RSI_PERIOD + 2:
        return result

    rsi_series = compute_rsi(df1m["close"])
    rsi = float(rsi_series.iloc[-1])
    result["rsi"] = rsi

    current_price = float(df1m["close"].iloc[-1])
    price_touch = _price_touching_zone(current_price, resistance_price)
    result["price_touch"] = price_touch

    pattern = None
    if _is_bearish_engulfing(df1m):
        pattern = "bearish_engulfing"
    elif _is_bearish_pin_bar(df1m):
        pattern = "pin_bar_bearish"
    result["pattern"] = pattern

    if price_touch and pattern and rsi > RSI_OVERBOUGHT:
        result["confirmed"] = True

    return result
