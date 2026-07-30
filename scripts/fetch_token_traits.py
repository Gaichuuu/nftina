"""Fetch the per-token filter trait (Alchemy attributes) for collections whose
token NAMES don't encode a type (coin_tokens, beasties_s1). 

Usage:
  python -m scripts.fetch_token_traits                 # all configured slugs
  python -m scripts.fetch_token_traits --slug coin_tokens --force
"""
import os
import re
import json
import argparse
from pathlib import Path

from scripts.config import CONTRACTS, TOKEN_FILTER_TRAITS
from scripts.clients.alchemy import Alchemy

ROOT = Path(__file__).parent.parent
INDEX = ROOT / "data" / "media_index"


def _trait(nft: dict, trait_type: str):
    attrs = (nft.get("raw", {}).get("metadata", {}) or {}).get("attributes") or []
    for a in attrs:
        if str(a.get("trait_type")) == trait_type:
            v = a.get("value")
            if v is None:
                return None
            return re.sub(r"\.(png|gif|jpe?g|webp|svg)$", "", str(v), flags=re.I)
    return None


def fetch_slug(client: Alchemy, slug: str, trait_type: str) -> dict:
    contract = CONTRACTS[slug]["address"]
    if not contract:
        print(f"[skip] {slug}: no contract address")
        return {}
    out, page_key = {}, None
    while True:
        page = client.nfts_for_contract(contract, page_key)
        for nft in page.get("nfts", []):
            tid = str(nft.get("tokenId"))
            val = _trait(nft, trait_type)
            if tid and val:
                out[tid] = val
        page_key = page.get("pageKey")
        if not page_key:
            break
    (INDEX / "traits").mkdir(parents=True, exist_ok=True)
    (INDEX / "traits" / f"{slug}.json").write_text(json.dumps(out, indent=1))
    distinct = sorted(set(out.values()))
    print(f"[{slug}] {len(out)} tokens tagged by '{trait_type}' -> "
          f"{len(distinct)} distinct: {distinct[:8]}{'…' if len(distinct) > 8 else ''}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch per-token filter traits (Alchemy)")
    ap.add_argument("--slug", help="one slug (default: all in TOKEN_FILTER_TRAITS)")
    ap.add_argument("--force", action="store_true", help="re-fetch even if the manifest exists")
    args = ap.parse_args()

    key = os.environ.get("ALCHEMY_API_KEY")
    if not key:
        print("ERROR: ALCHEMY_API_KEY not set (free at alchemy.com)")
        return 1
    client = Alchemy(key)

    slugs = [args.slug] if args.slug else list(TOKEN_FILTER_TRAITS)
    for slug in slugs:
        trait_type = TOKEN_FILTER_TRAITS.get(slug)
        if not trait_type:
            print(f"[skip] {slug}: no filter trait configured")
            continue
        dest = INDEX / "traits" / f"{slug}.json"
        if dest.exists() and not args.force:
            print(f"[skip] {slug}: {dest.relative_to(ROOT)} exists (--force to refetch)")
            continue
        fetch_slug(client, slug, trait_type)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
