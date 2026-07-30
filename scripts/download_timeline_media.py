"""Download the images attached to tweets recovered from timeline captures.

Scoped by default to the MetaZoo-relevant subset (`recovered_tweets_metazoo.json`).
The full sweep pulled three whole profiles, so most of its images are off-topic
holiday photos and tour posters; `--all` fetches those too if ever needed.

Resumable: an image already on disk is skipped on re-run.

  binaries  data/media/tweets_timeline/<tweet_id>/<n><ext>   (git-ignored)
  manifest  data/media_index/tweet_media.json                (tracked)

Run: python -m scripts.download_timeline_media
     python -m scripts.download_timeline_media --all
"""
import argparse
import json
from pathlib import Path

import requests

from scripts.clients.wayback import Wayback
from scripts.download_archived_media import (HDR, _validate_image,
                                             archived_media_url, pick_ext)

ROOT = Path(__file__).resolve().parent.parent
RELEVANT = ROOT / "data" / "evidence" / "recovered_tweets_metazoo.json"
FULL = ROOT / "data" / "raw" / "tweets_timeline_recovered.json"
MEDIA = ROOT / "data" / "media" / "tweets_timeline"
MANIFEST = ROOT / "data" / "media_index" / "tweet_media.json"
SAVE_EVERY = 25


def _rows(all_tweets: bool):
    if all_tweets:
        return json.loads(FULL.read_text())
    if not RELEVANT.exists():
        raise SystemExit(
            f"{RELEVANT.name} not found (it is a derived file, not tracked in git).\n"
            "Rebuild it with:  python -m scripts.export_recovered_tweets"
        )
    return json.loads(RELEVANT.read_text())["tweets"]


def pending(rows, done):
    """One job per image, skipping those already downloaded. Tweets carry several
    images, so the unit of work is (tweet, index), not the tweet."""
    jobs = []
    for r in rows:
        for i, url in enumerate(r.get("media") or []):
            if (r["tweet_id"], i) not in done:
                jobs.append((r, i, url))
    return jobs


def fetch_one(wb, capture, url):
    """(bytes, content_type, which_source). Live first: a 404 there is expected for
    a deleted account and is not an error worth retrying, so only the Wayback attempt
    goes through the client's backoff."""
    err = None
    for label, u in (("live", url), ("wayback", archived_media_url(capture, url))):
        try:
            resp = (requests.get(u, timeout=30, headers=HDR) if label == "live"
                    else wb._get(u, timeout=45))
            content, ct = _validate_image(resp)
            return content, ct, label, None
        except Exception as e:
            err = f"{label}: {str(e)[:70]}"
    return None, None, None, err


def download(all_tweets=False, wayback=None):
    rows = _rows(all_tweets)
    MEDIA.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    prior = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    manifest = [m for m in prior if m.get("file")]
    done = {(m["tweet_id"], m["index"]) for m in manifest}
    jobs = pending(rows, done)
    print(f"{len(rows)} tweets | {len(done)} images already on disk | {len(jobs)} to fetch")

    wb = wayback or Wayback(rate_delay=0.5)
    ok = fail = via_wb = 0
    for n, (r, i, url) in enumerate(jobs):
        content, ct, via, err = fetch_one(wb, r["capture"], url)
        entry = {"tweet_id": r["tweet_id"], "index": i, "author": r.get("author"),
                 "timestamp": r.get("timestamp"), "capture": r.get("capture"),
                 "source_url": url, "file": None, "via": via, "error": err}
        if content:
            d = MEDIA / r["tweet_id"]
            d.mkdir(parents=True, exist_ok=True)
            name = f"{i}{pick_ext(url, ct)}"
            (d / name).write_bytes(content)
            entry["file"] = f"{r['tweet_id']}/{name}"
            ok += 1
            via_wb += via == "wayback"
        else:
            fail += 1
        manifest.append(entry)
        if n and n % SAVE_EVERY == 0:
            MANIFEST.write_text(json.dumps(manifest, indent=1))
            print(f"  {n}/{len(jobs)} | {ok} ok ({via_wb} via wayback), {fail} failed")
    MANIFEST.write_text(json.dumps(manifest, indent=1))
    print(f"[done] {ok} images saved ({via_wb} recovered via Wayback), {fail} failed")
    print(f"  binaries -> {MEDIA.relative_to(ROOT)}/  |  manifest -> {MANIFEST.relative_to(ROOT)}")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="every recovered tweet, not just the MetaZoo-relevant subset")
    download(ap.parse_args().all)


if __name__ == "__main__":
    main()
