"""
High-Frequency Micro-Scalp Engine
Executes rapid micro-trades on high-confidence signals with tight profit targets
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)

class ScalpEngine:
    """
    High-frequency micro-scalping engine for rapid profit extraction
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.scalp_config = config.get('trading', {}).get('micro_scalping', {})
        
        # Core scalping parameters
        self.scalp_size = self.scalp_config.get('scalp_size', 0.05)  # £0.05/pt micro-trades
        self.scalp_tp = self.scalp_config.get('take_profit_points', 3)  # 3 point take-profit
        self.scalp_sl = self.scalp_config.get('stop_loss_points', 2)   # 2 point stop-loss
        self.max_scalps_per_signal = self.scalp_config.get('max_scalps_per_signal', 3)
        self.scalp_interval = self.scalp_config.get('scalp_interval_seconds', 0.5)
        
        # Signal requirements
        self.min_confidence = self.scalp_config.get('min_confidence', 0.85)
        self.min_volatility = self.scalp_config.get('min_volatility', 1.2)
        self.max_margin_threshold = self.scalp_config.get('max_margin_threshold', 50.0)
        
        # Tracking
        self.active_scalps = {}
        self.scalp_history = []
        self.last_scalp_time = {}
        
        logger.info("🏃 Scalp Engine initialized")
    
    async def scalp_signal_handler(self, signal: Dict, ig_api, get_margin_percent_func) -> List[Dict]:
        """
        Execute rapid micro-scalps on high-confidence signals
        Core Principle: Extract quick profits from high-probability setups
        """
        try:
            if not self.scalp_config.get('enabled', True):
                return []
            
            # Validate signal requirements
            confidence = signal.get('confidence', 0.0)
            volatility = signal.get('volatility', 0.0)
            epic = signal.get('epic')
            direction = signal.get('direction', 'BUY')
            
            if not self._is_scalp_worthy_signal(confidence, volatility, epic):
                return []
            
            logger.info(f"🏃 MICRO-SCALP OPPORTUNITY: {epic} | Confidence: {confidence:.3f} | Volatility: {volatility:.2f}")
            
            # Execute rapid scalp sequence
            executed_scalps = []
            current_margin = await get_margin_percent_func()
            
            for scalp_num in range(1, self.max_scalps_per_signal + 1):
                # Check margin safety before each scalp
                if current_margin > self.max_margin_threshold:
                    logger.warning(f"⚠️ Margin too high ({current_margin:.1f}%) - stopping scalp sequence at {scalp_num-1}/{self.max_scalps_per_signal}")
                    break
                
                # Execute micro-scalp
                scalp_result = await self._execute_micro_scalp(
                    epic=epic,
                    direction=direction,
                    scalp_num=scalp_num,
                    signal=signal,
                    ig_api=ig_api
                )
                
                if scalp_result:
                    executed_scalps.append(scalp_result)
                    logger.info(f"✅ Scalp {scalp_num}/{self.max_scalps_per_signal} executed: {scalp_result['deal_reference']}")
                else:
                    logger.warning(f"❌ Scalp {scalp_num} failed")
                
                # Rapid succession delay
                if scalp_num < self.max_scalps_per_signal:
                    await asyncio.sleep(self.scalp_interval)
                
                # Update margin for next iteration
                current_margin = await get_margin_percent_func()
            
            # Log scalp sequence results
            if executed_scalps:
                logger.info(f"🎯 SCALP SEQUENCE COMPLETE:")
                logger.info(f"   Epic: {epic}")
                logger.info(f"   Direction: {direction}")
                logger.info(f"   Executed: {len(executed_scalps)}/{self.max_scalps_per_signal}")
                logger.info(f"   Total Size: £{len(executed_scalps) * self.scalp_size:.2f}/pt")
                logger.info(f"   Target Profit: {self.scalp_tp} points each")
            
            return executed_scalps
            
        except Exception as e:
            logger.error(f"❌ Error in scalp_signal_handler: {e}")
            return []
    
    def _is_scalp_worthy_signal(self, confidence: float, volatility: float, epic: str) -> bool:
        """Validate if signal meets scalping requirements"""
        try:
            # Check confidence threshold
            if confidence < self.min_confidence:
                logger.debug(f"📊 Signal confidence {confidence:.3f} below scalp threshold {self.min_confidence}")
                return False
            
            # Check volatility threshold
            if volatility < self.min_volatility:
                logger.debug(f"📊 Signal volatility {volatility:.2f} below scalp threshold {self.min_volatility}")
                return False
            
            # Check cooldown period (prevent over-scalping same epic)
            cooldown_minutes = self.scalp_config.get('epic_cooldown_minutes', 2)
            last_scalp = self.last_scalp_time.get(epic)
            
            if last_scalp:
                time_since_last = (datetime.now() - last_scalp).total_seconds() / 60
                if time_since_last < cooldown_minutes:
                    logger.debug(f"📊 Epic {epic} in cooldown ({time_since_last:.1f}m < {cooldown_minutes}m)")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating scalp signal: {e}")
            return False
    
    async def _execute_micro_scalp(self, epic: str, direction: str, scalp_num: int, 
                                 signal: Dict, ig_api) -> Optional[Dict]:
        """Execute a single micro-scalp trade"""
        try:
            # Prepare scalp trade parameters
            trade_params = {
                'epic': epic,
                'direction': direction,
                'size': self.scalp_size,
                'orderType': 'MARKET',
                'guaranteedStop': False,
                'forceOpen': True,
                'currencyCode': 'GBP',
                'timeInForce': 'FILL_OR_KILL',
                'expiry': 'DFB'
            }
            
            logger.info(f"🏃 Executing micro-scalp {scalp_num}: {epic} {direction} £{self.scalp_size}/pt")
            
            # Execute the trade
            open_resp = await ig_api.open_position(**trade_params)

            # open_position may return a dict containing 'dealReference' or a direct deal reference string
            if not open_resp:
                return None

            if isinstance(open_resp, dict):
                deal_reference = open_resp.get('dealReference') or open_resp.get('deal_reference')
            else:
                deal_reference = open_resp

            if not deal_reference:
                logger.warning(f"⚠️ No deal reference returned from open_position: {open_resp}")
                return None

            # Verify trade execution
            trade_status = await ig_api.verify_trade_status(deal_reference)
            
            if not trade_status or trade_status.get('dealStatus') != 'ACCEPTED':
                logger.warning(f"⚠️ Scalp trade not accepted: {trade_status}")
                return None
            
            # Create scalp record
            scalp_record = {
                'deal_reference': deal_reference,
                'deal_id': trade_status.get('dealId'),
                'epic': epic,
                'direction': direction,
                'size': self.scalp_size,
                'entry_level': trade_status.get('level', 0.0),
                'take_profit_target': self.scalp_tp,
                'stop_loss_target': self.scalp_sl,
                'scalp_number': scalp_num,
                'signal_confidence': signal.get('confidence', 0.0),
                'signal_volatility': signal.get('volatility', 0.0),
                'timestamp': datetime.now(),
                'status': 'ACTIVE'
            }
            
            # Track active scalp
            self.active_scalps[trade_status.get('dealId')] = scalp_record
            self.last_scalp_time[epic] = datetime.now()
            
            return scalp_record
            
        except Exception as e:
            logger.error(f"❌ Error executing micro-scalp: {e}")
            return None
    
    async def monitor_scalp_positions(self, positions: List[Dict], ig_api) -> List[Dict]:
        """Monitor active scalp positions for profit targets and stop losses"""
        try:
            if not positions or not self.active_scalps:
                return []
            
            scalp_updates = []
            completed_scalps = []
            
            for pos_data in positions:
                try:
                    position = pos_data.get('position', {})
                    market = pos_data.get('market', {})
                    
                    deal_id = position.get('dealId')
                    
                    if deal_id not in self.active_scalps:
                        continue
                    
                    scalp_record = self.active_scalps[deal_id]
                    
                    # Get current market data
                    epic = market.get('epic')
                    direction = position.get('direction')
                    entry_level = scalp_record['entry_level']
                    current_price = market.get('bid' if direction == 'BUY' else 'offer', 0.0)
                    
                    if not current_price:
                        continue
                    
                    # Calculate profit/loss in points
                    if direction == 'BUY':
                        points_profit = current_price - entry_level
                    else:  # SELL
                        points_profit = entry_level - current_price
                    
                    # Check for take profit or stop loss conditions
                    should_close = False
                    close_reason = ""
                    
                    if points_profit >= self.scalp_tp:
                        should_close = True
                        close_reason = f"TAKE_PROFIT (+{points_profit:.1f} points)"
                    elif points_profit <= -self.scalp_sl:
                        should_close = True
                        close_reason = f"STOP_LOSS ({points_profit:.1f} points)"
                    
                    if should_close:
                        logger.info(f"🎯 SCALP EXIT SIGNAL: {epic} | {close_reason}")

                        # Attempt programmatic closure via IG API; fall back to recommendation if it fails
                        action_taken = 'RECOMMEND_CLOSE'
                        try:
                            await ig_api.close_position(deal_id)
                            action_taken = 'CLOSED'
                        except Exception as _:
                            logger.debug(f"Could not auto-close deal {deal_id}, recommend manual close")

                        scalp_updates.append({
                            'deal_id': deal_id,
                            'epic': epic,
                            'direction': direction,
                            'entry_level': entry_level,
                            'current_price': current_price,
                            'points_profit': points_profit,
                            'action': 'CLOSE',
                            'action_taken': action_taken,
                            'reason': close_reason,
                            'scalp_record': scalp_record
                        })

                        # Mark scalp as completed
                        scalp_record['status'] = 'COMPLETED'
                        scalp_record['exit_reason'] = close_reason
                        scalp_record['points_profit'] = points_profit
                        completed_scalps.append(deal_id)
                
                except Exception as pos_error:
                    logger.warning(f"⚠️ Error monitoring scalp position: {pos_error}")
                    continue
            
            # Remove completed scalps from active tracking
            for deal_id in completed_scalps:
                if deal_id in self.active_scalps:
                    completed_scalp = self.active_scalps.pop(deal_id)
                    self.scalp_history.append(completed_scalp)
            
            # Log monitoring results
            if scalp_updates:
                logger.info(f"🏃 SCALP MONITORING RESULTS:")
                logger.info(f"   Active Scalps: {len(self.active_scalps)}")
                logger.info(f"   Exit Signals: {len(scalp_updates)}")
                logger.info(f"   Completed: {len(completed_scalps)}")
            
            return scalp_updates
            
        except Exception as e:
            logger.error(f"❌ Error monitoring scalp positions: {e}")
            return []
    
    def get_scalp_statistics(self) -> Dict:
        """Get scalping performance statistics"""
        try:
            total_scalps = len(self.scalp_history)
            if total_scalps == 0:
                return {'total_scalps': 0, 'win_rate': 0.0, 'avg_profit': 0.0}
            
            profitable_scalps = [s for s in self.scalp_history if s.get('points_profit', 0) > 0]
            win_rate = len(profitable_scalps) / total_scalps * 100
            
            total_points = sum(s.get('points_profit', 0) for s in self.scalp_history)
            avg_profit = total_points / total_scalps
            
            return {
                'total_scalps': total_scalps,
                'active_scalps': len(self.active_scalps),
                'win_rate': win_rate,
                'avg_profit_points': avg_profit,
                'total_profit_points': total_points
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating scalp statistics: {e}")
            return {'error': str(e)}
