"""Download images from RECOVERED (deleted-account) tweets to data/media/<tweet_id>/,
writing a SEPARATE manifest (data/media/manifest_archived.json) so the live-media
manifest is never touched.

Resumable: a tweet whose image already downloaded is skipped on re-run.

Usage:
  python -m scripts.download_archived_media                 # MetaZoo archive (default)
  python -m scripts.download_archived_media --source aoki   # Aoki deleted set
"""
import re
import json
import argparse
import mimetypes
from pathlib import Path
import requests

from scripts.clients.wayback import Wayback

RAW = Path(__file__).parent.parent / "data" / "raw"
MEDIA = Path(__file__).parent.parent / "data" / "media"
WB = "http://web.archive.org/web"
HDR = {"User-Agent": "Mozilla/5.0 (research archive)"}

SOURCES = {
    "metazoo": "tweets_metazoo_archived.json",
    "aoki": "tweets_aoki_deleted.json",
}


def archived_media_url(timestamp: str, image_url: str) -> str:
    """Wayback raw-bytes URL for an image captured with a tweet page."""
    return f"{WB}/{timestamp}id_/{image_url}"


def pick_ext(url: str, content_type: str = "") -> str:
    """Image extension from a pbs.twimg URL (`?format=jpg`, `media/x.jpg:large`)
    or, failing that, the response content-type."""
    m = re.search(r"format=(jpe?g|png|gif|webp)", url or "", re.I)
    if m:
        return "." + m.group(1).lower().replace("jpeg", "jpg")
    for e in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"):
        if e in (url or "").lower():
            return ".jpg" if e == ".jpeg" else e
    guess = mimetypes.guess_extension((content_type or "").split(";")[0].strip() or "")
    return ".jpg" if guess == ".jpeg" else (guess or ".bin")


def _validate_image(r):
    """From a response, return (bytes, content_type) only if it's really an image."""
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    if "image" not in ct.lower() and r.content[:3] not in (b"\xff\xd8\xff", b"\x89PN", b"GIF"):
        raise ValueError(f"not an image (content-type {ct!r})")
    return r.content, ct


def download(source: str) -> None:
    MEDIA.mkdir(parents=True, exist_ok=True)
    recs = json.loads((RAW / SOURCES[source]).read_text())
    recs = [r for r in recs if r.get("matched") and r.get("image")]
    manifest_path = MEDIA / f"manifest_{source}.json"
    prior = {m["tweet_id"]: m for m in json.loads(manifest_path.read_text())} if manifest_path.exists() else {}
    done = {tid for tid, m in prior.items() if m.get("file")}
    todo = [r for r in recs if r["tweet_id"] not in done]
    print(f"[{source}] {len(recs)} tweets with images | {len(done)} already downloaded | {len(todo)} to fetch")

    wb = Wayback(rate_delay=0.5)
    manifest = [m for m in prior.values() if m.get("file")]
    ok = fail = via_wb = 0
    for n, r in enumerate(todo):
        tid, ts, img = r["tweet_id"], r["timestamp"], r["image"]
        entry = {"tweet_id": tid, "date": r.get("date_archived"), "text": r.get("text"),
                 "url": r.get("url"), "source": source, "source_url": img,
                 "file": None, "via": None, "error": None}
        content = ct = None
        for label, u in (("live", img), ("wayback", archived_media_url(ts, img))):
            try:
                resp = requests.get(u, timeout=30, headers=HDR) if label == "live" \
                    else wb._get(u, timeout=45)
                content, ct = _validate_image(resp)
                entry["via"] = label
                if label == "wayback":
                    via_wb += 1
                break
            except Exception as e:
                entry["error"] = f"{label}: {str(e)[:70]}"
        if content:
            tdir = MEDIA / tid
            tdir.mkdir(parents=True, exist_ok=True)
            fn = f"0{pick_ext(img, ct)}"
            (tdir / fn).write_bytes(content)
            entry["file"], entry["error"] = f"{tid}/{fn}", None
            ok += 1
        else:
            fail += 1
        manifest.append(entry)
        if n and n % 50 == 0:
            manifest_path.write_text(json.dumps(manifest, indent=2))
            print(f"  {n}/{len(todo)} | {ok} ok ({via_wb} via wayback), {fail} failed")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[done] {source}: {ok} images saved ({via_wb} recovered via Wayback), {fail} failed.")
    print(f"  media -> data/media/<tweet_id>/  |  index -> data/media/manifest_{source}.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=list(SOURCES), default="metazoo")
    download(ap.parse_args().source)


if __name__ == "__main__":
    main()
