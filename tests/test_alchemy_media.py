from scripts.clients.alchemy import normalize_ipfs, pick_image_url


def test_normalize_ipfs_gateway():
    assert normalize_ipfs("ipfs://bafyABC/1.png") == "https://ipfs.io/ipfs/bafyABC/1.png"


def test_normalize_ipfs_passthrough_https():
    assert normalize_ipfs("https://x/y.png") == "https://x/y.png"


def test_normalize_ipfs_empty():
    assert normalize_ipfs("") == ""
    assert normalize_ipfs(None) == ""


def test_pick_image_prefers_cached_over_original():
    nft = {"image": {"cachedUrl": "https://cdn/c.png", "originalUrl": "ipfs://Q/o.png"}}
    assert pick_image_url(nft) == "https://cdn/c.png"


def test_pick_image_falls_back_to_original_ipfs_normalized():
    nft = {"image": {"cachedUrl": None, "originalUrl": "ipfs://Q/o.png"}}
    assert pick_image_url(nft) == "https://ipfs.io/ipfs/Q/o.png"


def test_pick_image_falls_back_to_raw_metadata_image():
    nft = {"image": {}, "raw": {"metadata": {"image": "ipfs://Q/r.png"}}}
    assert pick_image_url(nft) == "https://ipfs.io/ipfs/Q/r.png"


def test_pick_image_none_when_absent():
    assert pick_image_url({"image": {}, "raw": {"metadata": {}}}) == ""
