"""Method: Alchemy `getNFTSales` with `buyerAddress` = each Aoki wallet gives every NFT
purchase (contract, tokenId, price, block). Block→date via Etherscan; USD via Binance
daily close. Aggregates by collection, top single buys, and a monthly timeline (so the
overlap with MetaZoo inflows — e.g. the Jan-2022 89.77 ETH payment — is visible).

Usage: python -m scripts.trace_acquisitions
Outputs: public/data/acquisitions.json + data/raw/acquisitions_raw.json (gitignored).
"""
import os
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
from scripts.config import AOKI_WALLETS

RAW = Path(__file__).parent.parent / "data" / "raw"
OUT = Path(__file__).parent.parent / "public" / "data"
ALCHEMY = f"https://eth-mainnet.g.alchemy.com/nft/v3/{os.environ.get('ALCHEMY_API_KEY','')}"
ES = "https://api.etherscan.io/v2/api"
EK = os.environ.get("ETHERSCAN_API_KEY", "")
METAZOO_INFLOWS = {"2022-01": 89.77}


def _fee(f):
    if not f or not f.get("amount"):
        return 0.0, None
    dec = f.get("decimals")
    dec = 18 if dec is None else int(dec)
    try:
        return int(f["amount"]) / (10 ** dec), (f.get("symbol") or "").upper()
    except (ValueError, TypeError):
        return 0.0, None


def fetch_purchases(wallet: str) -> list:
    """Every NFT sale where `wallet` was the buyer (paginated)."""
    out, page_key = [], None
    while True:
        params = {"buyerAddress": wallet, "limit": 1000, "order": "asc"}
        if page_key:
            params["pageKey"] = page_key
        r = requests.get(f"{ALCHEMY}/getNFTSales", params=params, timeout=40).json()
        for s in r.get("nftSales", []):
            price, sym = _fee(s.get("sellerFee"))
            roy, _ = _fee(s.get("royaltyFee"))
            proto, _ = _fee(s.get("protocolFee"))
            out.append({
                "contract": (s.get("contractAddress") or "").lower(),
                "token_id": str(s.get("tokenId")),
                "eth": round(price + roy + proto, 6) if sym in ("ETH", "WETH") else 0.0,
                "currency": sym or "other",
                "block": int(s.get("blockNumber", 0)),
                "marketplace": s.get("marketplace", ""),
            })
        page_key = r.get("pageKey")
        if not page_key:
            break
    return out


def _es(params):
    for _ in range(5):
        time.sleep(0.2)
        try:
            r = requests.get(ES, params={**params, "chainid": 1, "apikey": EK}, timeout=30).json()
            res = r.get("result")
            if isinstance(res, str) and "rate limit" in res.lower():
                time.sleep(1); continue
            return res
        except requests.RequestException:
            time.sleep(1)
    return None


def resolve_block_dates(blocks) -> dict:
    """block number -> 'YYYY-MM-DD' (cached to data/raw/block_dates.json)."""
    cache_p = RAW / "block_dates.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    todo = [b for b in blocks if str(b) not in cache]
    for i, b in enumerate(todo):
        res = _es({"module": "block", "action": "getblockreward", "blockno": b})
        ts = int(res["timeStamp"]) if isinstance(res, dict) and res.get("timeStamp") else None
        cache[str(b)] = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else None
        if i % 100 == 0:
            cache_p.write_text(json.dumps(cache)); print(f"  resolved {i}/{len(todo)} block dates…")
    cache_p.write_text(json.dumps(cache))
    return cache


