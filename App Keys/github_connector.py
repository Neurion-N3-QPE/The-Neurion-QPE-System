import jwt
import time
import requests
import os
import base64

# ---- Fill in from Dashlane -------------------------------------
APP_ID = "2206305"
INSTALLATION_ID = "92283991"
PEM_PATH = r"F:\Neurion QPE\App Keys\neurion-ai-integrator.2025-10-30.private-key.pem"
# ---------------------------------------------------------------

# 1️⃣  Build a short-lived JWT (10 min)
with open(PEM_PATH, "r") as f:
    private_key = f.read()

now = int(time.time())
payload = {"iat": now, "exp": now + 600, "iss": APP_ID}
jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

# 2️⃣  Exchange JWT → installation token
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Accept": "application/vnd.github+json"
}
url = f"https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens"
resp = requests.post(url, headers=headers)
resp.raise_for_status()
access_token = resp.json()["token"]
print("✅ Access token acquired (valid 1 hour)")

# 3️⃣  Use that token in API calls
api_headers = {
    "Authorization": f"token {access_token}",
    "Accept": "application/vnd.github+json"
}

# 4️⃣  Read a file from the repo
OWNER = "Neurion-N3-QPE"               # your GitHub username
REPO  = "The-Neurion-QPE-System"       # repo slug, not the full URL
FILE  = "README.md"                    # path within the repo

url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FILE}"
r = requests.get(url, headers=api_headers)
r.raise_for_status()
data = r.json()

file_text = base64.b64decode(data["content"]).decode("utf-8")
print(f"\n✅ Retrieved {FILE} from {OWNER}/{REPO}\n{'-'*60}\n")
print(file_text[:500])  # show first 500 chars
