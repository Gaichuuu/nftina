from scripts.trace_flows import build_summary

def test_build_summary_separates_flows():
    graph = {
        "nodes": [
            {"address": "0xdep", "kind": "eoa", "label": "MetaZoo: Deployer", "confidence": "confirmed"},
            {"address": "0x77", "kind": "eoa", "label": "MetaZoo: Deployer", "confidence": "confirmed"},
            {"address": "0xa6d3", "kind": "eoa", "label": "unlabeled", "confidence": "confirmed", "total_in_eth": 60.0},
            {"address": "0xe4", "kind": "eoa", "label": "Steve Aoki", "confidence": "confirmed", "total_in_eth": 30.0},
            {"address": "0x50", "kind": "eoa", "label": "unlabeled", "confidence": "confirmed", "total_in_eth": 25.0},
            {"address": "0xexch", "kind": "exchange", "label": "Kraken 4", "confidence": "leaf"},
            {"address": "0xmkt", "kind": "marketplace", "label": "OpenSea: Wyvern Exchange v1", "confidence": "leaf"},
            {"address": "0xbig", "kind": "eoa", "label": "unlabeled", "confidence": "leaf"},
        ],
        "edges": [
            {"from": "0xdep", "to": "0xa6d3", "eth_in": 0, "eth_out": 40, "tx_count": 2},
            {"from": "0x77", "to": "0xa6d3", "eth_in": 0, "eth_out": 20, "tx_count": 1},
            {"from": "0xa6d3", "to": "0x77", "eth_in": 0, "eth_out": 10, "tx_count": 1},   # return to MetaZoo
            {"from": "0xa6d3", "to": "0xe4", "eth_in": 0, "eth_out": 30, "tx_count": 1},   # internal (aoki->aoki)
            {"from": "0xa6d3", "to": "0x50", "eth_in": 0, "eth_out": 25, "tx_count": 1},   # internal (aoki->candidate)
            {"from": "0xe4", "to": "0xmkt", "eth_in": 0, "eth_out": 100, "tx_count": 3},   # NFT buy
            {"from": "0xa6d3", "to": "0xexch", "eth_in": 0, "eth_out": 120, "tx_count": 5},# cash-out
            {"from": "0xa6d3", "to": "0xbig", "eth_in": 0, "eth_out": 80, "tx_count": 1},  # unlabeled endpoint
        ],
        "caps_hit": {"max_depth": False, "max_nodes": False, "high_volume": False},
    }
    s = build_summary(graph, aoki_wallets=["0xa6d3", "0xe4"],
                      metazoo_wallets=["0xdep", "0x77"], candidate_wallets=["0x50"])
    assert s["metazoo_to_aoki_eth"] == 60          # 40 + 20
    assert s["aoki_to_metazoo_eth"] == 10
    o = s["aoki_outflow"]
    assert o["nft_marketplace_eth"] == 100
    assert o["cash_out_eth"] == 120
    assert o["by_exchange"]["Kraken 4"] == 120
    assert o["internal_cluster_eth"] == 55         # 30 + 25
    assert o["unlabeled_endpoints"]["count"] == 1 and o["unlabeled_endpoints"]["eth"] == 80
    assert s["aoki_wallet_inflow_eth"]["0xa6d3"] == 60.0
    assert "estimate" in s["disclaimer"].lower()

def test_build_summary_dedups_unlabeled_by_address():
    graph = {
        "nodes": [
            {"address": "0xa6d3", "kind": "eoa", "label": "unlabeled", "confidence": "confirmed", "total_in_eth": 0.0},
            {"address": "0xbig", "kind": "eoa", "label": "unlabeled", "confidence": "leaf"},
        ],
        "edges": [
            {"from": "0xa6d3", "to": "0xbig", "eth_in": 0, "eth_out": 5, "tx_count": 1},
            {"from": "0xa6d3", "to": "0xbig", "eth_in": 0, "eth_out": 7, "tx_count": 1},
        ],
        "caps_hit": {"max_depth": False, "max_nodes": False, "high_volume": False},
    }
    s = build_summary(graph, aoki_wallets=["0xa6d3"])
    assert s["aoki_outflow"]["unlabeled_endpoints"]["count"] == 1
    assert s["aoki_outflow"]["unlabeled_endpoints"]["eth"] == 12
