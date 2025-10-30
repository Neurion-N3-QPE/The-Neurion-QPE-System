"""
Check the deal confirmation immediately after placing
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
    
    # Check the most recent deal from test
    deal_ref = "F23ZDBPM24TYNK"
    
    print(f"\nChecking deal: {deal_ref}")
    
    # Wait a moment for processing
    await asyncio.sleep(2)
    
    # Get deal confirmation with all details
    url = f"{api.base_url}/confirms/{deal_ref}"
    headers = api._get_headers()
    headers['Version'] = '1'  # Use version 1 for confirms
    
    async with api.session.get(url, headers=headers) as response:
        status = response.status
        text = await response.text()
        
        print(f"\nStatus: {status}")
        print(f"Response:\n{text}\n")
        
        try:
            data = await response.json()
            print("Parsed JSON:")
            print(json.dumps(data, indent=2))
        except:
            pass
    
    # Also check positions
    print(f"\n{'='*60}")
    print("CURRENT POSITIONS:")
    headers = api._get_headers()
    headers['Version'] = '2'
    
    async with api.session.get(f"{api.base_url}/positions", headers=headers) as response:
        positions_data = await response.json()
        print(json.dumps(positions_data, indent=2))
    
    await api.close_session()


if __name__ == "__main__":
    asyncio.run(main())
