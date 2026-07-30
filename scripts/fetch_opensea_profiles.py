"""Fetch OpenSea account profiles (username + profile picture) for every wallet
the site displays, so holders/flippers show their OpenSea identity.

Run AFTER a build_site_data pass (it reads the per-collection holders.json for the
wallet list), same convention as identify_wallets:
  python -m scripts.fetch_opensea_profiles [--limit N] [--force]
"""
import os
import re
import json
import time
import argparse
from pathlib import Path

import requests

from scripts.identify_wallets import displayed_wallets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "evidence" / "opensea_profiles.json"
API = "https://api.opensea.io/api/v2/accounts/{addr}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


_AUTO_USERNAME = re.compile(r"^[0-9a-f]{24,}$")


def _real_username(data: dict) -> str | None:
    """A human OpenSea handle, or None if unset/auto-generated. Prefers display_name
    (what OpenSea shows) but falls back to username; rejects the hex auto-name."""
    for field in ("display_name", "username"):
        val = (data.get(field) or "").strip()
        if val and not _AUTO_USERNAME.match(val):
            return val
    return None


def parse_profile(data: dict) -> dict | None:
    """Pull {username, pfp} from an OpenSea account response; None if neither a real
    handle nor a picture is set (so the output only carries wallets with an identity)."""
    if not isinstance(data, dict):
        return None
    username = _real_username(data)
    pfp = (data.get("profile_image_url") or "").strip() or None
    if not username and not pfp:
        return None
    return {"username": username, "pfp": pfp}


def fetch_account(session: requests.Session, key: str, addr: str) -> dict | None:
    """One OpenSea account lookup, retried with backoff. Returns the parsed profile,
    or None (no profile / 404 / persistent error)."""
    for attempt in range(1, 5):
        try:
            r = session.get(API.format(addr=addr), headers={"X-API-KEY": key,
                            "accept": "application/json", "User-Agent": UA}, timeout=30)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(attempt * 2)
                continue
            r.raise_for_status()
            return parse_profile(r.json())
        except requests.RequestException:
            if attempt == 4:
                return None
            time.sleep(attempt)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch OpenSea usernames + pfps for displayed wallets")
    ap.add_argument("--top", type=int, default=50, help="top ecosystem flippers to include")
    ap.add_argument("--limit", type=int, default=0, help="cap wallets this run (0 = all)")
    ap.add_argument("--force", action="store_true", help="re-fetch already-cached addresses")
    args = ap.parse_args()

    key = os.environ.get("OPENSEA_API_KEY")
    if not key:
        print("ERROR: OPENSEA_API_KEY not set (get one at https://docs.opensea.io/reference/api-keys)")
        return 1

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
        prof = fetch_account(session, key, addr)
        cache[addr] = prof if prof else {}      # {} = looked up, no OpenSea profile
        if prof:
            hits += 1
        time.sleep(0.25)                         # ~4 req/s
        if i % 25 == 0:
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(cache, indent=1))
            print(f"  {i}/{len(todo)} fetched, {hits} with a profile so far")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cache, indent=1))
    have = sum(1 for p in cache.values() if p)
    print(f"Done: {have} of {len(cache)} looked-up wallets have an OpenSea profile "
          f"-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
