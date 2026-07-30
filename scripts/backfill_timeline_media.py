"""Add attached-image URLs to tweets already recovered from timeline captures.

Run: python -m scripts.backfill_timeline_media
     python -m scripts.backfill_timeline_media --handle steveaoki
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from scripts.clients.wayback import Wayback, extract_timeline_tweets

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "data" / "raw" / "tweets_timeline_recovered.json"
SAVE_EVERY = 5


def captures_needing_media(rows):
    """(page_handle, capture) pairs with at least one row that has no media key yet,
    each mapped to the ids it is expected to fill."""
    pending = defaultdict(list)
    for r in rows:
        if "media" not in r:
            pending[(r.get("page_handle"), r.get("capture"))].append(r["tweet_id"])
    return pending


def apply_media(rows, found):
    """Join extracted media onto rows by tweet id.

    Every row in the capture gets the key even when the list is empty: an absent key
    means "not looked at yet" and is what makes the run resumable, so it must not be
    confused with "looked at, no image"."""
    by_id = {r["tweet_id"]: r for r in rows}
    filled = images = 0
    for t in found:
        row = by_id.get(t["tweet_id"])
        if row is None or "media" in row:
            continue
        row["media"] = t.get("media") or []
        filled += 1
        images += len(row["media"])
    return filled, images


def backfill(handles=None, wayback=None, path=TARGET):
    rows = json.loads(path.read_text())
    wb = wayback or Wayback()
    pending = captures_needing_media(rows)
    if handles:
        want = {h.lower() for h in handles}
        pending = {k: v for k, v in pending.items() if k[0] in want}
    print(f"{len(rows)} recovered tweets | {len(pending)} captures to re-read")

    filled = images = 0
    for i, ((handle, capture), ids) in enumerate(sorted(pending.items())):
        try:
            html = wb.fetch(capture, f"https://twitter.com/{handle}")
        except Exception as e:
            print(f"  [skip] {handle} {capture}: {str(e)[:60]}")
            continue
        f, im = apply_media(rows, extract_timeline_tweets(html, handle))
        filled += f
        images += im
        if (i + 1) % SAVE_EVERY == 0:
            path.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        print(f"  {i+1}/{len(pending)} {handle} {capture}: "
              f"{f}/{len(ids)} rows filled, {im} images")
    path.write_text(json.dumps(rows, indent=1, ensure_ascii=False))

    withm = sum(1 for r in rows if r.get("media"))
    total = sum(len(r.get("media") or []) for r in rows)
    print(f"[done] {filled} rows filled this run ({images} images); "
          f"{withm} of {len(rows)} tweets now carry {total} image URLs")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", action="append", help="repeatable; default all")
    backfill(ap.parse_args().handle)


if __name__ == "__main__":
    main()
