"""Proxy for experience: wallet age (first-ever tx) at the coin drop (2021-11-29)
and lifetime tx count (nonce). New-to-space = wallet created near the drop.
"""
import os, time, json, requests
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
import sys; sys.path.insert(0, str(Path(__file__).parents[2]))
from scripts.config import MINT_PRICES
from scripts import econ

KEY = os.environ["ETHERSCAN_API_KEY"]
BASE = "https://api.etherscan.io/v2/api"
ZERO = econ.ZERO
DROP = datetime(2021, 11, 29, tzinfo=timezone.utc)


def get(params, tries=5):
    params.update({"chainid": 1, "apikey": KEY})
    for _ in range(tries):
        time.sleep(0.4)
        d = requests.get(BASE, params=params, timeout=30).json()
        r = d.get("result")
        if isinstance(r, str) and "rate limit" in r.lower():
            time.sleep(1.0); continue
        return d
    return {}


def first_tx_and_count(w):
    d = get({"module": "account", "action": "txlist", "address": w,
             "startblock": 0, "endblock": 99999999, "page": 1, "offset": 1, "sort": "asc"})
    res = d.get("result") or []
    first_ts = int(res[0]["timeStamp"]) if res else 0
    n = get({"module": "proxy", "action": "eth_getTransactionCount",
             "address": w, "tag": "latest"}).get("result", "0x0")
    count = int(n, 16) if isinstance(n, str) else 0
    return first_ts, count


# Build groups from cached data
d = Path(__file__).parents[2] / "data" / "raw"
t = json.load(open(d / "coin_tokens_transfers.json"));  [r.__setitem__("collection", "coin_tokens") for r in t]
mv = json.load(open(d / "coin_tokens_mintvalues.json"))
sales = json.load(open(d / "coin_tokens_sales.json"));  [s.__setitem__("collection", "coin_tokens") for s in sales]
mint_cost = econ.mint_cost_per_token(t, mv, MINT_PRICES.get("coin_tokens"))
pnl = econ.wallet_pnl(t, mint_cost, sales, {"coin_tokens": 0.00487})

wl = set()
for r in t:
    if r["from"] == ZERO:
        c = mint_cost.get(("coin_tokens", str(r["token_id"])), 0.0)
        if 0 < c <= 0.11:
            wl.add(r["to"])

# Group A: top whitelist-insider realized gainers
insiders = sorted(((w, v["realized_pnl_eth"]) for w, v in pnl.items()
                   if w in wl and v["realized_pnl_eth"] > 0), key=lambda x: -x[1])[:25]
# Group B: top secondary buyers still holding (bought high, never minted)
buyers = sorted(((w, v["unrealized_loss"]) for w, v in pnl.items()
                 if w not in wl and v["tokens_held"] > 0 and v["eth_spent"] > 0),
                key=lambda x: -x[1])[:25]


def summarize(label, group):
    ages, counts, newbies = [], [], 0
    for w, _ in group:
        ts, cnt = first_tx_and_count(w)
        if ts:
            age_days = (DROP - datetime.fromtimestamp(ts, tz=timezone.utc)).days
            ages.append(age_days)
            if age_days < 60:
                newbies += 1
        counts.append(cnt)
    ages.sort()
    print(f"\n{label} (n={len(group)}):")
    print(f"  median wallet age at drop: {ages[len(ages)//2]} days "
          f"({ages[len(ages)//2]/365:.1f} yr) | created <60d before drop: {newbies}/{len(group)}")
    print(f"  median lifetime tx count: {sorted(counts)[len(counts)//2]}")


print("Fetching wallet histories (rate-limited)…")
summarize("GROUP A — whitelist-insider top sellers", insiders)
summarize("GROUP B — secondary buyers now underwater", buyers)
