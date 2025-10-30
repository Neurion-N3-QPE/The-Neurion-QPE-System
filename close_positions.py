import asyncio
import os
import sys
from dotenv import load_dotenv

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
from integrations.ig_markets_api import IGMarketsAPI

async def close_old_position():
    api = IGMarketsAPI(
        api_key=os.getenv('IG_MARKETS_API_KEY'),
        username=os.getenv('IG_MARKETS_USERNAME'),
        password=os.getenv('IG_MARKETS_PASSWORD'),
        account_id=os.getenv('IG_MARKETS_ACCOUNT_ID'),
        demo=False
    )
    await api.initialize()
    
    # Get current positions
    positions = await api.get_positions()
    
    if positions and 'positions' in positions and len(positions['positions']) > 0:
        print(f"\n📊 Found {len(positions['positions'])} open position(s)")
        
        for pos_data in positions['positions']:
            deal_id = pos_data['position']['dealId']
            size = pos_data['position']['size']
            direction = pos_data['position']['direction']
            level = pos_data['position']['level']
            epic = pos_data['market']['epic']
            
            print(f"\nPosition: {deal_id}")
            print(f"  Epic: {epic}")
            print(f"  Direction: {direction}")
            print(f"  Size: £{size}/point")
            print(f"  Entry: {level}")
            
            print(f"\n🔄 Closing position {deal_id}...")
            result = await api.close_position(deal_id)
            
            if result and result.get('dealReference'):
                print(f"✅ Position closed! Deal reference: {result['dealReference']}")
            else:
                print(f"❌ Failed to close position")
    else:
        print("✅ No open positions found")
    
    await api.close_session()

asyncio.run(close_old_position())
