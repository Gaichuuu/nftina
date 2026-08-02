"""Recover deleted tweets from the Wayback Machine.

  --target metazoo       reconstruct the DELETED @MetaZooGames account
  --target aoki-deleted  find Aoki MetaZoo tweets that are archived but no longer
                         live on X — archived set minus the live set

Resumable: results are saved incrementally; re-running skips tweet ids already done.
Wayback is slow/flaky, so expect a long run and partial recovery.
"""
import json
import argparse
from pathlib import Path

from scripts.config import METAZOO_PROMO_TERMS, METAZOO_DELETED_HANDLE
from scripts.clients.wayback import Wayback, extract_tweet

RAW = Path(__file__).parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)


def _load_done(path: Path) -> dict:
    if path.exists():
        return {r["tweet_id"]: r for r in json.loads(path.read_text())}
    return {}


def _live_aoki_ids() -> set:
    p = RAW / "tweets_influencers.json"
    if not p.exists():
        return set()
    return {t["id"] for t in json.loads(p.read_text()) if t.get("author") == "steveaoki"}


def recover(pattern, out_name, from_date=None, to_date=None, terms=None, live_ids=None):
    wb = Wayback()
    out_path = RAW / out_name
    done = _load_done(out_path)
    print(f"[{out_name}] enumerating snapshots for {pattern} …")
    snaps = wb.snapshots(pattern, from_date, to_date)
    print(f"  {len(snaps)} unique archived tweet ids ({len(done)} already recovered)")

    results = list(done.values())
    todo = [s for s in snaps if s["tweet_id"] not in done]
    kept = sum(1 for r in results if r.get("matched"))
    for i, s in enumerate(todo):
        try:
            html = wb.fetch(s["timestamp"], s["original"])
        except Exception as e:
            print(f"  [skip] {s['tweet_id']}: {str(e)[:60]}")
            continue
        tw = extract_tweet(html)
        text_l = (tw["text"] or "").lower()
        matched = True
        if terms is not None:
            matched = any(t in text_l for t in terms)
        deleted = (live_ids is None) or (s["tweet_id"] not in live_ids)
        rec = {"tweet_id": s["tweet_id"], "timestamp": s["timestamp"],
               "url": s["original"], "date_archived": s["timestamp"][:8],
               "text": tw["text"], "author_title": tw["author_title"],
               "image": tw["image"], "matched": bool(matched and deleted),
               "source": "wayback"}
        results.append(rec)
        if rec["matched"]:
            kept += 1
        if (i + 1) % 25 == 0:
            out_path.write_text(json.dumps(results, indent=2))
            print(f"  {i+1}/{len(todo)} fetched | {kept} relevant recovered")
    out_path.write_text(json.dumps(results, indent=2))
    print(f"[done] {out_name}: {len(results)} archived, {kept} relevant "
          f"({'deleted MetaZoo' if live_ids is not None else 'account tweets'}). "
          f"-> data/raw/{out_name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["metazoo", "aoki-deleted"], required=True)
    args = ap.parse_args()
    if args.target == "metazoo":
        recover(f"twitter.com/{METAZOO_DELETED_HANDLE}/status/*",
                "tweets_metazoo_archived.json")
    else:
        recover("twitter.com/steveaoki/status/*", "tweets_aoki_deleted.json",
                from_date="20210301", to_date="20221231",
                terms=METAZOO_PROMO_TERMS, live_ids=_live_aoki_ids())


if __name__ == "__main__":
    main()
