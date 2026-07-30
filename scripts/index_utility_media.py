"""Prepare the authored utility-product images for the CDN.

`data/media/utility/` holds the images as dropped, with human-readable names
("MetaZoo Valentine's Day NFT.jpg"). `scripts/bunny-upload.sh` builds its upload
URLs as `$BASE/$remote/$(basename "$f")` with no percent-encoding, so a name
carrying spaces, brackets or an apostrophe would upload to a broken path. 

Run: python -m scripts.index_utility_media
"""
import hashlib
import json
import os
import shutil

from scripts.fetch_token_media import sniff_ext

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGUE = os.path.join(REPO, "data", "evidence", "utility_products.json")
SRC_DIR = os.path.join(REPO, "data", "media", "utility")
OUT_DIR = os.path.join(REPO, "data", "media", "utility_cdn")
MANIFEST = os.path.join(REPO, "data", "media_index", "utility.json")


def source_path(name: str) -> str:
    """Where a product's `image_file` lives. A bare filename is one of the images
    dropped in `data/media/utility/`; a name containing a slash is a repo-relative
    path, which lets a product reuse art that already exists elsewhere in the tree
    (a token's own asset, an overview illustration) instead of duplicating the
    file into the drop folder."""
    return os.path.join(REPO, name) if "/" in name else os.path.join(SRC_DIR, name)


def target_name(product_id: str, data: bytes, source_name: str) -> str:
    """CDN filename for a product's art: its id plus the real extension of the
    bytes, falling back to the source file's own extension when unrecognized."""
    ext = sniff_ext(data) or os.path.splitext(source_name)[1].lower()
    return f"{product_id}{ext}"


def build_manifest(products: list, read_bytes) -> dict:
    """{id: {file, source_name}} for every product whose image resolves.

    `read_bytes(image_file)` returns the file's bytes, or None when it is absent.
    A product with no `image_file`, or one whose file is missing, is skipped: the
    tile still renders with a gradient placeholder, so a missing drop is a gap in
    the art, not a build failure.
    """
    out = {}
    for p in products:
        name = p.get("image_file")
        if not name:
            continue
        data = read_bytes(name)
        if data is None:
            continue
        out[p["id"]] = {"file": target_name(p["id"], data, name),
                        "hash": hashlib.sha1(data).hexdigest()[:8],
                        "source_name": name}
    return out


def main():
    with open(CATALOGUE) as fh:
        products = json.load(fh)

    def read_bytes(name):
        path = source_path(name)
        if not os.path.isfile(path):
            print(f"  [miss] no source image: {name}")
            return None
        with open(path, "rb") as fh:
            return fh.read()

    manifest = build_manifest(products, read_bytes)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    for pid, entry in manifest.items():
        shutil.copyfile(source_path(entry["source_name"]),
                        os.path.join(OUT_DIR, entry["file"]))
        print(f"  [ok] {entry['source_name']} -> utility_cdn/{entry['file']}")
    with open(MANIFEST, "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    print(f"{len(manifest)} of {len(products)} product image(s) indexed -> {MANIFEST}")


if __name__ == "__main__":
    main()
