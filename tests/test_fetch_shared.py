"""Tests for the token-ID-filtered fetch of MetaZoo collections inside shared
contracts: Etherscan.token_transfers_for_holder + Alchemy.sales_for_tokens."""
from scripts.clients.etherscan import Etherscan, ZERO
from scripts.clients.alchemy import Alchemy


def _t(tid, frm, to, block):
    return {"hash": f"0x{block:064x}", "tokenID": str(tid), "from": frm, "to": to,
            "blockNumber": str(block), "timeStamp": "100", "tokenValue": "1"}


def test_token_transfers_for_holder_filters_to_requested_ids(monkeypatch):
    """A shared contract query filtered by the distributor still returns tokens the
    distributor merely received from unrelated creators — token_ids must drop them."""
    distributor = "0x77b94a55684c95d59a8f56a234b6e555fc79997c"
    page = [
        _t("111", distributor, "0xholder1", 10),
        _t("222", distributor, "0xholder2", 11),
        _t("999", "0xstranger", distributor, 12),   # incidental receipt
    ]
    calls = {"n": 0}

    def fake_get(self, params, tries=6):
        calls["n"] += 1
        return {"result": page if calls["n"] == 1 else []}

    monkeypatch.setattr(Etherscan, "_get", fake_get)
    es = Etherscan("dummy", rate_delay=0)
    out = es.token_transfers_for_holder(
        "0xSHARED", "erc1155", distributor.upper(), token_ids=["111", "222"])
    assert {t["token_id"] for t in out} == {"111", "222"}   # 999 dropped
    assert all(t["from"] == t["from"].lower() for t in out)
    assert out[0]["standard"] == "erc1155"


def test_token_transfers_for_holder_keeps_all_when_no_ids(monkeypatch):
    distributor = "0xabc0000000000000000000000000000000000abc"
    page = [_t("111", distributor, "0xh1", 10), _t("999", "0xstranger", distributor, 12)]
    calls = {"n": 0}

    def fake_get(self, params, tries=6):
        calls["n"] += 1
        return {"result": page if calls["n"] == 1 else []}

    monkeypatch.setattr(Etherscan, "_get", fake_get)
    es = Etherscan("dummy", rate_delay=0)
    out = es.token_transfers_for_holder("0xSHARED", "erc1155", distributor)
    assert {t["token_id"] for t in out} == {"111", "999"}   # unfiltered


def _sale(tid, amt="1000000000000000000"):
    return {"tokenId": str(tid), "sellerAddress": "0xSeller", "buyerAddress": "0xBuyer",
            "transactionHash": f"0x{tid}", "blockNumber": 1, "marketplace": "opensea",
            "sellerFee": {"amount": amt, "decimals": 18},
            "royaltyFee": {"amount": "0", "decimals": 18},
            "protocolFee": {"amount": "0", "decimals": 18}}


def test_sales_for_tokens_queries_each_id_and_concatenates(monkeypatch):
    """Whole-contract sales() is infeasible on a shared storefront; sales_for_tokens
    must query getNFTSales once per token ID and concatenate, paginating each."""
    seen_token_ids, pages = [], {}

    def fake_get(self, path, params, tries=5):
        assert path == "getNFTSales"
        tid = params["tokenId"]
        seen_token_ids.append(tid)
        if tid == "A" and "pageKey" not in params:
            return {"nftSales": [_sale("A")], "pageKey": "p2"}
        if tid == "A":
            return {"nftSales": [_sale("A")]}
        return {"nftSales": [_sale("B")]}

    monkeypatch.setattr(Alchemy, "_get", fake_get)
    al = Alchemy("dummy", rate_delay=0)
    out = al.sales_for_tokens("0xSHARED", ["A", "B"])
    assert len(out) == 3                       # A(2 pages) + B(1)
    assert {"A", "B"} == set(seen_token_ids)
    assert all(s["price_eth"] == 1.0 for s in out)
    assert all(s["collection"] == "0xSHARED" for s in out)


def test_sales_for_tokens_empty(monkeypatch):
    monkeypatch.setattr(Alchemy, "_get", lambda self, path, params, tries=5: {"nftSales": []})
    assert Alchemy("d", rate_delay=0).sales_for_tokens("0xC", ["1", "2"]) == []


# --- Shared/subset keys must not double-count a parent contract ---

def test_subset_keys_are_excluded_from_totals():
    """mothman_1of1 (token_id), wilderness (token_ids), and certain shared keys are token-ID
    subsets whose economics belong to a canonical key — analyze must skip them or it
    double-counts the shared contract. But tournament_prizes is canonical for its own tokens
    (creator 0x3dd341…, distinct from genesis_reissue_1155's 0x77b9…) so is NOT a subset."""
    from scripts.analyze import is_subset_key
    from scripts.config import CONTRACTS
    assert is_subset_key(CONTRACTS["mothman_1of1"]) is True      # single token inside aoki
    assert is_subset_key(CONTRACTS["wilderness"]) is True        # token subset inside valentines
    assert is_subset_key(CONTRACTS["tournament_prizes"]) is False # canonical for its 3 trophies (distributor 0x3dd341…)
    assert is_subset_key(CONTRACTS["mintable_early"]) is False
    assert is_subset_key(CONTRACTS["sandbox"]) is True           # shared Sandbox ASSETS store
    assert is_subset_key(CONTRACTS["aoki"]) is False
    assert is_subset_key(CONTRACTS["valentines"]) is False
    assert is_subset_key(CONTRACTS["coin_tokens"]) is False
    assert is_subset_key(CONTRACTS["genesis_reissue_1155"]) is False


def test_fetch_chain_skips_shared_and_subset_keys():
    """The documented `fetch_chain` (all contracts) run must not whole-fetch a subset key
    (would duplicate a parent contract) or a shared storefront (millions of records)."""
    from scripts.fetch_chain import is_shared_or_subset
    from scripts.config import CONTRACTS
    for k in ("genesis_reissue_1155", "tournament_prizes", "mothman_1of1", "wilderness",
              "mintable_early", "sandbox"):
        assert is_shared_or_subset(CONTRACTS[k]) is True, k
    for k in ("coin_tokens", "beasties_s1", "aoki", "valentines", "pfp_2", "genesis_2021"):
        assert is_shared_or_subset(CONTRACTS[k]) is False, k


# --- An API failure must not permanently flag a real sale phantom ---

def test_settlement_eth_returns_none_on_api_failure(monkeypatch):
    """When the tx or receipt lookup fails (_get returns None after retries), settlement_eth
    must return None (a 'could not determine' signal)."""
    import scripts.validate_sales as vs
    monkeypatch.setattr(vs, "_get", lambda params, api_key, retries=5: None)
    assert vs.settlement_eth("0xabc", "key") is None


def test_settlement_eth_genuine_zero_is_zero(monkeypatch):
    """A tx that truly settled 0 (success, value 0x0, no WETH logs) must return 0.0."""
    import scripts.validate_sales as vs

    def fake_get(params, api_key, retries=5):
        if params["action"] == "eth_getTransactionByHash":
            return {"value": "0x0"}
        return {"logs": []}                       # receipt, no WETH transfers

    monkeypatch.setattr(vs, "_get", fake_get)
    assert vs.settlement_eth("0xabc", "key") == 0.0
