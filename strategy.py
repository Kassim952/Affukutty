"""
strategy.py — Trend filter + Support & Resistance zone detection
Timeframes:
  - 15M: EMA50/EMA200 trend direction
  - 5M:  Swing high/low S&R zones (min 2 touches, strong wicks)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging

from config import (
    EMA_FAST, EMA_SLOW, MIN_15M_BARS,
    SWING_LOOKBACK, MIN_ZONE_TOUCHES, MAX_ZONES, ZONE_TOLERANCE_PCT,
)

logger = logging.getLogger(__name__)


@dataclass
class Zone:
    price: float
    kind: str          # 'support' or 'resistance'
    touches: int = 0
    strong_wick: bool = False
    score: float = 0.0


def get_trend(df15m: pd.DataFrame) -> str | None:
    """
    Returns 'BUY', 'SELL', or None based on EMA fast/slow crossover on 15M.
    """
    if df15m is None or len(df15m) < MIN_15M_BARS:
        return None

    close = df15m["close"]
    ema_fast = close.ewm(span=EMA_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_SLOW, adjust=False).mean()

    last_fast = ema_fast.iloc[-1]
    last_slow = ema_slow.iloc[-1]

    if last_fast > last_slow:
        return "BUY"
    elif last_fast < last_slow:
        return "SELL"
    return None


def _is_swing_high(df: pd.DataFrame, i: int) -> bool:
    if i < SWING_LOOKBACK or i >= len(df) - SWING_LOOKBACK:
        return False
    high = df["high"].iloc[i]
    left = df["high"].iloc[i - SWING_LOOKBACK:i]
    right = df["high"].iloc[i + 1:i + SWING_LOOKBACK + 1]
    return bool((high > left).all() and (high > right).all())


def _is_swing_low(df: pd.DataFrame, i: int) -> bool:
    if i < SWING_LOOKBACK or i >= len(df) - SWING_LOOKBACK:
        return False
    low = df["low"].iloc[i]
    left = df["low"].iloc[i - SWING_LOOKBACK:i]
    right = df["low"].iloc[i + 1:i + SWING_LOOKBACK + 1]
    return bool((low < left).all() and (low < right).all())


def _has_strong_wick(df: pd.DataFrame, i: int, kind: str) -> bool:
    """Check for strong rejection wick at candle i."""
    row = df.iloc[i]
    body = abs(row["close"] - row["open"])
    candle_range = row["high"] - row["low"]
    if candle_range == 0:
        return False
    upper_wick = row["high"] - max(row["close"], row["open"])
    lower_wick = min(row["close"], row["open"]) - row["low"]

    if kind == "resistance":
        return upper_wick > body and upper_wick / candle_range > 0.3
    else:
        return lower_wick > body and lower_wick / candle_range > 0.3


def _count_touches(df: pd.DataFrame, price: float, kind: str) -> int:
    tol = price * ZONE_TOLERANCE_PCT
    touches = 0
    for _, row in df.iterrows():
        if kind == "resistance":
            if abs(row["high"] - price) <= tol:
                touches += 1
        else:
            if abs(row["low"] - price) <= tol:
                touches += 1
    return touches


def detect_zones(df5m: pd.DataFrame) -> list[Zone]:
    """
    Detect valid support/resistance zones on 5M data.
    Filters: min MIN_ZONE_TOUCHES touches, strong rejection wick.
    Returns top MAX_ZONES zones sorted by score.
    """
    if df5m is None or len(df5m) < 20:
        return []

    zones: list[Zone] = []
    n = len(df5m)

    for i in range(SWING_LOOKBACK, n - SWING_LOOKBACK):
        if _is_swing_high(df5m, i):
            price = float(df5m["high"].iloc[i])
            touches = _count_touches(df5m, price, "resistance")
            strong = _has_strong_wick(df5m, i, "resistance")
            if touches >= MIN_ZONE_TOUCHES:
                score = touches * (2 if strong else 1)
                zones.append(Zone(price=price, kind="resistance",
                                  touches=touches, strong_wick=strong, score=score))

        if _is_swing_low(df5m, i):
            price = float(df5m["low"].iloc[i])
            touches = _count_touches(df5m, price, "support")
            strong = _has_strong_wick(df5m, i, "support")
            if touches >= MIN_ZONE_TOUCHES:
                score = touches * (2 if strong else 1)
                zones.append(Zone(price=price, kind="support",
                                  touches=touches, strong_wick=strong, score=score))

    # Deduplicate zones that are too close together
    deduped: list[Zone] = []
    for z in sorted(zones, key=lambda x: -x.score):
        too_close = any(
            abs(z.price - e.price) / e.price < ZONE_TOLERANCE_PCT * 3
            for e in deduped
        )
        if not too_close:
            deduped.append(z)

    return deduped[:MAX_ZONES]


def get_nearest_zone(zones: list[Zone], current_price: float, kind: str) -> Zone | None:
    """Return the nearest zone of the given kind to current_price."""
    candidates = [z for z in zones if z.kind == kind]
    if not candidates:
        return None
    return min(candidates, key=lambda z: abs(z.price - current_price))
