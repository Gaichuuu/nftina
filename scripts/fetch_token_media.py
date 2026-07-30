"""Fetch token art (name + image) for the site's collections and rehost-ready
images to data/media/, writing git-tracked manifests to data/media_index/.

Usage:
  python -m scripts.fetch_token_media                 # all site slugs (registry-driven)
  python -m scripts.fetch_token_media --collection coin_tokens
  python -m scripts.fetch_token_media --limit 50      # first 50 tokens/slug (preview)
  python -m scripts.fetch_token_media --collections-only  # just the collection logos
"""
import os
import re
import json
import time
import shutil
import hashlib
import argparse
import concurrent.futures as cf
from pathlib import Path

import requests

from scripts.config import CONTRACTS, SITE_COLLECTIONS, MEDIA_CDN_BASE, SANDBOX_TOKEN_IDS
from scripts.clients.alchemy import Alchemy, pick_image_url, normalize_ipfs

ROOT = Path(__file__).parent.parent
MEDIA = ROOT / "data" / "media"
INDEX = ROOT / "data" / "media_index"
RAW = ROOT / "data" / "raw"
PUBLIC_DATA = ROOT / "public" / "data"
HDR = {"User-Agent": "metazoonfts-archive/1.0"}

SITE_SLUGS = [c["slug"] for c in SITE_COLLECTIONS if c["slug"] != "sandbox"]

_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


def ext_from_url(url: str) -> str:
    low = (url or "").split("?")[0].lower()
    for e in _EXTS:
        if low.endswith(e):
            return e
    m = re.search(r"\.(png|jpe?g|gif|webp|svg)(?:$|[?/])", low)
    return f".{m.group(1)}" if m else ".png"


def img_filename(source: str, ext: str) -> str:
    """URL-addressed filename: identical source URL -> identical file, so
    artwork reused across many token ids is stored/hosted exactly once."""
    return hashlib.sha1(source.encode()).hexdigest()[:16] + ext


def is_shared(slug: str) -> bool:
    """Mirrors fetch_chain.is_shared_or_subset: True if the config entry is a
    shared-storefront / token-ID-subset contract (e.g. genesis_reissue_1155's
    OPENSTORE entry) that must NOT be whole-contract-fetched."""
    meta = CONTRACTS[slug]
    return bool(meta.get("distributor") or meta.get("token_id") or meta.get("token_ids")
                or meta.get("shared"))


def token_ids_from_transfers(transfers: list) -> list:
    """Distinct token_ids (as str), first-seen order, from raw transfer records."""
    seen = set()
    ids = []
    for t in transfers:
        tid = str(t.get("token_id"))
        if tid not in seen:
            seen.add(tid)
            ids.append(tid)
    return ids


def dedup_key(nft: dict) -> str:
    """The artwork's IDENTITY for dedup — the underlying token-metadata image
    (`raw.metadata.image`), which is SHARED across every token that reuses the
    same art (e.g. all "Mothman Gold" coin tokens point at the same .gif)."""
    raw = ((nft.get("raw") or {}).get("metadata") or {}).get("image")
    if raw:
        return normalize_ipfs(raw)
    return pick_image_url(nft)


def manifest_entries(nfts: list, ext_for) -> dict:
    """{token_id: {name, file, source}} for nfts that have an image.

    `file` is a hash of the DEDUP KEY (the underlying artwork identity, see
    dedup_key) so art reused across many token ids collapses to one stored
    file; `source` stays the per-token display URL."""
    out = {}
    for nft in nfts:
        src = pick_image_url(nft)
        if not src:
            continue
        key = dedup_key(nft)  # never empty when src exists
        tid = str(nft.get("tokenId"))
        out[tid] = {"name": nft.get("name"), "file": img_filename(key, ext_for(key)),
                    "source": src}
    return out


def _download(url: str, dest: Path, retries: int = 3) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=45, headers=HDR)
            r.raise_for_status()
            if r.content:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                return True
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return False


