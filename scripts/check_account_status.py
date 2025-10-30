"""
Check IG Markets account positions and history
"""
import asyncio
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config


async def main():
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
    print(f"IG MARKETS ACCOUNT CHECK")
    print(f"{'='*60}\n")
    
    # 1. Check account info
    print("1. ACCOUNT INFO:")
    account_info = await api.get_account_info()
    print(json.dumps(account_info, indent=2))
    
    # 2. Check open positions
    print(f"\n{'='*60}")
    print("2. OPEN POSITIONS:")
    headers = api._get_headers()
    headers['Version'] = '2'
    
    async with api.session.get(f"{api.base_url}/positions", headers=headers) as response:
        positions_data = await response.json()
        print(json.dumps(positions_data, indent=2))
    
    # 3. Check activity/history
    print(f"\n{'='*60}")
    print("3. RECENT ACTIVITY:")
    headers = api._get_headers()
    headers['Version'] = '3'
    
    async with api.session.get(f"{api.base_url}/history/activity", headers=headers) as response:
        activity_data = await response.json()
        print(json.dumps(activity_data, indent=2))
    
    await api.close_session()


if __name__ == "__main__":
    asyncio.run(main())
