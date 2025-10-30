import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from integrations.ig_markets_api import IGMarketsAPI

async def check_deal():
    api = IGMarketsAPI(
        api_key=os.getenv('IG_MARKETS_API_KEY'),
        username=os.getenv('IG_MARKETS_USERNAME'),
        password=os.getenv('IG_MARKETS_PASSWORD'),
        account_id=os.getenv('IG_MARKETS_ACCOUNT_ID'),
        demo=False
    )
    await api.initialize()
    
    # Check the most recent deal reference from logs
    deal_ref = '8PFUPND82S8TYNK'
    result = await api.verify_trade_status(deal_ref)
    print('\n=== Full Trade Status ===')
    import json
    print(json.dumps(result, indent=2))
    
    # Also check positions
    print('\n=== Current Positions ===')
    positions = await api.get_positions()
    print(json.dumps(positions, indent=2))
    
    await api.close_session()

asyncio.run(check_deal())
