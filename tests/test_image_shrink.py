import io

from PIL import Image

from scripts.image_shrink import shrink_image, MAX_EDGE


def _png(size, mode="RGBA", color=(200, 30, 90, 255)):
    bio = io.BytesIO()
    Image.new(mode, size, color[:len(mode)]).save(bio, "PNG")
    return bio.getvalue()


def _open(data):
    im = Image.open(io.BytesIO(data))
    im.load()
    return im


def test_large_png_becomes_webp_capped_at_max_edge():
    out = shrink_image(_png((2700, 2700)))
    assert out is not None
    data, ext = out
    assert ext == ".webp"
    im = _open(data)
    assert im.format == "WEBP"
    assert im.size == (MAX_EDGE, MAX_EDGE)


def test_non_square_keeps_aspect_ratio():
    data, _ = shrink_image(_png((3000, 1500)))
    assert _open(data).size == (MAX_EDGE, MAX_EDGE // 2)


def test_transparency_survives():
    data, _ = shrink_image(_png((2000, 2000), color=(0, 0, 0, 0)))
    im = _open(data).convert("RGBA")
    assert im.getchannel("A").getextrema() == (0, 0)


def test_small_image_is_left_alone():
    assert shrink_image(_png((MAX_EDGE, MAX_EDGE))) is None


def test_animated_gif_is_left_alone():
    frames = [Image.new("RGB", (1200, 1200), c) for c in ((255, 0, 0), (0, 0, 255))]
    bio = io.BytesIO()
    frames[0].save(bio, "GIF", save_all=True, append_images=frames[1:])
    assert shrink_image(bio.getvalue()) is None


def test_non_image_bytes_are_left_alone():
    assert shrink_image(b"<svg xmlns='http://www.w3.org/2000/svg'/>") is None
    assert shrink_image(b"") is None
