"""
Autonomous Trader V2 - Main Trading Engine
Fully automated trading with PIE integration
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

from core.integrity import IntegrityBus, IntegrityPrediction
from core.quantum_engine import QuantumEngine
from integrations.ig_markets_api import IGMarketsAPI

logger = logging.getLogger(__name__)


class AutonomousTraderV2:
    """
    Fully autonomous trading system
    
    Features:
    - PIE integration for predictions
    - Automatic position management
    - Risk management
    - Multi-broker support
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.pie = IntegrityBus()
        self.quantum = QuantumEngine()
        self.ig_api: Optional[IGMarketsAPI] = None # Initialize IG Markets API
        
        # State
        self.running = False
        self.positions = {}
        self.performance = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'total_profit': 0.0
        }
        
    async def initialize(self):
        """Initialize trading system"""
        logger.info("🚀 Initializing Autonomous Trader V2...")
        
        # Initialize PIE
        await self.pie.initialize()
        
        # Initialize Quantum Engine
        await self.quantum.initialize()
        
        # Initialize IG Markets API
        ig_api_config = self.config['brokers']['ig_markets']
        self.ig_api = IGMarketsAPI(
            api_key=ig_api_config['api_key'],
            username=ig_api_config['username'],
            password=ig_api_config['password'],
            account_id=ig_api_config['account_id'],
            demo=ig_api_config.get('demo', False)
        )
        await self.ig_api.initialize()
        
        # Load configuration
        self.risk_per_trade = self.config.get('risk_per_trade', 0.02)  # 2%
        self.max_positions = self.config.get('max_positions', 5)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.70)
        
        logger.info("  ✓ Risk per trade: {:.1%}".format(self.risk_per_trade))
        logger.info("  ✓ Max positions: {}".format(self.max_positions))
        logger.info("  ✓ Confidence threshold: {:.2f}".format(self.confidence_threshold))
        logger.info("✅ Autonomous Trader ready")
    
    async def start(self):
        """Start autonomous trading"""
        if self.running:
            logger.warning("⚠️  Trader already running")
            return
        
        self.running = True
        logger.info("🟢 Starting autonomous trading")
        
        try:
            await self._trading_loop()
        except Exception as e:
            logger.error(f"❌ Trading error: {e}")
            raise
        finally:
            self.running = False
    
    async def stop(self):
        """Stop autonomous trading"""
        logger.info("🛑 Stopping autonomous trading")
        self.running = False
        
        # Close all positions
        await self._close_all_positions()
        
        logger.info("✅ Trader stopped")
    
    async def _trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                # Get market state
                market_state = await self._get_market_state()
                
                # Get PIE prediction
                prediction = await self.pie.predict(
                    market_state=market_state,
                    historical_accuracy=self._calculate_historical_accuracy()
                )
                
                # Make trading decision
                await self._process_prediction(prediction, market_state)
                
                # Update positions
                await self._update_positions()
                
                # Wait before next iteration
                await asyncio.sleep(self.config.get('update_interval', 60))
                
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                await asyncio.sleep(5)
    
    async def _get_market_state(self) -> Dict:
        """Fetch current market state"""
        if not self.ig_api:
            logger.error("❌ IG Markets API not initialized.")
            return {}
            
        epic = self.config['brokers']['ig_markets'].get('default_epic', 'CS.D.GBPUSD.TODAY.SPR')
        market_data = await self.ig_api.get_market_data(epic)
        if market_data and market_data.get('snapshot'):
            snapshot = market_data['snapshot']
            return {
                'timestamp': datetime.now(),
                'price': snapshot.get('bid', snapshot.get('offer', 0.0)), # Use bid or offer as price
                'volume': snapshot.get('totalVolume', 0),
                'indicators': {}, # TODO: Populate with actual indicators
                'epic': epic
            }
        else:
            logger.warning(f"⚠️  Could not fetch market data for {epic}. Using dummy data.")
            return {
                'timestamp': datetime.now(),
                'price': 100.0,
                'volume': 1000,
                'indicators': {},
                'epic': epic
            }
    
    async def _process_prediction(
        self,
        prediction: IntegrityPrediction,
        market_state: Dict
    ):
        """Process prediction and take action"""
        logger.info(f"\n{'='*60}")
        logger.info(prediction.reasoning)
        
        if not prediction.is_tradeable:
            logger.info("⏸️  HOLD - Confidence below threshold")
            return
        
        # Check if we can open new position
        if len(self.positions) >= self.max_positions:
            logger.info("⏸️  HOLD - Maximum positions reached")
            return
        
        # Calculate position size
        position_size = await self._calculate_position_size(
            prediction.position_size_multiplier
        )
        if position_size <= 0:
            logger.warning("⚠️  Calculated position size is zero or negative. Holding.")
            return
        
        # Determine direction
        direction = 'BUY' if prediction.prediction_value > 0.5 else 'SELL' # Changed to 'BUY'/'SELL' for IG API
        
        # Execute trade
        await self._execute_trade(
            direction=direction,
            size=position_size,
            prediction=prediction,
            market_state=market_state
        )
    
    async def _calculate_position_size(self, multiplier: float) -> float:
        """Calculate position size based on risk and current account balance"""
        if not self.ig_api:
            logger.error("❌ IG Markets API not initialized for balance check.")
            return 0.0
            
        account_info = await self.ig_api.get_account_info()
        current_balance = 0.0
        if account_info and account_info.get('accounts'):
            for acc in account_info['accounts']:
                if acc.get('accountId') == self.config['brokers']['ig_markets']['account_id']: # Corrected access path
                    current_balance = acc.get('balance', {}).get('balance', 0.0)
                    break
        
        if current_balance == 0.0:
            logger.warning("⚠️  Could not fetch current account balance. Using dummy balance for position sizing.")
            current_balance = 264.63 # Fallback to initial known balance
            
        base_size = self.risk_per_trade * current_balance
        return base_size * multiplier
    
    async def _execute_trade(
        self,
        direction: str,
        size: float,
        prediction: IntegrityPrediction,
        market_state: Dict
    ):
        """Execute a trade"""
        logger.info(f"🎯 EXECUTING: {direction} | Size: ${size:.2f}")
        
        if not self.ig_api:
            logger.error("❌ IG Markets API not initialized.")
            return
        epic = self.config['brokers']['ig_markets'].get('default_epic', 'CS.D.GBPUSD.TODAY.SPR')
        
        try:
            trade_response = await self.ig_api.open_position(
                epic=epic,
                direction=direction,
                size=size,
                # stop_loss=... # TODO: Implement stop loss calculation
                # take_profit=... # TODO: Implement take profit calculation
            )
            
            if trade_response and trade_response.get('dealReference'):
                position_id = trade_response['dealReference']
                self.positions[position_id] = {
                    'direction': direction,
                    'size': size,
                    'entry_price': market_state['price'], # This will need to be updated with actual entry price from API
                    'entry_time': datetime.now(),
                    'prediction': prediction,
                    'status': 'OPEN',
                    'deal_id': position_id # Store dealReference as deal_id
                }
                self.performance['trades'] += 1
            else:
                logger.error(f"❌ Failed to open position. Response: {trade_response}")
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
    
    async def _update_positions(self):
        """Update and manage open positions"""
        for pos_id, position in list(self.positions.items()):
            if position['status'] != 'OPEN':
                continue
            
            # TODO: Implement position monitoring and exit logic
            # - Check stop loss
            # - Check take profit
            # - Check time-based exits
            pass
    
    async def _close_position(self, position_id: str, reason: str = "Manual"):
        """Close a position"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        if not self.ig_api:
            logger.error("❌ IG Markets API not initialized.")
            return
            
        try:
            close_response = await self.ig_api.close_position(deal_id=position['deal_id'])
            if not close_response or not close_response.get('dealReference'):
                logger.error(f"❌ Failed to close position {position_id}. Response: {close_response}")
                return
        except Exception as e:
            logger.error(f"❌ Error closing position {position_id}: {e}")
            return
        
        # Calculate P&L
        # TODO: Implement actual P&L calculation
        pnl = 0.0
        
        # Update performance
        if pnl > 0:
            self.performance['wins'] += 1
        else:
            self.performance['losses'] += 1
        self.performance['total_profit'] += pnl
        
        position['status'] = 'CLOSED'
        position['close_time'] = datetime.now()
        position['pnl'] = pnl
        position['close_reason'] = reason
        
        logger.info(f"🔴 Position closed: {position_id} | P&L: ${pnl:.2f} | Reason: {reason}")
    
    async def _close_all_positions(self):
        """Close all open positions"""
        open_positions = [
            pos_id for pos_id, pos in self.positions.items()
            if pos['status'] == 'OPEN'
        ]
        
        for pos_id in open_positions:
            await self._close_position(pos_id, reason="System shutdown")
    
    def _calculate_historical_accuracy(self) -> float:
        """Calculate recent prediction accuracy"""
        if self.performance['trades'] == 0:
            return 0.80  # Default starting accuracy
        
        win_rate = self.performance['wins'] / self.performance['trades']
        return win_rate
    
    def get_performance(self) -> Dict:
        """Get trading performance statistics"""
        total_trades = self.performance['trades']
        
        if total_trades == 0:
            return {
                'total_trades': 0,
                'message': 'No trades yet'
            }
        
        win_rate = self.performance['wins'] / total_trades
        
        return {
            'total_trades': total_trades,
            'wins': self.performance['wins'],
            'losses': self.performance['losses'],
            'win_rate': win_rate,
            'total_profit': self.performance['total_profit'],
            'open_positions': len([p for p in self.positions.values() if p['status'] == 'OPEN']),
            'pie_stats': self.pie.get_system_stats()
        }
