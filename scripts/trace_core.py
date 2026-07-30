"""Targeted-BFS flow-trace core. Pure logic with dependency-injected fetch/classify
so it runs offline in tests. Recurse only into EOAs that meet the linkage threshold;
classify everything else as a leaf. Hard caps on depth and node count, logged."""
from collections import deque

LINK_MIN_BIDIRECTIONAL = 25.0          # min(eth_in, eth_out) to recurse into an EOA
LINK_MIN_ONEWAY_FROM_CONFIRMED = 50.0  # one-way flow from a confirmed node
MAX_DEPTH = 3
MAX_NODES = 150
MAX_TXNS_PER_EXPANSION = 10000         # depth>0: a wallet this busy is a service/
                                       # exchange endpoint


def aggregate_counterparties(address: str, txns: list) -> dict:
    a = address.lower()
    agg = {}
    for t in txns:
        if t.get("is_error") or t["eth"] <= 0:
            continue
        frm, to = t["from"].lower(), t["to"].lower()
        if to == a and frm != a:
            e = agg.setdefault(frm, {"eth_in": 0.0, "eth_out": 0.0, "tx_count": 0})
            e["eth_in"] += t["eth"]; e["tx_count"] += 1
        elif frm == a and to != a:
            e = agg.setdefault(to, {"eth_in": 0.0, "eth_out": 0.0, "tx_count": 0})
            e["eth_out"] += t["eth"]; e["tx_count"] += 1
    return agg


def should_recurse(edge: dict, from_confirmed: bool) -> bool:
    if min(edge["eth_in"], edge["eth_out"]) >= LINK_MIN_BIDIRECTIONAL:
        return True
    return from_confirmed and max(edge["eth_in"], edge["eth_out"]) >= LINK_MIN_ONEWAY_FROM_CONFIRMED


def trace(seed, fetch_txns, classify_fn, is_confirmed,
          max_depth=MAX_DEPTH, max_nodes=MAX_NODES,
          max_txns_per_expansion=MAX_TXNS_PER_EXPANSION, log=print) -> dict:
    """`fetch_txns(addr, max_records)` returns the wallet's transfers, capped to
    `max_records` rows (None = uncapped)."""
    seed = [s.lower() for s in seed]
    nodes, edges, enqueued = {}, [], set()
    caps_hit = {"max_depth": False, "max_nodes": False, "high_volume": False}

    def add_node(addr, depth, confidence, c):
        nodes[addr] = {"address": addr, "label": c["label"], "kind": c["kind"],
                       "confidence": "confirmed" if is_confirmed(addr) else confidence,
                       "depth": depth, "total_in_eth": 0.0, "total_out_eth": 0.0,
                       "high_volume": False}

    q = deque()
    for s in seed:
        add_node(s, 0, "confirmed", classify_fn(s))
        q.append((s, 0)); enqueued.add(s)

    processed = 0
    while q:
        addr, depth = q.popleft()
        processed += 1
        cap = None if depth == 0 else max_txns_per_expansion
        txns = fetch_txns(addr, cap)
        node = nodes[addr]
        if cap is not None and len(txns) >= cap:
            node["high_volume"] = True
            caps_hit["high_volume"] = True
            log(f"  [{processed}] lvl={depth} HIGH-VOLUME endpoint "
                f"(>={cap} txns), not expanded: {addr[:12]}")
            continue
        log(f"  [{processed}] lvl={depth} queued={len(q)} total={len(nodes)} {addr[:12]}")
        for cp, edge in aggregate_counterparties(addr, txns).items():
            node["total_in_eth"] += edge["eth_in"]
            node["total_out_eth"] += edge["eth_out"]
            edges.append({"from": addr, "to": cp,
                          "eth_in": round(edge["eth_in"], 6),
                          "eth_out": round(edge["eth_out"], 6),
                          "tx_count": edge["tx_count"]})
            c = classify_fn(cp)
            strong = c["kind"] == "eoa" and should_recurse(edge, is_confirmed(addr))
            expandable = strong and depth + 1 <= max_depth
            if strong and not expandable:
                caps_hit["max_depth"] = True
            if cp in nodes:
                if expandable and cp not in enqueued:
                    nodes[cp]["confidence"] = "candidate"
                    q.append((cp, nodes[cp]["depth"])); enqueued.add(cp)
                continue
            if len(nodes) >= max_nodes:
                caps_hit["max_nodes"] = True
                continue
            add_node(cp, depth + 1, "candidate" if expandable else "leaf", c)
            if expandable:
                q.append((cp, depth + 1)); enqueued.add(cp)

    if caps_hit["max_nodes"]:
        log(f"  [cap] max_nodes={max_nodes} reached; further counterparties not added to the graph")
    if caps_hit["max_depth"]:
        log(f"  [cap] max_depth={max_depth} reached; deeper strongly-linked wallets not expanded")
    for n in nodes.values():
        n["total_in_eth"] = round(n["total_in_eth"], 6)
        n["total_out_eth"] = round(n["total_out_eth"], 6)
    return {"nodes": list(nodes.values()), "edges": edges, "caps_hit": caps_hit}
