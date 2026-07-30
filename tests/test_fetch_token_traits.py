from scripts.fetch_token_traits import _trait


def _nft(attrs):
    return {"raw": {"metadata": {"attributes": attrs}}}


def test_trait_extracts_matching_trait_type():
    nft = _nft([{"trait_type": "Type", "value": "Mothman Gold"},
                {"trait_type": "Coin Metal", "value": "Gold"}])
    assert _trait(nft, "Type") == "Mothman Gold"
    assert _trait(nft, "Coin Metal") == "Gold"


def test_trait_returns_none_when_absent_or_empty():
    assert _trait(_nft([{"trait_type": "Base", "value": "Bigfoot"}]), "Type") is None
    assert _trait(_nft([]), "Type") is None
    assert _trait({"raw": {"metadata": {}}}, "Type") is None       # no attributes key
    assert _trait({}, "Type") is None                               # no raw metadata


def test_trait_stringifies_non_string_values():
    assert _trait(_nft([{"trait_type": "Type", "value": 7}]), "Type") == "7"
