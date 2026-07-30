"""Pull the live tweet record via GetXAPI:
  - influencers: MetaZoo/NFT-promo tweets (filtered search) -> data/raw/tweets_influencers.json
  - MetaZoo's own accounts: full timelines -> data/raw/tweets_metazoo.json

Usage:
    python -m scripts.fetch_tweets                 # both
    python -m scripts.fetch_tweets --influencers   # influencer promo only
    python -m scripts.fetch_tweets --metazoo       # MetaZoo accounts only
"""
import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
from scripts.config import (INFLUENCERS, METAZOO_ACCOUNTS, METAZOO_PROMO_TERMS, PROMO_WINDOW)
from scripts.clients.getxapi import GetXAPI

RAW = Path(__file__).parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)


def _dedup(tweets: list) -> list:
    seen, out = set(), []
    for t in tweets:
        if t["id"] and t["id"] not in seen:
            seen.add(t["id"])
            out.append(t)
    return out


def fetch_influencers(gx: GetXAPI) -> list:
    since, until = PROMO_WINDOW
    terms = " OR ".join(f'"{t}"' if " " in t else t for t in METAZOO_PROMO_TERMS)
    all_t = []
    for handle in INFLUENCERS:
        q = f"from:{handle} ({terms}) since:{since} until:{until}"
        tweets = gx.search(q)
        for t in tweets:
            t["record"] = "influencer_promo"
        print(f"  @{handle}: {len(tweets)} MetaZoo/NFT tweets")
        all_t.extend(tweets)
    return _dedup(all_t)


def fetch_metazoo_accounts(gx: GetXAPI) -> list:
    all_t = []
    for handle in METAZOO_ACCOUNTS:
        tweets = gx.user_tweets(handle)
        for t in tweets:
            t["record"] = "metazoo_account"
        state = "LIVE" if tweets else "empty/deleted?"
        print(f"  @{handle}: {len(tweets)} tweets ({state})")
        all_t.extend(tweets)
    return _dedup(all_t)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--influencers", action="store_true")
    ap.add_argument("--metazoo", action="store_true")
    args = ap.parse_args()
    do_all = not (args.influencers or args.metazoo)

    if "GETXAPI_KEY" not in os.environ:
        print("ERROR: GETXAPI_KEY not set")
        sys.exit(1)
    gx = GetXAPI(os.environ["GETXAPI_KEY"])

    if args.influencers or do_all:
        print("[influencers] MetaZoo/NFT promo tweets:")
        inf = fetch_influencers(gx)
        (RAW / "tweets_influencers.json").write_text(json.dumps(inf, indent=2))
        print(f"  -> data/raw/tweets_influencers.json ({len(inf)} tweets, "
              f"{sum(1 for t in inf if t['media'])} with media)")

    if args.metazoo or do_all:
        print("[metazoo accounts] full timelines:")
        mz = fetch_metazoo_accounts(gx)
        (RAW / "tweets_metazoo.json").write_text(json.dumps(mz, indent=2))
        print(f"  -> data/raw/tweets_metazoo.json ({len(mz)} tweets, "
              f"{sum(1 for t in mz if t['media'])} with media)")

    print("\nDone. Next: python -m scripts.download_media, then Wayback recovery.")


if __name__ == "__main__":
    main()
