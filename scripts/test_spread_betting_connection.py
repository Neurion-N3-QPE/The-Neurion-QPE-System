import asyncio
import logging
from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config

logging.basicConfig(level=logging.DEBUG)

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
        print(f"✅ Account info: {account_info}")
        
        # Check account type
        if account_info and account_info.get('accounts'):
            for acc in account_info['accounts']:
                if acc.get('accountId') == ig_config['account_id']:
                    account_type = acc.get('accountType', 'Unknown')
                    print(f"✅ Account type: {account_type}")
                    if 'SPREAD' not in account_type.upper():
                        print("⚠️ Warning: Account may not be spread betting")
        
        # Test market data with spread betting EPIC
        epic = 'CS.D.GBPUSD.TODAY.SPR'  # Force spread betting EPIC
        print(f"Using EPIC for test: {epic}")
        market_data = await api.get_market_data(epic)
        if market_data:
            print(f"✅ Market data for {epic}: Available")
            snapshot = market_data.get('snapshot', {})
            print(f"   Bid: {snapshot.get('bid')}, Offer: {snapshot.get('offer')}")
        else:
            print(f"❌ No market data for {epic}")
    
        # Test small position opening
        print(f"Testing small position opening for EPIC: {epic} ...")
        test_trade = await api.open_position(
            epic=epic,
            direction='BUY',
            size=1.0  # Small size for testing
        )
    
        if test_trade and test_trade.get('dealReference'):
            print(f"✅ Test trade successful: {test_trade['dealReference']}")
        
            # Close test position immediately
            await asyncio.sleep(2)
            close_result = await api.close_position(test_trade['dealReference'])
            if close_result:
                print("✅ Test position closed")
        else:
            print(f"❌ Test trade failed: {test_trade}")
        
        await api.shutdown()
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_spread_betting_connection())
