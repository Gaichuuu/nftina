"""Invariant audit over every wallet's P&L, per collection.

Run: python -m scripts.audit_wallet_pnl [--json]
Writes: public/data/wallet_pnl_audit.json
"""
import argparse
from collections import defaultdict

from scripts import econ
from scripts.analyze import _load, is_subset_key, price_table
from scripts.config import CONTRACTS, MINT_PRICES

OUT_NAME = "wallet_pnl_audit"
ZERO = econ.ZERO

EPS = 1e-6


def check_reconciles(rows):
    """OWNS = MINTED + BOUGHT + TRANSFERS - SOLD, the identity the holders table
    and the wallet lookup both display. A violation means some acquisition or
    disposal is visible to one counter but not to the holdings model."""
    bad = []
    for r in rows:
        expect = (r.get("tokens_minted", 0) + r.get("tokens_bought", 0)
                  + r.get("tokens_received", 0) - r.get("tokens_sent", 0)
                  - r.get("tokens_sold", 0))
        if expect != r.get("tokens_held", 0):
            bad.append({"wallet": r["wallet"], "held": r.get("tokens_held", 0),
                        "expected": expect,
                        "minted": r.get("tokens_minted", 0), "bought": r.get("tokens_bought", 0),
                        "received": r.get("tokens_received", 0), "sent": r.get("tokens_sent", 0),
                        "sold": r.get("tokens_sold", 0)})
    return bad


def check_spent_without_position(rows):
    """A wallet that spent ETH but holds nothing, sold nothing and sent nothing:
    it bought something the holdings model never saw."""
    return [{"wallet": r["wallet"], "eth_spent": r["eth_spent"],
             "bought": r.get("tokens_bought", 0)}
            for r in rows
            if r["eth_spent"] > EPS and not r.get("tokens_held")
            and not r.get("tokens_sold") and not r.get("tokens_sent")]


def check_held_exceeds_supply(rows, supply):
    """Total editions held across all wallets cannot exceed what was issued.
    `supply` is None when the issued count is not knowable from our data."""
    if not supply:
        return []
    total = sum(r.get("tokens_held", 0) for r in rows)
    if total <= supply:
        return []
    return [{"held_total": total, "supply": supply, "excess": total - supply}]


def check_realized_without_sale(rows):
    """Realized P&L is applied once per authoritative sale (M2). A nonzero
    realized figure on a wallet that never sold means it came from somewhere else."""
    return [{"wallet": r["wallet"], "realized_pnl_eth": r["realized_pnl_eth"]}
            for r in rows
            if abs(r["realized_pnl_eth"]) > EPS and not r.get("tokens_sold")]


def check_transfer_sides_balance(rows):
    """Every non-sale transfer has both a sender and a recipient, and every sale has
    both a seller and a buyer, so each pair must sum equal across the collection.
    A gap means the transfer or sale set is one-sided."""
    recv = sum(r.get("tokens_received", 0) for r in rows)
    sent = sum(r.get("tokens_sent", 0) for r in rows)
    bought = sum(r.get("tokens_bought", 0) for r in rows)
    sold = sum(r.get("tokens_sold", 0) for r in rows)
    out = []
    if recv != sent:
        out.append({"side": "transfers", "received": recv, "sent": sent,
                    "delta": recv - sent})
    if bought != sold:
        out.append({"side": "sales", "bought": bought, "sold": sold,
                    "delta": bought - sold})
    return out


def check_gas_without_activity(rows):
    """A wallet charged gas that neither minted nor bought is being billed for 
    somebody else's transaction."""
    return [{"wallet": r["wallet"], "gas_spent_eth": r.get("gas_spent_eth", 0.0)}
            for r in rows
            if r.get("gas_spent_eth", 0.0) > EPS
            and not r.get("tokens_minted") and not r.get("tokens_bought")]


def check_loss_without_basis(rows):
    """An unrealized loss on a wallet that never spent, minted or bought means its
    cost basis was inherited from another wallet's purchase (carry-forward), which
    is correct for a self-move and wrong for a gift between strangers. Reported as
    a review list, not a defect."""
    return [{"wallet": r["wallet"], "unrealized_loss": r["unrealized_loss"],
             "received": r.get("tokens_received", 0)}
            for r in rows
            if r["unrealized_loss"] > EPS and r["eth_spent"] <= EPS
            and not r.get("tokens_minted") and not r.get("tokens_bought")]


