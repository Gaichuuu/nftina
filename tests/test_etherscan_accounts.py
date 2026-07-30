from scripts.clients.etherscan import Etherscan, _PAGE_SIZE

def _mk(hash_, frm, to, value, block, action_ok=True):
    return {"hash": hash_, "from": frm, "to": to, "value": str(value),
            "blockNumber": str(block), "timeStamp": "100", "isError": "0"}

def test_account_txns_paginates_and_normalizes(monkeypatch):
    page1 = [_mk(f"0x{i:064x}", "0xAAA", "0xBBB", 10**18, 200 + i) for i in range(_PAGE_SIZE)]
    boundary = page1[-1]
    page2 = [boundary, _mk("0xffff", "0xAAA", "0xCCC", 2 * 10**18, 9000)]
    seq = {"txlist": [page1, page2], "txlistinternal": [[]]}
    idx = {"txlist": 0, "txlistinternal": 0}

    def fake_get(self, params, tries=6):
        act = params["action"]; i = idx[act]; idx[act] += 1
        res = seq[act][i] if i < len(seq[act]) else []
        return {"result": res}

    monkeypatch.setattr(Etherscan, "_get", fake_get)
    es = Etherscan("dummy", rate_delay=0)
    txns = es.account_txns("0xAaA")
    assert len(txns) == _PAGE_SIZE + 1
    assert all(t["kind"] == "normal" for t in txns)
    assert txns[0]["eth"] == 1.0 and txns[0]["from"] == "0xaaa"

def test_is_contract_caches(monkeypatch):
    calls = {"n": 0}
    def fake_get(self, params, tries=6):
        calls["n"] += 1
        return {"result": "0x60006000"}  # non-empty code
    monkeypatch.setattr(Etherscan, "_get", fake_get)
    es = Etherscan("dummy", rate_delay=0)
    assert es.is_contract("0xDEAD") is True
    assert es.is_contract("0xdead") is True   # cached, no 2nd call
    assert calls["n"] == 1

def test_is_contract_eoa(monkeypatch):
    monkeypatch.setattr(Etherscan, "_get", lambda self, params, tries=6: {"result": "0x"})
    assert Etherscan("d", rate_delay=0).is_contract("0xbeef") is False

def test_contract_creator_parse(monkeypatch):
    monkeypatch.setattr(Etherscan, "_get", lambda self, params, tries=6: {
        "result": [{"contractAddress": "0xC0", "contractCreator": "0xCreAtoR", "txHash": "0xabc"}]})
    out = Etherscan("d", rate_delay=0).contract_creator("0xC0")
    assert out == {"creator": "0xcreator", "tx_hash": "0xabc"}
