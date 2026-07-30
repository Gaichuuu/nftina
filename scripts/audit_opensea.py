"""Cross-check our pipeline's per-collection numbers against OpenSea. For each
of the 10 site collections it resolves the OpenSea collection, pulls supply / fees /
volume / sales / owners / floor, and reconciles them against site/data + our derived
current-holder counts, flagging any divergence beyond tolerance.

Pure core (reconcile / creator_fee / pct_delta) is offline-testable; main() wires it
to the live OpenSea Data API. Needs OPENSEA_API_KEY. Output: public/data/opensea_audit.json.

  python -m scripts.audit_opensea
"""
import os
import json
import time
import argparse
from pathlib import Path

import requests

from scripts.config import (CONTRACTS, SITE_COLLECTIONS, AOKI_WALLETS,
                            METAZOO_WALLETS, METAZOO_DEPLOYER)

ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = ROOT / "site" / "data"
OUT = ROOT / "public" / "data" / "opensea_audit.json"
LABELS_PATH = ROOT / "scripts" / "labels.json"

API = "https://api.opensea.io/api/v2"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
OPENSEA_FEE_RECIPIENTS = {"0x0000a26b00c1f0df003000390027140000faa719"}

# Relative-difference thresholds (fraction) beyond which a metric is flagged.
SUPPLY_TOL = 0.02        # supply should essentially match on a dedicated contract
FLOOR_TOL = 0.25         # floor sources (OpenSea vs Alchemy) legitimately drift
OWNERS_TOL = 0.10        # current-owner count


def creator_fee(fees):
    """(percent, recipient) of the creator royalty in an OpenSea `fees` list, or
    (0.0, None) if none — excludes OpenSea's own protocol fee. Takes the largest
    non-protocol fee if several are present."""
    cand = [f for f in (fees or [])
            if isinstance(f, dict)
            and (f.get("recipient") or "").lower() not in OPENSEA_FEE_RECIPIENTS]
    if not cand:
        return 0.0, None
    best = max(cand, key=lambda f: float(f.get("fee") or 0.0))
    return float(best.get("fee") or 0.0), (best.get("recipient") or "").lower() or None


def pct_delta(ours, theirs):
    """Relative difference of two numbers vs the larger magnitude; None if both ~0."""
    a, b = float(ours or 0.0), float(theirs or 0.0)
    denom = max(abs(a), abs(b))
    return None if denom < 1e-9 else abs(a - b) / denom


def _check(metric, ours, opensea, status, note=""):
    numeric = isinstance(ours, (int, float)) and isinstance(opensea, (int, float))
    return {"metric": metric, "ours": ours, "opensea": opensea,
            "delta_pct": pct_delta(ours, opensea) if numeric else None,
            "status": status, "note": note}


