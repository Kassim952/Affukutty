"""
main.py — Trading bot main loop
Scans all symbols every 10 seconds, executes best setups.
AI analysis (GPT-5-mini) validates every setup before execution.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone

from config import (
    SYMBOLS, LOOP_INTERVAL_SECONDS, AI_CONFIDENCE_THRESHOLD,
    RSI_OVERSOLD, RSI_OVERBOUGHT,
)
from data import fetch_all_timeframes
from strategy import get_trend, detect_zones, get_nearest_zone
from confirmation import check_buy_confirmation, check_sell_confirmation
from execution import MetaAPIExecutor
from risk_manager import RiskManager
from filters import all_filters_pass
from ai_analyst import analyze_setup, format_ai_alert_section
from telegram_alerts import (
    alert_trade_opened, alert_trade_closed,
    alert_info, alert_error, send_alert,
    format_trade_opened,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log"),
    ],
)
logger = logging.getLogger("main")


class TradingBot:
    def __init__(self):
        self.executor = MetaAPIExecutor()
        self.risk_manager = RiskManager()
        self.open_trade_symbols: set[str] = set()
        self.running = False
        self._last_reset_day: int | None = None
        self._trade_entries: dict[str, dict] = {}

    async def start(self):
        logger.info("=" * 60)
        logger.info("  Multi-Asset S&R Trading Bot + AI Analysis")
        logger.info(f"  Symbols: {', '.join(SYMBOLS)}")
        logger.info(f"  AI confidence threshold: {AI_CONFIDENCE_THRESHOLD}%")
        logger.info("=" * 60)

        connected = await self.executor.connect()
        if not connected:
            logger.error("Failed to connect to MetaAPI. Exiting.")
            alert_error("Trading bot failed to connect to MetaAPI broker.")
            return

        alert_info(
            "🤖 AI-Powered Trading Bot started.\n"
            f"Scanning {len(SYMBOLS)} symbols. AI confidence threshold: {AI_CONFIDENCE_THRESHOLD}%"
        )
        self.running = True

        while self.running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.exception(f"Cycle error: {e}")
                alert_error(f"Bot cycle error: {e}")

            await asyncio.sleep(LOOP_INTERVAL_SECONDS)

    async def stop(self):
        logger.info("Shutting down trading bot...")
        self.running = False
        await self.executor.disconnect()
        alert_info("Trading bot stopped.")

    async def _run_cycle(self):
        now_utc = datetime.now(timezone.utc)
        logger.info(f"--- Cycle at {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC ---")

        # Daily reset check
        if self._last_reset_day != now_utc.day:
            self.risk_manager.reset_daily()
            self._last_reset_day = now_utc.day
            logger.info("Daily stats reset.")

        # Get account info
        account_info = await self.executor.get_account_info()
        if not account_info:
            logger.warning("Could not get account info. Skipping cycle.")
            return

        balance = account_info["balance"]
        self.risk_manager.set_balance(balance)
        logger.info(
            f"Balance: {balance:.2f} {account_info['currency']} "
            f"| Equity: {account_info['equity']:.2f}"
        )

        # Get current open positions
        open_positions = await self.executor.get_open_positions()
        open_symbols = {p.symbol for p in open_positions}
        self.open_trade_symbols = open_symbols

        # Detect closed trades
        for symbol, entry_data in list(self._trade_entries.items()):
            if symbol not in open_symbols:
                price_info = await self.executor.get_symbol_price(symbol)
                close_price = entry_data.get("entry_price", 0.0)
                if price_info:
                    close_price = (
                        price_info["bid"] if entry_data["direction"] == "BUY"
                        else price_info["ask"]
                    )

                pnl = 0.0
                if entry_data["direction"] == "BUY":
                    pnl = (close_price - entry_data["entry_price"]) * entry_data["lot_size"] * 100000
                else:
                    pnl = (entry_data["entry_price"] - close_price) * entry_data["lot_size"] * 100000

                self.risk_manager.record_trade_closed(pnl)
                alert_trade_closed(
                    symbol=symbol,
                    direction=entry_data["direction"],
                    entry=entry_data["entry_price"],
                    close_price=close_price,
                    sl=entry_data["stop_loss"],
                    tp=entry_data["take_profit"],
                    pnl=pnl,
                )
                del self._trade_entries[symbol]
                logger.info(f"Trade closed detected: {symbol}, estimated PnL: {pnl:.2f}")

        # Check daily limits
        can_trade, reason = self.risk_manager.can_trade(balance, len(open_positions))
        if not can_trade:
            logger.info(f"Trading paused: {reason}")
            return

        # Evaluate all symbols for setups
        setups = []
        for symbol in SYMBOLS:
            if symbol in open_symbols:
                continue
            setup = await self._evaluate_symbol(symbol, balance)
            if setup:
                setups.append(setup)

        if not setups:
            logger.info("No valid technical setups found this cycle.")
            return

        # Run AI analysis on all candidate setups (in event loop thread)
        logger.info(f"Running AI analysis on {len(setups)} setup(s)...")
        for setup in setups:
            ai = await asyncio.get_event_loop().run_in_executor(
                None, analyze_setup, setup
            )
            setup["ai_analysis"] = ai
            setup["ai_score"] = ai.enhanced_score

        # Filter by AI approval
        ai_approved = [s for s in setups if s["ai_analysis"].approved]
        ai_rejected = [s for s in setups if not s["ai_analysis"].approved]

        for s in ai_rejected:
            ai = s["ai_analysis"]
            logger.info(
                f"AI REJECTED {s['symbol']} {s['direction']}: "
                f"confidence={ai.confidence}% — {ai.reasoning}"
            )

        if not ai_approved:
            logger.info("All setups rejected by AI this cycle.")
            return

        # Sort approved setups by AI-enhanced score
        ai_approved.sort(key=lambda x: x["ai_score"], reverse=True)
        best = ai_approved[0]
        ai = best["ai_analysis"]
        logger.info(
            f"Best AI-approved setup: {best['symbol']} {best['direction']} "
            f"(AI confidence={ai.confidence}%, regime={ai.market_regime}, score={best['ai_score']:.2f})"
        )
        await self._execute_setup(best)

    async def _evaluate_symbol(self, symbol: str, balance: float) -> dict | None:
        """Run full technical analysis on a symbol. Returns setup dict or None."""
        try:
            data = fetch_all_timeframes(symbol)
            df15m = data.get("15m")
            df5m = data.get("5m")
            df1m = data.get("1m")

            if df15m is None or df5m is None or df1m is None:
                logger.debug(f"{symbol}: missing data")
                return None

            # 1. Trend filter (15M EMA50/200)
            trend = get_trend(df15m)
            if trend is None:
                logger.debug(f"{symbol}: no clear trend")
                return None

            # 2. Live price from broker
            price_info = await self.executor.get_symbol_price(symbol)
            if price_info:
                spread = price_info["spread"]
                current_price = price_info["ask"] if trend == "BUY" else price_info["bid"]
            else:
                current_price = float(df1m["close"].iloc[-1])
                spread = None

            # 3. Smart filters (session, spread, volatility, news)
            filters_ok, atr = all_filters_pass(symbol, df5m, current_price, spread)
            if not filters_ok:
                return None

            # 4. S&R zone detection (5M)
            zones = detect_zones(df5m)
            if not zones:
                logger.debug(f"{symbol}: no valid S&R zones")
                return None

            # 5. Entry confirmation (1M)
            if trend == "BUY":
                zone = get_nearest_zone(zones, current_price, "support")
                if not zone:
                    return None
                conf = check_buy_confirmation(df1m, zone.price)
                if not conf["confirmed"]:
                    return None
                score = zone.score
                if conf["rsi"] is not None:
                    score += max(0, (RSI_OVERSOLD - conf["rsi"]) / 10)

            else:  # SELL
                zone = get_nearest_zone(zones, current_price, "resistance")
                if not zone:
                    return None
                conf = check_sell_confirmation(df1m, zone.price)
                if not conf["confirmed"]:
                    return None
                score = zone.score
                if conf["rsi"] is not None:
                    score += max(0, (conf["rsi"] - RSI_OVERBOUGHT) / 10)

            logger.info(
                f"Technical setup found: {symbol} {trend} | "
                f"price={current_price:.5f} zone={zone.price:.5f} "
                f"RSI={conf.get('rsi', 'N/A')} pattern={conf.get('pattern')} score={score:.1f}"
            )

            return {
                "symbol": symbol,
                "direction": trend,
                "current_price": current_price,
                "zone_price": zone.price,
                "atr": atr or 0.0,
                "pattern": conf.get("pattern"),
                "rsi": conf.get("rsi"),
                "score": score,
                "balance": balance,
            }

        except Exception as e:
            logger.error(f"Error evaluating {symbol}: {e}")
            return None

    async def _execute_setup(self, setup: dict):
        """Execute an AI-approved trade setup."""
        symbol = setup["symbol"]
        direction = setup["direction"]
        balance = setup["balance"]
        atr = setup["atr"]
        ai = setup.get("ai_analysis")

        trade_params = self.risk_manager.build_trade_params(
            symbol=symbol,
            direction=direction,
            entry_price=setup["current_price"],
            zone_price=setup["zone_price"],
            account_balance=balance,
            atr=atr,
        )

        if not trade_params:
            logger.warning(f"{symbol}: could not calculate trade params")
            return

        logger.info(
            f"Executing {direction} on {symbol}: "
            f"entry={trade_params.entry_price}, "
            f"sl={trade_params.stop_loss}, "
            f"tp={trade_params.take_profit}, "
            f"lots={trade_params.lot_size}"
        )

        position_id = await self.executor.open_trade(
            symbol=symbol,
            direction=direction,
            lot_size=trade_params.lot_size,
            stop_loss=trade_params.stop_loss,
            take_profit=trade_params.take_profit,
        )

        if position_id:
            self.risk_manager.record_trade_opened()
            self._trade_entries[symbol] = {
                "position_id": position_id,
                "direction": direction,
                "entry_price": trade_params.entry_price,
                "stop_loss": trade_params.stop_loss,
                "take_profit": trade_params.take_profit,
                "lot_size": trade_params.lot_size,
            }

            # Build rich Telegram alert with AI analysis included
            base_msg = format_trade_opened(
                symbol=symbol,
                direction=direction,
                entry=trade_params.entry_price,
                sl=trade_params.stop_loss,
                tp=trade_params.take_profit,
                lot=trade_params.lot_size,
                pattern=setup.get("pattern"),
                rsi=setup.get("rsi"),
            )
            if ai:
                ai_section = format_ai_alert_section(ai)
                full_msg = base_msg + ai_section
            else:
                full_msg = base_msg

            send_alert(full_msg)
            logger.info(f"Trade opened: {symbol} {direction} position={position_id}")
        else:
            logger.error(f"Failed to execute trade on {symbol}")


async def main():
    bot = TradingBot()

    def handle_exit(sig, frame):
        logger.info(f"Signal {sig} received, shutting down...")
        asyncio.get_event_loop().create_task(bot.stop())

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
