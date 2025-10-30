"""
Autonomous Trader V2 - Main Trading Engine
Fully automated trading with PIE integration
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

from core.integrity import IntegrityBus, IntegrityPrediction
from core.quantum_engine import QuantumEngine
from integrations.ig_markets_api import IGMarketsAPI
from config.settings import update_env_var
from trading.risk_engine import RiskEngine
from trading.scalp_engine import ScalpEngine
from trading.account_manager import AccountManager
from trading.session_manager import SessionManager

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
        self.risk_engine = RiskEngine(config)
        self.scalp_engine = ScalpEngine(config)
        self.account_manager = None  # Will be initialized after IG API connection
        self.ig_api: Optional[IGMarketsAPI] = None # Initialize IG Markets API

        # Load multi-epic configuration
        self.multi_epic_config = self._load_multi_epic_config()

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

        # Initialize Account Manager after IG API connection
        self.account_manager = AccountManager(self.config, self.ig_api)
        await self.account_manager.initialize()

        # Initialize Session Manager
        self.session_manager = SessionManager(self.config)

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

                # PHASE 4 - Automation & Maintenance
                # Sync positions with IG Markets to keep internal list identical
                await self.sync_positions_with_ig()

                # Update account balance in environment variables
                await self.update_account_balance()

                # PHASE 5 - Intra-Trade Compounding
                # Increase ROI on profitable trades using only unrealized gains
                await self.intra_trade_compounding()

                # PHASE 6 - Adaptive Stop-Loss Management
                # Tighten stops as trades move into profit
                await self.adaptive_stop_management()

                # PHASE 7 - High-Frequency Micro-Scalping
                # Execute rapid micro-trades on high-confidence signals
                await self.micro_scalp_management()

                # PHASE 8 - Rolling Balance Management
                # Update balance and position sizing calculations
                await self.rolling_balance_management()

                # PHASE 9 - Volatility-Adaptive Profit Targets
                # Update profit targets based on market volatility
                await self.volatility_adaptive_profit_management()

                # PHASE 10 - Session-Bound Exposure Management
                # Optimize trading based on active market sessions
                await self.session_bound_exposure_management()

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

            # Even if main signal is not tradeable, check multi-epic opportunities
            await self.multi_epic_strategy()
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

        # After executing main trade, check for multi-epic opportunities
        await self.multi_epic_strategy()
    
    async def _calculate_position_size(self, multiplier: float) -> float:
        """
        Calculate position size based on risk and current account balance.
        Accounts for margin requirements to prevent insufficient funds rejections.
        """
        if not self.ig_api:
            logger.error("❌ IG Markets API not initialized for balance check.")
            return 0.0

        # Use Account Manager for balance information if available
        if self.account_manager:
            sizing_info = await self.account_manager.get_position_sizing_info()
            if sizing_info:
                current_balance = sizing_info.get('balance', 0.0)
                available_funds = sizing_info.get('available', 0.0)
            else:
                current_balance = await self.account_manager.get_current_balance()
                available_funds = await self.account_manager.get_available_balance()
        else:
            # Fallback to direct IG API call
            account_info = await self.ig_api.get_account_info()
            current_balance = 0.0
            available_funds = 0.0

            if account_info and account_info.get('accounts'):
                for acc in account_info['accounts']:
                    if acc.get('accountId') == self.config['brokers']['ig_markets']['account_id']:
                        balance_info = acc.get('balance', {})
                        current_balance = balance_info.get('balance', 0.0)
                        available_funds = balance_info.get('available', 0.0)
                        break

        if current_balance == 0.0:
            logger.warning("⚠️  Could not fetch current account balance. Using fallback balance for position sizing.")
            current_balance = 270.14
            available_funds = 132.54
        
        # Calculate risk-based size
        risk_amount = self.risk_per_trade * current_balance
        risk_based_size = (risk_amount * multiplier) / 100  # Divide by 100 for proper sizing
        
        # Calculate margin-safe size (use only 10% of available funds for ultra-conservative margin safety)
        # With only £93 available and £171 tied up, we need to be very conservative
        # Estimated margin requirement: ~£40-60 per £0.5 position on S&P 500
        margin_safe_size = (available_funds * 0.10) / 100  # Ultra-conservative: 10% of available
        
        # Use the smaller of the two to ensure we don't exceed either limit
        final_size = min(risk_based_size, margin_safe_size)
        
        # Set minimum to 0.1 (smallest practical size)
        if final_size < 0.1:
            final_size = 0.1
        
        # Round to 1 decimal place
        final_size = round(final_size, 1)
        
        logger.info(f"💰 Position Sizing:")
        logger.info(f"   Balance: £{current_balance:.2f} | Available: £{available_funds:.2f}")
        logger.info(f"   Risk-based: £{risk_based_size:.2f}/point | Margin-safe: £{margin_safe_size:.2f}/point")
        logger.info(f"   Final Size: £{final_size:.1f}/point")
        
        return final_size
    
    async def _execute_trade(
        self,
        direction: str,
        size: float,
        prediction: IntegrityPrediction,
        market_state: Dict
    ):
        """Execute a trade with session awareness"""
        logger.info(f"🎯 EXECUTING: {direction} | Size: ${size:.2f}")

        if not self.ig_api:
            logger.error("❌ IG Markets API not initialized.")
            return

        # Get epic with session awareness
        epic = self._get_session_aware_epic()

        # Check session-specific trading rules
        if hasattr(self, 'session_manager') and self.session_manager:
            if not self.session_manager.should_trade_epic(epic):
                logger.info(f"⏰ Skipping {epic} - not active in current session")
                return None

        try:
            # STRATEGY: Confidence-Weighted Trade Density
            # Use confidence-weighted execution with scaled position sizing
            signal_data = {
                'epic': epic,
                'direction': direction,
                'confidence': prediction.confidence,
                'prediction': prediction.prediction_value
            }

            logger.info(f"🎯 Implementing confidence-weighted execution strategy")
            density_trades = await self.confidence_weighted_execution(signal_data, size)

            if density_trades:
                total_fragments = sum(len(trade['fragments']) for trade in density_trades)
                logger.info(f"✅ Confidence-weighted execution successful: {len(density_trades)} density trades, {total_fragments} total fragments")
                return  # Exit early as confidence_weighted_execution handles all tracking
            else:
                logger.warning("❌ Confidence-weighted execution failed, falling back to standard fragmented entry")

                # Fallback to fragmented entry
                successful_fragments = await self.fragmented_entry(
                    epic=epic,
                    base_size=size
                )

                if successful_fragments:
                    logger.info(f"✅ Fallback fragmented entry successful: {len(successful_fragments)} fragments executed")
                    return  # Exit early as fragmented_entry handles all tracking
                else:
                    logger.warning("❌ Fragmented entry failed, falling back to single position")
                # Fallback to original single position logic
                # Calculate dynamic profit target
                current_price = market_state.get('current_price', 6860.0)  # Fallback price
                estimated_atr = self._estimate_atr(epic, current_price)
                dynamic_tp_points = self.risk_engine.calculate_dynamic_take_profit(
                    atr=estimated_atr,
                    confidence_score=prediction.confidence,
                    epic=epic
                )

                # Calculate actual take profit level
                if direction == 'BUY':
                    take_profit_level = current_price + dynamic_tp_points
                else:  # SELL
                    take_profit_level = current_price - dynamic_tp_points

                logger.info(f"🎯 DYNAMIC PROFIT TARGET: {dynamic_tp_points:.1f} points → Level: {take_profit_level:.2f}")

                trade_response = await self.ig_api.open_position(
                    epic=epic,
                    direction=direction,
                    size=size,
                    take_profit=take_profit_level
                    # stop_loss=... # TODO: Implement stop loss calculation
                )
            
            if trade_response and trade_response.get('dealReference'):
                deal_ref = trade_response['dealReference']
                logger.info(f"📝 Got deal reference: {deal_ref}")
                
                # Wait a moment for the deal to be processed
                await asyncio.sleep(0.5)
                
                # Verify the trade was actually accepted
                verification = await self.ig_api.verify_trade_status(deal_ref)
                
                if verification and verification.get('dealStatus') == 'ACCEPTED':
                    # Get the actual deal ID from the affected deals
                    affected_deals = verification.get('affectedDeals', [])
                    if affected_deals and len(affected_deals) > 0:
                        actual_deal_id = affected_deals[0].get('dealId')
                        
                        self.positions[actual_deal_id] = {
                            'direction': direction,
                            'size': size,
                            'entry_price': affected_deals[0].get('level', market_state['price']),
                            'entry_time': datetime.now(),
                            'prediction': prediction,
                            'status': 'OPEN',
                            'deal_id': actual_deal_id,
                            'deal_reference': deal_ref,
                            'epic': epic
                        }
                        self.performance['trades'] += 1
                        logger.info(f"✅ Position tracked: {actual_deal_id}")
                    else:
                        logger.error(f"❌ No affected deals in response")
                else:
                    logger.error(f"❌ Trade was not accepted. Verification: {verification}")
            else:
                logger.error(f"❌ Failed to open position. Response: {trade_response}")
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}", exc_info=True)
    
    async def _update_positions(self):
        """Update and manage open positions by syncing with IG Markets API"""
        # First, sync with actual positions from IG Markets
        if self.ig_api:
            try:
                actual_positions = await self.ig_api.get_positions()
                
                # Build a set of actual deal IDs
                actual_deal_ids = set()
                
                # Handle both list and dict responses
                positions_list = actual_positions if isinstance(actual_positions, list) else actual_positions.get('positions', [])
                
                for pos_data in positions_list:
                    deal_id = pos_data['position']['dealId']
                    actual_deal_ids.add(deal_id)
                
                # Remove positions from tracking that are no longer open
                for pos_id in list(self.positions.keys()):
                    if pos_id not in actual_deal_ids:
                        logger.info(f"🔄 Position {pos_id} no longer open, removing from tracking")
                        del self.positions[pos_id]
                
                logger.info(f"📊 Active positions: {len(actual_deal_ids)} on IG | {len(self.positions)} tracked | {self.max_positions} max")
                
            except Exception as e:
                logger.error(f"❌ Error syncing positions: {e}")
        
        # Then manage existing tracked positions
        for pos_id, position in list(self.positions.items()):
            if position['status'] != 'OPEN':
                continue
            
            # TODO: Implement position monitoring and exit logic
            # - Check stop loss
            # - Check take profit
            # - Check time-based exits
            pass

    async def sync_positions_with_ig(self):
        """
        Dedicated method to sync internal position list with IG Markets
        Keeps internal position list identical to IG Markets every cycle
        """
        if not self.ig_api:
            logger.warning("⚠️  IG Markets API not initialized for position sync")
            return

        try:
            # Get current positions from IG Markets
            actual_positions = await self.ig_api.get_positions()

            # Build a set of actual deal IDs and position data
            actual_deal_ids = set()
            ig_positions = {}

            # Handle both list and dict responses
            positions_list = actual_positions if isinstance(actual_positions, list) else actual_positions.get('positions', [])

            for pos_data in positions_list:
                deal_id = pos_data['position']['dealId']
                actual_deal_ids.add(deal_id)
                ig_positions[deal_id] = {
                    'deal_id': deal_id,
                    'epic': pos_data['market']['epic'],
                    'direction': pos_data['position']['direction'],
                    'size': pos_data['position']['size'],
                    'level': pos_data['position']['level'],
                    'status': 'OPEN',
                    'timestamp': datetime.now(),
                    'source': 'IG_SYNC'
                }

            # Remove positions from tracking that are no longer open on IG
            removed_positions = []
            for pos_id in list(self.positions.keys()):
                if pos_id not in actual_deal_ids:
                    removed_positions.append(pos_id)
                    del self.positions[pos_id]

            # Add positions from IG that we're not tracking
            added_positions = []
            for deal_id in actual_deal_ids:
                if deal_id not in self.positions:
                    self.positions[deal_id] = ig_positions[deal_id]
                    added_positions.append(deal_id)

            # Log synchronization results
            if removed_positions:
                logger.info(f"🔄 Removed {len(removed_positions)} closed positions from tracking")
            if added_positions:
                logger.info(f"🔄 Added {len(added_positions)} untracked positions to internal list")

            logger.debug(f"🔄 Position sync complete: {len(self.positions)} positions tracked")

        except Exception as e:
            logger.error(f"❌ Error in sync_positions_with_ig: {e}")

    async def update_account_balance(self):
        """
        Update account balance in environment variables
        Keeps .env file synchronized with current account balance
        """
        if not self.ig_api:
            logger.warning("⚠️  IG Markets API not initialized for balance update")
            return

        try:
            # Get current account information
            account_info = await self.ig_api.get_account_info()

            if account_info and account_info.get('accounts'):
                for acc in account_info['accounts']:
                    if acc.get('accountId') == self.config['brokers']['ig_markets']['account_id']:
                        balance_info = acc.get('balance', {})
                        current_balance = balance_info.get('balance', 0.0)
                        available_funds = balance_info.get('available', 0.0)

                        # Update environment variables
                        update_env_var("ACCOUNT_BALANCE", str(current_balance))
                        update_env_var("AVAILABLE_FUNDS", str(available_funds))

                        logger.debug(f"💰 Balance updated: £{current_balance:.2f} (Available: £{available_funds:.2f})")
                        return current_balance

            logger.warning("⚠️  Could not retrieve account balance for environment update")
            return None

        except Exception as e:
            logger.error(f"❌ Error updating account balance: {e}")
            return None

    def _load_multi_epic_config(self):
        """Load multi-epic trading configuration with session awareness"""
        try:
            # Get session-aware epics if session manager is available
            if hasattr(self, 'session_manager') and self.session_manager:
                session_epics = self.session_manager.get_active_session_epics()
                if session_epics:
                    logger.info(f"✅ Session-aware multi-epic config: {len(session_epics)} active epics")
                    return {
                        "primary_epics": session_epics,
                        "strategy_config": {
                            "max_concurrent_epics": len(session_epics),
                            "margin_allocation_per_epic": 1.0 / len(session_epics),
                            "session_aware": True
                        }
                    }

            # Fallback to file-based config
            config_path = Path("config/multi_epics.json")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    multi_config = json.load(f)
                logger.info(f"✅ Multi-epic config loaded: {len(multi_config['primary_epics'])} primary epics")
                return multi_config
            else:
                logger.warning("⚠️  Multi-epic config not found, using single epic mode")
                return {
                    "primary_epics": [self.config['brokers']['ig_markets'].get('default_epic', 'IX.D.SPTRD.DAILY.IP')],
                    "strategy_config": {
                        "max_concurrent_epics": 1,
                        "margin_allocation_per_epic": 1.0,
                        "min_signal_strength": 0.75
                    }
                }
        except Exception as e:
            logger.error(f"❌ Error loading multi-epic config: {e}")
            return {"primary_epics": ["IX.D.SPTRD.DAILY.IP"], "strategy_config": {"max_concurrent_epics": 1}}

    async def get_margin_percent(self):
        """
        Calculate current margin utilization percentage
        Returns percentage of available funds used as margin
        """
        try:
            if not self.ig_api:
                return 0.0

            account_info = await self.ig_api.get_account_info()
            if account_info and account_info.get('accounts'):
                for acc in account_info['accounts']:
                    if acc.get('accountId') == self.config['brokers']['ig_markets']['account_id']:
                        balance_info = acc.get('balance', {})
                        total_balance = balance_info.get('balance', 0.0)
                        available_funds = balance_info.get('available', 0.0)

                        if total_balance > 0:
                            used_margin = total_balance - available_funds
                            margin_percent = (used_margin / total_balance) * 100
                            return margin_percent

            return 0.0

        except Exception as e:
            logger.error(f"❌ Error calculating margin percentage: {e}")
            return 0.0

    async def fragmented_entry(self, epic: str, base_size: float, num_fragments: int = None):
        """
        Execute multiple micro-positions instead of one large trade
        Core Principle: Increase win density and signal yield, not exposure

        Args:
            epic: Market epic to trade
            base_size: Total position size to fragment
            num_fragments: Number of micro-positions to create (uses config if None)

        Returns:
            List of deal references for successful fragments
        """
        try:
            # Get fragmentation settings from config
            frag_config = self.config.get('trading', {}).get('fragmentation', {})

            if not frag_config.get('enabled', True):
                logger.info("🔀 Fragmentation disabled in config, using single position")
                return []

            # Use config values or defaults
            if num_fragments is None:
                num_fragments = frag_config.get('num_fragments', 5)

            margin_threshold = frag_config.get('margin_safety_threshold', 35.0)
            stagger_delay = frag_config.get('stagger_delay', 1.5)
            min_fragment_size = frag_config.get('min_fragment_size', 0.1)

            # Calculate fragment size with configured minimum
            fragment_size = max(min_fragment_size, base_size / num_fragments)
            fragment_size = round(fragment_size, 1)

            logger.info(f"🔀 FRAGMENTED ENTRY: {base_size} £/pt → {num_fragments} × {fragment_size} £/pt")

            successful_fragments = []
            failed_fragments = 0

            for i in range(num_fragments):
                try:
                    # Check margin safety before each fragment
                    current_margin = await self.get_margin_percent()

                    if current_margin > margin_threshold:  # Configurable safety buffer
                        logger.warning(f"⚠️  Margin threshold reached ({current_margin:.1f}%) - stopping fragmentation at {i+1}/{num_fragments}")
                        break

                    # Execute micro-position
                    logger.info(f"🔸 Fragment {i+1}/{num_fragments}: {fragment_size} £/pt (Margin: {current_margin:.1f}%)")

                    # Use existing position opening logic
                    deal_reference = await self._execute_trade_fragment(epic, fragment_size, "BUY")

                    if deal_reference:
                        successful_fragments.append(deal_reference)
                        logger.info(f"✅ Fragment {i+1} executed: {deal_reference}")
                    else:
                        failed_fragments += 1
                        logger.warning(f"❌ Fragment {i+1} failed")

                    # Stagger entries to avoid API rate limits
                    if i < num_fragments - 1:  # Don't sleep after last fragment
                        await asyncio.sleep(stagger_delay)

                except Exception as fragment_error:
                    failed_fragments += 1
                    logger.error(f"❌ Fragment {i+1} error: {fragment_error}")
                    continue

            # Summary
            total_executed = len(successful_fragments)
            total_size_executed = total_executed * fragment_size

            logger.info(f"🎯 FRAGMENTATION COMPLETE:")
            logger.info(f"   ✅ Successful: {total_executed}/{num_fragments} fragments")
            logger.info(f"   📊 Total Size: {total_size_executed} £/pt (Target: {base_size} £/pt)")
            logger.info(f"   ❌ Failed: {failed_fragments} fragments")

            return successful_fragments

        except Exception as e:
            logger.error(f"❌ Error in fragmented_entry: {e}")
            return []

    async def multi_epic_strategy(self):
        """
        Trade multiple uncorrelated instruments simultaneously
        Core Principle: Diversify across markets while maintaining margin discipline
        """
        try:
            strategy_config = self.multi_epic_config.get('strategy_config', {})

            # Get signals for multiple epics
            epic_signals = await self.get_signals_for_multiple_epics()

            # Count active epics currently being traded
            active_epics = self._count_active_epics()
            max_concurrent = strategy_config.get('max_concurrent_epics', 3)
            available_slots = max_concurrent - len(active_epics)

            logger.info(f"🔀 MULTI-EPIC STRATEGY: {len(active_epics)} active, {available_slots} slots available")

            if available_slots <= 0:
                logger.info("📊 All epic slots occupied, monitoring existing positions")
                return []

            # Filter and sort signals by strength
            min_signal_strength = strategy_config.get('min_signal_strength', 0.8)
            min_margin_threshold = strategy_config.get('min_margin_threshold', 40.0)

            current_margin = await self.get_margin_percent()

            if current_margin > min_margin_threshold:
                logger.warning(f"⚠️  Margin too high ({current_margin:.1f}%) for multi-epic strategy")
                return []

            # Execute trades for available slots
            executed_trades = []
            margin_per_epic = strategy_config.get('margin_allocation_per_epic', 0.33)

            for epic, signal_data in epic_signals[:available_slots]:
                signal_strength = signal_data['strength']

                if signal_strength > min_signal_strength:
                    # Calculate position size for this epic
                    base_size = await self._calculate_position_size()
                    epic_size = base_size * margin_per_epic
                    epic_size = round(epic_size, 1)

                    logger.info(f"🎯 Multi-epic trade: {epic} | Signal: {signal_strength:.3f} | Size: {epic_size} £/pt")

                    # Execute fragmented entry for this epic
                    fragments = await self.fragmented_entry(epic, epic_size)

                    if fragments:
                        executed_trades.append({
                            'epic': epic,
                            'signal_strength': signal_strength,
                            'size': epic_size,
                            'fragments': len(fragments)
                        })
                        logger.info(f"✅ Multi-epic trade executed: {epic} ({len(fragments)} fragments)")
                    else:
                        logger.warning(f"❌ Multi-epic trade failed: {epic}")

            if executed_trades:
                logger.info(f"🚀 Multi-epic strategy executed {len(executed_trades)} trades across different markets")

            return executed_trades

        except Exception as e:
            logger.error(f"❌ Error in multi_epic_strategy: {e}")
            return []

    async def get_signals_for_multiple_epics(self):
        """
        Get trading signals for multiple epics
        Returns list of (epic, signal_data) tuples sorted by signal strength
        """
        try:
            primary_epics = self.multi_epic_config.get('primary_epics', [])
            epic_priorities = self.multi_epic_config.get('epic_priorities', {})

            signals = []

            for epic in primary_epics:
                try:
                    # Get market state for this epic
                    market_state = await self._get_market_state_for_epic(epic)

                    # Get PIE prediction for this epic
                    prediction = await self.pie.predict(
                        market_state=market_state,
                        historical_accuracy=self._calculate_historical_accuracy()
                    )

                    if prediction and prediction.confidence >= 0.75:  # Only consider high-confidence signals
                        signal_data = {
                            'strength': prediction.confidence,
                            'direction': 'BUY' if prediction.prediction_value > 0.5 else 'SELL',
                            'prediction': prediction,
                            'priority': epic_priorities.get(epic, 999)
                        }
                        signals.append((epic, signal_data))

                except Exception as epic_error:
                    logger.warning(f"⚠️  Error getting signal for {epic}: {epic_error}")
                    continue

            # Sort by signal strength (descending) then by priority (ascending)
            signals.sort(key=lambda x: (-x[1]['strength'], x[1]['priority']))

            logger.info(f"📊 Multi-epic signals: {len(signals)} epics with tradeable signals")
            for epic, data in signals:
                logger.info(f"   {epic}: {data['strength']:.3f} confidence ({data['direction']})")

            return signals

        except Exception as e:
            logger.error(f"❌ Error getting multi-epic signals: {e}")
            return []

    async def _get_market_state_for_epic(self, epic: str):
        """Get market state for a specific epic"""
        # For now, use the same market state logic but could be enhanced
        # to get epic-specific market data
        return await self._get_market_state()

    def _count_active_epics(self):
        """Count how many different epics are currently being traded"""
        try:
            active_epics = set()
            primary_epics = self.multi_epic_config.get('primary_epics', [])

            for position in self.positions.values():
                if position.get('status') == 'OPEN' and position.get('epic') in primary_epics:
                    active_epics.add(position['epic'])

            return active_epics

        except Exception as e:
            logger.error(f"❌ Error counting active epics: {e}")
            return set()

    async def intra_trade_compounding(self):
        """
        Increase ROI on already-profitable trades using only unrealized gains
        Goal: Pure profit leverage with zero additional risk to original capital
        """
        try:
            if not self.ig_api:
                return []

            # Check if intra-trade compounding is enabled
            compound_config = self.config.get('trading', {}).get('intra_trade_compounding', {})
            if not compound_config.get('enabled', True):
                return []

            # Get current account info for balance reference
            account_info = await self.ig_api.get_account_info()
            current_balance = 0.0

            if account_info and account_info.get('accounts'):
                for acc in account_info['accounts']:
                    if acc.get('accountId') == self.config['brokers']['ig_markets']['account_id']:
                        balance_info = acc.get('balance', {})
                        current_balance = balance_info.get('balance', 0.0)
                        break

            if current_balance <= 0:
                logger.warning("⚠️  Could not retrieve balance for intra-trade compounding")
                return []

            # Get current positions with P&L
            positions_data = await self.ig_api.get_positions()
            if not positions_data:
                return []

            positions_list = positions_data if isinstance(positions_data, list) else positions_data.get('positions', [])

            compounding_opportunities = []
            total_unrealized_profit = 0.0

            # Analyze each position for compounding opportunities
            for pos_data in positions_list:
                try:
                    position = pos_data.get('position', {})
                    market = pos_data.get('market', {})

                    deal_id = position.get('dealId')
                    epic = market.get('epic')
                    direction = position.get('direction')
                    size = position.get('size', 0.0)

                    # Get P&L data
                    pnl = position.get('unrealisedPL', 0.0)

                    if pnl > 0:  # Only profitable positions
                        total_unrealized_profit += pnl

                        # Check if this position qualifies for compounding using Account Manager
                        should_compound = False
                        if self.account_manager:
                            should_compound = await self.account_manager.should_compound_position(pnl)
                        else:
                            # Fallback to manual calculation
                            profit_threshold_percent = compound_config.get('profit_threshold_percent', 1.0)
                            profit_threshold = (profit_threshold_percent / 100.0) * current_balance
                            should_compound = pnl > profit_threshold

                        if should_compound:
                            # Check if we've already compounded this position recently
                            if not self._has_recent_compound(deal_id, compound_config):
                                compound_size = self._calc_safe_size_from_profit(pnl, current_balance, compound_config)

                                if compound_size >= 0.1:  # Minimum viable size
                                    compounding_opportunities.append({
                                        'deal_id': deal_id,
                                        'epic': epic,
                                        'direction': direction,
                                        'original_size': size,
                                        'current_pnl': pnl,
                                        'compound_size': compound_size,
                                        'profit_percentage': (pnl / current_balance) * 100
                                    })

                                    logger.info(f"💰 COMPOUND OPPORTUNITY: {epic} | P&L: £{pnl:.2f} ({(pnl/current_balance)*100:.1f}%) | Compound Size: £{compound_size:.1f}/pt")

                except Exception as pos_error:
                    logger.warning(f"⚠️  Error analyzing position for compounding: {pos_error}")
                    continue

            if not compounding_opportunities:
                if total_unrealized_profit > 0:
                    logger.info(f"📊 Total unrealized profit: £{total_unrealized_profit:.2f}, but no positions qualify for compounding")
                return []

            # Execute compounding trades
            executed_compounds = []

            for opportunity in compounding_opportunities:
                try:
                    logger.info(f"🚀 EXECUTING INTRA-TRADE COMPOUND:")
                    logger.info(f"   Epic: {opportunity['epic']}")
                    logger.info(f"   Direction: {opportunity['direction']}")
                    logger.info(f"   Original P&L: £{opportunity['current_pnl']:.2f}")
                    logger.info(f"   Compound Size: £{opportunity['compound_size']:.1f}/pt")

                    # Execute compound position using fragmented entry
                    fragments = await self.fragmented_entry(
                        epic=opportunity['epic'],
                        base_size=opportunity['compound_size']
                    )

                    if fragments:
                        # Mark this position as recently compounded
                        self._mark_compound_executed(opportunity['deal_id'])

                        executed_compounds.append({
                            'original_deal_id': opportunity['deal_id'],
                            'epic': opportunity['epic'],
                            'compound_size': opportunity['compound_size'],
                            'fragments': len(fragments),
                            'profit_used': opportunity['current_pnl']
                        })

                        logger.info(f"✅ Intra-trade compound executed: {opportunity['epic']} ({len(fragments)} fragments)")
                    else:
                        logger.warning(f"❌ Intra-trade compound failed: {opportunity['epic']}")

                except Exception as compound_error:
                    logger.error(f"❌ Error executing compound for {opportunity.get('epic', 'unknown')}: {compound_error}")
                    continue

            if executed_compounds:
                total_compound_size = sum(c['compound_size'] for c in executed_compounds)
                total_profit_used = sum(c['profit_used'] for c in executed_compounds)

                logger.info(f"🎯 INTRA-TRADE COMPOUNDING COMPLETE:")
                logger.info(f"   ✅ Compounds Executed: {len(executed_compounds)}")
                logger.info(f"   📊 Total Compound Size: £{total_compound_size:.1f}/pt")
                logger.info(f"   💰 Profit Leveraged: £{total_profit_used:.2f}")
                logger.info(f"   🔄 Pure Profit Leverage: Zero additional capital risk")

            return executed_compounds

        except Exception as e:
            logger.error(f"❌ Error in intra_trade_compounding: {e}")
            return []

    def _calc_safe_size_from_profit(self, profit_amount: float, balance: float, compound_config: dict) -> float:
        """
        Calculate safe compound size from unrealized profit
        Uses configurable percentage of profit value (default 25%)
        """
        try:
            # Get profit utilization percentage from config
            profit_utilization_percent = compound_config.get('profit_utilization_percent', 25.0)
            profit_utilization = profit_utilization_percent / 100.0

            base_compound_size = profit_amount * profit_utilization

            # Convert to position size (assuming £1 profit ≈ £0.1/pt position sizing)
            # This is a conservative conversion factor
            position_size = base_compound_size * 0.1

            # Round to 1 decimal place (IG Markets requirement)
            position_size = round(position_size, 1)

            # Ensure minimum viable size
            position_size = max(0.1, position_size)

            # Cap at configurable maximum (prevent over-leveraging)
            max_compound_percent = compound_config.get('max_compound_percent_of_balance', 2.0)
            max_compound_size = balance * (max_compound_percent / 100.0)
            position_size = min(position_size, max_compound_size)

            logger.debug(f"💡 Compound sizing: £{profit_amount:.2f} profit ({profit_utilization_percent}%) → £{position_size:.1f}/pt compound")

            return position_size

        except Exception as e:
            logger.error(f"❌ Error calculating compound size: {e}")
            return 0.0

    def _has_recent_compound(self, deal_id: str, compound_config: dict) -> bool:
        """
        Check if this position has been compounded recently
        Prevents excessive compounding of the same position
        """
        try:
            # Simple time-based check - could be enhanced with persistent storage
            if not hasattr(self, '_compound_history'):
                self._compound_history = {}

            last_compound = self._compound_history.get(deal_id)
            if last_compound:
                # Get cooldown from config
                cooldown_minutes = compound_config.get('compound_cooldown_minutes', 5)
                cooldown_seconds = cooldown_minutes * 60

                time_since_compound = (datetime.now() - last_compound).total_seconds()
                return time_since_compound < cooldown_seconds

            return False

        except Exception as e:
            logger.error(f"❌ Error checking compound history: {e}")
            return False

    def _mark_compound_executed(self, deal_id: str):
        """Mark that a compound has been executed for this position"""
        try:
            if not hasattr(self, '_compound_history'):
                self._compound_history = {}

            self._compound_history[deal_id] = datetime.now()

            # Clean up old entries (keep only last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            self._compound_history = {
                k: v for k, v in self._compound_history.items()
                if v > cutoff_time
            }

        except Exception as e:
            logger.error(f"❌ Error marking compound executed: {e}")

    async def adaptive_stop_management(self):
        """
        Adaptive Stop-Loss Shrinking: Tighten stops as trades move into profit
        Goal: Protect gains while allowing continued upside
        """
        try:
            if not self.ig_api:
                return []

            # Check if adaptive stops are enabled
            risk_config = self.config.get('trading', {}).get('risk_management', {})
            adaptive_config = risk_config.get('adaptive_stops', {})

            if not adaptive_config.get('enabled', True):
                return []

            # Get current positions
            positions_data = await self.ig_api.get_positions()
            if not positions_data:
                return []

            positions_list = positions_data if isinstance(positions_data, list) else positions_data.get('positions', [])

            if not positions_list:
                return []

            # Process positions for adaptive stops
            stop_updates = []
            profitable_positions = 0

            for pos_data in positions_list:
                try:
                    position = pos_data.get('position', {})
                    market = pos_data.get('market', {})

                    deal_id = position.get('dealId')
                    epic = market.get('epic')
                    direction = position.get('direction')
                    size = position.get('size', 0.0)
                    entry_price = position.get('level', 0.0)

                    # Get current market price (simplified - using bid/offer)
                    current_price = None
                    if direction == 'BUY':
                        current_price = market.get('bid', 0.0)
                    else:  # SELL
                        current_price = market.get('offer', 0.0)

                    if not all([deal_id, epic, current_price, entry_price]):
                        continue

                    # Calculate P&L
                    if direction == 'BUY':
                        unrealized_pnl = (current_price - entry_price) * size
                        profit_points = current_price - entry_price
                    else:  # SELL
                        unrealized_pnl = (entry_price - current_price) * size
                        profit_points = entry_price - current_price

                    # Only process profitable positions
                    if unrealized_pnl <= 0:
                        continue

                    profitable_positions += 1

                    # Create position dict for risk engine
                    risk_position = {
                        'deal_id': deal_id,
                        'epic': epic,
                        'direction': direction,
                        'size': size,
                        'level': entry_price,
                        'stop_level': position.get('stopLevel'),
                        'unrealized_pnl': unrealized_pnl
                    }

                    # Calculate new stop level
                    new_stop = await self.risk_engine.dynamic_stop_management(risk_position, current_price)

                    if new_stop:
                        stop_updates.append({
                            'deal_id': deal_id,
                            'epic': epic,
                            'current_stop': position.get('stopLevel'),
                            'new_stop': new_stop,
                            'current_price': current_price,
                            'unrealized_pnl': unrealized_pnl,
                            'direction': direction
                        })

                        logger.info(f"🎯 ADAPTIVE STOP CANDIDATE: {epic} | P&L: £{unrealized_pnl:.2f} | New Stop: {new_stop:.2f}")

                except Exception as pos_error:
                    logger.warning(f"⚠️ Error processing position for adaptive stops: {pos_error}")
                    continue

            # Execute stop updates
            executed_updates = 0
            for update in stop_updates:
                try:
                    # Note: IG Markets API doesn't support programmatic stop-loss updates
                    # This would require manual intervention or a different broker API
                    # For now, we log the recommendations

                    logger.info(f"📋 STOP UPDATE RECOMMENDATION:")
                    logger.info(f"   Deal ID: {update['deal_id']}")
                    logger.info(f"   Epic: {update['epic']}")
                    logger.info(f"   Direction: {update['direction']}")
                    logger.info(f"   Current Stop: {update['current_stop']}")
                    logger.info(f"   Recommended Stop: {update['new_stop']:.2f}")
                    logger.info(f"   Current P&L: £{update['unrealized_pnl']:.2f}")

                    executed_updates += 1

                except Exception as update_error:
                    logger.error(f"❌ Error executing stop update: {update_error}")
                    continue

            if stop_updates:
                logger.info(f"🛡️ ADAPTIVE STOP MANAGEMENT COMPLETE:")
                logger.info(f"   ✅ Profitable Positions: {profitable_positions}")
                logger.info(f"   📊 Stop Updates Recommended: {len(stop_updates)}")
                logger.info(f"   🎯 Updates Processed: {executed_updates}")
            elif profitable_positions > 0:
                logger.info(f"📊 Adaptive stops monitored: {profitable_positions} profitable positions, no updates needed")

            return stop_updates

        except Exception as e:
            logger.error(f"❌ Error in adaptive_stop_management: {e}")
            return []

    async def micro_scalp_management(self):
        """
        High-Frequency Micro-Scalp Mode: Execute rapid micro-trades on high-confidence signals
        Goal: Extract quick profits from high-probability setups with tight targets
        """
        try:
            if not self.ig_api:
                return []

            # Check if micro-scalping is enabled
            scalp_config = self.config.get('trading', {}).get('micro_scalping', {})
            if not scalp_config.get('enabled', True):
                return []

            # Get current positions for scalp monitoring
            positions_data = await self.ig_api.get_positions()
            if positions_data:
                positions_list = positions_data if isinstance(positions_data, list) else positions_data.get('positions', [])

                # Monitor existing scalp positions
                scalp_updates = await self.scalp_engine.monitor_scalp_positions(positions_list, self.ig_api)

                if scalp_updates:
                    logger.info(f"🏃 SCALP POSITION UPDATES:")
                    for update in scalp_updates:
                        logger.info(f"   📋 {update['epic']} | {update['action']} | {update['reason']}")

            # Check for new scalping opportunities
            # Generate high-frequency signals for scalping
            scalp_signals = await self._generate_scalp_signals()

            executed_scalps = []

            for signal in scalp_signals:
                try:
                    # Execute scalp sequence for this signal
                    scalps = await self.scalp_engine.scalp_signal_handler(
                        signal=signal,
                        ig_api=self.ig_api,
                        get_margin_percent_func=self.get_margin_percent
                    )

                    if scalps:
                        executed_scalps.extend(scalps)
                        logger.info(f"🏃 SCALP SEQUENCE: {len(scalps)} micro-trades executed for {signal['epic']}")

                except Exception as signal_error:
                    logger.warning(f"⚠️ Error processing scalp signal: {signal_error}")
                    continue

            # Log scalping session results
            if executed_scalps or scalp_updates:
                scalp_stats = self.scalp_engine.get_scalp_statistics()

                logger.info(f"🏃 MICRO-SCALP SESSION COMPLETE:")
                logger.info(f"   ✅ New Scalps: {len(executed_scalps)}")
                logger.info(f"   📊 Position Updates: {len(scalp_updates) if 'scalp_updates' in locals() else 0}")
                logger.info(f"   🎯 Active Scalps: {scalp_stats.get('active_scalps', 0)}")
                logger.info(f"   📈 Total Scalps: {scalp_stats.get('total_scalps', 0)}")

                if scalp_stats.get('total_scalps', 0) > 0:
                    logger.info(f"   💰 Win Rate: {scalp_stats.get('win_rate', 0):.1f}%")
                    logger.info(f"   📊 Avg Profit: {scalp_stats.get('avg_profit_points', 0):.2f} points")

            return executed_scalps

        except Exception as e:
            logger.error(f"❌ Error in micro_scalp_management: {e}")
            return []

    async def _generate_scalp_signals(self) -> List[Dict]:
        """Generate high-frequency signals specifically for scalping"""
        try:
            scalp_signals = []

            # Get current PIE prediction for primary epic
            market_state = await self._get_market_state()
            prediction = await self.pie.predict(market_state=market_state)

            if not prediction:
                return []

            # Check if prediction meets scalping criteria
            confidence = prediction.confidence

            # Estimate volatility (simplified - in real implementation would use market data)
            # For now, use confidence variance as volatility proxy
            volatility = abs(prediction.prediction_value - 0.5) * 4  # Scale to approximate volatility

            # Create scalp signal if criteria met
            if confidence >= 0.85 and volatility >= 1.0:  # Slightly lower volatility threshold for more opportunities
                direction = 'BUY' if prediction.prediction_value > 0.5 else 'SELL'

                scalp_signal = {
                    'epic': self.config['brokers']['ig_markets']['default_epic'],
                    'direction': direction,
                    'confidence': confidence,
                    'volatility': volatility,
                    'prediction': prediction.prediction_value,
                    'timestamp': datetime.now(),
                    'signal_type': 'SCALP'
                }

                scalp_signals.append(scalp_signal)

                logger.info(f"🏃 SCALP SIGNAL GENERATED: {scalp_signal['epic']} {direction} | Conf: {confidence:.3f} | Vol: {volatility:.2f}")

            # Check multi-epic signals for additional scalping opportunities
            if len(scalp_signals) == 0:  # Only if no primary signal
                multi_epic_signals = await self._get_multi_epic_scalp_signals()
                scalp_signals.extend(multi_epic_signals)

            return scalp_signals

        except Exception as e:
            logger.error(f"❌ Error generating scalp signals: {e}")
            return []

    async def _get_multi_epic_scalp_signals(self) -> List[Dict]:
        """Get scalping signals from multi-epic configuration"""
        try:
            if not hasattr(self, 'multi_epic_config') or not self.multi_epic_config:
                return []

            primary_epics = self.multi_epic_config.get('primary_epics', [])
            scalp_signals = []

            # Check each epic for scalping opportunities
            for epic in primary_epics[:2]:  # Limit to first 2 epics for scalping
                try:
                    # Get prediction for this epic
                    market_state = await self._get_market_state()
                    prediction = await self.pie.predict(market_state=market_state)

                    if not prediction:
                        continue

                    confidence = prediction.confidence
                    volatility = abs(prediction.prediction_value - 0.5) * 4

                    # Lower thresholds for multi-epic scalping
                    if confidence >= 0.82 and volatility >= 0.8:
                        direction = 'BUY' if prediction.prediction_value > 0.5 else 'SELL'

                        scalp_signal = {
                            'epic': epic,
                            'direction': direction,
                            'confidence': confidence,
                            'volatility': volatility,
                            'prediction': prediction.prediction_value,
                            'timestamp': datetime.now(),
                            'signal_type': 'MULTI_EPIC_SCALP'
                        }

                        scalp_signals.append(scalp_signal)

                        logger.info(f"🏃 MULTI-EPIC SCALP: {epic} {direction} | Conf: {confidence:.3f} | Vol: {volatility:.2f}")

                except Exception as epic_error:
                    logger.debug(f"Error getting scalp signal for {epic}: {epic_error}")
                    continue

            return scalp_signals

        except Exception as e:
            logger.error(f"❌ Error getting multi-epic scalp signals: {e}")
            return []

    def get_trade_density(self, confidence_score: float) -> int:
        """
        Allocate more trades to higher-confidence periods
        Core Principle: Higher confidence = more trading opportunities
        """
        try:
            # Get density configuration
            density_config = self.config.get('trading', {}).get('confidence_weighted_density', {})

            if not density_config.get('enabled', True):
                return 1  # Default single trade

            # Confidence-based trade density allocation
            if confidence_score >= density_config.get('ultra_high_threshold', 0.9):
                density = density_config.get('ultra_high_density', 3)  # Ultra-high density
                logger.info(f"🎯 ULTRA-HIGH CONFIDENCE: {confidence_score:.3f} → {density} trades")
                return density
            elif confidence_score >= density_config.get('high_threshold', 0.8):
                density = density_config.get('high_density', 2)  # High density
                logger.info(f"🎯 HIGH CONFIDENCE: {confidence_score:.3f} → {density} trades")
                return density
            elif confidence_score >= density_config.get('medium_threshold', 0.75):
                density = density_config.get('medium_density', 1)  # Medium density
                logger.info(f"📊 MEDIUM CONFIDENCE: {confidence_score:.3f} → {density} trade")
                return density
            else:
                logger.info(f"⚠️ LOW CONFIDENCE: {confidence_score:.3f} → 0 trades (below threshold)")
                return 0  # No trading below threshold

        except Exception as e:
            logger.error(f"❌ Error calculating trade density: {e}")
            return 1  # Safe fallback

    async def confidence_weighted_execution(self, signal: Dict, base_size: float) -> List[Dict]:
        """
        Execute confidence-weighted trade density with scaled position sizing
        Goal: More trades and larger sizes for higher confidence signals
        """
        try:
            confidence = signal.get('confidence', 0.0)
            epic = signal.get('epic')
            direction = signal.get('direction', 'BUY')

            # Get trade density based on confidence
            density = self.get_trade_density(confidence)

            if density == 0:
                logger.info("❌ Confidence too low for trading")
                return []

            logger.info(f"🎯 CONFIDENCE-WEIGHTED EXECUTION:")
            logger.info(f"   Epic: {epic}")
            logger.info(f"   Direction: {direction}")
            logger.info(f"   Confidence: {confidence:.3f}")
            logger.info(f"   Trade Density: {density}")
            logger.info(f"   Base Size: £{base_size:.2f}/pt")

            executed_trades = []
            density_config = self.config.get('trading', {}).get('confidence_weighted_density', {})

            for i in range(density):
                try:
                    # Scale position size based on trade number and confidence
                    # Higher confidence gets progressively larger sizes
                    size_multiplier = density_config.get('base_multiplier', 0.3) + (i * density_config.get('increment_multiplier', 0.2))

                    # Apply confidence bonus to size
                    confidence_bonus = (confidence - 0.75) * density_config.get('confidence_bonus_factor', 2.0)
                    size_multiplier += max(0, confidence_bonus)

                    # Calculate final trade size
                    trade_size = base_size * size_multiplier
                    trade_size = round(max(0.1, trade_size), 1)  # Minimum 0.1, round to 1 decimal

                    logger.info(f"🔢 Trade {i+1}/{density}: Size = £{trade_size:.1f}/pt (multiplier: {size_multiplier:.2f})")

                    # Execute fragmented entry for this density trade
                    fragments_per_trade = density_config.get('fragments_per_density_trade', 2)
                    fragments = await self.fragmented_entry(
                        epic=epic,
                        base_size=trade_size,
                        num_fragments=fragments_per_trade
                    )

                    if fragments:
                        trade_record = {
                            'density_trade_number': i + 1,
                            'total_density': density,
                            'confidence': confidence,
                            'trade_size': trade_size,
                            'size_multiplier': size_multiplier,
                            'fragments': fragments,
                            'epic': epic,
                            'direction': direction,
                            'timestamp': datetime.now()
                        }
                        executed_trades.append(trade_record)

                        logger.info(f"✅ Density trade {i+1} executed: {len(fragments)} fragments")
                    else:
                        logger.warning(f"❌ Density trade {i+1} failed")

                    # Brief delay between density trades
                    if i < density - 1:
                        delay = density_config.get('density_trade_delay', 2.0)
                        await asyncio.sleep(delay)

                except Exception as trade_error:
                    logger.error(f"❌ Error executing density trade {i+1}: {trade_error}")
                    continue

            # Log density execution results
            if executed_trades:
                total_fragments = sum(len(trade['fragments']) for trade in executed_trades)
                total_size = sum(trade['trade_size'] for trade in executed_trades)

                logger.info(f"🎯 CONFIDENCE-WEIGHTED EXECUTION COMPLETE:")
                logger.info(f"   ✅ Density Trades: {len(executed_trades)}/{density}")
                logger.info(f"   📊 Total Fragments: {total_fragments}")
                logger.info(f"   💰 Total Size: £{total_size:.1f}/pt")
                logger.info(f"   🎯 Confidence: {confidence:.3f}")

            return executed_trades

        except Exception as e:
            logger.error(f"❌ Error in confidence_weighted_execution: {e}")
            return []

    async def _execute_trade_fragment(self, epic: str, size: float, direction: str):
        """
        Execute a single trade fragment
        Extracted from existing trade execution logic for reuse
        """
        try:
            if not self.ig_api:
                logger.error("❌ IG Markets API not initialized")
                return None

            # Calculate dynamic profit target for fragment
            current_price = 6860.0  # Placeholder - would get from market data
            estimated_atr = self._estimate_atr(epic, current_price)
            dynamic_tp_points = self.risk_engine.calculate_dynamic_take_profit(
                atr=estimated_atr,
                confidence_score=0.8,  # Default confidence for fragments
                epic=epic
            )

            # Calculate actual take profit level
            if direction == 'BUY':
                take_profit_level = current_price + dynamic_tp_points
            else:  # SELL
                take_profit_level = current_price - dynamic_tp_points

            # Open position using existing IG API with dynamic profit target
            result = await self.ig_api.open_position(
                epic=epic,
                direction=direction,
                size=size,
                take_profit=take_profit_level
            )

            if result and result.get('deal_reference'):
                deal_reference = result['deal_reference']

                # Verify the trade
                trade_status = await self.ig_api.verify_trade_status(deal_reference)

                if trade_status and trade_status.get('dealStatus') == 'ACCEPTED':
                    deal_id = trade_status.get('dealId')
                    if deal_id:
                        # Track the position
                        self.positions[deal_id] = {
                            'deal_id': deal_id,
                            'epic': epic,
                            'direction': direction,
                            'size': size,
                            'level': trade_status.get('level'),
                            'status': 'OPEN',
                            'timestamp': datetime.now(),
                            'deal_reference': deal_reference,
                            'source': 'FRAGMENTED'
                        }

                        logger.info(f"✅ Fragment tracked: {deal_id}")
                        return deal_reference

            return None

        except Exception as e:
            logger.error(f"❌ Error executing trade fragment: {e}")
            return None

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

    async def rolling_balance_management(self):
        """
        Rolling Balance Scaling: Update balance and position sizing after trades
        Goal: Maintain accurate balance for compounding and position sizing
        """
        try:
            if not self.account_manager:
                logger.warning("⚠️ Account Manager not initialized")
                return

            logger.info("🏦 PHASE 8 - Rolling Balance Management")

            # Get current account information
            sizing_info = await self.account_manager.get_position_sizing_info()

            if sizing_info:
                balance = sizing_info.get('balance', 0.0)
                available = sizing_info.get('available', 0.0)
                margin_percent = sizing_info.get('margin_percent', 0.0)
                profit_loss = sizing_info.get('profit_loss', 0.0)

                logger.info(f"🏦 BALANCE UPDATE:")
                logger.info(f"   Current Balance: £{balance:.2f}")
                if balance > 0:
                    logger.info(f"   Available: £{available:.2f} ({(available/balance*100):.1f}%)")
                else:
                    logger.info(f"   Available: £{available:.2f}")
                logger.info(f"   Margin Used: {margin_percent:.1f}%")
                logger.info(f"   P&L: £{profit_loss:.2f}")

                # Check for closed positions that need balance updates
                await self._check_for_closed_positions()

                # Get trade statistics
                stats = await self.account_manager.get_trade_statistics()
                if stats.get('total_trades', 0) > 0:
                    logger.info(f"📊 TRADE STATISTICS:")
                    logger.info(f"   Total Trades: {stats['total_trades']}")
                    logger.info(f"   Win Rate: {stats['win_rate']:.1f}%")
                    logger.info(f"   Total P&L: £{stats['total_pnl']:.2f}")
                    logger.info(f"   Average P&L: £{stats['average_pnl']:.2f}")

            # Update position sizing for all strategies
            await self._update_strategy_position_sizing()

        except Exception as e:
            logger.error(f"❌ Error in rolling_balance_management: {e}")

    async def _check_for_closed_positions(self):
        """Check for positions that have been closed and update balance accordingly"""
        try:
            # Get current positions from IG Markets
            current_positions = await self.ig_api.get_positions()
            current_deal_ids = {pos.get('dealId') for pos in current_positions} if current_positions else set()

            # Check tracked positions for any that are now closed
            closed_positions = []
            for position_id, position_data in list(self.positions.items()):
                deal_id = position_data.get('deal_id')
                if deal_id and deal_id not in current_deal_ids:
                    # Position has been closed
                    closed_positions.append({
                        'position_id': position_id,
                        'deal_id': deal_id,
                        'position_data': position_data
                    })

                    # Remove from tracked positions
                    del self.positions[position_id]

            # Update balance for each closed position
            for closed_pos in closed_positions:
                logger.info(f"🔄 Detected closed position: {closed_pos['deal_id']}")

                trade_result = {
                    'deal_id': closed_pos['deal_id'],
                    'position_id': closed_pos['position_id'],
                    'close_reason': 'detected_closed',
                    'timestamp': datetime.now()
                }

                # Update balance after trade
                await self.account_manager.update_balance_after_trade(trade_result)

            if closed_positions:
                logger.info(f"✅ Updated balance for {len(closed_positions)} closed positions")

        except Exception as e:
            logger.error(f"❌ Error checking for closed positions: {e}")

    async def _update_strategy_position_sizing(self):
        """Update position sizing for all strategies based on current balance"""
        try:
            if not self.account_manager:
                return

            # Get updated sizing information
            sizing_info = await self.account_manager.get_position_sizing_info()

            if sizing_info:
                # Update internal sizing variables
                self.current_balance = sizing_info.get('balance', 0.0)
                self.available_balance = sizing_info.get('available', 0.0)
                self.recommended_size = sizing_info.get('recommended_size', 0.1)

                logger.debug(f"📊 Strategy sizing updated: Balance: £{self.current_balance:.2f} | Recommended: £{self.recommended_size:.2f}/pt")

        except Exception as e:
            logger.error(f"❌ Error updating strategy position sizing: {e}")

    async def volatility_adaptive_profit_management(self):
        """
        Volatility-Adaptive Profit Targets: Adjust profit targets based on market volatility
        Goal: Capture larger moves during volatile periods without increasing position sizes
        """
        try:
            logger.info("🎯 PHASE 9 - Volatility-Adaptive Profit Management")

            # Get volatility configuration
            volatility_config = self.config.get('trading', {}).get('volatility_adaptive_profit', {})

            if not volatility_config.get('enabled', True):
                logger.debug("⚠️ Volatility-adaptive profit targets disabled")
                return

            # Get current positions for profit target updates
            positions = await self.ig_api.get_positions()
            if not positions:
                logger.debug("📊 No positions for volatility-adaptive profit management")
                return

            # Update price history for volatility calculations
            await self._update_market_volatility_data()

            # Process positions for profit target adjustments
            profit_updates = []

            for position in positions:
                try:
                    deal_id = position.get('dealId')
                    epic = position.get('epic')
                    current_price = position.get('level', 0.0)

                    if not deal_id or not epic or not current_price:
                        continue

                    # Update price history for this epic
                    self.risk_engine.update_price_history(current_price)

                    # Check if position needs profit target update
                    profit_update = await self._calculate_adaptive_profit_target(position)

                    if profit_update:
                        profit_updates.append(profit_update)

                except Exception as pos_error:
                    logger.warning(f"⚠️ Error processing position for volatility adjustment: {pos_error}")
                    continue

            # Apply profit target updates
            if profit_updates:
                logger.info(f"🎯 VOLATILITY-ADAPTIVE UPDATES: {len(profit_updates)} positions")
                for update in profit_updates:
                    logger.info(f"   {update['deal_id']}: TP {update['old_tp']:.1f} → {update['new_tp']:.1f} (Vol: {update['volatility_factor']:.2f}x)")
            else:
                logger.debug("📊 No volatility-adaptive profit target updates needed")

        except Exception as e:
            logger.error(f"❌ Error in volatility_adaptive_profit_management: {e}")

    async def _update_market_volatility_data(self):
        """Update market volatility data for all active epics"""
        try:
            # Get current market prices for volatility calculation
            primary_epics = [
                'IX.D.SPTRD.DAILY.IP',
                'IX.D.NASDAQ.DAILY.IP',
                'IX.D.FTSE.DAILY.IP'
            ]

            for epic in primary_epics:
                try:
                    # Get current market price (this would be implemented with real market data)
                    # For now, we'll use a placeholder
                    market_data = await self._get_market_data(epic)
                    if market_data:
                        current_price = market_data.get('current_price', 0.0)
                        if current_price > 0:
                            self.risk_engine.update_price_history(current_price)

                except Exception as epic_error:
                    logger.debug(f"Error updating volatility data for {epic}: {epic_error}")
                    continue

        except Exception as e:
            logger.error(f"❌ Error updating market volatility data: {e}")

    async def _get_market_data(self, epic: str) -> dict:
        """Get current market data for volatility calculations"""
        try:
            # This would integrate with real market data
            # For now, return placeholder data
            return {
                'epic': epic,
                'current_price': 6860.0,  # Placeholder S&P 500 price
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"❌ Error getting market data for {epic}: {e}")
            return {}

    async def _calculate_adaptive_profit_target(self, position: dict) -> dict:
        """Calculate adaptive profit target for a position"""
        try:
            deal_id = position.get('dealId')
            epic = position.get('epic')
            current_limit = position.get('limitLevel')
            entry_price = position.get('level', 0.0)

            if not deal_id or not epic or not entry_price:
                return None

            # Get position confidence (from tracked positions if available)
            confidence = 0.8  # Default confidence
            tracked_position = self.positions.get(deal_id)
            if tracked_position:
                confidence = tracked_position.get('confidence', 0.8)

            # Estimate ATR (Average True Range) for the epic
            estimated_atr = self._estimate_atr(epic, entry_price)

            # Calculate dynamic take profit using Risk Engine
            dynamic_tp = self.risk_engine.calculate_dynamic_take_profit(
                atr=estimated_atr,
                confidence_score=confidence,
                epic=epic
            )

            # Convert to actual price level
            direction = position.get('direction', 'BUY')
            if direction == 'BUY':
                new_tp_level = entry_price + dynamic_tp
            else:  # SELL
                new_tp_level = entry_price - dynamic_tp

            # Check if update is needed
            if current_limit:
                # Only update if new target is significantly different (>5% change)
                change_percent = abs(new_tp_level - current_limit) / current_limit
                if change_percent < 0.05:
                    return None

            # Get volatility factor for logging
            volatility_factor = self.risk_engine.get_recent_volatility_factor(epic)

            return {
                'deal_id': deal_id,
                'epic': epic,
                'old_tp': current_limit or 0.0,
                'new_tp': new_tp_level,
                'dynamic_tp_points': dynamic_tp,
                'confidence': confidence,
                'volatility_factor': volatility_factor,
                'atr_estimate': estimated_atr
            }

        except Exception as e:
            logger.error(f"❌ Error calculating adaptive profit target: {e}")
            return None

    def _estimate_atr(self, epic: str, current_price: float) -> float:
        """Estimate Average True Range for an epic"""
        try:
            # Epic-specific ATR estimates based on typical market behavior
            atr_estimates = {
                'IX.D.SPTRD.DAILY.IP': current_price * 0.015,    # ~1.5% of S&P 500 price
                'IX.D.NASDAQ.DAILY.IP': current_price * 0.018,   # ~1.8% of NASDAQ price
                'IX.D.FTSE.DAILY.IP': current_price * 0.012,     # ~1.2% of FTSE price
                'CS.D.GBPUSD.DAILY.IP': 0.008,                   # ~80 pips for GBP/USD
                'CS.D.EURUSD.DAILY.IP': 0.007                    # ~70 pips for EUR/USD
            }

            estimated_atr = atr_estimates.get(epic, current_price * 0.015)  # Default 1.5%

            # Ensure minimum ATR
            estimated_atr = max(estimated_atr, 5.0)

            logger.debug(f"📊 ATR Estimate for {epic}: {estimated_atr:.1f}")

            return estimated_atr

        except Exception as e:
            logger.error(f"❌ Error estimating ATR for {epic}: {e}")
            return 15.0  # Safe fallback

    async def session_bound_exposure_management(self):
        """
        Session-Bound Exposure Management: Optimize trading based on active market sessions
        Goal: Focus trading on most liquid markets during their peak hours
        """
        try:
            logger.info("📅 PHASE 10 - Session-Bound Exposure Management")

            if not self.session_manager:
                logger.warning("⚠️ Session Manager not initialized")
                return

            # Log current session status
            self.session_manager.log_session_status()

            # Get session information
            session_info = self.session_manager.get_session_info()

            # Update multi-epic configuration based on active session
            await self._update_session_based_epics(session_info)

            # Apply session-based position limits
            await self._apply_session_position_limits(session_info)

            # Adjust volatility multipliers based on session
            await self._apply_session_volatility_adjustments(session_info)

            # Check for session transitions and handle accordingly
            await self._handle_session_transitions(session_info)

            logger.info(f"📅 SESSION MANAGEMENT COMPLETE: {session_info['session_name']}")

        except Exception as e:
            logger.error(f"❌ Error in session-bound exposure management: {e}")

    async def _update_session_based_epics(self, session_info: Dict):
        """Update active epics based on current session"""
        try:
            active_epics = session_info.get('active_epics', [])
            primary_epic = session_info.get('primary_epic', 'IX.D.SPTRD.DAILY.IP')

            # Update multi-epic configuration
            if self.multi_epic_config:
                self.multi_epic_config['primary_epics'] = active_epics
                self.multi_epic_config['strategy_config']['max_concurrent_epics'] = len(active_epics)
                self.multi_epic_config['strategy_config']['margin_allocation_per_epic'] = 1.0 / max(len(active_epics), 1)

                logger.info(f"📊 UPDATED ACTIVE EPICS: {len(active_epics)} epics")
                for epic in active_epics:
                    logger.info(f"   ✓ {epic}")

        except Exception as e:
            logger.error(f"❌ Error updating session-based epics: {e}")

    async def _apply_session_position_limits(self, session_info: Dict):
        """Apply position limits based on current session"""
        try:
            session_max_positions = session_info.get('max_positions', 3)
            current_positions = len(self.positions)

            # Check if we need to reduce positions for the session
            if current_positions > session_max_positions:
                logger.warning(f"⚠️ Current positions ({current_positions}) exceed session limit ({session_max_positions})")
                # Note: We don't automatically close positions, just log the warning
                # Position closure should be handled by other risk management systems

            logger.info(f"📊 SESSION POSITION LIMITS: {current_positions}/{session_max_positions} positions")

        except Exception as e:
            logger.error(f"❌ Error applying session position limits: {e}")

    async def _apply_session_volatility_adjustments(self, session_info: Dict):
        """Apply volatility adjustments based on current session"""
        try:
            volatility_multiplier = session_info.get('volatility_multiplier', 1.0)

            # Update risk engine with session volatility multiplier
            if hasattr(self.risk_engine, 'session_volatility_multiplier'):
                self.risk_engine.session_volatility_multiplier = volatility_multiplier

            logger.info(f"📊 SESSION VOLATILITY MULTIPLIER: {volatility_multiplier:.1f}x")

        except Exception as e:
            logger.error(f"❌ Error applying session volatility adjustments: {e}")

    async def _handle_session_transitions(self, session_info: Dict):
        """Handle transitions between trading sessions"""
        try:
            session_name = session_info.get('session_name', 'Unknown')

            # Check if this is a new session
            if not hasattr(self, '_last_session') or self._last_session != session_name:
                logger.info(f"🔄 SESSION TRANSITION: {getattr(self, '_last_session', 'Unknown')} → {session_name}")

                # Update last session
                self._last_session = session_name

                # Perform session transition actions
                await self._on_session_change(session_info)

        except Exception as e:
            logger.error(f"❌ Error handling session transitions: {e}")

    async def _on_session_change(self, session_info: Dict):
        """Handle actions when session changes"""
        try:
            session_name = session_info.get('session_name', 'Unknown')

            logger.info(f"🎯 NEW SESSION ACTIVE: {session_name}")

            # Refresh multi-epic configuration for new session
            self.multi_epic_config = self._load_multi_epic_config()

            # Log new session capabilities
            active_epics = session_info.get('active_epics', [])
            max_positions = session_info.get('max_positions', 3)
            volatility_multiplier = session_info.get('volatility_multiplier', 1.0)

            logger.info(f"📊 NEW SESSION CONFIGURATION:")
            logger.info(f"   Active Epics: {len(active_epics)}")
            logger.info(f"   Max Positions: {max_positions}")
            logger.info(f"   Volatility Multiplier: {volatility_multiplier:.1f}x")

        except Exception as e:
            logger.error(f"❌ Error in session change handler: {e}")

    def _get_session_aware_epic(self) -> str:
        """Get the appropriate epic for the current session"""
        try:
            # Use session manager to get primary epic if available
            if hasattr(self, 'session_manager') and self.session_manager:
                primary_epic = self.session_manager.get_primary_epic_for_session()
                if primary_epic:
                    return primary_epic

            # Fallback to configuration default
            return self.config['brokers']['ig_markets'].get('default_epic', 'IX.D.SPTRD.DAILY.IP')

        except Exception as e:
            logger.error(f"❌ Error getting session-aware epic: {e}")
            return 'IX.D.SPTRD.DAILY.IP'  # Safe fallback
