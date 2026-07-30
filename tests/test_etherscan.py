import json
from pathlib import Path
from scripts.clients.etherscan import normalize_transfer, ZERO, Etherscan, _PAGE_SIZE

FIX = Path(__file__).parent / "fixtures"

def test_normalize_lowercases_and_flags_mint():
    raw = json.loads((FIX / "etherscan_tokentx_coin_tokens.json").read_text())
    out = [normalize_transfer(r, "coin_tokens", "erc721") for r in raw]
    assert all(t["from"] == t["from"].lower() for t in out)
    assert all(t["to"] == t["to"].lower() for t in out)
    mints = [t for t in out if t["is_mint"]]
    assert all(t["from"] == ZERO for t in mints)
    assert all(t["quantity"] >= 1 for t in out)
    assert len(mints) > 0


def test_paginate_collects_all_pages_and_dedups(monkeypatch):
    """Regression for the 1000-cap truncation bug: a full _PAGE_SIZE page must
    trigger another request (advancing by block), and the 1-block overlap at each
    window boundary must be deduped"""
    def rec(block, tok):
        return {"hash": f"0x{block}_{tok}", "tokenID": str(tok),
                "to": "0xAbC", "from": ZERO, "blockNumber": str(block),
                "timeStamp": "1", "value": "0"}

    page1 = [rec(100 + i, i) for i in range(_PAGE_SIZE)]          # ends at block 100+999
    boundary = page1[-1]
    page2 = [boundary] + [rec(1100 + i, _PAGE_SIZE + i) for i in range(_PAGE_SIZE - 1)]
    page3 = [rec(3000 + i, 5000 + i) for i in range(3)]           # partial → last page

    calls = {"n": 0}
    responses = [page1, page2, page3]

    def fake_get(self, params, tries=6):
        i = calls["n"]
        calls["n"] += 1
        return {"result": responses[i] if i < len(responses) else []}

    monkeypatch.setattr(Etherscan, "_get", fake_get)
    es = Etherscan("dummy", rate_delay=0)
    got = es._paginate_by_block({"module": "account", "action": "tokennfttx"}, "test")

    assert len(got) == _PAGE_SIZE + (_PAGE_SIZE - 1) + 3
    keys = {(r["hash"], r["tokenID"], r["to"]) for r in got}
    assert len(keys) == len(got)  # fully deduped
