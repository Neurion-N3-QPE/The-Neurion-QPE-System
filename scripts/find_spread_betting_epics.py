import asyncio
import logging
from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config

logging.basicConfig(level=logging.DEBUG)

async def discover_epics():
    """Discover available spread betting EPICs for your account"""
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
        
        test_epics = [
            "CS.D.GBPUSD.TODAY.SPR", "CS.D.GBPUSD.MINUTE.SPR", "CS.D.GBPUSD.DAILY.SPR", "CS.D.GBPUSD.WEEKLY.SPR", "CS.D.GBPUSD.MONTHLY.SPR", "CS.D.GBPUSD.SPT", "CS.D.GBPUSD.SB",
            "IX.D.FTSE.DAILY.IP", "IX.D.NASDAQ.DAILY.IP", "IX.D.DAX.DAILY.IP", "IX.D.SP500.DAILY.IP", "IX.D.DOW.DAILY.IP",
            "CS.D.GBPUSD.CFD.IP", "CS.D.EURUSD.TODAY.SPR", "CS.D.USDJPY.TODAY.SPR"
        ]
        
        available_epics = []
        
        for epic in test_epics:
            print(f"Testing EPIC: {epic}")
            market_data = await api.get_market_data(epic)
            
            if market_data and market_data.get('snapshot'):
                snapshot = market_data['snapshot']
                print(f"✅ Available: {epic}")
                print(f"   Instrument: {market_data.get('instrument', {}).get('name', 'Unknown')}")
                print(f"   Bid: {snapshot.get('bid')}, Offer: {snapshot.get('offer')}")
                print(f"   Spread: {abs(snapshot.get('offer', 0) - snapshot.get('bid', 0))}")
                available_epics.append(epic)
            else:
                print(f"❌ Not available: {epic}")
            print("-" * 50)
            await asyncio.sleep(1)
        
        print("\n" + "="*60)
        print("📊 DISCOVERY RESULTS:")
        print("="*60)
        for epic in available_epics:
            print(f"✅ {epic}")
        
        if available_epics:
            print(f"\n🎯 Recommended EPIC: {available_epics[0]}")
            print("Update your config.json with this EPIC")
        else:
            print("❌ No spread betting EPICs found. Check account type or contact IG support.")
        
        await api.shutdown()
        return available_epics
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return []

if __name__ == "__main__":
    asyncio.run(discover_epics())
