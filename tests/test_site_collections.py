from scripts.config import SITE_COLLECTIONS, SANDBOX_TOKEN_IDS, CONTRACTS

VALID_SOURCES = {"own", "subset", "placeholder", "showcase"}

def test_ten_collections_in_display_order():
    slugs = [c["slug"] for c in SITE_COLLECTIONS]
    assert slugs == ["genesis_2021", "genesis_reissue_1155", "coin_tokens",
                     "beasties_s1", "pfp_2", "valentines", "wilderness",
                     "tournament_prizes", "mothman_1of1", "sandbox"]

def test_every_entry_well_formed():
    for c in SITE_COLLECTIONS:
        assert c["source"] in VALID_SOURCES
        assert c["name"].startswith("MetaZoo")
        if c["source"] == "subset":
            assert c["parent"] in CONTRACTS and c["token_ids"]
        if c["source"] == "placeholder":
            assert c["note"]

def test_subset_parents_are_real_slugs():
    assert next(c for c in SITE_COLLECTIONS if c["slug"] == "wilderness")["parent"] == "valentines"
    assert next(c for c in SITE_COLLECTIONS if c["slug"] == "mothman_1of1")["parent"] == "aoki"

def test_sandbox_has_six_token_ids():
    assert len(SANDBOX_TOKEN_IDS) == 6

def test_tournament_prizes_fetch_config():
    tp = CONTRACTS["tournament_prizes"]
    assert tp.get("distributor", "").lower() == "0x3dd341664b2ffeedf9be108d4fa926dedfa9a0d6"
    assert len(tp.get("token_ids") or []) == 3
    assert tp.get("creator_encoded") is True

def test_mintable_early_fetch_and_merge_config():
    m = CONTRACTS["mintable_early"]
    assert m.get("distributor", "").lower() == "0x3dd341664b2ffeedf9be108d4fa926dedfa9a0d6"
    assert m.get("creator_encoded") is True
    assert m.get("merge_into") == "genesis_2021"
    assert m.get("token_ids") is None
    assert m.get("shared") is True
