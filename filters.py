"""
filters.py — Smart filters: Session, Spread, Volatility (ATR), News
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging

from config import (
    LONDON_SESSION_START, LONDON_SESSION_END,
    NEW_YORK_SESSION_START, NEW_YORK_SESSION_END,
    ATR_PERIOD, ATR_MAX_MULTIPLIER,
    MAX_SPREAD_PIPS, PIP_SIZE,
    NEWS_AVOID_MINUTES_BEFORE, NEWS_AVOID_MINUTES_AFTER,
)

logger = logging.getLogger(__name__)


def is_trading_session() -> bool:
    """Returns True if current UTC time is within London or New York session."""
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour

    in_london = LONDON_SESSION_START <= hour < LONDON_SESSION_END
    in_ny = NEW_YORK_SESSION_START <= hour < NEW_YORK_SESSION_END

    if not (in_london or in_ny):
        logger.info(f"Outside trading session (UTC {hour:02d}:00). Skipping.")
        return False
    return True


def compute_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> float | None:
    """Compute Average True Range."""
    if df is None or len(df) < period + 1:
        return None

    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean().iloc[-1]
    return float(atr) if not np.isnan(atr) else None


def check_volatility(df5m: pd.DataFrame, current_price: float) -> tuple[bool, float | None]:
    """
    Check if volatility is within acceptable range (not too low, not extreme spike).
    Returns (pass, atr_value).
    """
    atr = compute_atr(df5m)
    if atr is None:
        logger.warning("Could not compute ATR — skipping volatility check")
        return True, None

    min_move = current_price * 0.0001
    atr_min = max(min_move, current_price * 0.0002)

    if atr < atr_min:
        logger.info(f"Volatility too low: ATR={atr:.6f}")
        return False, atr

    atr_max = atr * ATR_MAX_MULTIPLIER * 2
    recent_range = float(df5m["high"].tail(3).max() - df5m["low"].tail(3).min())
    if recent_range > atr_max:
        logger.info(f"Extreme volatility spike: range={recent_range:.5f}, atr={atr:.5f}")
        return False, atr

    return True, atr


def check_spread(symbol: str, spread: float | None) -> bool:
    """
    Check if spread is within acceptable range.
    spread is in price units (not pips).
    """
    if spread is None:
        return True

    pip_size = PIP_SIZE.get(symbol, 0.0001)
    max_pips = MAX_SPREAD_PIPS.get(symbol, 5.0)
    spread_pips = spread / pip_size

    if spread_pips > max_pips:
        logger.info(f"{symbol} spread too high: {spread_pips:.1f} pips (max {max_pips})")
        return False
    return True


def check_news_filter(symbol: str) -> bool:
    """
    Basic news avoidance: skip trading N minutes before/after the top of each hour.
    Returns True if safe to trade.
    """
    now_utc = datetime.now(timezone.utc)
    minute = now_utc.minute

    if minute >= (60 - NEWS_AVOID_MINUTES_BEFORE) or minute <= NEWS_AVOID_MINUTES_AFTER:
        logger.info(f"Near top of hour — potential news time, skipping {symbol}")
        return False
    return True


def all_filters_pass(
    symbol: str,
    df5m: pd.DataFrame,
    current_price: float,
    spread: float | None = None,
) -> tuple[bool, float | None]:
    """
    Run all filters. Returns (pass, atr).
    If any filter fails, returns (False, atr or None).
    """
    if not is_trading_session():
        return False, None

    if not check_news_filter(symbol):
        return False, None

    spread_ok = check_spread(symbol, spread)
    if not spread_ok:
        return False, None

    vol_ok, atr = check_volatility(df5m, current_price)
    if not vol_ok:
        return False, atr

    return True, atr
