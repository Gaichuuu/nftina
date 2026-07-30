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
