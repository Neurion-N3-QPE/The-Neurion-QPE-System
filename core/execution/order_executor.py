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

    async def reconcile_positions(self, internal_positions: Dict[str, Dict]) -> Dict:
        """
        Reconcile internal positions with broker positions from IG Markets.

        Args:
            internal_positions: Mapping of dealId -> internal record

        Returns:
            Summary dict with reconciliation actions taken.
        """
        try:
            broker_positions = await self.ig_api.get_positions()
            broker_map = {p.get('position', {}).get('dealId'): p for p in broker_positions if p.get('position')}

            to_add = []
            to_remove = []

            # Find positions present at broker but missing internally
            for deal_id, broker_pos in broker_map.items():
                if deal_id not in internal_positions:
                    to_add.append({'dealId': deal_id, 'broker': broker_pos})

            # Find internal positions no longer at broker
            for deal_id in list(internal_positions.keys()):
                if deal_id not in broker_map:
                    to_remove.append(deal_id)

            # Apply reconciliation: add missing and mark removed
            for item in to_add:
                logger.warning(f"🔁 Reconciling: broker has position not tracked internally: {item['dealId']}")
                # Placeholder: in production, update internal store or create audit record

            for deal_id in to_remove:
                logger.warning(f"🔁 Reconciling: internal position {deal_id} not present at broker - marking closed")
                # Placeholder: mark internal position as closed and move to history
                internal_positions.pop(deal_id, None)

            summary = {'added': len(to_add), 'removed': len(to_remove), 'broker_total': len(broker_map)}
            logger.info(f"✅ Reconciliation complete: {summary}")
            return summary

        except Exception as e:
            logger.error(f"❌ Reconciliation failed: {e}")
            return {'error': str(e)}