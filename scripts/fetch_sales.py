"""Fetch secondary sales + floor price for each known contract via Alchemy,
caching to data/raw/<key>_sales.json and <key>_floor.json.

Usage:
    python -m scripts.fetch_sales                 # all contracts with addresses
    python -m scripts.fetch_sales --contract coin_tokens
    python -m scripts.fetch_sales --force
"""
import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
from scripts.config import CONTRACTS
from scripts.clients.alchemy import Alchemy

RAW = Path(__file__).parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)


def save(name: str, data) -> None:
    (RAW / f"{name}.json").write_text(json.dumps(data, indent=2))
    n = len(data) if isinstance(data, list) else 1
    print(f"  saved data/raw/{name}.json ({n} records)")


def fetch_one(al: Alchemy, key: str, meta: dict, force: bool) -> None:
    addr = meta.get("address")
    if not addr or meta.get("standard") == "imx":
        print(f"[skip] {key} — no Ethereum address")
        return
    if (RAW / f"{key}_sales.json").exists() and not force:
        print(f"[skip] {key} — cached (use --force)")
        return
    print(f"[fetch] {meta['name']} — sales + floor")
    sales = al.sales(addr)
    save(f"{key}_sales", sales)
    royalty = round(sum(s["royalty_eth"] for s in sales), 4)
    volume = round(sum(s["price_eth"] for s in sales), 4)
    print(f"  {len(sales)} sales | {volume} ETH volume | {royalty} ETH royalties")
    save(f"{key}_floor", al.floor(addr))


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch secondary sales + floor via Alchemy")
    ap.add_argument("--contract", help="single collection key")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get("ALCHEMY_API_KEY")
    if not api_key:
        print("ERROR: ALCHEMY_API_KEY not set (free at alchemy.com)")
        sys.exit(1)

    al = Alchemy(api_key)
    if args.contract:
        if args.contract not in CONTRACTS:
            print(f"ERROR: unknown contract '{args.contract}'. Options: {list(CONTRACTS)}")
            sys.exit(1)
        items = [(args.contract, CONTRACTS[args.contract])]
    else:
        items = list(CONTRACTS.items())

    for key, meta in items:
        fetch_one(al, key, meta, args.force)
    print("\nDone. Next: python -m scripts.analyze")


if __name__ == "__main__":
    main()
