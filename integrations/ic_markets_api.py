"""
IC Markets API Integration
Full API wrapper for IC Markets (MetaTrader 5)
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ICMarketsAPI:
    """
    IC Markets API Wrapper (MetaTrader 5)
    
    Supports:
    - Account management
    - Market data
    - Position management
    - Order execution via MT5
    """
    
    def __init__(
        self,
        account_number: str,
        password: str,
        server: str,
        demo: bool = True
    ):
        self.account_number = account_number
        self.password = password
        self.server = server
        self.demo = demo
        
        self.mt5 = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize MT5 connection"""
        logger.info("🔗 Connecting to IC Markets (MT5)...")
        
        try:
            # Try to import MT5
            try:
                import MetaTrader5 as MT5
                self.mt5 = MT5
            except ImportError:
                logger.warning("⚠️  MetaTrader5 not installed")
                logger.info("   Install with: pip install MetaTrader5")
                return
            
            # Initialize MT5
            if not self.mt5.initialize():
                logger.error("❌ MT5 initialization failed")
                return
            
            # Login
            authorized = self.mt5.login(
                login=int(self.account_number),
                password=self.password,
                server=self.server
            )
            
            if not authorized:
                logger.error("❌ MT5 login failed")
                return
            
            self.initialized = True
            logger.info("✅ IC Markets connected")
            
        except Exception as e:
            logger.error(f"❌ IC Markets initialization error: {e}")
    
    async def get_account_info(self) -> Dict:
        """Get account information"""
        if not self.initialized:
            return {}
        
        try:
            account_info = self.mt5.account_info()
            
            if account_info is None:
                return {}
            
            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'profit': account_info.profit,
                'leverage': account_info.leverage,
                'server': account_info.server,
                'currency': account_info.currency
            }
            
        except Exception as e:
            logger.error(f"❌ Get account info error: {e}")
            return {}
    
    async def get_market_data(self, symbol: str) -> Dict:
        """
        Get market data for a symbol
        
        Args:
            symbol: MT5 symbol (e.g., 'EURUSD')
        """
        if not self.initialized:
            return {}
        
        try:
            tick = self.mt5.symbol_info_tick(symbol)
            
            if tick is None:
                return {}
            
            return {
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'last': tick.last,
                'volume': tick.volume,
                'time': datetime.fromtimestamp(tick.time)
            }
            
        except Exception as e:
            logger.error(f"❌ Get market data error: {e}")
            return {}
    
    async def open_position(
        self,
        symbol: str,
        direction: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: str = "Neurion QPE"
    ) -> Dict:
        """
        Open a new position
        
        Args:
            symbol: MT5 symbol
            direction: 'BUY' or 'SELL'
            volume: Position size in lots
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            comment: Order comment
        """
        if not self.initialized:
            return {}
        
        try:
            # Get current price
            symbol_info = self.mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"❌ Symbol {symbol} not found")
                return {}
            
            # Determine order type
            if direction.upper() == 'BUY':
                order_type = self.mt5.ORDER_TYPE_BUY
                price = symbol_info.ask
            else:
                order_type = self.mt5.ORDER_TYPE_SELL
                price = symbol_info.bid
            
            # Prepare request
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            # Add SL/TP if provided
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Send order
            result = self.mt5.order_send(request)
            
            if result.retcode != self.mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Order failed: {result.comment}")
                return {}
            
            logger.info(f"✅ Position opened: {result.order}")
            
            return {
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'bid': result.bid,
                'ask': result.ask,
                'comment': result.comment
            }
            
        except Exception as e:
            logger.error(f"❌ Open position error: {e}")
            return {}
    
    async def close_position(self, position_id: int) -> Dict:
        """
        Close an existing position
        
        Args:
            position_id: Position ticket number
        """
        if not self.initialized:
            return {}
        
        try:
            # Get position info
            positions = self.mt5.positions_get(ticket=position_id)
            
            if positions is None or len(positions) == 0:
                logger.error(f"❌ Position {position_id} not found")
                return {}
            
            position = positions[0]
            
            # Determine close order type (opposite of position type)
            if position.type == self.mt5.ORDER_TYPE_BUY:
                order_type = self.mt5.ORDER_TYPE_SELL
                price = self.mt5.symbol_info_tick(position.symbol).bid
            else:
                order_type = self.mt5.ORDER_TYPE_BUY
                price = self.mt5.symbol_info_tick(position.symbol).ask
            
            # Prepare close request
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position_id,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Neurion close",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            # Send close order
            result = self.mt5.order_send(request)
            
            if result.retcode != self.mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Close failed: {result.comment}")
                return {}
            
            logger.info(f"✅ Position closed: {position_id}")
            
            return {
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'comment': result.comment
            }
            
        except Exception as e:
            logger.error(f"❌ Close position error: {e}")
            return {}
    
    async def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        if not self.initialized:
            return []
        
        try:
            positions = self.mt5.positions_get()
            
            if positions is None:
                return []
            
            return [
                {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'comment': pos.comment
                }
                for pos in positions
            ]
            
        except Exception as e:
            logger.error(f"❌ Get positions error: {e}")
            return []
    
    async def shutdown(self):
        """Shutdown MT5 connection"""
        if self.mt5 and self.initialized:
            self.mt5.shutdown()
        logger.info("✅ IC Markets disconnected")