def sniff_ext(data: bytes) -> str:
    """Real file extension from magic bytes, or "" if unrecognized (caller
    falls back to the URL-derived extension)."""
    if not data:
        return ""
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis"):
        return ".avif"
    if data[:4] == b"\x89PNG":
        return ".png"
    if data[:4] == b"GIF8":
        return ".gif"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    head = data[:512].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<?xml") and b"<svg" in data[:2048].lower():
        return ".svg"
    if head.startswith(b"<svg"):
        return ".svg"
    return ""


def _download_bytes(url: str, retries: int = 3) -> bytes | None:
    """Fetch raw bytes (no dest write) so the caller can sniff the real
    extension from content before deciding a filename."""
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=45, headers=HDR)
            r.raise_for_status()
            if r.content:
                return r.content
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return None


def _download_sniffed(url: str, dest_dir: Path, stem: str) -> tuple[str, bool]:
    """Download `url`, name the file `<stem><real-ext>` where the extension comes
    from the bytes' MAGIC NUMBER (sniff_ext), falling back to the URL-derived
    extension when unrecognized."""
    data = _download_bytes(url)
    ext = sniff_ext(data) or ext_from_url(url)   # sniff_ext(None/"") -> ""
    fname = f"{stem}{ext}"
    if data:
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / fname).write_bytes(data)
    return fname, bool(data)


WORKERS = 12


def _download_jobs(jobs: list, workers: int | None = None) -> int:
    """Download a list of (source_url, dest_path) concurrently; return the
    number that succeeded."""
    if not jobs:
        return 0
    ok = 0
    with cf.ThreadPoolExecutor(max_workers=workers or WORKERS) as ex:
        for success in ex.map(lambda j: _download(j[0], j[1]), jobs):
            if success:
                ok += 1
    return ok


def fetch_collection(client: Alchemy, slug: str, limit: int = 0) -> dict:
    contract = CONTRACTS[slug]["address"]
    if not contract:
        print(f"[skip] {slug}: no contract address")
        return {}
    if is_shared(slug):
        meta = CONTRACTS[slug]
        cfg_ids = meta.get("token_ids") or ([str(meta["token_id"])] if meta.get("token_id") else None)
        if cfg_ids:
            ids = cfg_ids
        else:
            transfers_path = RAW / f"{slug}_transfers.json"
            if not transfers_path.exists():
                print(f"[skip] {slug}: shared contract needs config token_ids or data/raw/{slug}_transfers.json")
                return {}
            ids = token_ids_from_transfers(json.loads(transfers_path.read_text()))
        if limit:
            ids = ids[:limit]
        nfts = [client.token_metadata(contract, tid) for tid in ids]
    else:
        nfts, page_key = [], None
        while True:
            page = client.nfts_for_contract(contract, page_key)
            nfts.extend(page.get("nfts", []))
            page_key = page.get("pageKey")
            if limit and len(nfts) >= limit:
                nfts = nfts[:limit]
                break
            if not page_key:
                break
    entries = manifest_entries(nfts, ext_from_url)
    seen, jobs = set(), []
    for e in entries.values():
        if e["file"] in seen:
            continue
        seen.add(e["file"])
        jobs.append((e["source"], MEDIA / "tokens" / slug / e["file"]))
    ok = _download_jobs(jobs)
    (INDEX / "tokens").mkdir(parents=True, exist_ok=True)
    (INDEX / "tokens" / f"{slug}.json").write_text(json.dumps(entries, indent=1))
    print(f"[{slug}] {len(entries)} tokens -> {len(seen)} distinct images, {ok} on disk")
    return entries


def acq_key(contract: str, token_id: str) -> str:
    return f"{contract.lower()}_{token_id}"


