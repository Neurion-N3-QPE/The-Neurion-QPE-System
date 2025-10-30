"""
IG Markets API Integration
Full API wrapper for IG Markets trading platform (SPREAD BETTING - NO CFD)
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IGMarketsAPI:
    """
    IG Markets API Wrapper for SPREAD BETTING
    
    Supports:
    - Authentication
    - Account management  
    - Market data
    - Position management (Spread Betting only)    """
    
    def __init__(
        self,
        api_key: str,
        username: str,
        password: str,
        account_id: str,
        demo: bool = False
    ):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.account_id = account_id
        self.demo = demo
        
        # API endpoints
        if demo:
            self.base_url = "https://demo-api.ig.com/gateway/deal"
        else:
            self.base_url = "https://api.ig.com/gateway/deal"
        
        # Session tokens
        self.security_token = None
        self.client_token = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.authenticated = False

    async def initialize(self):
        """Initialize API connection and authenticate"""
        logger.info("🔌 Connecting to IG Markets API...")
        
        # Create session
        self.session = aiohttp.ClientSession()
        
        # Authenticate
        await self._authenticate()
        
        logger.info(f"✅ Connected to IG Markets ({'DEMO' if self.demo else 'LIVE'})")
    
    async def _authenticate(self):
        """Authenticate with IG Markets API"""
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
                    # Store security tokens
                    self.security_token = response.headers.get('CST')
                    self.client_token = response.headers.get('X-SECURITY-TOKEN')
                    
                    data = await response.json()
                    logger.info(f"✅ Authenticated as {self.username}")
                    self.authenticated = True
                    return data
                else:
                    error = await response.text()
                    logger.error(f"❌ Authentication failed: {error}")
                    raise Exception(f"Authentication failed: {error}")
                    
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            raise

    def _get_headers(self) -> Dict:
        """Get request headers with auth tokens"""
        return {
            'X-IG-API-KEY': self.api_key,
            'CST': self.security_token,
            'X-SECURITY-TOKEN': self.client_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Version': '2'
        }
    
    async def get_account_info(self) -> Dict:
        """Get account information"""
        url = f"{self.base_url}/accounts"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Account info: {data}")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"❌ Account info error: {error}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Get account error: {e}")
            return {}
    
    async def get_market_data(self, epic: str) -> Dict:
        """Get market data for an instrument"""
        url = f"{self.base_url}/markets/{epic}"
        headers = self._get_headers()
        logger.debug(f"Getting market data for {epic}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Market data for {epic}: {data}")
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
        Open a new SPREAD BETTING position (NO CFD)
        
        Args:
            epic: Market epic code (e.g., 'CS.D.GBPUSD.TODAY.SPR')
            direction: 'BUY' or 'SELL'
            size: Position size in GBP per point
            stop_loss: Optional stop loss level
            take_profit: Optional take profit level
        
        Returns:
            Deal reference and confirmation
        """
        url = f"{self.base_url}/positions/otc"
        
        # Spread betting payload (NO CFD, NO EXPIRY)
        payload = {
            'epic': epic,
            'direction': direction.upper(),  # BUY or SELL
            'size': float(size),
            'orderType': 'MARKET',
            'guaranteedStop': False,
            'forceOpen': True,
            'currencyCode': 'GBP',
            'timeInForce': 'FILL_OR_KILL'
        }
        
        # Add stop loss if provided
        if stop_loss:
            payload['stopLevel'] = float(stop_loss)
        
        # Add take profit if provided  
        if take_profit:
            payload['limitLevel'] = float(take_profit)
        
        headers = self._get_headers()
        logger.info(f"Opening {direction} position for {epic}: £{size} per point")
        logger.debug(f"Payload: {payload}")
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    data = await response.json()
                    deal_ref = data.get('dealReference')
                    logger.info(f"✅ Position opened: {deal_ref}")
                    return data
                else:
                    logger.error(f"❌ Open position failed (Status {response.status}): {response_text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Open position exception: {e}")
            return {}

    async def close_position(self, deal_id: str) -> Dict:
        """
        Close an existing position
        
        Args:
            deal_id: The deal ID to close
        
        Returns:
            Deal reference and confirmation
        """
        # Get position details first
        position = await self.get_position(deal_id)
        if not position:
            logger.error(f"❌ Position {deal_id} not found")
            return {}
        
        url = f"{self.base_url}/positions/otc"
        
        # Close payload (opposite direction)
        payload = {
            'dealId': deal_id,
            'direction': 'SELL' if position['position']['direction'] == 'BUY' else 'BUY',
            'orderType': 'MARKET',
            'size': position['position']['dealSize'],
            'timeInForce': 'EXECUTE_AND_ELIMINATE'
        }
        
        try:
            headers = self._get_headers()
            headers['_method'] = 'DELETE'
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Position closed: {deal_id}")
                    return data
                else:
                    logger.error(f"❌ Close position failed (Status {response.status}): {response_text}")
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
                    positions = data.get('positions', [])
                    logger.debug(f"Open positions: {len(positions)}")
                    return positions
                else:
                    error = await response.text()
                    logger.error(f"❌ Get positions error: {error}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Get positions exception: {e}")
            return []
    
    async def get_position(self, deal_id: str) -> Optional[Dict]:
        """Get specific position details by deal ID"""
        positions = await self.get_positions()
        
        for position in positions:
            if position.get('position', {}).get('dealId') == deal_id:
                return position
        
        logger.warning(f"Position {deal_id} not found")
        return None
    
    async def shutdown(self):
        """Shutdown API connection"""
        if self.session:
            await self.session.close()
            self.authenticated = False
        logger.info("✅ IG Markets API disconnected")
