"""Downscale oversized token art before it is stored on the CDN.

The site never renders token art wider than a 420px tile (TokenThumb), and
Bunny Optimizer resizes at delivery, so full-size originals only cost storage:
beasties_s1 / pfp_2 shipped 2700x2700 RGBA PNGs at ~10 MB each (76 GB total).
"""
import io

from PIL import Image, UnidentifiedImageError

MAX_EDGE = 840
QUALITY = 85


def shrink_image(data: bytes, max_edge: int = MAX_EDGE,
                 quality: int = QUALITY) -> tuple[bytes, str] | None:
    """(webp_bytes, ".webp") for a static raster larger than `max_edge` on its
    longest side, else None."""
    if not data:
        return None
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except (UnidentifiedImageError, OSError):
        return None
    if getattr(im, "is_animated", False) or max(im.size) <= max_edge:
        return None
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P", "PA") else "RGB")
    im.thumbnail((max_edge, max_edge), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=quality, method=6)
    return out.getvalue(), ".webp"