def fetch_acquisitions(client: Alchemy) -> dict:
    acq_path = PUBLIC_DATA / "acquisitions.json"
    if not acq_path.exists():
        print("[acquisitions] public/data/acquisitions.json missing — run trace_acquisitions first")
        return {}
    items = json.loads(acq_path.read_text()).get("top_items", [])
    entries, ok = {}, 0
    dest_dir = MEDIA / "acquisitions"
    for it in items:
        contract, tid = it.get("contract"), str(it.get("token_id"))
        if not contract:
            continue
        nft = client.token_metadata(contract, tid)
        url = pick_image_url(nft)
        if not url:
            continue
        fname, wrote = _download_sniffed(url, dest_dir, acq_key(contract, tid))
        ok += wrote
        entries[acq_key(contract, tid)] = {
            "name": nft.get("name"), "file": fname, "source": url,
            "contract": contract.lower(), "token_id": str(tid)}
    INDEX.mkdir(parents=True, exist_ok=True)
    (INDEX / "acquisitions.json").write_text(json.dumps(entries, indent=1))
    print(f"[acquisitions] {len(entries)} items with art, {ok} images on disk")
    return entries


def collection_art_url(meta: dict) -> str | None:
    """OpenSea logo (imageUrl) from a getContractMetadata response, or None.
    ONLY valid for a slug's OWN dedicated contract"""
    return ((meta or {}).get("openSeaMetadata") or {}).get("imageUrl") or None


def _own_token_art_source(slug: str) -> tuple[Path, str] | None:
    """For a SHARED-contract slug (config `shared: True`, e.g. the OPENSTORE
    tenants `genesis_reissue_1155`/`tournament_prizes`), the collection logo
    must come from the collection's OWN already-fetched token art, never the
    shared contract's `contract_metadata`."""
    manifest_path = INDEX / "tokens" / f"{slug}.json"
    if not manifest_path.exists():
        return None
    entries = json.loads(manifest_path.read_text())
    if not entries:
        return None
    first = next(iter(entries.values()))
    file_name = first.get("file") if isinstance(first, dict) else None
    if not file_name:
        return None
    src = MEDIA / "tokens" / slug / file_name
    if not src.exists():
        return None
    return src, Path(file_name).suffix


def fetch_collection_art(client: Alchemy) -> dict:
    """Download each site collection's logo to data/media/collections/, write
    data/media_index/collection_art.json {slug: cdn_url}. Slugs with no
    contract address are skipped.

    Provenance splits in two:
    - Non-shared (dedicated) contract -> Alchemy `contract_metadata`'s
      OpenSea `imageUrl`, downloaded and the file EXTENSION set from the
      downloaded bytes' magic number (sniff_ext), not the URL/content-type
      header, since those aren't reliable either.
    - `shared: True` contract (multi-tenant OpenSea storefront, e.g.
      OPENSTORE) -> `contract_metadata` is untrustworthy for these (see
      `collection_art_url` docstring), so the logo is instead copied from
      the slug's OWN first fetched token image (`_own_token_art_source`);
      omitted if that token art doesn't exist yet."""
    out = {}
    meta_cache: dict[str, dict] = {}
    ok = 0
    (MEDIA / "collections").mkdir(parents=True, exist_ok=True)
    for reg in SITE_COLLECTIONS:
        slug = reg["slug"]
        contract = CONTRACTS.get(slug, {}).get("address")
        if not contract:
            continue

        if CONTRACTS[slug].get("shared"):
            own = _own_token_art_source(slug)
            if not own:
                continue
            src, ext = own
            dest = MEDIA / "collections" / f"{slug}{ext}"
            dest.write_bytes(src.read_bytes())
            out[slug] = f"{MEDIA_CDN_BASE}/collections/{slug}{ext}"
            ok += 1
            continue

        if contract not in meta_cache:
            meta_cache[contract] = client.contract_metadata(contract)
        url = collection_art_url(meta_cache[contract])
        if not url:
            continue
        fname, wrote = _download_sniffed(url, MEDIA / "collections", slug)
        if not wrote:
            continue
        out[slug] = f"{MEDIA_CDN_BASE}/collections/{fname}"
        ok += 1

    INDEX.mkdir(parents=True, exist_ok=True)
    (INDEX / "collection_art.json").write_text(json.dumps(out, indent=1))
    print(f"[collection-art] {len(out)} logos, {ok} images on disk")
    return out


