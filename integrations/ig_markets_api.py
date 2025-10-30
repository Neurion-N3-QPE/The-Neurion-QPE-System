"""
IG Markets API Integration
Full API wrapper for IG Markets trading platform
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IGMarketsAPI:
    """
    IG Markets API Wrapper
    
    Supports:
    - Account management
    - Market data
    - Position management
    - Order execution
    """
    
    BASE_URL = "https://api.ig.com/gateway/deal"
    DEMO_URL = "https://demo-api.ig.com/gateway/deal"
    
    def __init__(
        self,
        api_key: str,
        username: str,
        password: str,
        account_id: str,
        demo: bool = True
    ):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.account_id = account_id
        self.base_url = self.DEMO_URL if demo else self.BASE_URL
        
        self.session = None
        self.client_token = None
        self.security_token = None
        
    async def initialize(self):
        """Initialize API connection"""
        logger.info("🔗 Connecting to IG Markets...")
        
        self.session = aiohttp.ClientSession()
        
        # Authenticate
        await self._authenticate()
        
        logger.info("✅ IG Markets connected")
    
    async def _authenticate(self):
        """Authenticate with IG Markets"""
        url = f"{self.base_url}/session"
        
        headers = {
            'X-IG-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Version': '2'
        }
        
        payload = {
            'identifier': self.username,
            'password': self.password
        }
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.client_token = data['clientId']
                    self.security_token = response.headers['CST']
                    self.x_security_token = response.headers.get('X-SECURITY-TOKEN', self.security_token) # Store X-SECURITY-TOKEN separately
                    self.account_id = data.get('accountId', self.account_id)
                    logger.info("✅ Authentication successful")
                else:
                    error = await response.text()
                    raise Exception(f"Authentication failed: {error}")
                    
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            raise
    
    def _get_headers(self) -> Dict:
        """Get request headers with auth tokens"""
        return {
            'X-IG-API-KEY': self.api_key,
            'CST': self.security_token,
            'X-SECURITY-TOKEN': self.x_security_token, # Use the separately stored X-SECURITY-TOKEN
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Version': '2'
        }
    
    async def get_account_info(self) -> Dict:
        """Get account information"""
        url = f"{self.base_url}/accounts"
        headers = self._get_headers()
        logger.debug(f"DEBUG: GET Account Info - URL: {url}, Headers: {headers}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error = await response.text()
                    logger.error(f"❌ Account info error: {error}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Get account error: {e}")
            return {}
    
    async def get_market_data(self, epic: str) -> Dict:
        """
        Get market data for an instrument
        
        Args:
            epic: IG Markets epic code (e.g., 'CS.D.GBPUSD.TODAY.IP')
        """
        url = f"{self.base_url}/markets/{epic}"
        headers = self._get_headers()
        logger.debug(f"DEBUG: GET Market Data - URL: {url}, Headers: {headers}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error = await response.text()
                    logger.error(f"❌ Market data error: {error}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Get market data error: {e}")
            return {}
    
    async def open_position(
        self,
        epic: str,
        direction: str,
        size: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        """
        Open a new position
        
        Args:
            epic: IG Markets epic code
            direction: 'BUY' or 'SELL'
            size: Position size
            stop_loss: Stop loss level (optional)
            take_profit: Take profit level (optional)
        """
        url = f"{self.base_url}/positions/otc"
        
        payload = {
            'epic': epic,
            'direction': direction,
            'size': float(size), # Explicitly cast to Python float
            'orderType': 'MARKET',
            'timeInForce': 'GOOD_TILL_CANCELLED', # Changed timeInForce
            'guaranteedStop': False,
            'forceOpen': 'true'
        }
        
        if stop_loss:
            payload['stopLevel'] = stop_loss
            
        if take_profit:
            payload['limitLevel'] = take_profit
        
        headers = self._get_headers()
        logger.debug(f"DEBUG: POST Open Position - URL: {url}, Headers: {headers}, Payload: {payload}")
        
        try:
            async with self.session.post(
                url,
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    deal_ref = data.get('dealReference')
                    logger.info(f"✅ Position opened: {deal_ref}")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"❌ Open position error: {error}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Open position exception: {e}")
            return {}
    
    async def close_position(self, deal_id: str) -> Dict:
        """
        Close an existing position
        
        Args:
            deal_id: Deal ID to close
        """
        # Get position details first
        position = await self.get_position(deal_id)
        if not position:
            return {}
        
        url = f"{self.base_url}/positions/otc"
        
        payload = {
            'dealId': deal_id,
            'direction': 'SELL' if position['direction'] == 'BUY' else 'BUY',
            'orderType': 'MARKET',
            'size': position['size'],
            'timeInForce': 'EXECUTE_AND_ELIMINATE'
        }
        
        try:
            headers = self._get_headers()
            headers['_method'] = 'DELETE'
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Position closed: {deal_id}")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"❌ Close position error: {error}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Close position exception: {e}")
            return {}
    
    async def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        url = f"{self.base_url}/positions"
        
        try:
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('positions', [])
                else:
                    error = await response.text()
                    logger.error(f"❌ Get positions error: {error}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Get positions exception: {e}")
            return []
    
    async def get_position(self, deal_id: str) -> Optional[Dict]:
        """Get specific position details"""
        positions = await self.get_positions()
        
        for position in positions:
            if position.get('dealId') == deal_id:
                return position
        
        return None
    
    async def shutdown(self):
        """Shutdown API connection"""
        if self.session:
            await self.session.close()
        logger.info("✅ IG Markets disconnected")
