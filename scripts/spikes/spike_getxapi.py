"""Spike: capture the real response shape (where tweets live; field names
for text/date/id). 
"""
import os, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
KEY = os.environ["GETXAPI_KEY"]
BASE = "https://api.getxapi.com"
FIX = Path(__file__).parents[2] / "tests" / "fixtures"
headers = {"Authorization": f"Bearer {KEY}"}

r = requests.get(f"{BASE}/twitter/tweet/advanced_search",
                 params={"query": "from:steveaoki metazoo since:2021-01-01 until:2022-01-01"},
                 headers=headers, timeout=45)
print("HTTP", r.status_code)
try:
    data = r.json()
except Exception:
    print("non-JSON body:", r.text[:300]); raise SystemExit(1)

(FIX / "getxapi_search_2021.json").write_text(json.dumps(data, indent=2))
print("top-level type:", type(data).__name__)
if isinstance(data, dict):
    print("top-level keys:", list(data.keys()))
    for k in ("tweets", "data", "results", "statuses"):
        v = data.get(k)
        if isinstance(v, list) and v:
            print(f"array under {k!r}: {len(v)} items; first item keys: {list(v[0].keys())}")
            print("first item sample:", json.dumps(v[0], indent=2)[:500])
            break
