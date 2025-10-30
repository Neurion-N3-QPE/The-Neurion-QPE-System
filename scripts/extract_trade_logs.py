import json, sys, os
from datetime import datetime

date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
path = f"data/trades/{date}.json"

if not os.path.exists(path):
    print(f"No trade log found for {date}")
    sys.exit()

with open(path, "r") as f:
    data = json.load(f)

for t in data.get("trades", []):
    print(f"""
📈 TRADE VERIFIED
---------------------
Deal ID: {t.get('dealId')}
Asset: {t.get('epic')}
Direction: {t.get('direction')}
Size: {t.get('size')}
Open Level: {t.get('openLevel')}
Close Level: {t.get('closeLevel')}
Profit: £{t.get('profit')}
Executed By: {t.get('agent')}
Timestamp: {t.get('timestamp')}
---------------------
""")