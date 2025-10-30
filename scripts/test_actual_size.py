"""
Test with the actual size being used by autonomous trader
"""
import asyncio
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config


async def test_with_actual_size():
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
    
    # First close the test position
    print("Closing test position...")
    close_url = f"{api.base_url}/positions/otc"
    close_payload = {
        'dealId': 'DIAAAAQCZ7WQ8A4',
        'direction': 'SELL',
        'orderType': 'MARKET',
        'size': 0.5
    }
    headers = api._get_headers()
    headers['_method'] = 'DELETE'
    
    async with api.session.post(close_url, json=close_payload, headers=headers) as response:
        print(f"Close status: {response.status}")
        print(f"Close response: {await response.text()}\n")
    
    await asyncio.sleep(1)
    
    # Now test with size 4.9 (what autonomous trader uses)
    print("="*60)
    print("Testing with size 4.9 (autonomous trader size)")
    print("="*60)
    
    epic = 'IX.D.SPTRD.DAILY.IP'
    
    payload = {
        'epic': epic,
        'direction': 'BUY',
        'size': 4.9,  # Actual size from autonomous trader
        'orderType': 'MARKET',
        'guaranteedStop': False,
        'forceOpen': True,
        'currencyCode': 'GBP',
        'timeInForce': 'FILL_OR_KILL',
        'expiry': 'DFB'
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    url = f"{api.base_url}/positions/otc"
    headers = api._get_headers()
    
    async with api.session.post(url, json=payload, headers=headers) as response:
        status = response.status
        text = await response.text()
        
        print(f"\nResponse Status: {status}")
        print(f"Response Body: {text}")
        
        if status == 200:
            data = await response.json()
            deal_ref = data.get('dealReference')
            
            # Wait and check confirmation
            await asyncio.sleep(2)
            
            print(f"\nChecking deal confirmation for: {deal_ref}")
            conf_url = f"{api.base_url}/confirms/{deal_ref}"
            conf_headers = api._get_headers()
            conf_headers['Version'] = '1'
            
            async with api.session.get(conf_url, headers=conf_headers) as conf_response:
                conf_status = conf_response.status
                conf_text = await conf_response.text()
                
                print(f"Confirmation Status: {conf_status}")
                print(f"Confirmation Response: {conf_text}")
    
    await api.close_session()


if __name__ == "__main__":
    asyncio.run(test_with_actual_size())
