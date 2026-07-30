"""Analyze cached on-chain data into the public/data JSON the frontend consumes.
Usage:
    python -m scripts.analyze
    python -m scripts.analyze --whales 100
"""
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

from scripts.config import CONTRACTS, BANKRUPTCY, MINT_PRICES, ETH_PRICES
from scripts import econ

RAW = Path(__file__).parent.parent / "data" / "raw"
OUT = Path(__file__).parent.parent / "public" / "data"

_STOREFRONT_ADDRS = {m["address"] for m in CONTRACTS.values() if m.get("distributor")}

DAILY_USD_CACHE = RAW / "eth_usd_daily.json"


def price_table() -> dict:
    """The ETH/USD table for at-event valuation: the cached Binance daily close
    (2021-01-01 onward, every day) when present, else config's sparse ETH_PRICES.

    econ.eth_to_usd resolves by NEAREST date, so a sparse table silently marks an
    event at whatever snapshot happens to be closest — across 2021-06..2023-06 that
    is off by ~16% on average and up to 102% at worst, since ETH_PRICES holds only
    20 dates. The volume/royalty legs already priced off the daily table; this makes
    holder P&L and mint revenue share it, so every USD figure on the site is marked
    on one basis. The sparse fallback keeps a checkout without the gitignored cache
    building (same graceful degrade as the media manifests), coarsely.
    """
    if DAILY_USD_CACHE.exists():
        daily = json.loads(DAILY_USD_CACHE.read_text())
        if daily:
            return {**ETH_PRICES, **daily}
    return ETH_PRICES


def is_subset_key(meta: dict) -> bool:
    """True when a config key is a token-ID SUBSET of another key's contract, so its
    economics are already counted under the canonical (whole-contract) key. Counting it
    again would double the shared contract's volume/royalties (review Finding 2). Cases:
      - `token_id` set  → a single-token view (e.g. mothman_1of1 inside the aoki contract)
      - `token_ids` but no own fetch (`distributor`) → a subset like wilderness inside valentines
      - `shared` set with no `distributor` → a whole shared storefront with no curated token
        set of its own (e.g. mintable_early or sandbox) — a whole-contract fetch would
        conflict with other tenants, and these are economically negligible without own fetch
      - (backstop) address matches a KNOWN distributor storefront's address but the entry
        itself carries none of the flags above — same subset logic, kept in case a future
        config entry shares that address without also being tagged `token_id`/`token_ids`/`shared`
    Canonical distributor keys (e.g. genesis_reissue_1155, tournament_prizes as of Plan 4)
    are kept, not skipped — they own their curated tokens on the shared storefront."""
    if meta.get("distributor"):
        return False
    if meta.get("token_id") or meta.get("token_ids") or meta.get("shared"):
        return True
    if meta.get("address") in _STOREFRONT_ADDRS:
        return True
    return False


def _load(name: str):
    p = RAW / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _save(name: str, data) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2))
    print(f"  wrote public/data/{name}.json")


