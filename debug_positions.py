import asyncio
import os
import sys
from dotenv import load_dotenv
import json

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
from integrations.ig_markets_api import IGMarketsAPI

async def debug_positions():
    api = IGMarketsAPI(
        api_key=os.getenv('IG_MARKETS_API_KEY'),
        username=os.getenv('IG_MARKETS_USERNAME'),
        password=os.getenv('IG_MARKETS_PASSWORD'),
        account_id=os.getenv('IG_MARKETS_ACCOUNT_ID'),
        demo=False
    )
    await api.initialize()
    
    print("\n=== Checking get_positions() response ===")
    positions = await api.get_positions()
    print(f"Type: {type(positions)}")
    print(f"Content: {json.dumps(positions, indent=2)}")
    
    # Try to close the US 500 position we see in the UI
    if isinstance(positions, dict) and 'positions' in positions:
        for pos_data in positions['positions']:
            deal_id = pos_data['position']['dealId']
            print(f"\n🔄 Closing position: {deal_id}")
            result = await api.close_position(deal_id)
            print(f"Result: {result}")
    elif isinstance(positions, list):
        print(f"Positions is a list with {len(positions)} items")
        for pos_data in positions:
            if 'position' in pos_data:
                deal_id = pos_data['position']['dealId']
                print(f"\n🔄 Closing position: {deal_id}")
                result = await api.close_position(deal_id)
                print(f"Result: {result}")
    
    await api.close_session()

asyncio.run(debug_positions())
