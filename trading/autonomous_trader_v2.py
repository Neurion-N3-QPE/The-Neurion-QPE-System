"""
Autonomous Trader V2 - Main Trading Engine
Fully automated trading with PIE integration
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging
import json
from pathlib import Path

from core.integrity import IntegrityBus, IntegrityPrediction
from core.quantum_engine import QuantumEngine
from integrations.ig_markets_api import IGMarketsAPI
from config.settings import update_env_var

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
            logger.warning("⚠️  Could not fetch current account balance. Using dummy balance for position sizing.")
            current_balance = 264.63
            available_funds = 264.63
        
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
        """Execute a trade"""
        logger.info(f"🎯 EXECUTING: {direction} | Size: ${size:.2f}")
        
        if not self.ig_api:
            logger.error("❌ IG Markets API not initialized.")
            return
        epic = self.config['brokers']['ig_markets'].get('default_epic', 'CS.D.GBPUSD.TODAY.SPR')
        
        try:
            # STRATEGY: Max ROI Without Margin Expansion
            # Use fragmented entry instead of single large position
            logger.info(f"🔀 Implementing fragmented entry strategy for {size} £/pt")

            # Execute fragmented entry (uses config settings)
            successful_fragments = await self.fragmented_entry(
                epic=epic,
                base_size=size
            )

            if successful_fragments:
                logger.info(f"✅ Fragmented entry successful: {len(successful_fragments)} fragments executed")
                return  # Exit early as fragmented_entry handles all tracking
            else:
                logger.warning("❌ Fragmented entry failed, falling back to single position")
                # Fallback to original single position logic
                trade_response = await self.ig_api.open_position(
                    epic=epic,
                    direction=direction,
                    size=size,
                    # stop_loss=... # TODO: Implement stop loss calculation
                    # take_profit=... # TODO: Implement take profit calculation
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
        """Load multi-epic trading configuration"""
        try:
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
                            'direction': 'BUY' if prediction.signal > 0.5 else 'SELL',
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

    async def _execute_trade_fragment(self, epic: str, size: float, direction: str):
        """
        Execute a single trade fragment
        Extracted from existing trade execution logic for reuse
        """
        try:
            if not self.ig_api:
                logger.error("❌ IG Markets API not initialized")
                return None

            # Open position using existing IG API
            result = await self.ig_api.open_position(
                epic=epic,
                direction=direction,
                size=size
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
