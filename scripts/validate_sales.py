"""Validate that each Alchemy-reported sale actually settled on-chain.

Usage:
    python -m scripts.validate_sales                      # all collections
    python -m scripts.validate_sales --contract aoki
    python -m scripts.validate_sales --threshold 1.0
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

API = "https://api.etherscan.io/v2/api"
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RAW = Path(__file__).parent.parent / "data" / "raw"


def _get(params: dict, api_key: str, retries: int = 5):
    for i in range(retries):
        try:
            r = requests.get(API, params={**params, "chainid": 1, "apikey": api_key},
                             timeout=30).json()
            res = r.get("result")
            if isinstance(res, str) and "rate limit" in res.lower():
                time.sleep(1.0 * (i + 1)); continue
            return res
        except requests.RequestException:
            time.sleep(0.5 * (i + 1))
    return None


def settlement_eth(tx_hash: str, api_key: str):
    """Real ETH + WETH that changed hands in the sale tx. Uses tx.value for ETH-settled
    sales and the largest single WETH Transfer for offer-accepted (WETH) sales."""
    tx = _get({"module": "proxy", "action": "eth_getTransactionByHash", "txhash": tx_hash}, api_key)
    if tx is None:
        return None
    eth = int(tx.get("value", "0x0"), 16) / 1e18 if tx.get("value") else 0.0
    time.sleep(0.34)
    rc = _get({"module": "proxy", "action": "eth_getTransactionReceipt", "txhash": tx_hash}, api_key)
    if rc is None:
        return None
    max_weth = 0.0
    for lg in (rc.get("logs") or []):
        if lg["address"].lower() == WETH and lg["topics"] and lg["topics"][0].lower() == TRANSFER_TOPIC:
            try:
                max_weth = max(max_weth, int(lg["data"], 16) / 1e18)
            except (ValueError, KeyError):
                pass
    time.sleep(0.34)
    return eth + max_weth


def validate(key: str, threshold: float, api_key: str) -> None:
    p = RAW / f"{key}_sales.json"
    if not p.exists():
        return
    sales = json.loads(p.read_text())
    to_check = [s for s in sales if s.get("price_eth", 0.0) >= threshold and "settled_eth" not in s]
    print(f"[{key}] {len(sales)} sales | {len(to_check)} at >= {threshold} ETH to validate")
    done = 0
    for s in sales:
        if s.get("price_eth", 0.0) < threshold:
            s.setdefault("settled_eth", round(s.get("price_eth", 0.0), 4))
            s.setdefault("is_phantom", False)
            continue
        if "settled_eth" in s:
            continue
        settled = settlement_eth(s["hash"], api_key)
        if settled is None:
            continue
        s["settled_eth"] = round(settled, 4)
        s["is_phantom"] = settled < 0.5 * s["price_eth"]
        done += 1
        if done % 25 == 0:
            p.write_text(json.dumps(sales, indent=2))
            print(f"  {key}: {done}/{len(to_check)} validated…")
    p.write_text(json.dumps(sales, indent=2))
    phantom = [s for s in sales if s.get("is_phantom")]
    ph_vol = sum(s["price_eth"] for s in phantom)
    real_vol = sum(s["price_eth"] for s in sales if not s.get("is_phantom"))
    print(f"[{key}] phantom: {len(phantom)} sales / {ph_vol:.1f} ETH removed | "
          f"real volume {real_vol:.1f} ETH")


def main() -> None:
    ap = argparse.ArgumentParser(description="Flag Alchemy sales that never settled on-chain")
    ap.add_argument("--contract", help="single collection key")
    ap.add_argument("--threshold", type=float, default=1.0,
                    help="only validate sales at/above this ETH price (default 1.0)")
    args = ap.parse_args()

    api_key = os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        print("ERROR: ETHERSCAN_API_KEY not set"); sys.exit(1)

    if args.contract:
        keys = [args.contract]
    else:
        keys = [f.name.replace("_sales.json", "") for f in sorted(RAW.glob("*_sales.json"))]

    for key in keys:
        validate(key, args.threshold, api_key)
    print("\nDone. Re-run: python -m scripts.analyze")


if __name__ == "__main__":
    main()
