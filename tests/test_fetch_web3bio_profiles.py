from scripts.fetch_web3bio_profiles import parse_web3bio


def test_prefers_ens_then_farcaster_and_first_avatar():
    profiles = [
        {"platform": "ethereum", "identity": "0xabc", "displayName": "0xabc", "avatar": None},
        {"platform": "farcaster", "identity": "whale", "displayName": "Whale", "avatar": "https://fc.png"},
        {"platform": "ens", "identity": "whale.eth", "displayName": "whale.eth", "avatar": None},
    ]
    out = parse_web3bio(profiles)
    assert out["username"] == "whale.eth"           # ens ordered before farcaster
    assert out["pfp"] == "https://fc.png"           # first non-null avatar across profiles


def test_none_when_only_raw_address():
    assert parse_web3bio([{"platform": "ethereum", "identity": "0xabc",
                           "displayName": "0xabc", "avatar": None}]) is None
    assert parse_web3bio([]) is None
    assert parse_web3bio(None) is None


def test_avatar_only_identity():
    out = parse_web3bio([{"platform": "lens", "identity": "x.lens",
                          "displayName": None, "avatar": "https://a.png"}])
    assert out == {"username": "x.lens", "pfp": "https://a.png"}