def analyze(top_n: int = 50) -> dict:
    prices = price_table()
    all_transfers: list = []
    collections: list = []
    mint_cost: dict = {}            # (collection_key, token_id) -> mint eth cost
    all_sales: list = []            # authoritative sale records (collection-tagged)
    floor_by_collection: dict = {}  # collection_key -> floor eth
    total_royalty = 0.0             # royalties to MetaZoo across all sales

    for key, meta in CONTRACTS.items():
        if meta.get("third_party"):
            # The Mothman 1/1 lives inside Steve Aoki's own contract
            continue
        if is_subset_key(meta):
            continue
        transfers = _load(f"{key}_transfers")
        if not transfers:
            continue
        for t in transfers:
            t["collection"] = key

        mintvals = _load(f"{key}_mintvalues") or {}
        sales = _load(f"{key}_sales") or []          
        sales = [s for s in sales if not s.get("is_phantom")]
        for s in sales:
            s["collection"] = key
        sales = econ.dedupe_sale_legs(sales)
        floor = (_load(f"{key}_floor") or {}).get("floor_eth", 0.0)
        floor_by_collection[key] = floor

        mint_cost.update(econ.mint_cost_per_token(transfers, mintvals, MINT_PRICES.get(key)))
        all_sales.extend(sales)

        all_transfers.extend(transfers)

        mints = [t for t in transfers if t["is_mint"]]
        mint_rev = round(sum(mintvals.values()), 4)
        mint_rev_usd = econ.mint_revenue_usd(transfers, mintvals, prices)
        royalty = round(sum(s["royalty_eth"] for s in sales), 4)
        volume = round(sum(s["price_eth"] for s in sales), 4)
        total_royalty += royalty
        collections.append({
            "collection": key,
            "name": meta["name"],
            "contract": meta["address"],
            "standard": meta["standard"],
            "total_transfers": len(transfers),
            "total_mints": len(mints),
            "unique_minters": len(set(t["to"] for t in mints)),
            "mint_revenue_eth": mint_rev,
            "mint_revenue_usd": mint_rev_usd,   
            "secondary_sales": len(sales),
            "secondary_volume_eth": volume,
            "royalty_eth": royalty,
            "floor_eth": floor,
            "include_in_loss_calc": meta.get("include_in_loss_calc", True),
        })
        print(f"  {key}: {len(transfers)} transfers | {len(mints)} mints | "
              f"{mint_rev} ETH mint rev | {len(sales)} sales / {volume} ETH vol / "
              f"{royalty} ETH royalties | floor {floor} ETH")

    if not all_transfers:
        print("No data in data/raw/. Run: python -m scripts.fetch_chain")
        return {}

    included = {c["collection"] for c in collections if c["include_in_loss_calc"]}
    loss_transfers = [t for t in all_transfers if t["collection"] in included]
    loss_sales = [s for s in all_sales if s["collection"] in included]
    now_price = prices[max(prices)]
    gas = econ.gas_by_wallet(loss_transfers, loss_sales)
    pnl = econ.wallet_pnl(loss_transfers, mint_cost, loss_sales, floor_by_collection,
                          prices=prices, now_price=now_price, gas=gas)

    total_spent = sum(v["eth_spent"] for v in pnl.values())
    total_realized = sum(v["realized_loss"] for v in pnl.values())
    total_unrealized = sum(v["unrealized_loss"] for v in pnl.values())
    total_realized_usd = sum(v.get("realized_loss_usd", 0.0) for v in pnl.values())
    total_unrealized_usd = sum(v.get("unrealized_loss_usd", 0.0) for v in pnl.values())
    total_gas = sum(v.get("gas_spent_eth", 0.0) for v in pnl.values())
    total_gas_usd = sum(v.get("gas_spent_usd", 0.0) for v in pnl.values())
    realized_gains = round(sum(v["realized_pnl_eth"] for v in pnl.values()
                               if v["realized_pnl_eth"] > 0), 4)
    realized_losses = round(sum(-v["realized_pnl_eth"] for v in pnl.values()
                                if v["realized_pnl_eth"] < 0), 4)
    realized_gains_usd = round(sum(v.get("realized_pnl_usd", 0.0) for v in pnl.values()
                                   if v["realized_pnl_eth"] > 0), 2)
    losers = [v for v in pnl.values()
              if v["realized_pnl_eth"] - v["unrealized_loss"] - v.get("gas_spent_eth", 0.0) < 0]
    whales = sorted((v for v in pnl.values() if v["eth_spent"] > 0),
                    key=lambda w: w["eth_spent"], reverse=True)[:top_n]
    flippers = sorted((v for v in pnl.values() if v["realized_pnl_eth"] != 0),
                      key=lambda w: w["realized_pnl_eth"], reverse=True)[:top_n]

    has_floor = any(f > 0 for f in floor_by_collection.values())
    total_volume = round(sum(c["secondary_volume_eth"] for c in collections), 4)
    total_mint_usd = round(sum(c["mint_revenue_usd"] for c in collections), 2)
    total_mint_eth = round(sum(c["mint_revenue_eth"] for c in collections), 4)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "collections_count": len(collections),
        "total_transfers": len(all_transfers),
        "total_wallets": len(pnl),
        "total_spent_eth": round(total_spent, 4),
        "total_mint_revenue_eth": total_mint_eth,
        "total_mint_revenue_usd": total_mint_usd,
        "secondary_volume_eth": total_volume,
        "royalties_to_metazoo_eth": round(total_royalty, 4),
        "realized_gains_eth": realized_gains,
        "realized_gains_usd": realized_gains_usd,
        "realized_losses_eth": realized_losses,
        "unrealized_loss_eth": round(total_unrealized, 4),
        "total_loss_eth": round(total_realized + total_unrealized + total_gas, 4),
        "gas_spent_eth": round(total_gas, 4),
        "unrealized_loss_usd": round(total_unrealized_usd, 2),
        "total_loss_usd": round(total_realized_usd + total_unrealized_usd + total_gas_usd, 2),
        "gas_spent_usd": round(total_gas_usd, 2),
        "wallets_net_loss": len(losers),
        "floor_data_available": has_floor,
        "bankruptcy": BANKRUPTCY,
        "disclaimer": ("Figures are estimates from public on-chain data; "
                       "Aoki payment amounts are alleged, not proven."),
    }

    _save("summary", summary)
    _save("collections", collections)
    _save("whales", whales)
    _save("flippers", flippers)
    _save("wallet_pnl", list(pnl.values()))

    print(f"\n  wallets {len(pnl)} | spent {total_spent:.2f} ETH")
    print(f"  Primary mint revenue: {total_mint_eth:.2f} ETH = ${total_mint_usd:,.0f} "
          f"(priced per mint date)")
    print(f"  Q1 royalties to MetaZoo: {total_royalty:.2f} ETH "
          f"(from {total_volume:.2f} ETH secondary volume)")
    print(f"  Q2 realized: +{realized_gains:.2f} ETH gains / -{realized_losses:.2f} ETH losses")
    print(f"  Q3 current holders unrealized loss: {total_unrealized:.2f} ETH "
          f"({'floor-adjusted' if has_floor else 'NO FLOOR DATA — run fetch_sales'})")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze cached data into public/data JSON")
    ap.add_argument("--whales", type=int, default=50, help="top N wallets by ETH spent")
    args = ap.parse_args()
    analyze(top_n=args.whales)


if __name__ == "__main__":
    main()
