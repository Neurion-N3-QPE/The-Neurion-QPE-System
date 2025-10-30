"""
Test actual position opening with detailed error handling
"""
import asyncio
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config


async def test_position():
    config = load_config()
    ig_config = config['brokers']['ig_markets']
    
    api = IGMarketsAPI(
        api_key=ig_config['api_key'],
        username=ig_config['username'],
        password=ig_config['password'],
        account_id=ig_config['account_id'],
        demo=ig_config.get('demo', False)
    )
    
    await api.initialize()
    
    print(f"\n{'='*60}")
    print("TESTING POSITION OPENING")
    print(f"{'='*60}\n")
    
    # First, check if market is tradeable
    epic = 'IX.D.SPTRD.DAILY.IP'
    print(f"1. Checking market: {epic}")
    
    market_data = await api.get_market_data(epic)
    if market_data:
        print(f"   OK Market Status: {market_data.get('snapshot', {}).get('marketStatus')}")
        print(f"   OK Bid: {market_data.get('snapshot', {}).get('bid')}")
        print(f"   OK Offer: {market_data.get('snapshot', {}).get('offer')}")
        
        # Check dealing rules
        dealing_rules = market_data.get('dealingRules', {})
        print(f"   OK Min Deal Size: {dealing_rules.get('minDealSize', {})}")
        print(f"   OK Max Deal Size: {dealing_rules.get('maxDealSize', {})}")
        print(f"   OK Min Step: {dealing_rules.get('minStepDistance', {})}")
    
    print(f"\n2. Attempting to open position...")
    
    # Try to open position with very detailed logging
    url = f"{api.base_url}/positions/otc"
    
    payload = {
        'epic': epic,
        'direction': 'BUY',
        'size': 0.5,  # Try minimum size
        'orderType': 'MARKET',
        'guaranteedStop': False,
        'forceOpen': True,
        'currencyCode': 'GBP',
        'timeInForce': 'FILL_OR_KILL',
        'expiry': 'DFB'
    }
    
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    headers = api._get_headers()
    
    async with api.session.post(url, json=payload, headers=headers) as response:
        status = response.status
        text = await response.text()
        
        print(f"\n   Response Status: {status}")
        print(f"   Response Body: {text}")
        
        # Get all response headers
        print(f"\n   Response Headers:")
        for key, value in response.headers.items():
            print(f"      {key}: {value}")
    
    await api.close_session()


if __name__ == "__main__":
    asyncio.run(test_position())
