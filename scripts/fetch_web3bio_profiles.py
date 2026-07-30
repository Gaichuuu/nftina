"""Resolve wallet identities via web3.bio (a free, no-key universal profile API)
for every wallet the site displays.

No API key. Resumable: an address already looked up is skipped unless --force.
Run AFTER a build_site_data pass (reads the per-collection holders.json for the
wallet list), same convention as identify_wallets:
  python -m scripts.fetch_web3bio_profiles [--limit N] [--force]
"""
import json
import time
import argparse
from pathlib import Path

import requests

from scripts.identify_wallets import displayed_wallets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "evidence" / "web3bio_profiles.json"
API = "https://api.web3.bio/profile/{addr}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_ORDER = {"ens": 0, "basenames": 1, "farcaster": 2, "lens": 3, "unstoppabledomains": 4}


def parse_web3bio(profiles) -> dict | None:
    """Best {username, pfp} across a wallet's web3.bio profiles; None if the wallet
    has no real identity (only the raw-address 'ethereum' entry)."""
    if not isinstance(profiles, list):
        return None
    real = [p for p in profiles if isinstance(p, dict) and p.get("platform") != "ethereum"]
    real.sort(key=lambda p: _ORDER.get(p.get("platform"), 9))
    name = next((p.get("displayName") or p.get("identity")
                 for p in real if (p.get("displayName") or p.get("identity"))), None)
    pfp = next((p.get("avatar") for p in real if p.get("avatar")), None)
    if not name and not pfp:
        return None
    return {"username": name, "pfp": pfp}


def fetch_profile(session: requests.Session, addr: str) -> dict | None:
    """One web3.bio lookup, retried with backoff. Returns the parsed profile or None
    (no identity / 404 / persistent error)."""
    for attempt in range(1, 5):
        try:
            r = session.get(API.format(addr=addr),
                            headers={"User-Agent": UA, "accept": "application/json"}, timeout=30)
            if r.status_code in (404, 400):
                return None
            if r.status_code == 429:
                time.sleep(attempt * 3)
                continue
            r.raise_for_status()
            return parse_web3bio(r.json())
        except requests.RequestException:
            if attempt == 4:
                return None
            time.sleep(attempt)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve wallet names+pfps via web3.bio")
    ap.add_argument("--top", type=int, default=50, help="top ecosystem flippers to include")
    ap.add_argument("--limit", type=int, default=0, help="cap wallets this run (0 = all)")
    ap.add_argument("--force", action="store_true", help="re-fetch already-cached addresses")
    args = ap.parse_args()

    cache = json.loads(OUT.read_text()) if OUT.exists() else {}
    wallets = displayed_wallets(args.top)
    todo = [w for w in wallets if args.force or w not in cache]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(wallets)} displayed wallets; {len(todo)} to fetch "
          f"({len(wallets) - len(todo)} cached).")

    session = requests.Session()
    hits = 0
    for i, addr in enumerate(todo, 1):
        prof = fetch_profile(session, addr)
        cache[addr] = prof if prof else {}      # {} = looked up, no identity
        if prof:
            hits += 1
        time.sleep(0.25)                          # ~4 req/s
        if i % 50 == 0:
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(cache, indent=1))
            print(f"  {i}/{len(todo)} fetched, {hits} named so far")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cache, indent=1))
    have = sum(1 for p in cache.values() if p)
    print(f"Done: {have} of {len(cache)} looked-up wallets have a web3 identity "
          f"-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
