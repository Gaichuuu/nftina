"""Spike: does the Alchemy key return getNFTSales + getFloorPrice for a MetaZoo
contract? Capture real shapes + the fields composing a sale's total price.
"""
import os, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
KEY = os.environ["ALCHEMY_API_KEY"]
BASE = f"https://eth-mainnet.g.alchemy.com/nft/v3/{KEY}"
COIN = "0x2d366be8fa4d15c289964dd4adf7be6cc5e896e8"
FIX = Path(__file__).parents[2] / "tests" / "fixtures"


def get(path, params):
    r = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    print(f"{path} -> HTTP {r.status_code}")
    return r


rs = get("getNFTSales", {"contractAddress": COIN, "order": "asc", "limit": 100})
if rs.ok:
    sales = rs.json()
    (FIX / "alchemy_sales_coin_tokens.json").write_text(json.dumps(sales, indent=2))
    print("top-level keys:", list(sales.keys()))
    arr = sales.get("nftSales", [])
    print(f"nftSales count: {len(arr)}")
    if arr:
        s0 = arr[0]
        print("sample sale keys:", list(s0.keys()))
        for f in ("sellerFee", "royaltyFee", "protocolFee", "marketplaceFee"):
            if f in s0:
                print(f"  {f}: {s0[f]}")
else:
    print("body:", rs.text[:300])

rf = get("getFloorPrice", {"contractAddress": COIN})
if rf.ok:
    floor = rf.json()
    (FIX / "alchemy_floor_coin_tokens.json").write_text(json.dumps(floor, indent=2))
    print("floor payload:", json.dumps(floor, indent=2)[:400])
else:
    print("body:", rf.text[:300])