def reconcile(slug, ours, os_detail, os_stats, comparable, label_lookup=None):
    """Pure reconciliation of one collection. `ours` has supply/volume_eth/sales/
    owners/royalty_eth/floor_eth; `os_detail` has total_supply/fees; `os_stats` has
    volume/sales/num_owners/floor. `comparable` gates the whole-contract metrics.
    Returns {slug, os_slug?, checks:[...], flags:[...], royalty_recipient, ...}."""
    label_lookup = label_lookup or {}
    checks, flags = [], []

    fee_pct, fee_recip = creator_fee(os_detail.get("fees"))
    os_supply = os_detail.get("total_supply")

    # --- Royalty config
    our_roy = float(ours.get("royalty_eth") or 0.0)
    if fee_pct > 0 and our_roy == 0.0:
        checks.append(_check("royalty", f"{our_roy} ETH captured",
                             f"{fee_pct}% configured -> {fee_recip}", "diverge",
                             "OpenSea has a creator royalty configured but our sales captured 0 "
                             "ETH of it (check EIP-2981 vs marketplace-registry enforcement)."))
        flags.append(f"royalty configured ({fee_pct}%) but 0 captured")
    else:
        checks.append(_check("royalty", f"{our_roy} ETH captured",
                             f"{fee_pct}% -> {fee_recip}" if fee_pct else "none configured",
                             "info"))
    if fee_recip:
        known = label_lookup.get(fee_recip)
        if known:
            checks.append(_check("royalty_recipient_id", fee_recip,
                                 known.get("label") if isinstance(known, dict) else str(known),
                                 "info", "recipient is a known wallet"))
        else:
            flags.append(f"royalty recipient {fee_recip} is UNLABELED (trace lead)")

    # --- Supply / volume / sales / owners / floor: only for dedicated whole contracts
    if comparable:
        d = pct_delta(ours.get("supply"), os_supply)
        checks.append(_check("supply", ours.get("supply"), os_supply,
                             "ok" if (d is not None and d <= SUPPLY_TOL) else "diverge"))
        if d is not None and d > SUPPLY_TOL:
            flags.append(f"supply {ours.get('supply')} vs OpenSea {os_supply}")

        ov, tv = float(ours.get("volume_eth") or 0.0), float(os_stats.get("volume") or 0.0)
        vstatus = "ok"
        if tv > 0 and ov < tv * 0.9:
            vstatus, note = "diverge", "ours is BELOW OpenSea-only volume — we may be missing sales"
            flags.append(f"volume {ov:.1f} ETH < OpenSea {tv:.1f} ETH (missing sales?)")
        elif tv > 0 and ov > tv * 4:
            vstatus, note = "diverge", "ours is >4x OpenSea volume — possible wash/phantom inflation"
            flags.append(f"volume {ov:.1f} ETH >> OpenSea {tv:.1f} ETH (inflation?)")
        else:
            note = "ours >= OpenSea-only (expected: we include Blur/LooksRare/etc.)"
        checks.append(_check("secondary_volume_eth", round(ov, 2), round(tv, 2), vstatus, note))

        checks.append(_check("secondary_sales", ours.get("sales"), os_stats.get("sales"),
                             "info", "counts differ by marketplace coverage"))

        if ours.get("owners") is not None:
            d = pct_delta(ours.get("owners"), os_stats.get("num_owners"))
            checks.append(_check("current_owners", ours.get("owners"), os_stats.get("num_owners"),
                                 "ok" if (d is not None and d <= OWNERS_TOL) else "diverge"))
            if d is not None and d > OWNERS_TOL:
                flags.append(f"owners {ours.get('owners')} vs OpenSea {os_stats.get('num_owners')}")

        of, tf = float(ours.get("floor_eth") or 0.0), float(os_stats.get("floor") or 0.0)
        if tf <= 0:
            checks.append(_check("floor_eth", of, tf, "info", "OpenSea reported no floor (0/none)"))
        else:
            d = pct_delta(of, tf)
            checks.append(_check("floor_eth", of, tf,
                                 "ok" if (d is not None and d <= FLOOR_TOL) else "diverge"))
            if d is not None and d > FLOOR_TOL:
                flags.append(f"floor {of} vs OpenSea {tf} ETH")
    else:
        for m in ("supply", "secondary_volume_eth", "secondary_sales", "current_owners", "floor_eth"):
            checks.append(_check(m, None, None, "not_comparable",
                                 "subset/shared collection — OpenSea stats aggregate other tokens/tenants"))

    return {"slug": slug, "os_slug": os_detail.get("_os_slug"),
            "comparable": comparable, "royalty_pct": fee_pct,
            "royalty_recipient": fee_recip, "checks": checks, "flags": flags}


# ---------------------------------------------------------------- live wiring

def _get(session, key, url):
    for attempt in range(1, 5):
        try:
            r = session.get(url, headers={"X-API-KEY": key, "accept": "application/json",
                                          "User-Agent": UA}, timeout=30)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(attempt * 2)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == 4:
                return None
            time.sleep(attempt)
    return None


