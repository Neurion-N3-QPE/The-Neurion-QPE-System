"""
Risk Engine for Dynamic Stop-Loss Management
Implements adaptive stop-loss shrinking to protect profits while allowing upside
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)

class RiskEngine:
    """
    Advanced risk management engine with adaptive stop-loss functionality
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.risk_config = config.get('trading', {}).get('risk_management', {})
        self.stop_updates = {}  # Track stop-loss updates
        
        logger.info("🛡️ Risk Engine initialized")
    
    async def dynamic_stop_management(self, position: Dict, current_price: float) -> Optional[float]:
        """
        Tighten stops as trade moves in profit
        Core Principle: Protect gains while allowing continued upside
        """
        try:
            if not position or not current_price:
                return None
            
            # Get position details
            deal_id = position.get('deal_id')
            entry_price = position.get('level', 0.0)
            direction = position.get('direction', 'BUY')
            size = position.get('size', 0.0)
            current_stop = position.get('stop_level')
            
            if not entry_price or not deal_id:
                return None
            
            # Calculate current P&L and profit ratio
            if direction == 'BUY':
                unrealized_pnl = (current_price - entry_price) * size
                profit_points = current_price - entry_price
            else:  # SELL
                unrealized_pnl = (entry_price - current_price) * size
                profit_points = entry_price - current_price
            
            # Calculate initial risk (R) - distance from entry to original stop
            initial_risk = self._calculate_initial_risk(position, entry_price)
            if initial_risk <= 0:
                return None
            
            # Calculate profit in terms of R (risk units)
            profit_r = profit_points / initial_risk if initial_risk > 0 else 0
            
            logger.debug(f"📊 Stop Analysis - {deal_id}: P&L: £{unrealized_pnl:.2f}, Profit: {profit_r:.2f}R")
            
            # Apply adaptive stop-loss rules
            new_stop = await self._apply_adaptive_stops(
                position, entry_price, current_price, profit_r, initial_risk
            )
            
            # Validate and return new stop level
            if new_stop and self._is_valid_stop_update(position, current_stop, new_stop):
                logger.info(f"🎯 ADAPTIVE STOP UPDATE: {deal_id} | New Stop: {new_stop:.2f} | Profit: {profit_r:.2f}R")
                return new_stop
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in dynamic_stop_management: {e}")
            return None
    
    async def _apply_adaptive_stops(self, position: Dict, entry_price: float, 
                                  current_price: float, profit_r: float, 
                                  initial_risk: float) -> Optional[float]:
        """Apply tiered adaptive stop-loss rules based on profit levels"""
        try:
            direction = position.get('direction', 'BUY')
            deal_id = position.get('deal_id')
            
            # Get adaptive stop configuration
            adaptive_config = self.risk_config.get('adaptive_stops', {})
            
            # Tier 1: +0.5R profit - Move to breakeven + 0.1R
            if profit_r >= adaptive_config.get('tier1_profit_r', 0.5):
                breakeven_buffer = adaptive_config.get('breakeven_buffer_r', 0.1)
                
                if direction == 'BUY':
                    new_stop = entry_price + (breakeven_buffer * initial_risk)
                    # Ensure stop is not too close to current price (0.5% buffer)
                    min_stop = current_price * 0.995
                    new_stop = max(new_stop, min_stop)
                else:  # SELL
                    new_stop = entry_price - (breakeven_buffer * initial_risk)
                    # Ensure stop is not too close to current price (0.5% buffer)
                    max_stop = current_price * 1.005
                    new_stop = min(new_stop, max_stop)
                
                logger.info(f"🔄 Tier 1 Stop: {deal_id} | Breakeven + {breakeven_buffer}R = {new_stop:.2f}")
                return new_stop
            
            # Tier 2: +1.0R profit - Move to +0.5R profit protection
            if profit_r >= adaptive_config.get('tier2_profit_r', 1.0):
                profit_protection_r = adaptive_config.get('tier2_protection_r', 0.5)
                
                if direction == 'BUY':
                    new_stop = entry_price + (profit_protection_r * initial_risk)
                    min_stop = current_price * 0.99  # 1% buffer
                    new_stop = max(new_stop, min_stop)
                else:  # SELL
                    new_stop = entry_price - (profit_protection_r * initial_risk)
                    max_stop = current_price * 1.01  # 1% buffer
                    new_stop = min(new_stop, max_stop)
                
                logger.info(f"🔄 Tier 2 Stop: {deal_id} | +{profit_protection_r}R protection = {new_stop:.2f}")
                return new_stop
            
            # Tier 3: +2.0R profit - Move to +1.0R profit protection
            if profit_r >= adaptive_config.get('tier3_profit_r', 2.0):
                profit_protection_r = adaptive_config.get('tier3_protection_r', 1.0)
                
                if direction == 'BUY':
                    new_stop = entry_price + (profit_protection_r * initial_risk)
                    min_stop = current_price * 0.985  # 1.5% buffer
                    new_stop = max(new_stop, min_stop)
                else:  # SELL
                    new_stop = entry_price - (profit_protection_r * initial_risk)
                    max_stop = current_price * 1.015  # 1.5% buffer
                    new_stop = min(new_stop, max_stop)
                
                logger.info(f"🔄 Tier 3 Stop: {deal_id} | +{profit_protection_r}R protection = {new_stop:.2f}")
                return new_stop
            
            # Tier 4: +3.0R profit - Trailing stop at 50% of current profit
            if profit_r >= adaptive_config.get('tier4_profit_r', 3.0):
                trailing_percentage = adaptive_config.get('trailing_percentage', 0.5)
                current_profit_points = abs(current_price - entry_price)
                trailing_distance = current_profit_points * trailing_percentage
                
                if direction == 'BUY':
                    new_stop = current_price - trailing_distance
                    # Ensure we don't move stop backwards
                    current_stop = position.get('stop_level', 0)
                    if current_stop and new_stop < current_stop:
                        new_stop = current_stop
                else:  # SELL
                    new_stop = current_price + trailing_distance
                    # Ensure we don't move stop backwards
                    current_stop = position.get('stop_level', float('inf'))
                    if current_stop and new_stop > current_stop:
                        new_stop = current_stop
                
                logger.info(f"🔄 Tier 4 Stop: {deal_id} | Trailing {trailing_percentage*100}% = {new_stop:.2f}")
                return new_stop
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error applying adaptive stops: {e}")
            return None
    
    def _calculate_initial_risk(self, position: Dict, entry_price: float) -> float:
        """Calculate initial risk (R) for the position"""
        try:
            # Try to get original stop level
            original_stop = position.get('original_stop_level')
            if original_stop:
                return abs(entry_price - original_stop)
            
            # Fallback: estimate based on typical risk percentage
            risk_percent = self.risk_config.get('risk_per_trade_percent', 3.0) / 100.0
            estimated_risk = entry_price * risk_percent
            
            return estimated_risk
            
        except Exception as e:
            logger.error(f"❌ Error calculating initial risk: {e}")
            return 0.0
    
    def _is_valid_stop_update(self, position: Dict, current_stop: Optional[float], 
                            new_stop: float) -> bool:
        """Validate that the stop update is beneficial and safe"""
        try:
            direction = position.get('direction', 'BUY')
            deal_id = position.get('deal_id')
            
            # Check if we have a current stop to compare
            if not current_stop:
                return True  # First stop update is always valid
            
            # For BUY positions, new stop should be higher (tighter)
            # For SELL positions, new stop should be lower (tighter)
            if direction == 'BUY':
                is_tighter = new_stop > current_stop
            else:  # SELL
                is_tighter = new_stop < current_stop
            
            if not is_tighter:
                logger.debug(f"⚠️ Stop update rejected - not tighter: {deal_id}")
                return False
            
            # Check cooldown period to prevent excessive updates
            last_update = self.stop_updates.get(deal_id)
            if last_update:
                cooldown_minutes = self.risk_config.get('stop_update_cooldown_minutes', 2)
                time_since_update = (datetime.now() - last_update).total_seconds() / 60
                
                if time_since_update < cooldown_minutes:
                    logger.debug(f"⚠️ Stop update rejected - cooldown: {deal_id}")
                    return False
            
            # Update is valid
            self.stop_updates[deal_id] = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating stop update: {e}")
            return False
    
    async def process_all_positions(self, positions: List[Dict], ig_api) -> List[Dict]:
        """Process adaptive stops for all positions"""
        try:
            if not positions or not ig_api:
                return []
            
            stop_updates = []
            
            for position in positions:
                try:
                    deal_id = position.get('deal_id')
                    epic = position.get('epic')
                    
                    if not deal_id or not epic:
                        continue
                    
                    # Get current market price
                    current_price = await self._get_current_price(epic, ig_api)
                    if not current_price:
                        continue
                    
                    # Calculate new stop level
                    new_stop = await self.dynamic_stop_management(position, current_price)
                    
                    if new_stop:
                        stop_updates.append({
                            'deal_id': deal_id,
                            'epic': epic,
                            'new_stop': new_stop,
                            'current_price': current_price,
                            'position': position
                        })
                
                except Exception as pos_error:
                    logger.warning(f"⚠️ Error processing position: {pos_error}")
                    continue
            
            return stop_updates
            
        except Exception as e:
            logger.error(f"❌ Error processing all positions: {e}")
            return []
    
    async def _get_current_price(self, epic: str, ig_api) -> Optional[float]:
        """Get current market price for an epic"""
        try:
            # This would integrate with your IG Markets API
            # For now, return None to indicate price unavailable
            # In real implementation, you'd call ig_api.get_market_price(epic)
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting current price for {epic}: {e}")
            return None
