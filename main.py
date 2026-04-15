"""
XAUUSD Gold Scalping Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market Data : Yahoo Finance (yfinance)
Execution   : MetaAPI Cloud (MT4/MT5)
Alerts      : Telegram Bot API

Strategy    : BOLLINGER BANDS ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Signal Logic:
  BUY  → price closes at/below lower band  (oversold  → bounce to mid)
  SELL → price closes at/above upper band  (overbought → drop to mid)

Entry filter:
  • %B <= 0.0  for BUY  (%B >= 1.0  for SELL)
  • BB width > minimum (reject low-volatility squeezes)
  • Confirmation: previous candle also outside / touching the band

Exit logic:
  • TP  = BB mid-band (mean-reversion target)
  • SL  = ATR × 1.5  (adaptive to current volatility)
  • Early close if USD profit target hit (scalp mode)
  • Early close if USD loss limit hit
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import pandas as pd
import numpy as np
import yfinance as yf

from ta.volatility import BollingerBands, AverageTrueRange

from metaapi_cloud_sdk import MetaApi
from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
METAAPI_TOKEN = os.environ["eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI1YTU0ZGY2YWMwMmU5NGRlOWJkNjEzNDdkYzU5NDQ5ZiIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVzdC1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtZXRhc3RhdHMtYXBpIiwibWV0aG9kcyI6WyJtZXRhc3RhdHMtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6InJpc2stbWFuYWdlbWVudC1hcGkiLCJtZXRob2RzIjpbInJpc2stbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoiY29weWZhY3RvcnktYXBpIiwibWV0aG9kcyI6WyJjb3B5ZmFjdG9yeS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibXQtbWFuYWdlci1hcGkiLCJtZXRob2RzIjpbIm10LW1hbmFnZXItYXBpOnJlc3Q6ZGVhbGluZzoqOioiLCJtdC1tYW5hZ2VyLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJiaWxsaW5nLWFwaSIsIm1ldGhvZHMiOlsiYmlsbGluZy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiNWE1NGRmNmFjMDJlOTRkZTliZDYxMzQ3ZGM1OTQ0OWYiLCJpYXQiOjE3NzYxNjg1NjUsImV4cCI6MTc4Mzk0NDU2NX0.kyHCubU_iIhPiPQp87BAA-Qdf_6DrFBudgvHZafpLFkG0ODr70wbco-6fCavdtTGz7oYXTWauVhb_jB-aOH8GUI3Yv0oZstqrj0xl-DuyBPtltMAx9J1GuFg-BecVeB9bnmVRK7J4dweSDosq7BJMJBDuVo_HdAL2zprKaBg21rXFBsN-Fv5hpbRgcmC87h-pHkl5g-7SesTSFvJMP0i0znycA2PlJJIBcGB4TtNrwSSBijbIkwA_OCP3autzl9vqg-hcA6eQuKfAu2H13m01sataHKqlH-LKtubSmU_B7wYhALmM-2qqVm_7_6NCI0x4wRIQ4TDg1yDwSxxYGfeACUanOH1qoF_5iY5cyi8IdUwF4jIwffMFtUTyZWEoxSVT1bw1T8O-JOfah-FbKsm3i0zOoG4lpIzhwiALn-tWeGfzY6QNxxjpM5E3HKRe5nrVgYeUBzzizMfrkGnqBe1RFMpNRx8Ih2kfo88_wk-UUanLi0HU4iUiSbAeMDgLHBPZWahM1oLTwi_AMqdLpccRkSce-1X3cHcgFERM44IbrBnMDiPXGEWvycgFUONgnIj7iZ_XBO3PgUh2cq-Q32Ux84HgfNHxQC64VDA-NjU5MlAgZCcKRxz9vPK09XAtUbfewSfzFizPVtfw6oaku0OvyYc_N6B296xrfnsKEEqWF0"]
METAAPI_ACCOUNT_ID = os.environ["3f3a5aee-91fe-43ce-97d4-18f1136dbde6"]
TELEGRAM_BOT_TOKEN = os.environ["8376148746:AAGQcbL-r620xlPNjAsIptkF-mzmoQv2qDg"]
TELEGRAM_CHAT_ID = os.environ["8235208636"]

YF_TICKER = "GC=F"  # Gold Futures — best proxy for XAUUSD
YF_INTERVAL = "1m"
YF_PERIOD = "5d"
CANDLE_HISTORY = 200

SYMBOL = "XAUUSD.m"  # broker symbol (adjust if needed)

# ── Bollinger Band settings ──────────────────────────────────────────────────
BB_PERIOD = 20
BB_STD = 2.0
BB_ENTRY_PCT_B_BUY = 0.05  # %B ≤ this  → BUY  signal (below lower band)
BB_ENTRY_PCT_B_SELL = 0.95  # %B ≥ this  → SELL signal (above upper band)
BB_MIN_WIDTH_PCT = 0.06  # minimum BB width % of price (avoids squeeze)

# ── ATR settings ─────────────────────────────────────────────────────────────
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.5  # SL = ATR × this

# ── Risk & execution ─────────────────────────────────────────────────────────
LOT_SIZE = 0.01
PROFIT_TARGET_USD = 1.20  # early scalp close
LOSS_LIMIT_USD = -0.90  # early stop
DAILY_LOSS_LIMIT_PCT = 5.0  # stop trading if daily drawdown > 5 %
LOOP_INTERVAL = 5  # seconds between scans
MAX_RETRIES = 5

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("trading_bot/bot.log"),
    ],
)
log = logging.getLogger("GoldBot_BB")


# ─────────────────────────────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────────────────────────────
class BotState:
    def __init__(self):
        self.open_trade: Optional[dict] = None
        self.daily_loss_usd: float = 0.0
        self.daily_loss_stopped: bool = False
        self.trade_count: int = 0
        self.session_pnl: float = 0.0
        self.account_balance: float = 0.0


state = BotState()


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────────────────────────────────────
async def send_telegram_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    log.warning(f"Telegram error {resp.status}: {await resp.text()}")
                else:
                    log.info("📨 Telegram message sent.")
    except Exception as e:
        log.error(f"Telegram failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# METAAPI CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
async def connect_metaapi():
    log.info("Connecting to MetaAPI…")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            api = MetaApi(METAAPI_TOKEN)
            account = await api.metatrader_account_api.get_account(METAAPI_ACCOUNT_ID)

            if account.state not in ("DEPLOYING", "DEPLOYED"):
                log.info("Deploying account…")
                await account.deploy()

            await account.wait_connected()
            connection = account.get_streaming_connection()
            await connection.connect()
            await connection.wait_synchronized()

            log.info("✅ MetaAPI connected and synchronised.")
            return api, connection, account

        except Exception as e:
            log.error(f"Connection attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(10 * attempt)
            else:
                raise RuntimeError("Max retries exceeded.") from e


# ─────────────────────────────────────────────────────────────────────────────
# MARKET DATA — YAHOO FINANCE + BOLLINGER BANDS + ATR
# ─────────────────────────────────────────────────────────────────────────────
def get_market_data() -> Optional[pd.DataFrame]:
    """
    Fetch 1-minute OHLCV from Yahoo Finance and compute:
      • Bollinger Bands (20, 2.0) — upper / mid / lower / %B / width
      • ATR (14)                  — for adaptive stop-loss sizing
    """
    try:
        ticker = yf.Ticker(YF_TICKER)
        df = ticker.history(period=YF_PERIOD, interval=YF_INTERVAL, auto_adjust=True)

        if df is None or df.empty:
            log.warning("Yahoo Finance returned no data.")
            return None

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        df = df.tail(CANDLE_HISTORY).copy()
        df.reset_index(drop=True, inplace=True)

        # ── Bollinger Bands ───────────────────────────────────────────────
        bb = BollingerBands(df["Close"], window=BB_PERIOD, window_dev=BB_STD)
        df["BB_upper"] = bb.bollinger_hband()
        df["BB_mid"] = bb.bollinger_mavg()
        df["BB_lower"] = bb.bollinger_lband()
        df["BB_pct_b"] = bb.bollinger_pband()  # %B  (0=lower, 1=upper)
        df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / df["BB_mid"] * 100  # %

        # ── ATR ───────────────────────────────────────────────────────────
        df["ATR"] = AverageTrueRange(
            df["High"], df["Low"], df["Close"], window=ATR_PERIOD
        ).average_true_range()

        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)

        c = df.iloc[-1]
        log.info(
            f"📊 BB | Close: {c['Close']:.2f} | "
            f"Upper: {c['BB_upper']:.2f} | Mid: {c['BB_mid']:.2f} | Lower: {c['BB_lower']:.2f} | "
            f"%B: {c['BB_pct_b']:.3f} | Width: {c['BB_width']:.2f}% | ATR: {c['ATR']:.2f}"
        )
        return df

    except Exception as e:
        log.error(f"get_market_data error: {e}", exc_info=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY — BOLLINGER BAND SIGNAL
# ─────────────────────────────────────────────────────────────────────────────
def detect_bb_signal(df: pd.DataFrame) -> Optional[str]:
    """
    Pure Bollinger Band mean-reversion signal:

    BUY  conditions (all must be true):
      1. Current %B ≤ BB_ENTRY_PCT_B_BUY  (price at/below lower band)
      2. Previous candle also had %B < 0.15 (band confirmed, not one spike)
      3. BB width > BB_MIN_WIDTH_PCT       (bands are expanded, not squeezing)

    SELL conditions (all must be true):
      1. Current %B ≥ BB_ENTRY_PCT_B_SELL  (price at/above upper band)
      2. Previous candle also had %B > 0.85 (band confirmed, not one spike)
      3. BB width > BB_MIN_WIDTH_PCT        (bands are expanded)
    """
    if len(df) < BB_PERIOD + 3:
        return None

    curr = df.iloc[-1]
    prev = df.iloc[-2]

    width_ok = curr["BB_width"] > BB_MIN_WIDTH_PCT

    if not width_ok:
        log.info(
            f"BB squeeze detected (width {curr['BB_width']:.2f}% < {BB_MIN_WIDTH_PCT}%) — no trade."
        )
        return None

    # ── BUY: price at or below lower band ────────────────────────────────
    if curr["BB_pct_b"] <= BB_ENTRY_PCT_B_BUY and prev["BB_pct_b"] < 0.15:
        log.info(
            f"🔵 BB BUY signal | %B: {curr['BB_pct_b']:.3f} | "
            f"Close: {curr['Close']:.2f} ≤ Lower: {curr['BB_lower']:.2f} | "
            f"Width: {curr['BB_width']:.2f}%"
        )
        return "BUY"

    # ── SELL: price at or above upper band ───────────────────────────────
    if curr["BB_pct_b"] >= BB_ENTRY_PCT_B_SELL and prev["BB_pct_b"] > 0.85:
        log.info(
            f"🔴 BB SELL signal | %B: {curr['BB_pct_b']:.3f} | "
            f"Close: {curr['Close']:.2f} ≥ Upper: {curr['BB_upper']:.2f} | "
            f"Width: {curr['BB_width']:.2f}%"
        )
        return "SELL"

    log.info(
        f"No BB signal | %B: {curr['BB_pct_b']:.3f} | Width: {curr['BB_width']:.2f}%"
    )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# TRADE EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
async def execute_trade(connection, direction: str, df: pd.DataFrame) -> bool:
    """
    Place a BUY or SELL order.
    SL  = entry ± ATR × ATR_SL_MULTIPLIER   (adaptive)
    TP  = BB mid-band                         (mean-reversion target)
    """
    curr = df.iloc[-1]
    price = curr["Close"]
    atr = curr["ATR"]
    sl_dist = round(atr * ATR_SL_MULTIPLIER, 2)

    if direction == "BUY":
        sl = round(price - sl_dist, 2)
        tp = round(curr["BB_mid"], 2)
        band_label = f"Lower: {curr['BB_lower']:.2f}"
    else:
        sl = round(price + sl_dist, 2)
        tp = round(curr["BB_mid"], 2)
        band_label = f"Upper: {curr['BB_upper']:.2f}"

    log.info(
        f"📤 {direction} | Entry: {price:.2f} | SL: {sl:.2f} | TP: {tp:.2f} | ATR: {atr:.2f} | Lot: {LOT_SIZE}"
    )

    try:
        if direction == "BUY":
            result = await connection.create_market_buy_order(
                SYMBOL, LOT_SIZE, sl, tp, options={"comment": "BB_BUY"}
            )
        else:
            result = await connection.create_market_sell_order(
                SYMBOL, LOT_SIZE, sl, tp, options={"comment": "BB_SELL"}
            )

        trade_id = result.get("orderId") or result.get("positionId", "unknown")
        log.info(f"✅ Trade opened — ID: {trade_id}")

        state.open_trade = {
            "id": trade_id,
            "type": direction,
            "entry": price,
            "sl": sl,
            "tp": tp,
            "bb_mid": curr["BB_mid"],
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }
        state.trade_count += 1

        msg = (
            f"🚀 <b>TRADE OPENED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Symbol : {SYMBOL}\n"
            f"Type   : <b>{direction}</b>\n"
            f"Entry  : {price:.2f}\n"
            f"SL     : {sl:.2f}  (ATR×{ATR_SL_MULTIPLIER})\n"
            f"TP     : {tp:.2f}  (BB Mid)\n"
            f"Band   : {band_label}\n"
            f"%B     : {curr['BB_pct_b']:.3f}\n"
            f"BB W   : {curr['BB_width']:.2f}%\n"
            f"Lot    : {LOT_SIZE}\n"
            f"Strategy: Bollinger Bands Mean-Reversion\n"
            f"Trade #{state.trade_count}"
        )
        await send_telegram_message(msg)
        return True

    except TradeException as e:
        log.error(f"TradeException: {e.message} | code: {e.stringCode}")
        return False
    except Exception as e:
        log.error(f"execute_trade error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# POSITION MONITORING
# ─────────────────────────────────────────────────────────────────────────────
async def get_open_positions(connection) -> list:
    try:
        terminal = connection.terminal_state
        positions = terminal.positions if terminal else []
        return [p for p in positions if p.get("symbol") == SYMBOL]
    except Exception as e:
        log.error(f"get_open_positions error: {e}")
        return []


async def close_trade(
    connection, position_id: str, reason: str = ""
) -> Optional[float]:
    try:
        positions = await get_open_positions(connection)
        pos = next((p for p in positions if str(p.get("id")) == str(position_id)), None)

        if pos is None:
            log.warning(f"Position {position_id} not found (already closed by broker).")
            state.open_trade = None
            return None

        await connection.close_position(
            position_id, options={"comment": f"BB_{reason}"}
        )
        pnl = pos.get("profit", 0.0)

        log.info(f"🔒 Closed {position_id} | PnL: ${pnl:.2f} | Reason: {reason}")
        state.session_pnl += pnl
        state.daily_loss_usd += min(pnl, 0)

        trade_type = state.open_trade["type"] if state.open_trade else "N/A"

        if pnl >= 0:
            msg = (
                f"✅ <b>PROFIT — CLOSED</b>\n"
                f"Symbol : {SYMBOL} | {trade_type}\n"
                f"Profit : +${pnl:.2f}\n"
                f"Reason : {reason}\n"
                f"Session P&amp;L: ${state.session_pnl:.2f}"
            )
        else:
            msg = (
                f"❌ <b>LOSS — CLOSED</b>\n"
                f"Symbol : {SYMBOL} | {trade_type}\n"
                f"Loss   : -${abs(pnl):.2f}\n"
                f"Reason : {reason}\n"
                f"Session P&amp;L: ${state.session_pnl:.2f}"
            )

        await send_telegram_message(msg)
        state.open_trade = None
        return pnl

    except Exception as e:
        log.error(f"close_trade error: {e}")
        return None


async def monitor_open_trade(connection, df: Optional[pd.DataFrame]) -> None:
    """
    Monitor the open trade. Close when:
      1. USD profit target hit (scalp exit)
      2. USD loss limit hit (emergency exit)
      3. Broker already closed it via SL/TP
    Also logs current %B so you can see progress toward mid-band.
    """
    if not state.open_trade:
        return

    positions = await get_open_positions(connection)
    pos_id = str(state.open_trade["id"])
    pos = next((p for p in positions if str(p.get("id")) == pos_id), None)

    if pos is None:
        log.info(f"Position {pos_id} closed by broker (SL/TP hit).")
        state.open_trade = None
        return

    pnl = pos.get("profit", 0.0)

    bb_info = ""
    if df is not None and len(df) > 0:
        c = df.iloc[-1]
        bb_info = f" | %B: {c['BB_pct_b']:.3f} | Mid: {c['BB_mid']:.2f}"

    log.info(f"💼 Open {state.open_trade['type']} | PnL: ${pnl:.2f}{bb_info}")

    if pnl >= PROFIT_TARGET_USD:
        log.info(f"🎯 Profit target ${pnl:.2f} reached — scalp exit.")
        await close_trade(connection, pos_id, reason="ScalpProfit")

    elif pnl <= LOSS_LIMIT_USD:
        log.info(f"⛔ Loss limit ${pnl:.2f} reached — emergency exit.")
        await close_trade(connection, pos_id, reason="LossLimit")


# ─────────────────────────────────────────────────────────────────────────────
# DAILY LOSS GUARD
# ─────────────────────────────────────────────────────────────────────────────
async def check_daily_loss_limit(connection) -> bool:
    try:
        terminal = connection.terminal_state
        account_info = terminal.account_information if terminal else None
        if account_info:
            state.account_balance = account_info.get("balance", state.account_balance)

        if state.account_balance > 0:
            loss_pct = (abs(state.daily_loss_usd) / state.account_balance) * 100
            if loss_pct >= DAILY_LOSS_LIMIT_PCT:
                if not state.daily_loss_stopped:
                    log.warning(
                        f"🚨 Daily loss limit: {loss_pct:.1f}% ≥ {DAILY_LOSS_LIMIT_PCT}%"
                    )
                    await send_telegram_message(
                        f"🚨 <b>DAILY LOSS LIMIT REACHED</b>\n"
                        f"Loss: {loss_pct:.1f}% of balance\nTrading paused for today."
                    )
                    state.daily_loss_stopped = True
                return True
    except Exception as e:
        log.error(f"check_daily_loss_limit error: {e}")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# MARKET SUMMARY (periodic Telegram update)
# ─────────────────────────────────────────────────────────────────────────────
def build_bb_summary(df: pd.DataFrame) -> str:
    c = df.iloc[-1]
    p = df.iloc[-2]
    chg = c["Close"] - p["Close"]
    pct = (chg / p["Close"]) * 100

    zone = (
        "🔵 At/Below Lower Band — BUY Zone"
        if c["BB_pct_b"] <= 0.10
        else "🔴 At/Above Upper Band — SELL Zone"
        if c["BB_pct_b"] >= 0.90
        else "⚪ Inside Bands — No Signal"
    )

    squeeze = (
        "⚠️ Squeeze (low volatility)"
        if c["BB_width"] < BB_MIN_WIDTH_PCT
        else "✅ Bands expanded"
    )

    return (
        f"📊 <b>XAUUSD — BB Report</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Price  : {c['Close']:.2f}  ({'+' if chg >= 0 else ''}{chg:.2f}, {pct:+.2f}%)\n"
        f"Upper  : {c['BB_upper']:.2f}\n"
        f"Mid    : {c['BB_mid']:.2f}\n"
        f"Lower  : {c['BB_lower']:.2f}\n"
        f"%B     : {c['BB_pct_b']:.3f}\n"
        f"Width  : {c['BB_width']:.2f}%   {squeeze}\n"
        f"ATR    : {c['ATR']:.2f}\n"
        f"Zone   : {zone}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Trades : #{state.trade_count} | Session P&amp;L: ${state.session_pnl:.2f}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TRADING LOOP
# ─────────────────────────────────────────────────────────────────────────────
async def trading_loop(connection) -> None:
    log.info("🤖 Bollinger Band trading loop started.")
    await send_telegram_message(
        f"🤖 <b>Gold BB Bot — LIVE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Data     : Yahoo Finance ({YF_TICKER}) M1\n"
        f"Execution: MetaAPI → {SYMBOL}\n"
        f"Strategy : Bollinger Bands Mean-Reversion\n"
        f"BB       : period={BB_PERIOD}, std={BB_STD}\n"
        f"BUY at   : %B ≤ {BB_ENTRY_PCT_B_BUY} (lower band touch)\n"
        f"SELL at  : %B ≥ {BB_ENTRY_PCT_B_SELL} (upper band touch)\n"
        f"TP       : BB Mid-band\n"
        f"SL       : ATR × {ATR_SL_MULTIPLIER}\n"
        f"Lot      : {LOT_SIZE}  |  Max loss/day: {DAILY_LOSS_LIMIT_PCT}%"
    )

    summary_counter = 0
    df_cache: Optional[pd.DataFrame] = None

    while True:
        try:
            # ── Daily loss guard ─────────────────────────────────────────
            if state.daily_loss_stopped:
                await check_daily_loss_limit(connection)
                log.info("⏸ Daily loss limit active — skipping.")
                await asyncio.sleep(60)
                continue

            # ── Fetch fresh market data ──────────────────────────────────
            df = await asyncio.get_event_loop().run_in_executor(None, get_market_data)
            if df is None or len(df) < BB_PERIOD + 3:
                log.warning("Insufficient data — retrying…")
                await asyncio.sleep(LOOP_INTERVAL)
                continue
            df_cache = df

            # ── Monitor existing trade (higher priority) ─────────────────
            if state.open_trade :
                  await monitor_open_trade(connection, df)
                await asyncio.sleep(LOOP_INTERVAL)
                continue

            # ── Periodic BB summary every ~5 minutes ─────────────────────
            summary_counter += 1
            if summary_counter % 60 == 0:
                await send_telegram_message(build_bb_summary(df))

            # ── BB signal detection ──────────────────────────────────────
            direction = detect_bb_signal(df)
            if direction is None:
                await asyncio.sleep(LOOP_INTERVAL)
                continue

            # ── Daily loss check before entry ────────────────────────────
            if await check_daily_loss_limit(connection):
                await asyncio.sleep(LOOP_INTERVAL)
                continue

            # ── Execute trade ────────────────────────────────────────────
            await execute_trade(connection, direction, df)

        except asyncio.CancelledError:
            log.info("Loop cancelled.")
            break
        except Exception as e:
            log.error(f"Loop error: {e}", exc_info=True)
            await send_telegram_message(f"⚠️ Bot error: {e}")
            await asyncio.sleep(15)

        await asyncio.sleep(LOOP_INTERVAL)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    log.info("=" * 60)
    log.info("  XAUUSD BOLLINGER BAND SCALPING BOT")
    log.info("=" * 60)
    api, connection, account = await connect_metaapi()
    try:
        await trading_loop(connection)
    finally:
        log.info("Closing connection…")
        await connection.close()
        log.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
  
                     
