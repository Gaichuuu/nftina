from scripts.trace_core import aggregate_counterparties, should_recurse, trace

def _t(frm, to, eth, kind="normal", is_error=False):
    return {"from": frm, "to": to, "eth": eth, "kind": kind, "is_error": is_error,
            "hash": "0x1", "timestamp": 1}

def test_aggregate_directions_and_skips_errors_and_self():
    txns = [_t("0xC", "0xA", 5.0), _t("0xA", "0xD", 3.0),
            _t("0xC", "0xA", 1.0), _t("0xA", "0xA", 9.0),
            _t("0xC", "0xA", 100.0, is_error=True)]
    agg = aggregate_counterparties("0xA", txns)
    assert agg["0xc"] == {"eth_in": 6.0, "eth_out": 0.0, "tx_count": 2}
    assert agg["0xd"] == {"eth_in": 0.0, "eth_out": 3.0, "tx_count": 1}
    assert "0xa" not in agg  # self-transfer ignored

def test_should_recurse_bidirectional():
    assert should_recurse({"eth_in": 30, "eth_out": 26}, from_confirmed=False) is True
    assert should_recurse({"eth_in": 30, "eth_out": 10}, from_confirmed=False) is False

def test_should_recurse_oneway_only_from_confirmed():
    assert should_recurse({"eth_in": 60, "eth_out": 0}, from_confirmed=True) is True
    assert should_recurse({"eth_in": 60, "eth_out": 0}, from_confirmed=False) is False

def test_trace_recurses_eoa_over_threshold_but_not_exchange():
    graph = {
        "0xa": [_t("0xa", "0xexch", 200.0), _t("0xa", "0xeoa2", 30.0), _t("0xeoa2", "0xa", 30.0)],
        "0xeoa2": [_t("0xeoa2", "0xleaf", 5.0)],
    }
    kinds = {"0xexch": "exchange", "0xeoa2": "eoa", "0xleaf": "eoa", "0xa": "eoa"}
    out = trace(["0xa"], fetch_txns=lambda a, mr=None: graph.get(a, []),
                classify_fn=lambda a: {"kind": kinds.get(a, "eoa"), "label": a},
                is_confirmed=lambda a: a == "0xa")
    addrs = {n["address"] for n in out["nodes"]}
    assert "0xeoa2" in addrs                       # recursed (30/30 bidirectional)
    assert next(n for n in out["nodes"] if n["address"] == "0xexch")["confidence"] == "leaf"
    assert next(n for n in out["nodes"] if n["address"] == "0xeoa2")["confidence"] == "candidate"
    assert next(n for n in out["nodes"] if n["address"] == "0xleaf")["confidence"] == "leaf"

def test_trace_node_cap_logs_drop():
    seed_txns = []
    for i in range(10):
        a = f"0x{i:02x}"
        seed_txns += [_t("0xa", a, 30.0), _t(a, "0xa", 30.0)]
    logs = []
    out = trace(["0xa"], fetch_txns=lambda x, mr=None: seed_txns if x == "0xa" else [],
                classify_fn=lambda a: {"kind": "eoa", "label": a},
                is_confirmed=lambda a: a == "0xa", max_nodes=4, log=logs.append)
    assert len(out["nodes"]) <= 4
    assert out["caps_hit"]["max_nodes"] is True
    assert any("cap" in m.lower() for m in logs)

def test_should_recurse_exact_boundary():
    assert should_recurse({"eth_in": 25.0, "eth_out": 25.0}, from_confirmed=False) is True
    assert should_recurse({"eth_in": 24.999, "eth_out": 24.999}, from_confirmed=False) is False
    assert should_recurse({"eth_in": 50.0, "eth_out": 0.0}, from_confirmed=True) is True
    assert should_recurse({"eth_in": 49.999, "eth_out": 0.0}, from_confirmed=True) is False

def test_trace_node_cap_applies_to_leaves():
    txns = [_t("0xa", f"0x{i:02x}", 1.0) for i in range(10)]
    logs = []
    out = trace(["0xa"], fetch_txns=lambda x, mr=None: txns if x == "0xa" else [],
                classify_fn=lambda a: {"kind": "eoa", "label": a},
                is_confirmed=lambda a: a == "0xa", max_nodes=4, log=logs.append)
    assert len(out["nodes"]) <= 4
    assert out["caps_hit"]["max_nodes"] is True
    assert any("cap" in m.lower() for m in logs)

def test_trace_max_depth_cap_logs():
    graph = {"0xa": [_t("0xa", "0xb", 30.0), _t("0xb", "0xa", 30.0)],
             "0xb": [_t("0xb", "0xc", 30.0), _t("0xc", "0xb", 30.0)]}
    logs = []
    out = trace(["0xa"], fetch_txns=lambda a, mr=None: graph.get(a, []),
                classify_fn=lambda a: {"kind": "eoa", "label": a},
                is_confirmed=lambda a: a == "0xa", max_depth=1, log=logs.append)
    b = next(n for n in out["nodes"] if n["address"] == "0xb")
    c = next(n for n in out["nodes"] if n["address"] == "0xc")
    assert b["confidence"] == "candidate"
    assert c["confidence"] == "leaf"
    assert out["caps_hit"]["max_depth"] is True
    assert any("depth" in m.lower() for m in logs)

def test_trace_promotes_leaf_when_later_edge_qualifies():
    graph = {
        "0xa": [_t("0xa", "0xw", 5.0)],
        "0xb": [_t("0xb", "0xw", 30.0), _t("0xw", "0xb", 30.0)],
        "0xw": [_t("0xw", "0xz", 1.0)],
    }
    out = trace(["0xa", "0xb"], fetch_txns=lambda a, mr=None: graph.get(a, []),
                classify_fn=lambda a: {"kind": "eoa", "label": a},
                is_confirmed=lambda a: a in ("0xa", "0xb"))
    w = next(n for n in out["nodes"] if n["address"] == "0xw")
    assert w["confidence"] == "candidate"
    assert any(n["address"] == "0xz" for n in out["nodes"])

def test_trace_flags_high_volume_endpoint_and_skips_expansion():
    big = [_t("0xbig", f"0x{i:02x}", 1.0) for i in range(6)] + [_t("0xbig", "0xhidden", 99.0)]
    graph = {"0xa": [_t("0xa", "0xbig", 30.0), _t("0xbig", "0xa", 30.0)], "0xbig": big}
    logs = []
    out = trace(["0xa"], fetch_txns=lambda a, mr=None: graph.get(a, []),
                classify_fn=lambda a: {"kind": "eoa", "label": a},
                is_confirmed=lambda a: a == "0xa",
                max_txns_per_expansion=3, log=logs.append)
    bignode = next(n for n in out["nodes"] if n["address"] == "0xbig")
    assert bignode["high_volume"] is True
    assert out["caps_hit"]["high_volume"] is True
    assert not any(n["address"] == "0xhidden" for n in out["nodes"])  # not expanded
    assert any("high-volume" in m.lower() for m in logs)

def test_trace_seed_never_capped_even_if_huge():
    big = [_t("0xa", f"0x{i:02x}", 30.0) for i in range(50)]
    out = trace(["0xa"], fetch_txns=lambda a, mr=None: big if a == "0xa" else [],
                classify_fn=lambda a: {"kind": "eoa", "label": a},
                is_confirmed=lambda a: a == "0xa", max_txns_per_expansion=3)
    seed = next(n for n in out["nodes"] if n["address"] == "0xa")
    assert seed["high_volume"] is False
