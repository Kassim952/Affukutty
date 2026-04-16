"""
risk_manager.py — Dynamic lot sizing, SL/TP calculation, daily limits
"""

import logging
from dataclasses import dataclass

from config import (
    RISK_PER_TRADE_PCT, RISK_REWARD_RATIO,
    MAX_DAILY_TRADES, MAX_DAILY_LOSS_PCT, MAX_CONCURRENT_TRADES,
    MIN_LOT_SIZE, MAX_LOT_SIZE,
    PIP_SIZE, PIP_VALUE_USD,
)

logger = logging.getLogger(__name__)


@dataclass
class TradeParams:
    symbol: str
    direction: str      # 'BUY' or 'SELL'
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    risk_usd: float


class RiskManager:
    def __init__(self):
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.starting_balance = None

    def set_balance(self, balance: float):
        if self.starting_balance is None:
            self.starting_balance = balance

    def reset_daily(self):
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.starting_balance = None
        logger.info("Daily stats reset.")

    def can_trade(self, account_balance: float, open_trades: int) -> tuple[bool, str]:
        """Check all daily limits before allowing a trade."""
        if self.daily_trades >= MAX_DAILY_TRADES:
            return False, f"Daily trade limit reached ({MAX_DAILY_TRADES})"

        if open_trades >= MAX_CONCURRENT_TRADES:
            return False, f"Max concurrent trades reached ({MAX_CONCURRENT_TRADES})"

        if self.starting_balance and account_balance < self.starting_balance:
            loss_pct = (self.starting_balance - account_balance) / self.starting_balance
            if loss_pct >= MAX_DAILY_LOSS_PCT:
                return False, f"Daily loss limit hit ({loss_pct:.1%})"

        return True, "OK"

    def calculate_lot_size(
        self,
        symbol: str,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        """Calculate lot size based on account risk % and SL distance."""
        risk_usd = account_balance * RISK_PER_TRADE_PCT
        sl_distance = abs(entry_price - stop_loss)

        if sl_distance == 0:
            logger.warning(f"SL distance is 0 for {symbol}, using min lot")
            return MIN_LOT_SIZE

        pip_size  = PIP_SIZE.get(symbol, 0.0001)
        pip_value = PIP_VALUE_USD.get(symbol, 10.0)

        sl_pips  = sl_distance / pip_size
        lot_size = risk_usd / (sl_pips * pip_value)
        lot_size = round(lot_size, 2)
        lot_size = max(MIN_LOT_SIZE, min(lot_size, MAX_LOT_SIZE))

        logger.info(
            f"{symbol} lot calc: balance={account_balance:.2f}, "
            f"risk={risk_usd:.2f}, sl_pips={sl_pips:.1f}, lots={lot_size}"
        )
        return lot_size

    def build_trade_params(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        zone_price: float,
        account_balance: float,
        atr: float,
    ) -> TradeParams | None:
        """
        Build complete trade parameters.
        SL placed below support (BUY) or above resistance (SELL).
        TP at RISK_REWARD_RATIO × risk.
        """
        pip_size = PIP_SIZE.get(symbol, 0.0001)
        buffer   = atr * 0.5 if atr > 0 else pip_size * 10

        if direction == "BUY":
            stop_loss  = zone_price - buffer
            risk       = entry_price - stop_loss
            take_profit = entry_price + (risk * RISK_REWARD_RATIO)
        else:
            stop_loss  = zone_price + buffer
            risk       = stop_loss - entry_price
            take_profit = entry_price - (risk * RISK_REWARD_RATIO)

        if risk <= 0:
            logger.warning(f"{symbol} invalid risk: {risk}")
            return None

        lot_size = self.calculate_lot_size(symbol, account_balance, entry_price, stop_loss)
        risk_usd = account_balance * RISK_PER_TRADE_PCT

        return TradeParams(
            symbol=symbol,
            direction=direction,
            entry_price=round(entry_price, 5),
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            lot_size=lot_size,
            risk_usd=round(risk_usd, 2),
        )

    def record_trade_opened(self):
        self.daily_trades += 1

    def record_trade_closed(self, pnl: float):
        self.daily_pnl += pnl