def fetch_opensea(session, key, address):
    """Resolve a contract to its OpenSea collection and pull detail + stats.
    Returns (os_detail, os_stats) with os_detail['_os_slug'] set, or ({}, {}) on miss."""
    contract = _get(session, key, f"{API}/chain/ethereum/contract/{address}")
    os_slug = (contract or {}).get("collection")
    if not os_slug:
        return {}, {}
    detail = _get(session, key, f"{API}/collections/{os_slug}") or {}
    detail["_os_slug"] = os_slug
    stats_raw = _get(session, key, f"{API}/collections/{os_slug}/stats") or {}
    total = stats_raw.get("total") or {}
    stats = {"volume": total.get("volume"), "sales": total.get("sales"),
             "num_owners": total.get("num_owners"), "floor": total.get("floor_price")}
    return detail, stats


def _our_numbers(coll_row, holders):
    """Map a site/data collections.json row + its holders list to the reconcile shape."""
    owners = None
    if holders:
        owners = sum(1 for h in holders if int(h.get("tokens_held") or 0) > 0)
    return {"supply": coll_row.get("total_mints"),
            "volume_eth": coll_row.get("secondary_volume_eth"),
            "sales": coll_row.get("secondary_sales"),
            "owners": owners,
            "royalty_eth": coll_row.get("royalty_eth"),
            "floor_eth": coll_row.get("floor_eth")}


def _load_holders(slug):
    p = SITE_DATA / "collections" / slug / "holders.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return data.get("holders", []) if isinstance(data, dict) else data


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-check pipeline numbers against OpenSea")
    ap.add_argument("--delay", type=float, default=0.3, help="seconds between wallets/collections")
    args = ap.parse_args()

    key = os.environ.get("OPENSEA_API_KEY")
    if not key:
        print("ERROR: OPENSEA_API_KEY not set (needs a CLASSIC 32-char key, not a scoped token)")
        return 1

    rows = {r["collection"]: r for r in json.loads((SITE_DATA / "collections.json").read_text())}
    labels = {k.lower(): v for k, v in
              (json.loads(LABELS_PATH.read_text()) if LABELS_PATH.exists() else {}).items()}
    for a in AOKI_WALLETS:
        labels.setdefault(a.lower(), {"label": "Steve Aoki (config AOKI_WALLETS)"})
    for a in METAZOO_WALLETS:
        labels.setdefault(a.lower(), {"label": "MetaZoo (config METAZOO_WALLETS)"})
    if METAZOO_DEPLOYER:
        labels.setdefault(str(METAZOO_DEPLOYER).lower(), {"label": "MetaZoo: Deployer"})

    session = requests.Session()
    results = []
    for entry in SITE_COLLECTIONS:
        slug = entry["slug"]
        host = entry.get("parent") or slug
        contract = CONTRACTS.get(host, {})
        address = contract.get("address")
        comparable = (entry["source"] == "own" and not contract.get("shared"))
        if not address:
            results.append({"slug": slug, "error": "no contract address", "flags": []})
            continue

        os_detail, os_stats = fetch_opensea(session, key, address)
        if not os_detail:
            results.append({"slug": slug, "error": "no OpenSea collection resolved",
                            "address": address, "flags": []})
            time.sleep(args.delay)
            continue

        ours = _our_numbers(rows.get(slug, {}), _load_holders(slug))
        rec = reconcile(slug, ours, os_detail, os_stats, comparable, labels)
        rec["address"] = address
        results.append(rec)
        time.sleep(args.delay)

    diverging = [r for r in results if r.get("flags")]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"collections": results,
                               "diverging_count": len(diverging)}, indent=1))

    # --- console reconciliation table
    print(f"\n{'collection':22} {'cmp':4} {'roy%':>5} {'flags'}")
    print("-" * 78)
    for r in results:
        if r.get("error"):
            print(f"{r['slug']:22}  ERROR: {r['error']}")
            continue
        cmp = "yes" if r["comparable"] else "no"
        flags = "; ".join(r["flags"]) if r["flags"] else "clean"
        print(f"{r['slug']:22} {cmp:4} {r['royalty_pct']:>5} {flags}")
    print(f"\n{len(diverging)} collection(s) with flags -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
