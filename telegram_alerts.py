"""
telegram_alerts.py — Telegram alert system for trade events
"""

import os
import asyncio
import aiohttp
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def _send_message(text: str) -> bool:
    """Send a message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not set — skipping alert")
        return False

    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    logger.info("Telegram alert sent successfully")
                    return True
                else:
                    body = await resp.text()
                    logger.error(f"Telegram API error {resp.status}: {body}")
                    return False
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


def send_alert(text: str):
    """Synchronous wrapper for sending Telegram alerts."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_send_message(text))
        else:
            loop.run_until_complete(_send_message(text))
    except Exception as e:
        logger.error(f"Alert send error: {e}")


def format_trade_opened(
    symbol: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    lot: float,
    pattern: str | None = None,
    rsi: float | None = None,
) -> str:
    emoji = "🟢" if direction == "BUY" else "🔴"
    lines = [
        f"{emoji} <b>TRADE OPENED</b>",
        f"",
        f"<b>Symbol:</b> {symbol}",
        f"<b>Type:</b> {direction}",
        f"<b>Entry:</b> {entry:.5f}",
        f"<b>SL:</b> {sl:.5f}",
        f"<b>TP:</b> {tp:.5f}",
        f"<b>Lot Size:</b> {lot}",
    ]
    if pattern:
        lines.append(f"<b>Pattern:</b> {pattern.replace('_', ' ').title()}")
    if rsi is not None:
        lines.append(f"<b>RSI:</b> {rsi:.1f}")
    return "\n".join(lines)


def format_trade_closed(
    symbol: str,
    direction: str,
    entry: float,
    close_price: float,
    sl: float,
    tp: float,
    pnl: float,
) -> str:
    result_emoji = "✅" if pnl >= 0 else "❌"
    result_str = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
    lines = [
        f"{result_emoji} <b>TRADE CLOSED</b>",
        f"",
        f"<b>Symbol:</b> {symbol}",
        f"<b>Type:</b> {direction}",
        f"<b>Entry:</b> {entry:.5f}",
        f"<b>Close:</b> {close_price:.5f}",
        f"<b>SL:</b> {sl:.5f}",
        f"<b>TP:</b> {tp:.5f}",
        f"<b>Result:</b> {result_str} USD",
    ]
    return "\n".join(lines)


def alert_trade_opened(symbol, direction, entry, sl, tp, lot, pattern=None, rsi=None):
    text = format_trade_opened(symbol, direction, entry, sl, tp, lot, pattern, rsi)
    send_alert(text)


def alert_trade_closed(symbol, direction, entry, close_price, sl, tp, pnl):
    text = format_trade_closed(symbol, direction, entry, close_price, sl, tp, pnl)
    send_alert(text)


def alert_info(message: str):
    send_alert(f"ℹ️ {message}")


def alert_error(message: str):
    send_alert(f"⚠️ <b>ERROR:</b> {message}")
