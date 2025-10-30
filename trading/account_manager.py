"""
🏦 Account Manager - Rolling Balance Scaling System

Manages account balance updates and position sizing calculations
with real-time balance tracking for accurate compounding.

Core Features:
- Real-time balance updates after each trade
- Environment variable synchronization
- Position sizing based on current balance
- Trade result tracking and analysis
"""

import asyncio
import structlog
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import set_key
import os

logger = structlog.get_logger(__name__)


class AccountManager:
    """
    Manages account balance and position sizing with rolling updates
    
    Key Features:
    1. Real-time balance tracking
    2. Environment variable updates
    3. Position sizing calculations
    4. Trade result analysis
    5. Compounding support
    """
    
    def __init__(self, config: Dict, ig_api):
        self.config = config
        self.ig_api = ig_api
        self.balance = 0.0
        self.available_balance = 0.0
        self.margin_used = 0.0
        self.profit_loss = 0.0
        
        # Rolling balance configuration
        self.rolling_config = config.get('trading', {}).get('rolling_balance_scaling', {})
        self.update_frequency = self.rolling_config.get('update_frequency', 'after_each_trade')
        self.env_file_path = self.rolling_config.get('env_file_path', '.env')
        self.balance_var_name = self.rolling_config.get('balance_var_name', 'ACCOUNT_BALANCE')
        
        # Trade tracking
        self.trade_history = []
        self.last_balance_update = None
        
        logger.info("🏦 Account Manager initialized")
    
    async def initialize(self):
        """Initialize account manager with current balance"""
        try:
            # Get initial account information
            await self.refresh_account_info()
            
            # Update environment variable with current balance
            await self.update_env_balance()
            
            logger.info(f"🏦 Account Manager ready - Balance: £{self.balance:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing Account Manager: {e}")
            raise
    
    async def refresh_account_info(self):
        """Refresh account information from IG Markets"""
        try:
            account_info = await self.ig_api.get_account_info()

            if account_info:
                # Handle different response formats
                if 'accounts' in account_info and account_info['accounts']:
                    # Multi-account format
                    for acc in account_info['accounts']:
                        if acc.get('accountId') == self.config['brokers']['ig_markets']['account_id']:
                            balance_info = acc.get('balance', {})
                            self.balance = float(balance_info.get('balance', 0.0))
                            self.available_balance = float(balance_info.get('available', 0.0))
                            self.profit_loss = float(balance_info.get('profitLoss', 0.0))
                            break
                else:
                    # Direct format
                    self.balance = float(account_info.get('balance', 0.0))
                    self.available_balance = float(account_info.get('available', 0.0))
                    self.profit_loss = float(account_info.get('profitLoss', 0.0))

                self.margin_used = self.balance - self.available_balance

                logger.debug(f"📊 Account refreshed: Balance: £{self.balance:.2f} | Available: £{self.available_balance:.2f}")
                return True
            else:
                logger.warning("⚠️ Failed to get account information")
                return False

        except Exception as e:
            logger.error(f"❌ Error refreshing account info: {e}")
            return False
    
    async def update_balance_after_trade(self, trade_result: Dict):
        """
        Update balance after each successful trade close
        Core Rolling Balance Scaling functionality
        """
        try:
            logger.info(f"🔄 Updating balance after trade: {trade_result.get('deal_id', 'Unknown')}")
            
            # Get fresh account balance from IG Markets
            old_balance = self.balance
            success = await self.refresh_account_info()
            
            if not success:
                logger.warning("❌ Failed to refresh account info after trade")
                return False
            
            # Calculate balance change
            balance_change = self.balance - old_balance
            
            # Update environment variable for compounding calculations
            await self.update_env_balance()
            
            # Record trade result
            trade_record = {
                'timestamp': datetime.now(),
                'deal_id': trade_result.get('deal_id'),
                'old_balance': old_balance,
                'new_balance': self.balance,
                'balance_change': balance_change,
                'profit_loss': self.profit_loss,
                'trade_result': trade_result
            }
            
            self.trade_history.append(trade_record)
            self.last_balance_update = datetime.now()
            
            # Log balance update
            if balance_change > 0:
                logger.info(f"💰 BALANCE INCREASED: £{old_balance:.2f} → £{self.balance:.2f} (+£{balance_change:.2f})")
            elif balance_change < 0:
                logger.info(f"📉 BALANCE DECREASED: £{old_balance:.2f} → £{self.balance:.2f} (£{balance_change:.2f})")
            else:
                logger.info(f"📊 BALANCE UNCHANGED: £{self.balance:.2f}")
            
            # Update position sizing calculations
            await self.recalculate_position_sizes()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating balance after trade: {e}")
            return False
    
    async def update_env_balance(self):
        """Update environment variable with current balance"""
        try:
            # Update .env file
            set_key(self.env_file_path, self.balance_var_name, str(self.balance))
            
            # Update current environment
            os.environ[self.balance_var_name] = str(self.balance)
            
            logger.debug(f"🔧 Environment updated: {self.balance_var_name}={self.balance:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating environment balance: {e}")
            return False
    
    async def recalculate_position_sizes(self):
        """Recalculate position sizes based on updated balance"""
        try:
            # Get risk configuration
            risk_config = self.config.get('trading', {}).get('risk_management', {})
            risk_per_trade_percent = risk_config.get('risk_per_trade_percent', 3.0)
            
            # Calculate new position sizes
            risk_amount = self.balance * (risk_per_trade_percent / 100.0)
            margin_safe_size = self.available_balance * 0.001  # Conservative margin-based sizing
            
            # Log updated sizing
            logger.info(f"📊 POSITION SIZING UPDATED:")
            logger.info(f"   Balance: £{self.balance:.2f} | Available: £{self.available_balance:.2f}")
            logger.info(f"   Risk-based: £{risk_amount:.2f} | Margin-safe: £{margin_safe_size:.2f}")
            
            return {
                'balance': self.balance,
                'available': self.available_balance,
                'risk_based_size': risk_amount,
                'margin_safe_size': margin_safe_size,
                'recommended_size': min(risk_amount, margin_safe_size)
            }
            
        except Exception as e:
            logger.error(f"❌ Error recalculating position sizes: {e}")
            return None
    
    async def get_current_balance(self) -> float:
        """Get current account balance"""
        return self.balance
    
    async def get_available_balance(self) -> float:
        """Get available balance for trading"""
        return self.available_balance
    
    async def get_margin_percent(self) -> float:
        """Get current margin utilization percentage"""
        if self.balance <= 0:
            return 0.0
        return (self.margin_used / self.balance) * 100.0
    
    async def get_position_sizing_info(self) -> Dict:
        """Get comprehensive position sizing information"""
        try:
            # Refresh account info
            await self.refresh_account_info()
            
            # Calculate position sizes
            sizing_info = await self.recalculate_position_sizes()
            
            if sizing_info:
                sizing_info.update({
                    'margin_used': self.margin_used,
                    'margin_percent': await self.get_margin_percent(),
                    'profit_loss': self.profit_loss,
                    'last_update': self.last_balance_update
                })
            
            return sizing_info
            
        except Exception as e:
            logger.error(f"❌ Error getting position sizing info: {e}")
            return {}
    
    async def should_compound_position(self, position_pnl: float) -> bool:
        """
        Check if position should be compounded based on current balance
        Uses updated balance for accurate compounding calculations
        """
        try:
            # Get compounding configuration
            compound_config = self.config.get('trading', {}).get('intra_trade_compounding', {})
            profit_threshold_percent = compound_config.get('profit_threshold_percent', 1.0)
            
            # Calculate threshold based on current balance
            profit_threshold = self.balance * (profit_threshold_percent / 100.0)
            
            should_compound = position_pnl >= profit_threshold
            
            if should_compound:
                logger.info(f"💰 COMPOUND OPPORTUNITY: P&L £{position_pnl:.2f} ≥ Threshold £{profit_threshold:.2f}")
            
            return should_compound
            
        except Exception as e:
            logger.error(f"❌ Error checking compound eligibility: {e}")
            return False
    
    async def get_trade_statistics(self) -> Dict:
        """Get trading statistics based on balance updates"""
        try:
            if not self.trade_history:
                return {'total_trades': 0, 'total_pnl': 0.0, 'win_rate': 0.0}
            
            total_trades = len(self.trade_history)
            total_pnl = sum(trade['balance_change'] for trade in self.trade_history)
            winning_trades = sum(1 for trade in self.trade_history if trade['balance_change'] > 0)
            win_rate = (winning_trades / total_trades) * 100.0 if total_trades > 0 else 0.0
            
            return {
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'average_pnl': total_pnl / total_trades if total_trades > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating trade statistics: {e}")
            return {}
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trade history"""
        return self.trade_history[-limit:] if self.trade_history else []
