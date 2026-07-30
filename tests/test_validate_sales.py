"""Settlement validation (scripts/validate_sales.py)"""
import json

import pytest

from scripts import validate_sales as v

WETH = v.WETH
TOPIC = v.TRANSFER_TOPIC


def _log(addr, topic, data):
    return {"address": addr, "topics": [topic], "data": data}


def fake_get(tx=None, receipt=None, fail=None):
    """Stand in for validate_sales._get: returns the tx, then the receipt.
    `fail` picks which call returns None (an exhausted-retry API failure)."""
    calls = {"n": 0}

    def _get(params, api_key, retries=5):
        calls["n"] += 1
        which = "tx" if params["action"] == "eth_getTransactionByHash" else "receipt"
        if fail == which:
            return None
        return tx if which == "tx" else receipt
    _get.calls = calls
    return _get


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(v.time, "sleep", lambda *_: None)


def test_settlement_reads_eth_from_tx_value(monkeypatch):
    monkeypatch.setattr(v, "_get", fake_get(tx={"value": hex(2 * 10**18)}, receipt={"logs": []}))
    assert v.settlement_eth("0xh", "k") == pytest.approx(2.0)


def test_settlement_takes_the_largest_weth_transfer_for_an_accepted_offer(monkeypatch):
    logs = [_log(WETH, TOPIC, hex(int(0.3 * 10**18))),
            _log(WETH, TOPIC, hex(int(1.5 * 10**18))),      # the sale itself
            _log("0xother", TOPIC, hex(int(9 * 10**18))),   # a different token: ignored
            _log(WETH, "0xnottransfer", hex(int(9 * 10**18)))]
    monkeypatch.setattr(v, "_get", fake_get(tx={"value": "0x0"}, receipt={"logs": logs}))
    assert v.settlement_eth("0xh", "k") == pytest.approx(1.5)


def test_settlement_returns_none_on_api_failure_not_zero(monkeypatch):
    monkeypatch.setattr(v, "_get", fake_get(tx=None, fail="tx"))
    assert v.settlement_eth("0xh", "k") is None
    monkeypatch.setattr(v, "_get", fake_get(tx={"value": "0x0"}, fail="receipt"))
    assert v.settlement_eth("0xh", "k") is None


def test_settlement_zero_is_a_real_phantom_signal(monkeypatch):
    monkeypatch.setattr(v, "_get", fake_get(tx={"value": "0x0"}, receipt={"logs": []}))
    assert v.settlement_eth("0xh", "k") == 0.0


def test_validate_flags_phantoms_and_passes_settled_sales(monkeypatch, tmp_path):
    sales = [
        {"hash": "0xreal", "price_eth": 2.0},        # settles in full
        {"hash": "0xphantom", "price_eth": 404.0},   # a Wyvern order that never paid
        {"hash": "0xsmall", "price_eth": 0.05},      # below threshold: trusted as-is
    ]
    p = tmp_path / "coin_tokens_sales.json"
    p.write_text(json.dumps(sales))
    monkeypatch.setattr(v, "RAW", tmp_path)
    monkeypatch.setattr(v, "settlement_eth",
                        lambda h, k: {"0xreal": 2.0, "0xphantom": 0.0}[h])
    v.validate("coin_tokens", 1.0, "key")

    out = {s["hash"]: s for s in json.loads(p.read_text())}
    assert out["0xreal"]["is_phantom"] is False and out["0xreal"]["settled_eth"] == 2.0
    assert out["0xphantom"]["is_phantom"] is True
    assert out["0xsmall"]["is_phantom"] is False and out["0xsmall"]["settled_eth"] == 0.05


def test_validate_leaves_a_failed_lookup_unvalidated_for_the_next_run(monkeypatch, tmp_path):
    p = tmp_path / "coin_tokens_sales.json"
    p.write_text(json.dumps([{"hash": "0xa", "price_eth": 3.0}]))
    monkeypatch.setattr(v, "RAW", tmp_path)
    monkeypatch.setattr(v, "settlement_eth", lambda h, k: None)
    v.validate("coin_tokens", 1.0, "key")
    row = json.loads(p.read_text())[0]
    assert "is_phantom" not in row and "settled_eth" not in row


def test_validate_is_resumable_and_skips_already_settled_rows(monkeypatch, tmp_path):
    p = tmp_path / "coin_tokens_sales.json"
    p.write_text(json.dumps([{"hash": "0xa", "price_eth": 3.0,
                              "settled_eth": 3.0, "is_phantom": False}]))
    monkeypatch.setattr(v, "RAW", tmp_path)
    called = []
    monkeypatch.setattr(v, "settlement_eth", lambda h, k: called.append(h))
    v.validate("coin_tokens", 1.0, "key")
    assert called == []                      # no re-fetch of a validated sale


def test_validate_is_a_noop_when_the_collection_has_no_sales_file(tmp_path, monkeypatch):
    monkeypatch.setattr(v, "RAW", tmp_path)
    v.validate("never_fetched", 1.0, "key")  # must not raise
