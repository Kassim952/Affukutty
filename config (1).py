"""
config.py — Central configuration for the trading bot.
Edit this file to tune strategy, risk, filters, and AI settings.
"""

import os

# ─────────────────────────────────────────────
# BROKER / API CREDENTIALS (from environment)
# ─────────────────────────────────────────────
METAAPI_TOKEN      = os.environ.get("METAAPI_TOKEN", "")
METAAPI_ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
AI_BASE_URL        = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL", "")
AI_API_KEY         = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY", "")

# ─────────────────────────────────────────────
# SYMBOLS
# ─────────────────────────────────────────────
SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
    "NZDUSD",
    "XAUUSD",   # Gold
    "BTCUSD",   # Bitcoin
]

# yfinance ticker mapping
YFINANCE_SYMBOL_MAP = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "CAD=X",
    "USDCHF": "CHF=X",
    "NZDUSD": "NZDUSD=X",
    "XAUUSD": "GC=F",
    "BTCUSD": "BTC-USD",
}

# Pip sizes per symbol (used for SL/TP distance calculations)
PIP_SIZE = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "USDJPY": 0.01,
    "AUDUSD": 0.0001,
    "USDCAD": 0.0001,
    "USDCHF": 0.0001,
    "NZDUSD": 0.0001,
    "XAUUSD": 0.01,
    "BTCUSD": 1.0,
}

# Pip value in USD per 1 standard lot
PIP_VALUE_USD = {
    "EURUSD": 10.0,
    "GBPUSD": 10.0,
    "USDJPY": 9.09,
    "AUDUSD": 10.0,
    "USDCAD": 7.69,
    "USDCHF": 10.0,
    "NZDUSD": 10.0,
    "XAUUSD": 1.0,
    "BTCUSD": 1.0,
}

# ─────────────────────────────────────────────
# BOT LOOP
# ─────────────────────────────────────────────
LOOP_INTERVAL_SECONDS = 10      # How often the bot scans all symbols
MAGIC_NUMBER          = 777888  # MT4/MT5 order magic number

# ─────────────────────────────────────────────
# STRATEGY — TREND FILTER (15M)
# ─────────────────────────────────────────────
EMA_FAST   = 50    # Fast EMA period (15M chart)
EMA_SLOW   = 200   # Slow EMA period (15M chart)
MIN_15M_BARS = 200 # Minimum bars needed for trend calculation

# ─────────────────────────────────────────────
# STRATEGY — SUPPORT & RESISTANCE (5M)
# ─────────────────────────────────────────────
SWING_LOOKBACK      = 5      # Candles left/right to confirm swing high/low
MIN_ZONE_TOUCHES    = 2      # Minimum touches to qualify a zone
MAX_ZONES           = 3      # Max zones to store per symbol
ZONE_TOLERANCE_PCT  = 0.0015 # Zone proximity tolerance (0.15%)

# ─────────────────────────────────────────────
# STRATEGY — ENTRY CONFIRMATION (1M)
# ─────────────────────────────────────────────
RSI_PERIOD      = 14   # RSI calculation period
RSI_OVERSOLD    = 30   # RSI threshold for BUY confirmation
RSI_OVERBOUGHT  = 70   # RSI threshold for SELL confirmation
ZONE_TOUCH_TOLERANCE_PCT = 0.002  # Price must be within 0.2% of zone

# ─────────────────────────────────────────────
# RISK MANAGEMENT
# ─────────────────────────────────────────────
RISK_PER_TRADE_PCT    = 0.01  # 1% of account balance per trade
RISK_REWARD_RATIO     = 2.0   # Minimum reward:risk (1:2)
MAX_CONCURRENT_TRADES = 3     # Max open trades at any time
MAX_DAILY_TRADES      = 15    # Max trades per day
MAX_DAILY_LOSS_PCT    = 0.05  # Stop trading after -5% daily drawdown
MIN_LOT_SIZE          = 0.01  # Minimum order size
MAX_LOT_SIZE          = 10.0  # Maximum order size

# ─────────────────────────────────────────────
# SMART FILTERS
# ─────────────────────────────────────────────

# Session filter (UTC hours)
LONDON_SESSION_START = 8    # 08:00 UTC
LONDON_SESSION_END   = 17   # 17:00 UTC
NEW_YORK_SESSION_START = 13 # 13:00 UTC
NEW_YORK_SESSION_END   = 22 # 22:00 UTC

# Spread filter — max allowed spread in pips per symbol
MAX_SPREAD_PIPS = {
    "EURUSD": 2.0,
    "GBPUSD": 3.0,
    "USDJPY": 2.0,
    "AUDUSD": 2.5,
    "USDCAD": 3.0,
    "USDCHF": 3.0,
    "NZDUSD": 3.0,
    "XAUUSD": 30.0,
    "BTCUSD": 50.0,
}

# ATR volatility filter
ATR_PERIOD          = 14   # ATR calculation period
ATR_MAX_MULTIPLIER  = 3.0  # Reject if recent range > ATR * this value * 2

# News avoidance — skip within N minutes of the top of each hour
NEWS_AVOID_MINUTES_BEFORE = 5
NEWS_AVOID_MINUTES_AFTER  = 5

# ─────────────────────────────────────────────
# AI ANALYSIS
# ─────────────────────────────────────────────
AI_MODEL               = "gpt-5-mini"  # OpenAI model via Replit AI Integrations
AI_CONFIDENCE_THRESHOLD = 65           # Min confidence (0-100) to approve a trade
AI_MAX_TOKENS          = 512           # Max tokens in AI response

# Market regime score multipliers
AI_REGIME_MULTIPLIERS = {
    "trending":  1.2,
    "ranging":   1.0,
    "volatile":  0.7,
    "uncertain": 0.5,
}
