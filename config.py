"""
config.py — Central configuration for the trading bot.
Edit this file to tune strategy, risk, filters, and AI settings.
"""

import os

# ─────────────────────────────────────────────
# BROKER / API CREDENTIALS (from environment)
# ─────────────────────────────────────────────
METAAPI_TOKEN      = os.environ.get("METAAPI_TOKEN", "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI1YTU0ZGY2YWMwMmU5NGRlOWJkNjEzNDdkYzU5NDQ5ZiIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVzdC1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtZXRhc3RhdHMtYXBpIiwibWV0aG9kcyI6WyJtZXRhc3RhdHMtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6InJpc2stbWFuYWdlbWVudC1hcGkiLCJtZXRob2RzIjpbInJpc2stbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoiY29weWZhY3RvcnktYXBpIiwibWV0aG9kcyI6WyJjb3B5ZmFjdG9yeS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibXQtbWFuYWdlci1hcGkiLCJtZXRob2RzIjpbIm10LW1hbmFnZXItYXBpOnJlc3Q6ZGVhbGluZzoqOioiLCJtdC1tYW5hZ2VyLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJiaWxsaW5nLWFwaSIsIm1ldGhvZHMiOlsiYmlsbGluZy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiNWE1NGRmNmFjMDJlOTRkZTliZDYxMzQ3ZGM1OTQ0OWYiLCJpYXQiOjE3NzYzMjc5MTAsImV4cCI6MTc4NDEwMzkxMH0.cVqCVfrNRVckWB0TGF9hfmih9mgnM2U4lbBOCLUt8slQAoMDBX6S_09_rZXSPBM76wJhQJF_kx7DWje7LghfGDf5YciXt5x82HdWmpOtKV04hDSRI2nwfsmeHQARzrs1OSrNmjNdry2jebEXRuZeocyKmAX1bLWAYtOPdIZoQ25vhyadWYl2TLBITAry5NE1vvP1P3Cxo0FpJD7gztWuMwY5rgQdlK4NsKzWtQLQVuvBnrMdtNb3C7HoelFNwyvwMw97fOJLKoTJjMOVzzwi6zT9rAOb8QDNvnXeEcWpT-SDacB4UWnTbhowXgL35Hlh142yOP2FvZsHtZPwQD8uTt6bdVBvhqx2rPPfc0GTBphz5FZnb8mxUjE9P2joIrnpDy0gg5F7TRWiCu-Kkso8-vnZdmbQzarx1pyyU-cM7-3CpQfmiZhLXICCL3yAHkDLHlAtaueUfw-EVWruESzkpfLmIPZ2W4UWV3sWS8oxq1b-8j673AnZEfaCooRW37xbtzMKkIsw7sae3lhHp9yxOgdphd26-aR2CVthC6w_bUD16WeY1vLcv78B8825k3Dv9jYTgOvDstCDwMTt1pLMvSrPLMUwRSaQM2GhbUyBtHEftaxj-KYxsXWxa_YCz09EU1X5BT2RqB2xjDwE9AWfD84u_OWQvfFSi_h0K7ZOhXE")
METAAPI_ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "3f3a5aee-91fe-43ce-97d4-18f1136dbde6")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8376148746:AAGQcbL-r620xlPNjAsIptkF-mzmoQv2qDg")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "8376148746")
AI_BASE_URL        = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL", "")
AI_API_KEY         = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY", "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")

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
