"""Recover tweets from archived PROFILE-TIMELINE captures (a second Wayback source).

`fetch_wayback.py` enumerates Wayback's index for `twitter.com/<handle>/status/*`
and reads one tweet per snapshot. That misses two whole categories:

  1. A tweet whose own status URL a crawler never happened to hit. It can still sit,
     fully server-rendered, inside a capture of the account's timeline page.
  2. Every retweet. `twitter.com/<retweeter>/status/<rt id>` redirects to the
     original, so the retweeter's URL is never archived; a timeline capture instead
     labels the block "<Name> Retweeted".

Run: python -m scripts.fetch_timelines            (all default handles)
     python -m scripts.fetch_timelines --handle steveaoki
"""
import argparse
import json
from pathlib import Path

from scripts.clients.wayback import Wayback, extract_timeline_tweets

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = RAW / "tweets_timeline_recovered.json"

HANDLES = ["steveaoki", "MetaZooGames", "farokh"]
SAVE_EVERY = 5
YEARS = range(2020, 2025)


def _enumerate(wb, url, from_date=None, to_date=None):
    """Captures of one page, year by year when no explicit range is given."""
    if from_date or to_date:
        return wb.page_snapshots(url, from_date, to_date)
    snaps, seen = [], set()
    for y in YEARS:
        try:
            got = wb.page_snapshots(url, f"{y}0101", f"{y}1231")
        except Exception as e:
            print(f"  [skip] {y}: {str(e)[:70]}")
            continue
        for s in got:
            if s["timestamp"] not in seen:
                seen.add(s["timestamp"])
                snaps.append(s)
        print(f"    {y}: {len(got)} captures")
    return snaps


def _load_done(path: Path):
    """Prior results plus the set of captures already fetched, so a killed run
    resumes instead of re-crawling. Wayback is slow and rate-limits hard."""
    if not path.exists():
        return [], set()
    rows = json.loads(path.read_text())
    return rows, {(r.get("page_handle"), r.get("capture")) for r in rows}


def sweep(handles=None, from_date=None, to_date=None, wayback=None):
    wb = wayback or Wayback()
    rows, done = _load_done(OUT)
    seen_ids = {r["tweet_id"] for r in rows}
    for handle in (handles or HANDLES):
        url = f"twitter.com/{handle}"
        print(f"[{handle}] enumerating timeline captures …")
        try:
            snaps = _enumerate(wb, url, from_date, to_date)
        except Exception as e:
            print(f"  [skip] enumeration failed: {str(e)[:80]}")
            continue
        if not snaps:
            print(f"  [warn] no captures enumerated for {handle}. A silent empty "
                  f"result usually means the CDX request timed out; retry this handle.")
        todo = [s for s in snaps if (handle.lower(), s["timestamp"]) not in done]
        print(f"  {len(snaps)} captures ({len(snaps) - len(todo)} already read)")
        for i, s in enumerate(todo):
            try:
                html = wb.fetch(s["timestamp"], s["original"])
            except Exception as e:
                print(f"  [skip] {s['timestamp']}: {str(e)[:60]}")
                continue
            found = extract_timeline_tweets(html, handle)
            new = 0
            for t in found:
                if t["tweet_id"] in seen_ids:
                    continue
                seen_ids.add(t["tweet_id"])
                rows.append({**t, "capture": s["timestamp"],
                             "source": "wayback-timeline"})
                new += 1
            done.add((handle.lower(), s["timestamp"]))
            if (i + 1) % SAVE_EVERY == 0 or new:
                OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
            print(f"  {i+1}/{len(todo)} {s['timestamp']}: "
                  f"{len(found)} on page, {new} new (total {len(rows)})")
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    rt = sum(1 for r in rows if r.get("retweeted_by"))
    print(f"[done] {len(rows)} tweets recovered from timeline captures "
          f"({rt} retweets) -> {OUT}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", action="append",
                    help="repeatable; defaults to every handle in HANDLES")
    ap.add_argument("--from-date", help="CDX from, YYYYMMDD")
    ap.add_argument("--to-date", help="CDX to, YYYYMMDD")
    a = ap.parse_args()
    sweep(a.handle, a.from_date, a.to_date)


if __name__ == "__main__":
    main()
