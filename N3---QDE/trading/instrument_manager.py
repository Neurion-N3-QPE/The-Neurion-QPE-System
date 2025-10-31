"""
Instrument Manager - Handles instrument-specific trading parameters
Manages margin requirements, minimum position sizes, and trading constraints per epic
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class InstrumentManager:
    """Manages instrument-specific trading parameters and constraints"""
    
    def __init__(self, ig_api=None):
        self.ig_api = ig_api
        self.instrument_cache = {}
        self.last_cache_update = {}
        self.cache_duration = 300  # 5 minutes
        
        # Instrument-specific configurations
        self.instrument_configs = {
            # Major Forex Pairs (Lower margin requirements)
            "CS.D.GBPUSD.TODAY.IP": {
                "name": "GBP/USD",
                "type": "forex",
                "min_size": 0.5,
                "typical_margin_per_unit": 3.33,  # £3.33 per £1/pip
                "point_value": 1.0,
                "recommended_balance": 50.0,
                "priority": 1
            },
            "CS.D.EURUSD.TODAY.IP": {
                "name": "EUR/USD", 
                "type": "forex",
                "min_size": 0.5,
                "typical_margin_per_unit": 3.33,
                "point_value": 1.0,
                "recommended_balance": 50.0,
                "priority": 2
            },
            "CS.D.USDJPY.TODAY.IP": {
                "name": "USD/JPY",
                "type": "forex", 
                "min_size": 0.5,
                "typical_margin_per_unit": 3.33,
                "point_value": 1.0,
                "recommended_balance": 50.0,
                "priority": 3
            },
            
            # UK Indices (Medium margin requirements)
            "IX.D.FTSE.DAILY.IP": {
                "name": "FTSE 100",
                "type": "index",
                "min_size": 0.5,
                "typical_margin_per_unit": 20.0,  # £20 per £1/point
                "point_value": 1.0,
                "recommended_balance": 150.0,
                "priority": 4
            },
            
            # US Indices (Higher margin requirements)
            "IX.D.SPTRD.DAILY.IP": {
                "name": "S&P 500",
                "type": "index",
                "min_size": 0.1,
                "typical_margin_per_unit": 80.0,  # £80 per £1/point
                "point_value": 1.0,
                "recommended_balance": 400.0,
                "priority": 5
            },
            "IX.D.NASDAQ.DAILY.IP": {
                "name": "NASDAQ 100",
                "type": "index",
                "min_size": 0.1,
                "typical_margin_per_unit": 100.0,  # £100 per £1/point
                "point_value": 1.0,
                "recommended_balance": 500.0,
                "priority": 6
            },
            
            # Asian Indices (Very high margin requirements)
            "IX.D.NIKKEI.DAILY.IP": {
                "name": "Nikkei 225",
                "type": "index",
                "min_size": 0.1,
                "typical_margin_per_unit": 200.0,  # £200 per £1/point
                "point_value": 1.0,
                "recommended_balance": 1000.0,
                "priority": 10
            },
            "IX.D.HANGSENG.DAILY.IP": {
                "name": "Hang Seng",
                "type": "index", 
                "min_size": 0.1,
                "typical_margin_per_unit": 150.0,  # £150 per £1/point
                "point_value": 1.0,
                "recommended_balance": 800.0,
                "priority": 9
            },
            
            # Commodities (Variable margin requirements)
            "CS.D.USCGC.TODAY.IP": {
                "name": "Gold",
                "type": "commodity",
                "min_size": 0.5,
                "typical_margin_per_unit": 10.0,  # £10 per £1/point
                "point_value": 1.0,
                "recommended_balance": 100.0,
                "priority": 7
            }
        }
    
    async def get_instrument_info(self, epic: str) -> Dict:
        """Get comprehensive instrument information"""
        try:
            # Check cache first
            if self._is_cache_valid(epic):
                return self.instrument_cache[epic]
            
            # Get static config
            static_config = self.instrument_configs.get(epic, {})
            
            # Get live market data if API available
            live_data = {}
            if self.ig_api:
                try:
                    market_data = await self.ig_api.get_market_data(epic)
                    if market_data and 'instrument' in market_data:
                        instrument = market_data['instrument']
                        live_data = {
                            'min_deal_size': instrument.get('minDealSize', {}).get('value', 0.1),
                            'margin_factor': instrument.get('marginFactor', 5.0),
                            'margin_factor_unit': instrument.get('marginFactorUnit', 'PERCENTAGE'),
                            'currency': instrument.get('currencies', [{}])[0].get('code', 'GBP'),
                            'lot_size': instrument.get('lotSize', 1.0),
                            'one_pip_means': instrument.get('onePipMeans', '1 point'),
                            'value_of_one_pip': instrument.get('valueOfOnePip', '1.0')
                        }
                except Exception as e:
                    logger.debug(f"Could not fetch live data for {epic}: {e}")
            
            # Combine static and live data
            instrument_info = {
                **static_config,
                **live_data,
                'epic': epic,
                'last_updated': datetime.now()
            }
            
            # Cache the result
            self.instrument_cache[epic] = instrument_info
            self.last_cache_update[epic] = datetime.now()
            
            return instrument_info
            
        except Exception as e:
            logger.error(f"❌ Error getting instrument info for {epic}: {e}")
            return self.instrument_configs.get(epic, {'epic': epic, 'min_size': 0.1, 'typical_margin_per_unit': 50.0})
    
    async def calculate_safe_position_size(self, epic: str, available_balance: float, risk_amount: float) -> Tuple[float, str]:
        """Calculate safe position size for specific instrument"""
        try:
            instrument_info = await self.get_instrument_info(epic)
            
            # Get instrument constraints
            min_size = instrument_info.get('min_size', instrument_info.get('min_deal_size', 0.1))
            margin_per_unit = instrument_info.get('typical_margin_per_unit', 50.0)
            recommended_balance = instrument_info.get('recommended_balance', 200.0)
            
            # Check if we have sufficient balance for this instrument
            if available_balance < recommended_balance:
                return 0.0, f"Insufficient balance for {instrument_info.get('name', epic)}. Need £{recommended_balance:.0f}, have £{available_balance:.2f}"
            
            # Calculate margin-based maximum size
            margin_safety_factor = 0.3  # Use only 30% of available balance for margin
            safe_margin_balance = available_balance * margin_safety_factor
            max_size_by_margin = safe_margin_balance / margin_per_unit
            
            # Calculate risk-based size
            # Assume 50 point stop loss for sizing calculation
            assumed_stop_distance = 50.0
            max_size_by_risk = risk_amount / assumed_stop_distance
            
            # Use the smaller of the two
            calculated_size = min(max_size_by_margin, max_size_by_risk)
            
            # Ensure minimum size
            if calculated_size < min_size:
                # Check if we can afford at least the minimum size given safety factor
                required_margin_for_min = (margin_per_unit * min_size) / margin_safety_factor
                if available_balance >= required_margin_for_min:
                    calculated_size = min_size
                else:
                    return 0.0, f"Cannot meet minimum size {min_size} for {instrument_info.get('name', epic)}"
            
            # Round to appropriate precision depending on min_size granularity
            precision = 2 if min_size < 0.1 else 1
            calculated_size = round(calculated_size, precision)
            # Ensure rounding did not drop below min_size
            if calculated_size < min_size:
                calculated_size = min_size
            
            reason = f"Safe size for {instrument_info.get('name', epic)}: margin={max_size_by_margin:.2f}, risk={max_size_by_risk:.2f}"
            
            return calculated_size, reason
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size for {epic}: {e}")
            return 0.1, f"Error calculating size, using minimum: {e}"
    
    def get_suitable_instruments(self, available_balance: float) -> list:
        """Get list of instruments suitable for current balance, sorted by priority"""
        suitable = []
        
        for epic, config in self.instrument_configs.items():
            recommended_balance = config.get('recommended_balance', 200.0)
            priority = config.get('priority', 10)
            
            if available_balance >= recommended_balance:
                suitable.append({
                    'epic': epic,
                    'name': config.get('name', epic),
                    'type': config.get('type', 'unknown'),
                    'priority': priority,
                    'recommended_balance': recommended_balance,
                    'margin_per_unit': config.get('typical_margin_per_unit', 50.0)
                })
        
        # Sort by priority (lower number = higher priority)
        suitable.sort(key=lambda x: x['priority'])
        
        return suitable
    
    def _is_cache_valid(self, epic: str) -> bool:
        """Check if cached data is still valid"""
        if epic not in self.instrument_cache:
            return False
        
        if epic not in self.last_cache_update:
            return False
        
        time_diff = (datetime.now() - self.last_cache_update[epic]).total_seconds()
        return time_diff < self.cache_duration
    
    async def get_fallback_epic(self, available_balance: float, exclude_epics: list = None) -> Optional[str]:
        """Get the best fallback epic for current balance"""
        exclude_epics = exclude_epics or []
        suitable = self.get_suitable_instruments(available_balance)
        
        for instrument in suitable:
            if instrument['epic'] not in exclude_epics:
                return instrument['epic']
        
        return None
    
    def log_instrument_analysis(self, available_balance: float):
        """Log analysis of suitable instruments for current balance"""
        suitable = self.get_suitable_instruments(available_balance)
        
        logger.info(f"💰 INSTRUMENT ANALYSIS (Balance: £{available_balance:.2f}):")
        
        if suitable:
            logger.info(f"   ✅ Suitable Instruments ({len(suitable)}):")
            for i, instrument in enumerate(suitable[:5]):  # Show top 5
                logger.info(f"      {i+1}. {instrument['name']} ({instrument['epic']})")
                logger.info(f"         Type: {instrument['type']} | Margin: £{instrument['margin_per_unit']:.0f}/unit")
        else:
            logger.warning(f"   ❌ No suitable instruments for current balance")
            logger.info(f"   💡 Minimum recommended balance: £{min(config.get('recommended_balance', 200) for config in self.instrument_configs.values()):.0f}")
