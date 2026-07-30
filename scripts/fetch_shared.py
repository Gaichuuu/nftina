"""Fetch MetaZoo collections that live inside a SHARED lazy-mint contract.

  1. query the contract's transfers filtered by the MetaZoo `distributor` wallet
  2. keep only the configured `token_ids` (drops tokens the wallet merely received
     from unrelated creators)
  3. resolve secondary sales per token via Alchemy (whole-contract sales would be
     the entire storefront)

Run AFTER fetch_chain (dedicated contracts) and BEFORE analyze:
    python -m scripts.fetch_shared
    python -m scripts.fetch_shared --contract genesis_reissue_1155 --force
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
from scripts.clients.alchemy import Alchemy

RAW = Path(__file__).parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)


def save(name: str, data) -> None:
    (RAW / f"{name}.json").write_text(json.dumps(data, indent=2))
    n = len(data) if isinstance(data, (list, dict)) else 1
    print(f"  saved data/raw/{name}.json ({n} records)")


def shared_keys() -> list:
    return [k for k, m in CONTRACTS.items() if m.get("distributor")]


def fetch_one(es: Etherscan, al: Alchemy, key: str, meta: dict, force: bool) -> None:
    addr, distributor = meta.get("address"), meta.get("distributor")
    token_ids = meta.get("token_ids")
    if not addr or not distributor:
        print(f"[skip] {key} — not a shared/distributor collection")
        return
    if (RAW / f"{key}_transfers.json").exists() and not force:
        print(f"[skip] {key} — cached (use --force)")
        return

    standard = meta.get("standard", "erc1155")
    print(f"[fetch] {meta['name']} — shared {standard} via distributor {distributor[:12]}…")
    transfers = es.token_transfers_for_holder(addr, standard, distributor, token_ids)
    if meta.get("creator_encoded"):
        dnum = int(distributor, 16)
        before = len(transfers)
        transfers = [t for t in transfers
                     if t["token_id"].isdigit() and (int(t["token_id"]) >> 96) == dnum]
        if before != len(transfers):
            print(f"  creator_encoded filter: dropped {before - len(transfers)} "
                  f"transfer(s) of tokens not created by the distributor")
    for t in transfers:
        t["collection"] = key
    save(f"{key}_transfers", transfers)
    save(f"{key}_mintvalues", {})

    ids = token_ids or sorted({t["token_id"] for t in transfers})
    print(f"  {len(transfers)} transfers over {len(ids)} token IDs; resolving secondary sales…")
    sales = al.sales_for_tokens(addr, ids)
    save(f"{key}_sales", sales)
    volume = round(sum(s["price_eth"] for s in sales), 4)
    royalty = round(sum(s["royalty_eth"] for s in sales), 4)
    print(f"  {len(sales)} secondary sales | {volume} ETH volume | {royalty} ETH royalties")
    save(f"{key}_floor", {"floor_eth": 0.0})


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch MetaZoo collections inside shared contracts")
    ap.add_argument("--contract", help="single collection key")
    ap.add_argument("--force", action="store_true", help="re-fetch even if cached")
    args = ap.parse_args()

    es_key = os.environ.get("ETHERSCAN_API_KEY")
    al_key = os.environ.get("ALCHEMY_API_KEY")
    if not es_key or not al_key:
        print("ERROR: ETHERSCAN_API_KEY and ALCHEMY_API_KEY must both be set")
        sys.exit(1)

    es, al = Etherscan(es_key), Alchemy(al_key)
    if args.contract:
        if args.contract not in CONTRACTS:
            print(f"ERROR: unknown contract '{args.contract}'. Options: {list(CONTRACTS)}")
            sys.exit(1)
        keys = [args.contract]
    else:
        keys = shared_keys()
        if not keys:
            print("No shared collections (none have a `distributor`).")
            return
        print(f"Shared collections: {keys}")

    for key in keys:
        fetch_one(es, al, key, CONTRACTS[key], args.force)
    print("\nDone. Next: python -m scripts.validate_sales, then python -m scripts.analyze")


if __name__ == "__main__":
    main()
