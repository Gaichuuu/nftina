import json

from scripts import identify_wallets as idf

RES = "0x000000000000000000000000000000000000d011"   # a fake resolver address


def _pad_addr(addr: str) -> str:
    return "0x" + addr[2:].lower().rjust(64, "0")


def _abi_string(s: str) -> str:
    raw = s.encode()
    body = raw.ljust((len(raw) + 31) // 32 * 32, b"\x00")
    return ("0x"
            + (32).to_bytes(32, "big").hex()          # offset
            + len(raw).to_bytes(32, "big").hex()      # length
            + body.hex())


def make_call_fn(name, forward_addr):
    """Fake ENS: resolver(node)->RES, name(node)->`name`, addr(node)->`forward_addr`.
    Dispatches on the 4-byte selector, independent of node."""
    def call_fn(to, data, tries=4):
        sel = data[:10]
        if sel == idf._SEL_RESOLVER:
            return _pad_addr(RES)
        if sel == idf._SEL_NAME:
            return _abi_string(name)
        if sel == idf._SEL_ADDR:
            return _pad_addr(forward_addr)
        return "0x"
    return call_fn


ADDR = "0x00000000000000000000000000000000000000a1"


def test_resolve_identity_verified_ens():
    fn = make_call_fn("alice.eth", forward_addr=ADDR)   # forward matches -> verified
    out = idf.resolve_identity(ADDR, labels={}, call_fn=fn)
    assert out["ens"] == "alice.eth"
    assert out["ens_verified"] is True
    assert out["label"] == "alice.eth"
    assert "verified" in out["source"]


def test_resolve_identity_unverified_ens_gets_no_label():
    fn = make_call_fn("alice.eth", forward_addr="0x00000000000000000000000000000000000000ff")
    out = idf.resolve_identity(ADDR, labels={}, call_fn=fn)
    assert out["ens"] == "alice.eth"
    assert out["ens_verified"] is False
    assert out["label"] is None
    assert "unverified" in out["source"]


def test_resolve_identity_curated_label_wins():
    fn = make_call_fn("alice.eth", forward_addr=ADDR)
    labels = {ADDR.lower(): {"label": "Steve Aoki", "type": "eoa", "source": "Etherscan tag"}}
    out = idf.resolve_identity(ADDR, labels=labels, call_fn=fn)
    assert out["label"] == "Steve Aoki"           # curated beats ENS
    assert out["ens"] == "alice.eth"              # ENS still reported alongside


def test_resolve_identity_anonymous():
    def fn(to, data, tries=4):
        return "0x"                               # no resolver -> no name
    out = idf.resolve_identity(ADDR, labels={}, call_fn=fn)
    assert out["ens"] is None
    assert out["label"] is None
    assert out["source"] is None


def test_decode_string_empty():
    assert idf._decode_string("0x") == ""
    assert idf._decode_string(None) == ""


def test_decode_addr_zero_is_none():
    assert idf._decode_addr("0x" + "0" * 64) is None
    assert idf._decode_addr(_pad_addr(ADDR)) == ADDR.lower()


def test_graph_wallets_returns_flow_nodes_biggest_volume_first(tmp_path, monkeypatch):
    """Flow-graph nodes were never resolved because displayed_wallets only read the
    holders/flippers tables. They are the investigation-relevant wallets,
    so they must be in the resolve set, highest-volume first: ranked by their
    incident EDGES."""
    flows = tmp_path / "treasury_flows.json"
    flows.write_text(json.dumps({
        "nodes": [
            {"address": "0xSMALL", "total_in_eth": 0.0, "total_out_eth": 0.0},
            {"address": "0xBIG", "total_in_eth": 0.0, "total_out_eth": 0.0},
            {"address": "0xMID", "total_in_eth": 5.0, "total_out_eth": 5.0},
        ],
        "edges": [
            {"from": "0xHUB", "to": "0xBIG", "eth_in": 900.0, "eth_out": 100.0},
            {"from": "0xHUB", "to": "0xMID", "eth_in": 5.0, "eth_out": 5.0},
            {"from": "0xHUB", "to": "0xSMALL", "eth_in": 1.0, "eth_out": 0.0},
        ],
    }))
    monkeypatch.setattr(idf, "TREASURY_FLOWS", flows)
    assert idf.graph_wallets() == ["0xbig", "0xmid", "0xsmall"]


def test_graph_wallets_absent_file_degrades_to_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(idf, "TREASURY_FLOWS", tmp_path / "nope.json")
    assert idf.graph_wallets() == []


def test_displayed_wallets_appends_graph_nodes_without_duplicating(tmp_path, monkeypatch):
    monkeypatch.setattr(idf, "FLIPPERS", tmp_path / "flippers.json")
    idf.FLIPPERS.write_text(json.dumps([{"wallet": "0xAAA"}]))
    monkeypatch.setattr(idf, "HOLDERS_GLOB", tmp_path / "collections")
    monkeypatch.setattr(idf, "graph_wallets", lambda: ["0xaaa", "0xnew"])
    out = idf.displayed_wallets(top=10)
    assert out == ["0xaaa", "0xnew"]          # 0xaaa not repeated
