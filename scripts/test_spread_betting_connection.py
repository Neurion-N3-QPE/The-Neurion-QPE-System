import asyncio
import logging
import pytest
from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config

logging.basicConfig(level=logging.DEBUG)

@pytest.mark.asyncio
async def test_spread_betting_connection():
    config = load_config()
    ig_config = config['brokers']['ig_markets']
    
    api = IGMarketsAPI(
        api_key=ig_config['api_key'],
        username=ig_config['username'], 
        password=ig_config['password'],
        account_id=ig_config['account_id'],
        demo=ig_config.get('demo', True)
    )
    
    try:
        await api.initialize()
        print("✅ Authentication successful")
        
        # Test account info to confirm spread betting account
        account_info = await api.get_account_info()
        assert account_info, "Failed to fetch account info"
        print(f"✅ Account info: {account_info}")
        
        # Check account type
        if account_info and account_info.get('accounts'):
            for acc in account_info['accounts']:
                if acc.get('accountId') == ig_config['account_id']:
                    account_type = acc.get('accountType', 'Unknown')
                    print(f"✅ Account type: {account_type}")
                    assert 'SPREAD' in account_type.upper(), "Account may not be spread betting"
        
        # Test market data with spread betting EPIC
        epic = 'CS.D.GBPUSD.TODAY.SPR'  # Force spread betting EPIC
        market_data = await api.get_market_data(epic)
        assert market_data, f"No market data for {epic}"
        snapshot = market_data.get('snapshot', {})
        print(f"✅ Market data for {epic}: Available")
        print(f"   Bid: {snapshot.get('bid')}, Offer: {snapshot.get('offer')}")
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
