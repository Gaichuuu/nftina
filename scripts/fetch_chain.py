"""Fetch on-chain transfer history + mint transaction values for each known
contract, caching to data/raw/.

Usage:
    python -m scripts.fetch_chain                    # all contracts with addresses
    python -m scripts.fetch_chain --contract coin_tokens
    python -m scripts.fetch_chain --force            # re-fetch (ignore cache)
"""
import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
from scripts.config import CONTRACTS
from scripts.clients.etherscan import Etherscan

RAW = Path(__file__).parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

_STOREFRONT_ADDRS = {m["address"] for m in CONTRACTS.values() if m.get("distributor")}


def is_shared_or_subset(meta: dict) -> bool:
    """A key fetch_chain must NOT whole-contract-fetch, because it is a token-ID subset
    of a shared contract."""
    if (meta.get("distributor") or meta.get("token_id") or meta.get("token_ids")
            or meta.get("shared")):
        return True
    return meta.get("address") in _STOREFRONT_ADDRS


def save(name: str, data) -> None:
    (RAW / f"{name}.json").write_text(json.dumps(data, indent=2))
    n = len(data)
    print(f"  saved data/raw/{name}.json ({n} records)")


def fetch_one(es: Etherscan, key: str, meta: dict, force: bool) -> None:
    addr = meta.get("address")
    if not addr:
        print(f"[skip] {key} — no address in config")
        return
    if meta.get("standard") == "imx":
        print(f"[skip] {key} — Immutable X (not on Etherscan)")
        return
    if is_shared_or_subset(meta):
        print(f"[skip] {key} — token-ID subset of a shared contract; use fetch_shared")
        return
    if (RAW / f"{key}_transfers.json").exists() and not force:
        print(f"[skip] {key} — cached (use --force to refresh)")
        return

    detected = es.detect_standard(addr)
    standard = meta.get("standard")
    if standard not in ("erc721", "erc1155"):
        standard = detected
    elif detected != standard:
        print(f"  [warn] {key}: config says standard={standard} but chain suggests "
              f"{detected}. Using config value; verify manually.")

    print(f"[fetch] {meta['name']} (standard={standard})")
    transfers = es.token_transfers(addr, standard)
    for t in transfers:
        t["collection"] = key   # tag with config key
    save(f"{key}_transfers", transfers)

    mint_hashes = {t["hash"] for t in transfers if t["is_mint"] and t["hash"]}
    print(f"  resolving {len(mint_hashes)} unique mint tx values (this is the slow part)…")
    save(f"{key}_mintvalues", es.tx_values(mint_hashes))


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch on-chain transfers + mint tx values")
    ap.add_argument("--contract", help="single collection key, e.g. coin_tokens")
    ap.add_argument("--force", action="store_true", help="re-fetch even if cached")
    args = ap.parse_args()

    api_key = os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        print("ERROR: ETHERSCAN_API_KEY not set (copy .env.example to .env)")
        sys.exit(1)

    es = Etherscan(api_key)
    if args.contract:
        if args.contract not in CONTRACTS:
            print(f"ERROR: unknown contract '{args.contract}'. Options: {list(CONTRACTS)}")
            sys.exit(1)
        items = [(args.contract, CONTRACTS[args.contract])]
    else:
        items = list(CONTRACTS.items())

    for key, meta in items:
        fetch_one(es, key, meta, args.force)
    print("\nDone. Next: python -m scripts.fetch_sales, then python -m scripts.analyze")


if __name__ == "__main__":
    main()
