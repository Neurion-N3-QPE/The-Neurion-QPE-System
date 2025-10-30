import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config

async def test_epics():
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
    print("Authenticated successfully")
    
    # Get account info
    account_info = await api.get_account_info()
    print(f"\nAccount Info:")
    print(f"  Accounts: {len(account_info.get('accounts', []))}")
    if account_info.get('accounts'):
        for acc in account_info['accounts']:
            print(f"    ID: {acc.get('accountId')}")
            print(f"    Name: {acc.get('accountName')}")
            print(f"    Type: {acc.get('accountType')}")
            if acc.get('balance'):
                print(f"    Balance: {acc['balance'].get('balance')} {acc['balance'].get('currency')}")
    
    # Test various epics
    test_epics = [
        'CS.D.GBPUSD.TODAY.SPR',  # GBP/USD spread betting
        'CS.D.GBPUSD.TODAY.IP',   # Alternative
        'CS.D.GBPUSD.MINI.IP',    # Mini contract
        'IX.D.FTSE.TODAY.IP',     # FTSE index
        'IX.D.SPTRD.TODAY.IP',    # S&P500
    ]
    
    print("\n\nTesting EPICs:")
    for epic in test_epics:
        print(f"\n  Testing {epic}...")
        market_data = await api.get_market_data(epic)
        if market_data and market_data.get('snapshot'):
            snapshot = market_data['snapshot']
            print(f"    AVAILABLE - Bid: {snapshot.get('bid')}, Offer: {snapshot.get('offer')}")
        else:
            print(f"    NOT AVAILABLE")
    
    await api.shutdown()

if __name__ == "__main__":
    asyncio.run(test_epics())
