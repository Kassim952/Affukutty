"""
execution.py — MetaAPI trade execution (MT4/MT5)
Handles: open trade, close trade, get open positions, account info
"""

import os
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

METAAPI_TOKEN = os.environ.get("METAAPI_TOKEN", "")
METAAPI_ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "")
MAGIC_NUMBER = 777888


@dataclass
class OpenTrade:
    position_id: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    open_time: str


class MetaAPIExecutor:
    def __init__(self):
        self._api = None
        self._connection = None
        self._account = None

    async def connect(self):
        """Connect to MetaAPI and synchronize the account."""
        try:
            from metaapi_cloud_sdk import MetaApi
            self._api = MetaApi(METAAPI_TOKEN)
            self._account = await self._api.metatrader_account_api.get_account(METAAPI_ACCOUNT_ID)

            initial_state = self._account.state
            if initial_state not in ["DEPLOYED", "DEPLOYING"]:
                logger.info("Deploying MetaAPI account...")
                await self._account.deploy()

            logger.info("Waiting for MetaAPI account to connect to broker...")
            await self._account.wait_connected(timeout_in_seconds=60)

            self._connection = self._account.get_rpc_connection()
            await self._connection.connect()
            await self._connection.wait_synchronized(timeout_in_seconds=60)

            logger.info("MetaAPI connected and synchronized successfully")
            return True

        except Exception as e:
            logger.error(f"MetaAPI connection failed: {e}")
            return False

    async def disconnect(self):
        """Close the MetaAPI connection."""
        try:
            if self._connection:
                await self._connection.close()
            if self._api:
                self._api.close()
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

    async def get_account_info(self) -> dict | None:
        """Returns account balance, equity, currency."""
        try:
            info = await self._connection.get_account_information()
            return {
                "balance": info.get("balance", 0.0),
                "equity": info.get("equity", 0.0),
                "currency": info.get("currency", "USD"),
                "margin_free": info.get("freeMargin", 0.0),
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None

    async def get_open_positions(self) -> list[OpenTrade]:
        """Return list of currently open positions placed by this bot (magic=777888)."""
        try:
            positions = await self._connection.get_positions()
            result = []
            for pos in positions:
                if pos.get("magic") != MAGIC_NUMBER:
                    continue
                result.append(OpenTrade(
                    position_id=pos.get("id", ""),
                    symbol=pos.get("symbol", ""),
                    direction="BUY" if pos.get("type") == "POSITION_TYPE_BUY" else "SELL",
                    entry_price=pos.get("openPrice", 0.0),
                    stop_loss=pos.get("stopLoss", 0.0),
                    take_profit=pos.get("takeProfit", 0.0),
                    lot_size=pos.get("volume", 0.0),
                    open_time=str(pos.get("time", "")),
                ))
            return result
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    async def open_trade(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "SR_Bot",
    ) -> str | None:
        """
        Open a market order.
        Returns position ID on success, None on failure.
        """
        try:
            if direction == "BUY":
                result = await self._connection.create_market_buy_order(
                    symbol=symbol,
                    volume=lot_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    options={
                        "comment": comment,
                        "magic": MAGIC_NUMBER,
                    },
                )
            else:
                result = await self._connection.create_market_sell_order(
                    symbol=symbol,
                    volume=lot_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    options={
                        "comment": comment,
                        "magic": MAGIC_NUMBER,
                    },
                )

            if result and result.get("numericCode") in [0, 10009]:
                pos_id = result.get("positionId", "unknown")
                logger.info(f"Trade opened: {symbol} {direction} {lot_size} lots, ID={pos_id}")
                return pos_id
            else:
                logger.error(f"Order failed: {result}")
                return None

        except Exception as e:
            logger.error(f"Failed to open trade {symbol} {direction}: {e}")
            return None

    async def close_trade(self, position_id: str, symbol: str) -> bool:
        """Close a position by ID."""
        try:
            result = await self._connection.close_position(position_id)
            if result and result.get("numericCode") in [0, 10009]:
                logger.info(f"Trade closed: {symbol} position {position_id}")
                return True
            else:
                logger.error(f"Failed to close {position_id}: {result}")
                return False
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            return False

    async def get_symbol_price(self, symbol: str) -> dict | None:
        """Get current bid/ask price from broker."""
        try:
            price = await self._connection.get_symbol_price(symbol)
            return {
                "bid": price.get("bid", 0.0),
                "ask": price.get("ask", 0.0),
                "spread": price.get("ask", 0.0) - price.get("bid", 0.0),
            }
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    def is_connected(self) -> bool:
        return self._connection is not None
