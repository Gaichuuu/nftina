"""Insider cash-out audit: follow every MetaZoo insider payment forward, hop by
hop, until it reaches a terminal endpoint

Live-trace investigation script:

    python -m scripts.audit_insider_cashout

Writes data/evidence/insider_cashout_audit.json
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from scripts.clients.etherscan import Etherscan
from scripts.wallet_labeling import load_labels

ROOT = Path(__file__).resolve().parent.parent

INSIDER_PAYMENTS = [
    {"addr": "0xccc55c38603ad1a1dc54db871166fa90f78edd11", "eth": 104.448, "date": "2021-12-06"},
    {"addr": "0xe693fbc0df4db03d3b75017b7a423dd38d49487c", "eth": 17.931, "date": "2021-12-06 / 2022-07-27"},
    {"addr": "0x37eccdcbc448e07cb19331277aebf9b13ec5a6a3", "eth": 130.000, "date": "2022-07-27"},
    {"addr": "0x08b96fad98c2366f6e483de584167dd695d30c27", "eth": 7.370, "date": "2022-07-27"},
    {"addr": "0x2f7eb4f5d083c5607f1f1ec278728323a84acc6b", "eth": 9.500, "date": "2024-01-29"},
]

MIN_HOP_ETH = 3.0          # follow onward transfers of at least this size
TOP_BRANCHES = 3           # per node, follow at most the 3 largest material hops
MAX_DEPTH = 4
MAX_NODES = 80
HIGH_VOLUME = 1500         # a wallet this busy is a service/exchange -> terminal
COMMINGLE = 2.5            # node inflow > this * tracked amount -> commingled, stop
FETCH_CAP = 2000           # bound the per-wallet fetch (exchanges are huge)


def is_exchange(node_addr, labels):
    e = labels.get(node_addr.lower())
    return bool(e) and e.get("type") == "exchange"


def node_inflow(addr, txns):
    return sum(t["eth"] for t in txns if t["to"] == addr and t["eth"] > 0)


def trace_payment(seed, seed_eth, es, labels):
    """Follow the DOMINANT material flow from `seed` forward to a terminal
    endpoint. Terminal reasons: labeled_exchange, defi_contract,
    high_volume_service, commingled"""
    edges, endpoints = [], []
    root_txns = fetch(seed, es)
    seed_in = min((t["timestamp"] for t in root_txns
                   if t["to"] == seed.lower() and t["eth"] > 1), default=0)
    queue = [(seed.lower(), seed_eth, 0, [seed.lower()], seed_in)]
    seen = set()

    def terminal(addr, eth_in, reason, path):
        endpoints.append({"addr": addr, "eth": round(eth_in, 3),
                          "reason": reason, "path": path})

    while queue and len(seen) < MAX_NODES:
        addr, eth_in, depth, path, since = queue.pop(0)
        if addr in seen:
            continue
        seen.add(addr)
        if is_exchange(addr, labels):
            terminal(addr, eth_in, "labeled_exchange", path)
            continue
        txns = fetch(addr, es)
        if len(txns) >= HIGH_VOLUME:
            terminal(addr, eth_in, "high_volume_service", path)
            continue
        if es.is_contract(addr):
            terminal(addr, eth_in, "defi_contract", path)
            continue
        if depth > 0 and node_inflow(addr, txns) > COMMINGLE * eth_in:
            terminal(addr, eth_in, "commingled", path)
            continue
        if depth >= MAX_DEPTH:
            terminal(addr, eth_in, "max_depth", path)
            continue
        outs = [t for t in txns if t["from"] == addr and t["eth"] >= MIN_HOP_ETH
                and not t["is_error"] and t["timestamp"] >= since - 3600]
        if not outs:
            terminal(addr, eth_in, "no_onward_flow", path)
            continue
        for t in sorted(outs, key=lambda x: -x["eth"])[:TOP_BRANCHES]:
            edges.append({"from": addr, "to": t["to"], "eth": round(t["eth"], 3),
                          "hash": t["hash"], "ts": t["timestamp"]})
            queue.append((t["to"], min(t["eth"], eth_in), depth + 1,
                          path + [t["to"]], t["timestamp"]))
    return edges, endpoints


EXCHANGE_KEYWORDS = ("coinbase", "ftx", "binance", "kraken")


def classify_payment(endpoints, labels):
    """Summarize a payment's terminal endpoints into a verdict + the named
    exchanges it reached. A payment reaches an exchange if any endpoint is a
    labeled exchange OR a labeled cash-out hop whose name identifies the
    exchange it forwards to."""
    venues = []
    for ep in endpoints:
        lbl = (labels.get(ep["addr"], {}).get("label") or "")
        low = lbl.lower()
        for kw in EXCHANGE_KEYWORDS:
            if kw in low:
                name = lbl if labels.get(ep["addr"], {}).get("type") == "exchange" \
                    else kw.upper() if kw == "ftx" else kw.capitalize()
                if name not in venues:
                    venues.append(name)
    coinbase = any("coinbase" in v.lower() for v in venues)
    if coinbase:
        verdict = "Coinbase (identity unknown)"
    elif venues:
        verdict = f"exchange ({venues[0]}) (identity unknown)"
    else:
        verdict = "commingled / DeFi (no clean exchange endpoint)"
    return {"verdict": verdict, "venues": venues, "hit_coinbase": coinbase}


_cache_mem = {}


def fetch(addr, es):
    a = addr.lower()
    if a in _cache_mem:
        return _cache_mem[a]
    txns = es.account_txns(a, max_records=FETCH_CAP)
    _cache_mem[a] = txns
    return txns


def main():
    load_dotenv(ROOT / ".env")
    key = os.environ.get("ETHERSCAN_API_KEY")
    if not key:
        raise SystemExit("ETHERSCAN_API_KEY required")
    es = Etherscan(key)
    labels = load_labels()

    result = {"payments": [], "distinct_endpoints": {}}
    for pay in INSIDER_PAYMENTS:
        print(f"\n=== tracing {pay['addr']} ({pay['eth']} ETH, {pay['date']}) ===")
        edges, endpoints = trace_payment(pay["addr"], pay["eth"], es, labels)
        for ep in endpoints:
            ep["label"] = labels.get(ep["addr"], {}).get("label")
            short_path = " -> ".join(a[:8] for a in ep["path"])
            print(f"  endpoint {ep['addr']}  {ep['eth']:>8.3f} ETH  [{ep['reason']}]"
                  f"  {ep['label'] or '?'}")
            print(f"     path: {short_path}")
            d = result["distinct_endpoints"].setdefault(
                ep["addr"], {"label": ep["label"], "reason": ep["reason"],
                             "total_eth": 0.0, "hit_by": []})
            d["total_eth"] = round(d["total_eth"] + ep["eth"], 3)
            d["hit_by"].append(pay["addr"])
        cls = classify_payment(endpoints, labels)
        print(f"  => {cls['verdict']}  ({', '.join(cls['venues']) or 'no named exchange'})")
        result["payments"].append({**pay, "classification": cls,
                                   "edges": edges, "endpoints": endpoints})

    out = ROOT / "data" / "evidence" / "insider_cashout_audit.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"\nwrote {out.relative_to(ROOT)}")
    print("\n=== PER-PAYMENT VERDICT ===")
    for p in result["payments"]:
        print(f"  {p['addr']}  {p['eth']:>8.3f} ETH  ->  {p['classification']['verdict']}"
              f"  ({', '.join(p['classification']['venues']) or '-'})")
    print("\n=== DISTINCT TERMINAL ENDPOINTS ===")
    for a, d in sorted(result["distinct_endpoints"].items(),
                       key=lambda kv: -kv[1]["total_eth"]):
        print(f"  {a}  {d['total_eth']:>8.3f} ETH  [{d['reason']}]  {d['label'] or 'UNVERIFIED'}")


if __name__ == "__main__":
    main()