SANDBOX_CONTRACT = "0xa342f5d851e866e18ff98f351f2c6637f4478db5"


def _slugify_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "asset").lower()).strip("-")


def sandbox_assets(meta: dict) -> dict | None:
    """Pull the 3D model + poster image URL from a Sandbox getNFTMetadata
    response. `raw.metadata.animation_url` is the ipfs:// .gltf model; the
    poster prefers the top-level `image.originalUrl`."""
    model = ((meta.get("raw") or {}).get("metadata") or {}).get("animation_url")
    if not model:
        return None
    image = (((meta.get("image") or {}).get("originalUrl"))
             or ((meta.get("raw") or {}).get("metadata") or {}).get("image"))
    return {"name": meta.get("name") or "Asset", "model_ipfs": model, "image_url": image}


def fetch_sandbox_3d(client: Alchemy) -> list:
    """Download the 6 Sandbox characters' .gltf model + poster image to
    data/media/sandbox3d/, write data/media_index/sandbox3d.json = list of
    {"token_id","name","model","image"} CDN urls"""
    (MEDIA / "sandbox3d").mkdir(parents=True, exist_ok=True)
    entries = []
    model_ok = image_ok = 0
    for tid in SANDBOX_TOKEN_IDS:
        a = sandbox_assets(client.token_metadata(SANDBOX_CONTRACT, tid))
        if not a:
            continue
        base = _slugify_name(a["name"])

        model_dest = MEDIA / "sandbox3d" / f"{base}.gltf"
        if _download(normalize_ipfs(a["model_ipfs"]), model_dest):
            model_ok += 1
            model_url = f"{MEDIA_CDN_BASE}/sandbox3d/{base}.gltf"
        else:
            model_url = None

        image_url = None
        if a["image_url"]:
            existing = [p for p in (MEDIA / "sandbox3d").glob(f"{base}.*")
                        if p.suffix != ".gltf" and p.stat().st_size > 0]
            if existing:
                image_ok += 1
                image_url = f"{MEDIA_CDN_BASE}/sandbox3d/{existing[0].name}"
            else:
                fname, wrote = _download_sniffed(normalize_ipfs(a["image_url"]),
                                                 MEDIA / "sandbox3d", base)
                if wrote:
                    image_ok += 1
                    image_url = f"{MEDIA_CDN_BASE}/sandbox3d/{fname}"

        entries.append({"token_id": tid, "name": a["name"], "model": model_url, "image": image_url})

    INDEX.mkdir(parents=True, exist_ok=True)
    (INDEX / "sandbox3d.json").write_text(json.dumps(entries, indent=1))
    print(f"[sandbox3d] {len(entries)} characters, {model_ok} models + {image_ok} posters on disk")
    return entries


GENESIS_ARTICLE_EVIDENCE = ROOT / "data" / "evidence" / "genesis_article_assets.json"
DEFAULT_ARTICLE_SRC = "/Users/camel/metasued/scratch/articles"


def infer_missing_genesis(manifest: dict, total: int = 595) -> dict:
    """Genesis token IDs sit in contiguous per-cryptid runs, so a missing ID whose
    nearest present neighbors on BOTH sides share a name belongs to that cryptid.
    Returns {token_id: name} for confidently inferable gaps only."""
    present = sorted(int(k) for k in manifest)
    out = {}
    for tid in range(1, total + 1):
        if str(tid) in manifest:
            continue
        lo = max((p for p in present if p < tid), default=None)
        hi = min((p for p in present if p > tid), default=None)
        if lo is None or hi is None:
            continue
        if manifest[str(lo)]["name"] == manifest[str(hi)]["name"]:
            out[str(tid)] = manifest[str(lo)]["name"]
    return out


