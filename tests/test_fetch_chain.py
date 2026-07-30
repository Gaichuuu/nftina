"""scripts/fetch_chain.py the whole-contract fetch. Its skip rules are what keep
a shared storefront's other tenants (and a subset's parent) out of data/raw."""
import json

from scripts import fetch_chain as fc


def test_is_shared_or_subset_skips_every_shape_that_must_not_be_whole_fetched():
    assert fc.is_shared_or_subset({"distributor": "0xd", "address": "0xc"})
    assert fc.is_shared_or_subset({"token_id": "1017", "address": "0xc"})
    assert fc.is_shared_or_subset({"token_ids": [7, 8], "address": "0xc"})
    assert fc.is_shared_or_subset({"shared": True, "address": "0xc"})
    assert not fc.is_shared_or_subset({"address": "0xdedicated", "standard": "erc721"})


def test_is_shared_or_subset_backstops_on_a_known_storefront_address(monkeypatch):
    monkeypatch.setattr(fc, "_STOREFRONT_ADDRS", {"0xstore"})
    assert fc.is_shared_or_subset({"address": "0xstore"})


class FakeEs:
    def __init__(self, transfers, standard="erc721"):
        self._t, self._s = transfers, standard
        self.fetched = []

    def detect_standard(self, addr):
        return self._s

    def token_transfers(self, addr, standard):
        self.fetched.append((addr, standard))
        return [dict(t) for t in self._t]

    def tx_values(self, hashes):
        return {h: 0.1 for h in sorted(hashes)}


def _run(tmp_path, monkeypatch, meta, transfers=None, force=False, standard="erc721"):
    monkeypatch.setattr(fc, "RAW", tmp_path)
    es = FakeEs(transfers if transfers is not None else [], standard)
    fc.fetch_one(es, "coin_tokens", meta, force)
    return es


def test_fetch_one_tags_every_transfer_with_the_CONFIG_KEY_not_the_address(tmp_path, monkeypatch):
    transfers = [{"hash": "0xm", "token_id": "1", "is_mint": True, "collection": "0xCONTRACT"},
                 {"hash": "0xx", "token_id": "1", "is_mint": False, "collection": "0xCONTRACT"}]
    _run(tmp_path, monkeypatch, {"address": "0xc", "name": "Coin", "standard": "erc721"}, transfers)
    saved = json.loads((tmp_path / "coin_tokens_transfers.json").read_text())
    assert {t["collection"] for t in saved} == {"coin_tokens"}


def test_fetch_one_resolves_mint_values_for_mint_hashes_only(tmp_path, monkeypatch):
    transfers = [{"hash": "0xm1", "token_id": "1", "is_mint": True},
                 {"hash": "0xm1", "token_id": "2", "is_mint": True},   # same batch tx
                 {"hash": "0xsale", "token_id": "1", "is_mint": False}]
    _run(tmp_path, monkeypatch, {"address": "0xc", "name": "Coin", "standard": "erc721"}, transfers)
    vals = json.loads((tmp_path / "coin_tokens_mintvalues.json").read_text())
    assert set(vals) == {"0xm1"}          # one entry per unique mint TX, not per token


def test_fetch_one_skips_a_cached_collection_unless_forced(tmp_path, monkeypatch):
    (tmp_path / "coin_tokens_transfers.json").write_text("[]")
    es = _run(tmp_path, monkeypatch, {"address": "0xc", "name": "Coin", "standard": "erc721"})
    assert es.fetched == []
    es = _run(tmp_path, monkeypatch, {"address": "0xc", "name": "Coin", "standard": "erc721"},
              transfers=[], force=True)
    assert es.fetched == [("0xc", "erc721")]


def test_fetch_one_skips_addressless_imx_and_shared_entries(tmp_path, monkeypatch):
    for meta in ({"name": "n"},                                        # no address
                 {"address": "0xc", "name": "n", "standard": "imx"},   # L2, not on Etherscan
                 {"address": "0xc", "name": "n", "distributor": "0xd"}):
        es = _run(tmp_path, monkeypatch, meta)
        assert es.fetched == []
    assert not (tmp_path / "coin_tokens_transfers.json").exists()


def test_fetch_one_prefers_the_config_standard_but_detects_when_it_is_unusable(tmp_path, monkeypatch):
    es = _run(tmp_path, monkeypatch, {"address": "0xc", "name": "n", "standard": "erc1155"},
              transfers=[], standard="erc721")
    assert es.fetched == [("0xc", "erc1155")]
    es = _run(tmp_path, monkeypatch, {"address": "0xc", "name": "n", "standard": None},
              transfers=[], standard="erc1155", force=True)
    assert es.fetched == [("0xc", "erc1155")]
