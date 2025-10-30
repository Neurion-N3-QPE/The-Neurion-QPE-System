import asyncio
import os
import sys
from dotenv import load_dotenv

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
from integrations.ig_markets_api import IGMarketsAPI

async def check_account():
    api = IGMarketsAPI(
        api_key=os.getenv('IG_MARKETS_API_KEY'),
        username=os.getenv('IG_MARKETS_USERNAME'),
        password=os.getenv('IG_MARKETS_PASSWORD'),
        account_id=os.getenv('IG_MARKETS_ACCOUNT_ID'),
        demo=False
    )
    await api.initialize()
    
    # Get account info
    account_info = await api.get_account_info()
    
    if account_info and 'accounts' in account_info:
        for acc in account_info['accounts']:
            if acc.get('accountId') == os.getenv('IG_MARKETS_ACCOUNT_ID'):
                balance_info = acc.get('balance', {})
                print(f"\n💰 Account Balance Info:")
                print(f"  Total Balance: £{balance_info.get('balance', 0):.2f}")
                print(f"  Available: £{balance_info.get('available', 0):.2f}")
                print(f"  Deposit: £{balance_info.get('deposit', 0):.2f}")
                print(f"  Profit/Loss: £{balance_info.get('profitLoss', 0):.2f}")
                break
    
    # Get positions
    positions = await api.get_positions()
    if isinstance(positions, list):
        print(f"\n📊 Open Positions: {len(positions)}")
    else:
        print(f"\n📊 Open Positions: {len(positions.get('positions', []))}")
    
    await api.close_session()

asyncio.run(check_account())