def fill_genesis_article_art(article_src) -> int:
    """Fill genesis_2021 manifest gaps: cryptid via neighbor-run inference, art by
    reusing the same-cryptid file already in the manifest, else the Wayback
    article's GIF (copied into data/media/tokens/genesis_2021/)."""
    article_src = Path(article_src)
    mpath = INDEX / "tokens" / "genesis_2021.json"
    manifest = json.loads(mpath.read_text())
    evidence = json.loads(GENESIS_ARTICLE_EVIDENCE.read_text())
    art_by_manifest_name = {c["manifest_name"]: c for c in evidence["cryptids"]
                            if c["manifest_name"] and c["file"]}
    by_name_file = {}
    for e in manifest.values():
        by_name_file.setdefault(e["name"], e["file"])
    added = 0
    for tid, name in sorted(infer_missing_genesis(manifest).items(), key=lambda kv: int(kv[0])):
        file = by_name_file.get(name)
        note = "art reused from same-cryptid token"
        if not file:
            c = art_by_manifest_name.get(name)
            if not c:
                print(f"[genesis-article] token {tid} ({name}): no art available")
                continue
            file = f"article_{_slugify_name(name)}.gif"
            dest = MEDIA / "tokens" / "genesis_2021" / file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(article_src / c["file"], dest)
            note = f"art from wayback article-38 ({c['file']})"
        manifest[tid] = {"name": name, "file": file, "source": "inferred-neighbor-run",
                         "note": note}
        added += 1
    mpath.write_text(json.dumps(manifest, indent=1))
    art_path = INDEX / "collection_art.json"
    art = json.loads(art_path.read_text()) if art_path.exists() else {}
    if not art.get("genesis_2021"):
        moth = next((c for c in evidence["cryptids"]
                     if c["name"] == "Mothman" and c["file"]), None)
        if moth:
            dest = MEDIA / "collections" / "genesis_2021.gif"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(article_src / moth["file"], dest)
            art["genesis_2021"] = f"{MEDIA_CDN_BASE}/collections/genesis_2021.gif"
            INDEX.mkdir(parents=True, exist_ok=True)
            art_path.write_text(json.dumps(art, indent=1))
    print(f"[genesis-article] filled {added} manifest gaps "
          f"(genesis logo: {art.get('genesis_2021')})")
    return added


def main() -> int:
    global WORKERS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--collection", help="one slug (default: all site slugs)")
    ap.add_argument("--limit", type=int, default=0, help="first N tokens/slug (0 = all)")
    ap.add_argument("--tokens-only", action="store_true", help="skip the acquisitions pass")
    ap.add_argument("--acquisitions-only", action="store_true", help="skip the token pass")
    ap.add_argument("--collections-only", action="store_true",
                    help="only fetch collection logo art (skip tokens + acquisitions)")
    ap.add_argument("--sandbox-only", action="store_true",
                    help="only fetch the Sandbox 3D models + posters")
    ap.add_argument("--genesis-article", action="store_true",
                    help="offline: fill genesis_2021 manifest gaps from the Wayback "
                         "'MetaZoo Tokens & NFTs' article (no Alchemy key needed)")
    ap.add_argument("--article-src", default=DEFAULT_ARTICLE_SRC,
                    help=f"dir holding the article GIFs (default {DEFAULT_ARTICLE_SRC})")
    ap.add_argument("--workers", type=int, default=WORKERS,
                    help=f"concurrent image downloads (default {WORKERS})")
    args = ap.parse_args()
    WORKERS = args.workers
    if args.genesis_article:
        fill_genesis_article_art(args.article_src)
        return 0
    key = os.environ.get("ALCHEMY_API_KEY")
    if not key:
        print("ERROR: ALCHEMY_API_KEY not set (free at alchemy.com)")
        return 1
    client = Alchemy(key)
    if args.sandbox_only:
        fetch_sandbox_3d(client)
        return 0
    if args.collections_only:
        fetch_collection_art(client)
        return 0
    if not args.acquisitions_only:
        slugs = [args.collection] if args.collection else SITE_SLUGS
        for slug in slugs:
            fetch_collection(client, slug, args.limit)
    if not args.tokens_only:
        fetch_acquisitions(client)
    if not (args.tokens_only or args.acquisitions_only or args.collection):
        fetch_sandbox_3d(client)
        fetch_collection_art(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
