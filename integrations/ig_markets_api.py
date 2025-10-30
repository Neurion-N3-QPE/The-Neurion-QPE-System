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

    async def close_session(self):
        """
        Close the aiohttp client session.
        """
        if self.session:
            await self.session.close()
            logger.info("✅ Client session closed")

    async def initialize(self):
        """
        Initialize API connection and authenticate.
        """
        logger.info("🔌 Connecting to IG Markets API...")

        # Create session
        self.session = aiohttp.ClientSession()

        try:
            # Authenticate
            await self._authenticate()
            logger.info(f"✅ Connected to IG Markets ({'DEMO' if self.demo else 'LIVE'})")
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            await self.close_session()
            raise

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
        headers['Version'] = '1'  # Use Version 1 for accounts endpoint
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Account info: {data}")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"❌ Account info error (Status {response.status}): {error}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Get account error: {e}")
            return {}
    
    async def get_market_data(self, epic: str) -> Dict:
        """Get market data for an instrument"""
        url = f"{self.base_url}/markets/{epic}"
        headers = self._get_headers()
        headers['Version'] = '3'  # Use Version 3 for markets endpoint
        logger.debug(f"Getting market data for {epic}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Market data for {epic}: {data}")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"❌ Market data error (Status {response.status}): {error}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Get market data error: {e}")
            return {}

    async def verify_trade_status(self, deal_reference: str) -> Dict:
        """
        Verify the status of a trade using the deal reference.

        Args:
            deal_reference: The deal reference returned when opening a position.

        Returns:
            Trade status details including dealStatus and reason.
        """
        url = f"{self.base_url}/confirms/{deal_reference}"
        headers = self._get_headers()
        headers['Version'] = '1'  # Use Version 1 for confirms

        try:
            async with self.session.get(url, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"Trade status response: {response_text}")

                if response.status == 200:
                    data = await response.json()
                    deal_status = data.get('dealStatus', 'UNKNOWN')
                    reason = data.get('reason', '')
                    
                    logger.info(f"Deal Status: {deal_status}")
                    if reason:
                        logger.info(f"Reason: {reason}")
                    
                    # Check if deal was accepted
                    if deal_status == 'ACCEPTED':
                        logger.info(f"✅ Trade ACCEPTED: {data}")
                        return data
                    else:
                        logger.error(f"❌ Trade {deal_status}: {reason}")
                        return {}
                        
                elif response.status == 404:
                    # Deal not found yet - might be processing
                    logger.warning(f"⚠️ Deal not found (might be processing): {deal_reference}")
                    return {}
                else:
                    logger.error(f"❌ Trade status check failed (Status {response.status}): {response_text}")
                    return {}

        except Exception as e:
            logger.error(f"❌ Trade status verification exception: {e}")
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
            epic: Market epic code (e.g., 'IX.D.SPTRD.DAILY.IP')
            direction: 'BUY' or 'SELL'
            size: Position size in GBP per point
            stop_loss: Optional stop loss level
            take_profit: Optional take profit level
        
        Returns:
            Deal reference and confirmation
        """
        url = f"{self.base_url}/positions/otc"
        
        # Spread betting payload - Include expiry field for DFB (Daily Funded Bets)
        # DFB = Spread Betting without fixed expiry (rolls daily)
        # Ensure size is rounded to 1 decimal place (IG Markets requirement for spread betting)
        rounded_size = round(float(size), 1)  # Round to 1 decimal place
        # Don't enforce a minimum - let the API reject if too small
        # IG Markets minimum varies by instrument, typically 0.1-0.5
        
        payload = {
            'epic': epic,
            'direction': direction.upper(),  # BUY or SELL
            'size': rounded_size,
            'orderType': 'MARKET',
            'guaranteedStop': False,
            'forceOpen': True,
            'currencyCode': 'GBP',
            'timeInForce': 'FILL_OR_KILL',
            'expiry': 'DFB'  # Daily Funded Bet - NO FIXED EXPIRY (Spread Betting)
        }
        
        logger.info(f"Payload for opening position: {payload}")

        # Add stop loss if provided
        if stop_loss:
            payload['stopLevel'] = float(stop_loss)
        
        # Add take profit if provided  
        if take_profit:
            payload['limitLevel'] = float(take_profit)
        
        headers = self._get_headers()
        logger.info(f"Opening {direction} position for {epic}: £{rounded_size} per point")
        logger.debug(f"Payload: {payload}")
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"API Response: {response_text}")

                if response.status == 200:
                    data = await response.json()
                    deal_ref = data.get('dealReference')
                    logger.info(f"✅ Position opened: {deal_ref}")

                    # Verify trade status
                    trade_status = await self.verify_trade_status(deal_ref)
                    if trade_status:
                        logger.info(f"✅ Trade confirmed: {trade_status}")
                    else:
                        logger.error("❌ Trade confirmation failed")

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
        
        # Use DELETE method with deal ID in payload
        url = f"{self.base_url}/positions/otc"
        
        payload = {
            'dealId': deal_id,
            'direction': 'SELL' if position['position']['direction'] == 'BUY' else 'BUY',
            'orderType': 'MARKET',
            'size': position['position']['size'],
            'timeInForce': 'FILL_OR_KILL'
        }
        
        try:
            headers = self._get_headers()
            headers['_method'] = 'DELETE'
            headers['Version'] = '1'
            
            logger.info(f"Closing position {deal_id} with payload: {payload}")
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"Close response ({response.status}): {response_text}")
                
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Position closed: {deal_id}")
                    return data
                else:
                    logger.error(f"❌ Close position failed (Status {response.status}): {response_text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Close position exception: {e}", exc_info=True)
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

    async def get_trade_history(self, days: int = 7) -> Dict:
        """
        Retrieve trade history for the account.

        Args:
            days: Number of days to look back for trade history.

        Returns:
            Trade history details.
        """
        url = f"{self.base_url}/history/transactions?from={datetime.now().isoformat()}&to={datetime.now().isoformat()}&type=ALL"
        headers = self._get_headers()

        try:
            async with self.session.get(url, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"Trade history response: {response_text}")

                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Trade history retrieved: {data}")
                    return data
                else:
                    logger.error(f"❌ Trade history retrieval failed (Status {response.status}): {response_text}")
                    return {}
        except Exception as e:
            logger.error(f"❌ Trade history retrieval exception: {e}")
            return {}

    async def shutdown(self):
        """
        Shutdown the API connection.
        """
        await self.close_session()
        logger.info("✅ IG Markets API shutdown complete")
