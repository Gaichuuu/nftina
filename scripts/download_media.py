"""Download the images/videos from the collected tweets to data/media/<tweet_id>/,
and write a manifest (data/media/manifest.json) linking each tweet to its local
files + the full tweet metadata.

Usage: python -m scripts.download_media
"""
import json
import time
import mimetypes
from pathlib import Path
import requests

RAW = Path(__file__).parent.parent / "data" / "raw"
MEDIA = Path(__file__).parent.parent / "data" / "media"
SOURCES = ["tweets_influencers.json", "tweets_metazoo.json"]


def _load_all() -> list:
    out, seen = [], set()
    for name in SOURCES:
        p = RAW / name
        if not p.exists():
            continue
        for t in json.loads(p.read_text()):
            if t["id"] not in seen and t.get("media"):
                seen.add(t["id"])
                out.append(t)
    return out


def _ext(url: str, content_type: str) -> str:
    for e in (".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webp"):
        if e in url.lower():
            return e
    return mimetypes.guess_extension(content_type or "") or ".bin"


def _fetch(url: str, retries: int = 3) -> requests.Response:
    """GET with a few backoff retries so a transient blip doesn't permanently
    drop an asset (the original single-shot fetch lost ~350 assets that way)."""
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(0.5 * (attempt + 1))
    raise last


def download() -> None:
    MEDIA.mkdir(parents=True, exist_ok=True)
    tweets = _load_all()
    print(f"{len(tweets)} tweets with media to fetch")
    manifest, ok, fail, skipped = [], 0, 0, 0
    for n, t in enumerate(tweets):
        tdir = MEDIA / t["id"]
        files = []
        for i, m in enumerate(t["media"]):
            url = m["url"]
            existing = next(iter(sorted(tdir.glob(f"{i}.*"))), None) if tdir.exists() else None
            if existing:
                files.append({"file": f"{t['id']}/{existing.name}", "type": m["type"],
                              "source_url": url})
                ok += 1; skipped += 1
                continue
            try:
                r = _fetch(url)
                tdir.mkdir(parents=True, exist_ok=True)
                fn = f"{i}{_ext(url, r.headers.get('content-type', ''))}"
                (tdir / fn).write_bytes(r.content)
                files.append({"file": f"{t['id']}/{fn}", "type": m["type"], "source_url": url})
                ok += 1
            except Exception as e:
                files.append({"file": None, "type": m["type"], "source_url": url,
                              "error": str(e)[:80]})
                fail += 1
            time.sleep(0.15)
        manifest.append({
            "id": t["id"], "author": t["author"], "date": t["date"],
            "text": t["text"], "url": t["url"], "record": t.get("record"),
            "media": files,
        })
        if n % 50 == 0 and n:
            print(f"  {n}/{len(tweets)} tweets | {ok} files ok, {fail} failed")
    (MEDIA / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nDone. {ok} media files present ({skipped} already on disk, "
          f"{ok - skipped} newly fetched), {fail} failed (dead URLs).")
    print(f"  media -> data/media/<tweet_id>/  |  index -> data/media/manifest.json")


if __name__ == "__main__":
    download()
