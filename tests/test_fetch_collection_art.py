from scripts.fetch_token_media import collection_art_url, sniff_ext


def test_collection_art_url_prefers_opensea_image():
    meta = {"openSeaMetadata": {"imageUrl": "https://i2c.seadn.io/x/logo.png",
                                "bannerImageUrl": "https://i2c.seadn.io/x/banner.png"}}
    assert collection_art_url(meta) == "https://i2c.seadn.io/x/logo.png"


def test_collection_art_url_none_when_absent():
    assert collection_art_url({"openSeaMetadata": {"imageUrl": None}}) is None
    assert collection_art_url({}) is None


def test_sniff_ext_png():
    assert sniff_ext(b"\x89PNG\r\n\x1a\n" + b"restofbytes") == ".png"


def test_sniff_ext_gif():
    assert sniff_ext(b"GIF89a" + b"restofbytes") == ".gif"


def test_sniff_ext_jpg():
    assert sniff_ext(b"\xff\xd8\xff\xe0" + b"restofbytes") == ".jpg"


def test_sniff_ext_webp():
    data = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"restofbytes"
    assert sniff_ext(data) == ".webp"


def test_sniff_ext_avif():
    data = b"\x00\x00\x00\x18" + b"ftyp" + b"avif" + b"restofbytes"
    assert sniff_ext(data) == ".avif"


def test_sniff_ext_unknown_or_empty_falls_back():
    assert sniff_ext(b"not an image, plain text") == ""
    assert sniff_ext(b"") == ""
