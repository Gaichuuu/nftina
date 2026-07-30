from scripts.fetch_token_media import sandbox_assets


def test_sandbox_assets_extracts_model_and_image():
    meta = {"name": "Mothman",
            "image": {"originalUrl": "https://ipfs.io/ipfs/bafy/mothman.png"},
            "raw": {"metadata": {"animation_url": "ipfs://bafy/mothman.gltf",
                                 "image": "ipfs://bafy/mothman.png"}}}
    a = sandbox_assets(meta)
    assert a["name"] == "Mothman"
    assert a["model_ipfs"] == "ipfs://bafy/mothman.gltf"
    assert a["image_url"].endswith("mothman.png")


def test_sandbox_assets_none_without_model():
    assert sandbox_assets({"raw": {"metadata": {}}}) is None