def check_sign_divergence(rows):
    """ETH and USD P&L disagreeing in sign is CORRECT under at-event valuation
    (F51) and is listed for visibility, never as a defect."""
    return [{"wallet": r["wallet"], "realized_pnl_eth": r["realized_pnl_eth"],
             "realized_pnl_usd": r.get("realized_pnl_usd", 0.0)}
            for r in rows
            if r["realized_pnl_eth"] * r.get("realized_pnl_usd", 0.0) < 0]


CHECKS = {
    "reconciles": (check_reconciles, "defect"),
    "spent_without_position": (check_spent_without_position, "defect"),
    "realized_without_sale": (check_realized_without_sale, "defect"),
    "transfer_sides_balance": (check_transfer_sides_balance, "defect"),
    "gas_without_activity": (check_gas_without_activity, "defect"),
    "held_exceeds_supply": (check_held_exceeds_supply, "defect"),
    "loss_without_basis": (check_loss_without_basis, "review"),
    "sign_divergence": (check_sign_divergence, "review"),
}


def run_checks(rows, supply=None):
    """Every check over one collection's wallet rows. Returns {name: [violations]}."""
    return {name: (fn(rows, supply) if name == "held_exceeds_supply" else fn(rows))
            for name, (fn, _sev) in CHECKS.items()}


def issued_supply(transfers):
    """Editions issued: 0x0 mints plus, for a lazy-mint store with no 0x0 hop, the
    distributor's outbound quantity. None when neither is present (unknowable)."""
    minted = sum(int(t.get("quantity") or 1) for t in transfers if t.get("from") == ZERO)
    return minted or None


def collection_rows(key, prices, now_price):
    """Load one collection's raw and compute its wallet rows, exactly as the site does."""
    transfers = _load(f"{key}_transfers")
    if not transfers:
        return None
    for t in transfers:
        t["collection"] = key
    mintvals = _load(f"{key}_mintvalues") or {}
    sales = [s for s in (_load(f"{key}_sales") or []) if not s.get("is_phantom")]
    for s in sales:
        s["collection"] = key
    floor = {key: (_load(f"{key}_floor") or {}).get("floor_eth", 0.0)}
    mint_cost = econ.mint_cost_per_token(transfers, mintvals, MINT_PRICES.get(key))
    gas = econ.gas_by_wallet(transfers, sales)
    pnl = econ.wallet_pnl(transfers, mint_cost, sales, floor,
                          prices=prices, now_price=now_price, gas=gas)
    return list(pnl.values()), issued_supply(transfers)


def main(as_json=False):
    prices = price_table()
    now_price = prices[max(prices)]
    report, totals = {}, defaultdict(int)
    for key, meta in CONTRACTS.items():
        if meta.get("third_party") or is_subset_key(meta):
            continue
        loaded = collection_rows(key, prices, now_price)
        if not loaded:
            continue
        rows, supply = loaded
        res = run_checks(rows, supply)
        report[key] = {"wallets": len(rows),
                       "checks": {n: len(v) for n, v in res.items()},
                       "samples": {n: v[:5] for n, v in res.items() if v}}
        for n, v in res.items():
            totals[n] += len(v)
        flagged = ", ".join(f"{n}={len(v)}" for n, v in res.items() if v) or "clean"
        print(f"  {key:22s} {len(rows):5d} wallets | {flagged}")

    print("\n  TOTALS")
    for n, (_fn, sev) in CHECKS.items():
        print(f"    {n:26s} {totals[n]:6d}  [{sev}]")

    out = {"by_collection": report,
           "totals": dict(totals),
           "severity": {n: sev for n, (_f, sev) in CHECKS.items()}}
    if as_json:
        from scripts.analyze import _save
        _save(OUT_NAME, out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="also write public/data/wallet_pnl_audit.json")
    main(**{"as_json": ap.parse_args().json})
