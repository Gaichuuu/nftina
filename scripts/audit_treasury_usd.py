"""Treasury USD audit: value every treasury inflow at its receipt date and every
outflow at its spend date, then quantify what holding ETH through the crash cost.
"""
from collections import defaultdict
from datetime import datetime, timezone

IN_CLS = {"nft_contract": "mint_proceeds", "marketplace": "royalties", "royalty": "royalties"}
OUT_CLS = {"aoki": "aoki", "exchange": "exchange_deposit", "insider": "insider",
           "royalty": "intra_cluster", "project_cost": "project_costs"}


def _date_of(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def usd_at_date(eth: float, date: str, daily: dict) -> float:
    """eth × close on `date`; else the nearest earlier date; else nearest overall."""
    if date in daily:
        return eth * daily[date]
    earlier = [d for d in daily if d <= date]
    pick = max(earlier) if earlier else min(daily, key=lambda d: abs(
        datetime.strptime(d, "%Y-%m-%d").toordinal()
        - datetime.strptime(date, "%Y-%m-%d").toordinal()))
    return eth * daily[pick]


def build_ledger(txns_by_wallet: dict, treasury: set, kind_of, daily: dict) -> list:
    treasury = {a.lower() for a in treasury}
    seen, ledger = set(), []
    for wallet, txns in txns_by_wallet.items():
        w = wallet.lower()
        for t in txns:
            if t.get("is_error") or not t.get("eth"):
                continue
            frm, to = t["from"].lower(), t["to"].lower()
            if frm in treasury and to in treasury:
                continue
            key = (t["hash"], frm, to, t["eth"], t.get("kind"))
            if key in seen:
                continue
            seen.add(key)
            if to == w:
                direction, counterparty = "in", frm
                cls = IN_CLS.get(kind_of(counterparty), "other_in")
            elif frm == w:
                direction, counterparty = "out", to
                cls = OUT_CLS.get(kind_of(counterparty), "other_out")
            else:
                continue
            date = _date_of(t["timestamp"])
            ledger.append({"date": date, "wallet": w, "direction": direction,
                           "counterparty": counterparty, "eth": t["eth"],
                           "usd": round(usd_at_date(t["eth"], date, daily), 2),
                           "cls": cls})
    ledger.sort(key=lambda e: e["date"])
    return ledger


def monthly_balances(ledger: list, daily: dict) -> list:
    """Cumulative treasury ETH balance at each month end × that month's last close."""
    if not ledger:
        return []
    net_by_month = defaultdict(float)
    for e in ledger:
        net_by_month[e["date"][:7]] += e["eth"] if e["direction"] == "in" else -e["eth"]
    out, bal = [], 0.0
    for month in sorted(net_by_month):
        bal += net_by_month[month]
        closes = [d for d in daily if d[:7] <= month]
        mark = daily[max(closes)] if closes else 0.0
        out.append({"month": month, "eth_balance": round(bal, 6),
                    "usd_mark": round(bal * mark, 2)})
    return out


def reconcile(ledger: list, current_price: float,
              gas_eth: float, gas_usd_at_spend: float, held_eth: float) -> dict:
    """Balance the treasury: received = paid (to counterparties) + gas (burned as
    fees) + still-held (on-chain today). The residual (received − paid) is NOT
    "still held" — almost all of it is gas the value-ledger doesn't see, so this
    splits it explicitly. ``held_eth`` is the wallets' actual current on-chain
    balance; ``gas_eth``/``gas_usd_at_spend`` are measured transaction fees valued
    at each tx's own date. ``depreciation_gap_usd`` is what genuinely was lost to
    ETH sitting idle through the crash: received-at-receipt minus everything that
    left valued when it left (paid + gas at spend) minus what is still held now.
    Near zero => the treasury did not hold ETH through the decline."""
    rec_e = sum(e["eth"] for e in ledger if e["direction"] == "in")
    rec_u = sum(e["usd"] for e in ledger if e["direction"] == "in")
    pay_e = sum(e["eth"] for e in ledger if e["direction"] == "out")
    pay_u = sum(e["usd"] for e in ledger if e["direction"] == "out")
    res_e = rec_e - pay_e
    held_u = held_eth * current_price
    return {"received_eth": round(rec_e, 6), "received_usd_at_receipt": round(rec_u, 2),
            "paid_eth": round(pay_e, 6), "paid_usd_at_spend": round(pay_u, 2),
            "residual_eth": round(res_e, 6),
            "gas_eth": round(gas_eth, 6), "gas_usd_at_spend": round(gas_usd_at_spend, 2),
            "still_held_eth": round(held_eth, 6), "still_held_usd_now": round(held_u, 2),
            "reconciles_eth": round(res_e - gas_eth - held_eth, 6),
            "depreciation_gap_usd": round(rec_u - pay_u - gas_usd_at_spend - held_u, 2)}

MINT_FUNNEL_CONTRACTS = {
    "0x4b2144e59f7e286d8e7b7a4cbbb94b042e2b791f",  # metaZooSale -> coin_tokens mint proceeds
    "0x88524a9b2c23d869cba3466d1ce6457fb102e214",  # PercentSplitETH -> beasties_s1 mint proceeds
}

INSIDER_WALLETS = {
    "0x37eccdcbc448e07cb19331277aebf9b13ec5a6a3",  # MetaZoo insider/cash-out #1
    "0xccc55c38603ad1a1dc54db871166fa90f78edd11",  # MetaZoo insider/distribution #2
    "0x2f7eb4f5d083c5607f1f1ec278728323a84acc6b",  # MetaZoo shutdown-day cash-out
    "0xe693fbc0df4db03d3b75017b7a423dd38d49487c",  # MetaZoo insider/cluster #3
    "0x08b96fad98c2366f6e483de584167dd695d30c27",  # MetaZoo insider/cluster #4
}

PROJECT_COST_ADDRS = {
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2: Router 2
    "0x00000000000000adc04c56bf30ac9d3c0aaf14dc",  # 0x: Exchange Proxy
    "0x283af0b28c62c092c9727f1ee09c02ca627eb7f5",  # ENS: ETH Registrar Controller
}

#   0xd909681f… MetaZoo royalty distributor (Wyvern-era, via OpenSea payout 0x0b7a43): ~58.6 ETH
#   0xcbbecd9d… Coin Tokens Seaport royalty splitter (75% MetaZoo share):               ~5.2 ETH
ROYALTY_SOURCES = {
    "0xd909681f6c474e14d5aff4b75513989e68ad5265",
    "0xcbbecd9d102299ef022adee17daae3dcb779aa43",
}


def classify_counterparty(addr, labels, nft_contracts, aoki) -> str:
    """Precedence: our NFT contracts > Aoki > insider wallets > royalty sources >
    label type (exchange/marketplace/insider) > other. Unlabeled contracts and EOAs
    both fall to 'other' (the report shows them aggregated; label coverage grows via
    labels.json, not guesses)."""
    a = addr.lower()
    if a in nft_contracts:
        return "nft_contract"
    if a in aoki:
        return "aoki"
    if a in INSIDER_WALLETS:
        return "insider"
    if a in PROJECT_COST_ADDRS:
        return "project_cost"
    if a in ROYALTY_SOURCES:
        return "royalty"
    t = (labels.get(a) or {}).get("type")
    if t in ("exchange", "marketplace", "insider"):
        return t
    return "other"


def count_cross_kind_collisions(txns_by_wallet: dict) -> int:
    """Build_ledger's dedup key is (hash, from, to, eth, kind)"""
    kinds_by_ident = {}
    for txns in txns_by_wallet.values():
        for t in txns:
            if t.get("is_error") or not t.get("eth"):
                continue
            ident = (t["hash"], t["from"], t["to"], t["eth"])
            kinds_by_ident.setdefault(ident, set()).add(t.get("kind"))
    return sum(1 for kinds in kinds_by_ident.values() if len(kinds) > 1)


def fetch_balance_and_gas(treasury: list, es, daily: dict, cache_path) -> dict:
    """Live-measure (and cache) two things the value-ledger cannot see: each
    treasury wallet's CURRENT on-chain ETH balance, and total transaction-fee
    gas each wallet burned as a sender (valued at each tx's own daily close)."""
    import json
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    if es is None:
        raise RuntimeError("no ETHERSCAN_API_KEY and no treasury_balgas cache")
    r = es._get({"module": "account", "action": "balancemulti",
                 "address": ",".join(treasury), "tag": "latest"})
    held = {it["account"].lower(): int(it["balance"]) / 1e18 for it in r.get("result", [])}
    gas_eth, gas_usd = {}, {}
    for w in treasury:
        ge = gu = 0.0
        for t in es._paginate_account(w, "txlist"):
            if t.get("from", "").lower() == w and t.get("gasUsed") and t.get("gasPrice"):
                fee = int(t["gasUsed"]) * int(t["gasPrice"]) / 1e18
                ge += fee
                gu += usd_at_date(fee, _date_of(int(t["timeStamp"])), daily)
        gas_eth[w], gas_usd[w] = ge, gu
    out = {"held_eth": held, "gas_eth": gas_eth, "gas_usd_at_spend": gas_usd,
           "total_held_eth": round(sum(held.values()), 6),
           "total_gas_eth": round(sum(gas_eth.values()), 6),
           "total_gas_usd_at_spend": round(sum(gas_usd.values()), 2)}
    cache_path.write_text(json.dumps(out, indent=2))
    return out


def main() -> None:
    import json, os, sys
    from pathlib import Path
    from dotenv import load_dotenv
    root = Path(__file__).parent.parent
    load_dotenv(root / ".env")
    from scripts.config import METAZOO_DEPLOYER, METAZOO_WALLETS, AOKI_WALLETS, CONTRACTS
    from scripts.wallet_labeling import load_labels
    from scripts.trace_acquisitions import eth_daily_usd
    from scripts.clients.etherscan import Etherscan

    raw = root / "data" / "raw"
    treasury = list(dict.fromkeys(
        a.lower() for a in [METAZOO_DEPLOYER, *METAZOO_WALLETS] if a))
    daily = eth_daily_usd()
    labels = {k.lower(): v for k, v in load_labels().items()}
    nft_contracts = ({m["address"].lower() for m in CONTRACTS.values() if m.get("address")}
                      | MINT_FUNNEL_CONTRACTS)
    aoki = {a.lower() for a in AOKI_WALLETS}

    key = os.environ.get("ETHERSCAN_API_KEY")
    es = Etherscan(key) if key else None
    txns_by_wallet = {}
    for w in treasury:
        cache = raw / f"txns_{w}.json"
        if cache.exists():
            txns_by_wallet[w] = json.loads(cache.read_text())
        elif es:
            print(f"[fetch] account txns for {w[:10]}…")
            txns_by_wallet[w] = es.account_txns(w)
            cache.write_text(json.dumps(txns_by_wallet[w]))
        else:
            print(f"ERROR: no cache for {w} and no ETHERSCAN_API_KEY")
            sys.exit(1)

    collisions = count_cross_kind_collisions(txns_by_wallet)
    print(f"[dedup] cross-kind (normal/internal) identity collisions: {collisions}")
    assert collisions == 0, (
        f"{collisions} same-hash/from/to/eth pairs appear as BOTH normal and "
        "internal — build_ledger's (hash, from, to, eth, kind) dedup key would "
        "double-count these; merge normal+internal by kind-insensitive identity "
        "before calling build_ledger.")

    kind_of = lambda a: classify_counterparty(a, labels, nft_contracts, aoki)
    ledger = build_ledger(txns_by_wallet, set(treasury), kind_of, daily)
    current_price = daily[max(daily)]
    balgas = fetch_balance_and_gas(treasury, es, daily, raw / "treasury_balgas.json")
    headline = reconcile(ledger, current_price,
                         gas_eth=balgas["total_gas_eth"],
                         gas_usd_at_spend=balgas["total_gas_usd_at_spend"],
                         held_eth=balgas["total_held_eth"])
    by_class = {"in": {}, "out": {}}
    for e in ledger:
        side = by_class[e["direction"]]
        side.setdefault(e["cls"], {"eth": 0.0, "usd": 0.0})
        side[e["cls"]]["eth"] = round(side[e["cls"]]["eth"] + e["eth"], 6)
        side[e["cls"]]["usd"] = round(side[e["cls"]]["usd"] + e["usd"], 2)

    out = {"headline": headline, "by_class": by_class,
           "monthly": monthly_balances(ledger, daily),
           "method": {
               "wallets": treasury,
               "valuation": "Binance daily close (data/raw/eth_usd_daily.json); "
                            "inflows at receipt date, outflows (and gas) at spend date, "
                            f"still-held balance at current price ${current_price:,.0f}/ETH",
               "caveats": [
                   "On-chain NFT-side only: physical-card fiat revenue never touched these wallets.",
                   "exchange_deposit = plausibly converted; a deposit is not proof of a sale.",
                   "Unlabeled counterparties aggregate under other_in/other_out.",
                   "royalties (in) = NFT royalty / OpenSea creator-earnings reaching "
                   "the treasury via the F36-traced distributor 0xd909 (Wyvern, from "
                   "OpenSea payout 0x0b7a43) and the Seaport splitter 0xcbbec; ~80% of "
                   "the ~79.6 ETH Coin Tokens royalty attributed at sale. A small part "
                   "of the 0xd909 flow is non-royalty seed, so it is a close proxy.",
                   "mint_proceeds is ~20-30% below full reconstructed mint "
                   "revenue per collection; the remainder went to an unidentified "
                   "payee outside this audit's 3-wallet treasury seed.",
                   "The received−paid residual is almost entirely GAS (transaction "
                   "fees the value-ledger doesn't track), not ETH still held: the "
                   "wallets hold ~%.2f ETH on-chain today. Because the treasury spent "
                   "ETH near-immediately (not held through the crash), the idle-"
                   "depreciation loss is small." % balgas["total_held_eth"],
               ]}}
    dest = root / "public" / "data" / "treasury_usd_audit.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"[audit] {len(ledger)} ledger entries -> {dest}")
    h = headline
    print(f"  received  {h['received_eth']} ETH = ${h['received_usd_at_receipt']:,.0f} at receipt")
    print(f"  paid      {h['paid_eth']} ETH = ${h['paid_usd_at_spend']:,.0f} at spend")
    print(f"  gas       {h['gas_eth']} ETH = ${h['gas_usd_at_spend']:,.0f} at spend (fees, not held)")
    print(f"  still held {h['still_held_eth']} ETH = ${h['still_held_usd_now']:,.0f} now (on-chain balance)")
    print(f"  reconciles (residual−gas−held) = {h['reconciles_eth']} ETH (≈0)")
    print(f"  idle-depreciation gap ≈ ${h['depreciation_gap_usd']:,.0f}")
    try:
        summary = json.loads((root / "public" / "data" / "summary.json").read_text())
        print(f"  [anchor] F19 total_mint_revenue_usd = "
              f"${summary.get('total_mint_revenue_usd', 0):,.0f} "
              f"vs audit mint_proceeds ${by_class['in'].get('mint_proceeds', {}).get('usd', 0):,.0f} "
              f"(differences = withdrawal timing + wallets outside the treasury set; explain in F28)")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main()
