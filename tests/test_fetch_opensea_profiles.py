from scripts.fetch_opensea_profiles import parse_profile


def test_parse_profile_extracts_username_and_pfp():
    p = parse_profile({"username": "cryptowhale", "profile_image_url": "https://i.seadn.io/x.png"})
    assert p == {"username": "cryptowhale", "pfp": "https://i.seadn.io/x.png"}


def test_parse_profile_partial():
    assert parse_profile({"username": "just_a_name", "profile_image_url": ""}) == {
        "username": "just_a_name", "pfp": None}
    assert parse_profile({"username": "", "profile_image_url": "https://p.png"}) == {
        "username": None, "pfp": "https://p.png"}


def test_parse_profile_none_when_empty():
    assert parse_profile({"username": "", "profile_image_url": ""}) is None
    assert parse_profile({}) is None
    assert parse_profile(None) is None


def test_rejects_opensea_auto_hash_username():
    p = parse_profile({"username": "dd6468a4b069c32fdbbd3eb635a614",
                       "display_name": "dd6468a4b069c32fdbbd3eb635a614",
                       "profile_image_url": "https://p.png"})
    assert p == {"username": None, "pfp": "https://p.png"}
    assert parse_profile({"username": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                          "profile_image_url": ""}) is None


def test_prefers_display_name_when_real():
    p = parse_profile({"display_name": "Crypto Whale", "username": "cryptowhale99",
                       "profile_image_url": "https://p.png"})
    assert p == {"username": "Crypto Whale", "pfp": "https://p.png"}
