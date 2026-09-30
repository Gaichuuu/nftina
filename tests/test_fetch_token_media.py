from scripts.fetch_token_media import ext_from_url, img_filename, manifest_entries, acq_key


def test_ext_from_url():
    assert ext_from_url("https://x/a.png") == ".png"
    assert ext_from_url("https://x/a.jpeg?y=1") == ".jpeg"
    assert ext_from_url("https://x/a.gif") == ".gif"
    assert ext_from_url("https://x/nodext") == ".png"  # default


def test_img_filename_is_url_addressed_and_stable():
    a = img_filename("https://c/bigfoot.png", ".png")
    assert a == img_filename("https://c/bigfoot.png", ".png")   # deterministic
    assert a.endswith(".png") and len(a) == len("0123456789abcdef") + 4
    assert a != img_filename("https://c/mothman.png", ".png")   # different art differs


def test_manifest_entries_skips_imageless():
    nfts = [
        {"tokenId": "1", "name": "Bigfoot", "image": {"cachedUrl": "https://c/1.png"}},
        {"tokenId": "2", "name": "NoImage", "image": {}},
    ]
    m = manifest_entries(nfts, ext_from_url)
    assert set(m) == {"1"}
    assert m["1"]["name"] == "Bigfoot"
    assert m["1"]["source"] == "https://c/1.png"
    assert m["1"]["file"].endswith(".png")


def test_manifest_entries_dedup_shared_art():
    nfts = [
        {"tokenId": "1", "name": "Bigfoot Gold", "image": {"cachedUrl": "https://c/bigfoot.png"}},
        {"tokenId": "2", "name": "Bigfoot Gold", "image": {"cachedUrl": "https://c/bigfoot.png"}},
        {"tokenId": "3", "name": "Mothman Gold", "image": {"cachedUrl": "https://c/mothman.png"}},
    ]
    m = manifest_entries(nfts, ext_from_url)
    assert m["1"]["file"] == m["2"]["file"]      # shared art, shared file
    assert m["1"]["file"] != m["3"]["file"]      # distinct art, distinct file


def test_dedup_key_prefers_underlying_metadata_image():
    from scripts.fetch_token_media import dedup_key
    nft = {"image": {"cachedUrl": "https://cdn/per-token-abc.png"},
           "raw": {"metadata": {"image": "ipfs://Q/1.gif"}}}
    assert dedup_key(nft) == "https://ipfs.io/ipfs/Q/1.gif"


def test_dedup_key_falls_back_to_display_url():
    from scripts.fetch_token_media import dedup_key
    nft = {"image": {"cachedUrl": "https://cdn/x.png"}, "raw": {"metadata": {}}}
    assert dedup_key(nft) == "https://cdn/x.png"


def test_manifest_entries_dedup_by_underlying_art_not_cachedurl():
    nfts = [
        {"tokenId": "1", "name": "Token #1", "image": {"cachedUrl": "https://cdn/a1.png"},
         "raw": {"metadata": {"image": "ipfs://Q/1.gif"}}},
        {"tokenId": "2", "name": "Token #2", "image": {"cachedUrl": "https://cdn/a2.png"},
         "raw": {"metadata": {"image": "ipfs://Q/1.gif"}}},
        {"tokenId": "3", "name": "Token #3", "image": {"cachedUrl": "https://cdn/b1.png"},
         "raw": {"metadata": {"image": "ipfs://Q/2.gif"}}},
    ]
    m = manifest_entries(nfts, ext_from_url)
    assert m["1"]["file"] == m["2"]["file"]          # same underlying art -> one file
    assert m["1"]["file"] != m["3"]["file"]          # different art -> different file
    assert m["1"]["source"] == "https://cdn/a1.png"  # source stays the per-token cached copy
    assert m["2"]["source"] == "https://cdn/a2.png"


def test_download_jobs_runs_all_and_counts(monkeypatch):
    import scripts.fetch_token_media as m
    calls = []
    monkeypatch.setattr(m, "_download", lambda url, dest: (calls.append(url), url != "bad")[1])
    n = m._download_jobs([("a", "da"), ("bad", "db"), ("c", "dc")], workers=4)
    assert n == 2
    assert set(calls) == {"a", "bad", "c"}


def test_download_jobs_empty_is_zero():
    import scripts.fetch_token_media as m
    assert m._download_jobs([]) == 0


def test_manifest_entries_null_name_ok():
    nfts = [{"tokenId": "7", "name": None, "image": {"cachedUrl": "https://c/7.jpg"}}]
    m = manifest_entries(nfts, ext_from_url)
    assert m["7"]["name"] is None
    assert m["7"]["file"].endswith(".jpg")


def test_is_shared_flags_shared_contracts():
    from scripts.fetch_token_media import is_shared
    assert is_shared("genesis_reissue_1155") is True
    assert is_shared("coin_tokens") is False


def test_token_ids_from_transfers_distinct_ordered():
    from scripts.fetch_token_media import token_ids_from_transfers
    tr = [{"token_id": "5"}, {"token_id": "5"}, {"token_id": "9"}]
    assert token_ids_from_transfers(tr) == ["5", "9"]


def test_acq_key_lowercases_contract():
    assert acq_key("0xABC", "5") == "0xabc_5"


def test_sniff_ext_detects_svg():
    from scripts.fetch_token_media import sniff_ext
    assert sniff_ext(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>') == ".svg"
    assert sniff_ext(b'<?xml version="1.0"?>\n<svg width="24"></svg>') == ".svg"
    assert sniff_ext(b'\xef\xbb\xbf<svg></svg>') == ".svg"          # UTF-8 BOM
    assert sniff_ext(b"\x89PNG\r\n\x1a\n") == ".png"                # still PNG
    assert sniff_ext(b"<html><body>not an image</body>") == ""     # HTML != SVG


def _png_file(path, size):
    import io
    from PIL import Image
    bio = io.BytesIO()
    Image.new("RGBA", size, (1, 2, 3, 255)).save(bio, "PNG")
    path.write_bytes(bio.getvalue())


def test_shrink_token_art_replaces_oversized_png_with_webp(tmp_path):
    from scripts.fetch_token_media import shrink_token_art
    _png_file(tmp_path / "big.png", (2700, 2700))
    _png_file(tmp_path / "small.png", (400, 400))
    entries = {"1": {"file": "big.png"}, "2": {"file": "big.png"}, "3": {"file": "small.png"}}
    assert shrink_token_art(entries, tmp_path) == 1
    assert entries["1"]["file"] == entries["2"]["file"] == "big.webp"
    assert entries["3"]["file"] == "small.png"
    assert (tmp_path / "big.webp").exists() and not (tmp_path / "big.png").exists()
    assert (tmp_path / "small.png").exists()


def test_shrink_token_art_reuses_existing_webp(tmp_path):
    from scripts.fetch_token_media import shrink_token_art
    (tmp_path / "big.webp").write_bytes(b"already shrunk")
    entries = {"1": {"file": "big.png"}}
    assert shrink_token_art(entries, tmp_path) == 1
    assert entries["1"]["file"] == "big.webp"
    assert (tmp_path / "big.webp").read_bytes() == b"already shrunk"
