import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class OrderExecutor:
    """
    Handles the execution of trades by building payloads and sending requests to IG Markets.
    """

    def __init__(self, ig_api):
        self.ig_api = ig_api

    async def execute_trade(
        self,
        epic: str,
        direction: str,
        size: float,
        open_level: Optional[float] = None,
        close_level: Optional[float] = None,
        agent: str = "Unknown"
    ) -> Dict:
        """
        Execute a trade with the given parameters.

        Args:
            epic: Market epic code (e.g., 'IX.D.SPTRD.DAILY.IP')
            direction: 'BUY' or 'SELL'
            size: Position size in GBP per point
            open_level: Optional open level
            close_level: Optional close level
            agent: The agent executing the trade

        Returns:
            API response from IG Markets.
        """
        payload = {
            "epic": epic,
            "direction": direction.upper(),
            "size": round(float(size), 2),
            "orderType": "MARKET",
            "guaranteedStop": False,
            "forceOpen": True,
            "currencyCode": "GBP",
            "timeInForce": "FILL_OR_KILL",
            "expiry": "DFB",
        }

        logger.info(f"Executing trade: {payload}")

        try:
            response = await self.ig_api.open_position(
                epic=epic,
                direction=direction,
                size=size,
                stop_loss=None,
                take_profit=None
            )

            logger.info(f"Trade executed by {agent}: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return {"error": str(e)}