def eth_daily_usd() -> dict:
    """Binance daily ETH/USD close, 2021-01-01 through today (cached). Task 7
    extended the original 2021-2024 range: the treasury audit's tx history runs
    past 2024 (small ongoing royalty trickle into 2025/2026), and usd_at_date's
    "current price" residual mark needs a real up-to-date close, not a stale
    2024-12-31 fallback."""
    cache_p = RAW / "eth_usd_daily.json"
    if cache_p.exists():
        return json.loads(cache_p.read_text())
    out = {}
    this_year = datetime.now(tz=timezone.utc).year
    for yr in range(2021, this_year + 1):
        start = f"{yr}-01-01"
        end = f"{yr}-12-31" if yr < this_year else datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        s = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
        e = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
        r = requests.get("https://api.binance.com/api/v3/klines",
                         params={"symbol": "ETHUSDT", "interval": "1d", "startTime": s,
                                 "endTime": e, "limit": 1000}, timeout=30).json()
        for k in r:
            out[datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")] = float(k[4])
    cache_p.write_text(json.dumps(out))
    return out


def collection_name(contract: str, cache: dict) -> str:
    if contract in cache:
        return cache[contract]
    try:
        r = requests.get(f"{ALCHEMY}/getContractMetadata",
                         params={"contractAddress": contract}, timeout=20).json()
        name = r.get("name") or (r.get("openSeaMetadata") or {}).get("collectionName") or contract[:10]
    except requests.RequestException:
        name = contract[:10]
    cache[contract] = name
    return name


def build_output(purchases: list, ncache: dict) -> dict:
    """Pure assembly of the acquisitions.json shape from already-priced
    `purchases` (each carrying contract/token_id/eth/usd/date/marketplace) and
    a contract->name cache. No network I/O beyond `collection_name`'s cache
    hit path (a miss falls back to a live Alchemy lookup, so callers pre-warm
    `ncache` when they want this fully offline)."""
    by_collection = defaultdict(lambda: {"n": 0, "eth": 0.0, "usd": 0.0})
    by_month = defaultdict(lambda: {"n": 0, "eth": 0.0})
    for p in purchases:
        c = by_collection[p["contract"]]
        c["n"] += 1; c["eth"] += p["eth"]; c["usd"] += p.get("usd", 0.0)
        d = p.get("date")
        if d:
            m = d[:7]
            by_month[m]["n"] += 1; by_month[m]["eth"] += p["eth"]

    collections = []
    for c, agg in sorted(by_collection.items(), key=lambda x: -x[1]["eth"]):
        collections.append({"contract": c, "name": collection_name(c, ncache),
                            "purchases": agg["n"], "eth": round(agg["eth"], 2),
                            "usd": round(agg["usd"], 2)})
    top_items = sorted(purchases, key=lambda x: -x["eth"])[:25]
    for t in top_items:
        t["name"] = collection_name(t["contract"], ncache)
    timeline = [{"month": m, "purchases": by_month[m]["n"], "eth": round(by_month[m]["eth"], 2),
                 "metazoo_inflow_eth": METAZOO_INFLOWS.get(m, 0.0)}
                for m in sorted(by_month)]

    total_eth = round(sum(c["eth"] for c in collections), 2)
    total_usd = round(sum(c["usd"] for c in collections), 2)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": ("Acquisition ledger of Aoki's NFT-buying wallets — what the ETH that "
                 "reached them was spent on. Aoki's own buying dwarfs MetaZoo's ~210 ETH "
                 "payments (which commingled here); ETH is fungible, so no single NFT is "
                 "attributed to MetaZoo money. Figures are ETH/WETH-settled purchases."),
        "wallets": [w.lower() for w in AOKI_WALLETS],
        "total_purchases": len(purchases),
        "total_eth": total_eth,
        "total_usd": total_usd,
        "by_collection": collections,
        "top_items": [{"name": t["name"], "token_id": t["token_id"],
                       "contract": t["contract"],
                       "eth": t["eth"], "usd": round(t["usd"], 2),
                       "date": t["date"], "marketplace": t["marketplace"]}
                      for t in top_items],
        "monthly_timeline": timeline,
    }


def build() -> dict:
    purchases = []
    for w in AOKI_WALLETS:
        p = fetch_purchases(w.lower())
        print(f"  {w[:12]}: {len(p)} purchases")
        purchases.extend(p)
    (RAW / "acquisitions_raw.json").write_text(json.dumps(purchases, indent=2))

    dates = resolve_block_dates(sorted({p["block"] for p in purchases}))
    prices = eth_daily_usd()
    last_price = list(prices.values())[-1]
    ncache: dict = {}

    for p in purchases:
        d = dates.get(str(p["block"]))
        usd = p["eth"] * prices.get(d, last_price) if d else 0.0
        p["date"], p["usd"] = d, usd

    result = build_output(purchases, ncache)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "acquisitions.json").write_text(json.dumps(result, indent=2))
    print(f"\n  {result['total_purchases']} purchases | {result['total_eth']} ETH = ${result['total_usd']:,.0f}")
    print("  top collections bought:")
    for c in result["by_collection"][:8]:
        print(f"    {c['eth']:8.1f} ETH  ${c['usd']:>12,.0f}  {c['purchases']:3d}x  {c['name']}")
    print("  -> public/data/acquisitions.json")
    return result


if __name__ == "__main__":
    if not os.environ.get("ALCHEMY_API_KEY") or not EK:
        raise SystemExit("ALCHEMY_API_KEY and ETHERSCAN_API_KEY required")
    build()
