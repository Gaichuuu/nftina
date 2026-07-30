"""Spike: validate Etherscan V2 works with the existing key, capture real
response shapes, and sanity-check the economics premise 
"""
import os, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
KEY = os.environ["ETHERSCAN_API_KEY"]
BASE = "https://api.etherscan.io/v2/api"
COIN = "0x2d366be8fa4d15c289964dd4adf7be6cc5e896e8"
ZERO = "0x0000000000000000000000000000000000000000"
FIX = Path(__file__).parents[2] / "tests" / "fixtures"
FIX.mkdir(parents=True, exist_ok=True)


def get(params):
    params.update({"chainid": 1, "apikey": KEY})
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


# 1. ERC-1155 transfers for coin_tokens (first page)
tx = get({"module": "account", "action": "token1155tx",
          "contractaddress": COIN, "page": 1, "offset": 1000, "sort": "asc"})
print("token1155tx status:", tx.get("status"), "| message:", tx.get("message"))
result = tx.get("result")
if not isinstance(result, list):
    print("UNEXPECTED result:", str(result)[:200])
    raise SystemExit(1)
print("records:", len(result))
print("first record keys:", list(result[0].keys()) if result else "NONE")
(FIX / "etherscan_tokentx_coin_tokens.json").write_text(json.dumps(result[:200], indent=2))

# 2. Reconstruct mint revenue: for each unique mint tx, read the tx value once.
mint_hashes = {r["hash"] for r in result if r.get("from", "").lower() == ZERO}
print(f"unique mint txs in first page: {len(mint_hashes)}")

total_eth = 0.0
sample = []
for i, h in enumerate(sorted(mint_hashes)):
    d = get({"module": "proxy", "action": "eth_getTransactionByHash", "txhash": h})
    res = d.get("result") or {}
    wei = int(res.get("value", "0x0"), 16) if res.get("value") else 0
    eth = wei / 1e18
    total_eth += eth
    if i < 5:
        sample.append({"hash": h, "eth": eth})

print("sample mint tx values:", json.dumps(sample, indent=2))
print(f"\nSUM of mint-tx ETH over first-page mints only: {total_eth:.4f} ETH")
print("(coin_tokens documented ~408 ETH total across the full sale — this is a partial-page sanity check)")
