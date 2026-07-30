"""Resolves the MetaZoo deployer, seeds from the confirmed Aoki cluster, 
runs the targeted BFS, and writes an auditable money map + headline numbers. 

Usage: python -m scripts.trace_flows
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
from scripts.config import (CONTRACTS, AOKI_WALLETS, AOKI_HUB_EOA_CANDIDATES,
                            METAZOO_WALLETS, METAZOO_DEPLOYER)
from scripts.clients.etherscan import Etherscan
from scripts.wallet_labeling import load_labels, classify
from scripts.trace_core import trace

OUT = Path(__file__).parent.parent / "public" / "data"


def build_summary(graph: dict, aoki_wallets, metazoo_wallets=(), candidate_wallets=()) -> dict:
    """Separate the money flows so no single number conflates them:
      - metazoo_to_aoki / aoki_to_metazoo: ETH between MetaZoo-controlled wallets and
        CONFIRMED Aoki wallets.
      - aoki_outflow: where the Aoki side's money goes, split by destination KIND —
        NFT-marketplace *spend* (OpenSea/CryptoPunks/Genie; buying NFTs, NOT cash-out),
        exchange cash-out (labeled exchanges), internal-cluster movement (Aoki-side ↔
        Aoki-side incl. unproven candidates), and unlabeled endpoints (untagged deposit/
        consolidation chains; the likely-but-unverifiable cash-out).
      - aoki_wallet_inflow_eth: per-wallet inflow, reported separately."""
    aoki = {a.lower() for a in aoki_wallets}
    metazoo = {a.lower() for a in metazoo_wallets}
    cands = {a.lower() for a in candidate_wallets}
    cluster = aoki | cands                      # the Aoki side
    by_addr = {n["address"]: n for n in graph["nodes"]}

    mz_to_aoki = aoki_to_mz = nft_spend = cash_out = internal = 0.0
    by_exchange, unlabeled = {}, {}             # unlabeled dedup'd by address
    for e in graph["edges"]:
        src, dst, eth = e["from"], e["to"], e["eth_out"]
        dn = by_addr.get(dst, {})
        if src in metazoo and dst in aoki:
            mz_to_aoki += eth
        if src in aoki and dst in metazoo:
            aoki_to_mz += eth
        if src in cluster:                      # money leaving the Aoki side
            if dst in cluster:
                internal += eth
            elif dn.get("kind") == "marketplace":
                nft_spend += eth
            elif dn.get("kind") == "exchange":
                cash_out += eth
                lbl = dn.get("label", dst)
                by_exchange[lbl] = by_exchange.get(lbl, 0.0) + eth
            elif dn.get("kind") == "eoa" and dn.get("label") in (None, "unlabeled") and dst not in metazoo:
                unlabeled[dst] = unlabeled.get(dst, 0.0) + eth
    inflow = {a: round(by_addr.get(a, {}).get("total_in_eth", 0.0), 6) for a in sorted(aoki)}
    return {
        "metazoo_to_aoki_eth": round(mz_to_aoki, 6),
        "aoki_to_metazoo_eth": round(aoki_to_mz, 6),
        "aoki_wallet_inflow_eth": inflow,
        "aoki_outflow": {
            "nft_marketplace_eth": round(nft_spend, 6),
            "cash_out_eth": round(cash_out, 6),
            "by_exchange": {k: round(v, 6) for k, v in sorted(by_exchange.items(), key=lambda x: -x[1])},
            "internal_cluster_eth": round(internal, 6),
            "unlabeled_endpoints": {"count": len(unlabeled), "eth": round(sum(unlabeled.values()), 6)},
        },
        "confirmed_aoki_wallets": sorted(aoki),
        "unproven_candidates": sorted(cands),
        "caps_hit": graph["caps_hit"],
        "disclaimer": ("Figures are estimates from public on-chain data. NFT-marketplace "
                       "spend is not cash-out. Candidate wallets are unproven; Aoki "
                       "allegations are unproven."),
    }


def main():
    es = Etherscan(os.environ["ETHERSCAN_API_KEY"])
    labels = load_labels()

    deployer = METAZOO_DEPLOYER
    if not deployer:
        info = es.contract_creator(CONTRACTS["coin_tokens"]["address"])
        deployer = info["creator"]
        print(f"[deployer] resolved via coin_tokens creator: {deployer} (tx {info['tx_hash']})")
        print(f"           paste into config.py:  METAZOO_DEPLOYER = \"{deployer}\"")

    metazoo_wallets = ([deployer.lower()] if deployer else []) + [a.lower() for a in METAZOO_WALLETS]
    seed = list(metazoo_wallets)
    seed += [a.lower() for a in AOKI_WALLETS] + [a.lower() for a in AOKI_HUB_EOA_CANDIDATES]
    seed = list(dict.fromkeys(a for a in seed if a))
    confirmed = set(seed)   # seed set is treated as confirmed anchors
    print(f"[trace] seed of {len(seed)} wallets; BFS (depth<=3, <=150 nodes)…")

    graph = trace(
        seed,
        fetch_txns=es.account_txns,
        classify_fn=lambda a: classify(a, labels, es.is_contract(a)),
        is_confirmed=lambda a: a.lower() in confirmed,
    )
    summary = build_summary(graph, AOKI_WALLETS,
                            metazoo_wallets=metazoo_wallets,
                            candidate_wallets=AOKI_HUB_EOA_CANDIDATES)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "treasury_flows.json").write_text(json.dumps(graph, indent=2))
    (OUT / "flow_summary.json").write_text(json.dumps(summary, indent=2))
    o = summary["aoki_outflow"]
    print(f"[done] {len(graph['nodes'])} nodes, {len(graph['edges'])} edges | "
          f"MetaZoo->Aoki {summary['metazoo_to_aoki_eth']} ETH | "
          f"NFT-spend {o['nft_marketplace_eth']} | cash-out {o['cash_out_eth']} | "
          f"unlabeled {o['unlabeled_endpoints']['eth']} ETH")
    print(f"       -> public/data/treasury_flows.json + flow_summary.json")


if __name__ == "__main__":
    main()
