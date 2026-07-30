"""Transform pipeline outputs (public/data, data/raw) into site/data/ JSON
for the metazoonfts.com frontend. Run: python -m scripts.build_site_data"""
import bisect
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scripts import econ
from scripts.config import (MINT_PRICES, AOKI_WALLETS, METAZOO_WALLETS, MEDIA_CDN_BASE,
                            CONTRACTS)
from scripts.config import SITE_COLLECTIONS, SANDBOX_ASSET_SUPPLY
from scripts.analyze import price_table
from scripts.trace_acquisitions import resolve_block_dates, eth_daily_usd

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DATA = ROOT / "public" / "data"
RAW = ROOT / "data" / "raw"
SITE_DATA = ROOT / "site" / "data"
PAYOUT_LEDGER_PATH = ROOT / "data" / "evidence" / "payout_ledger.json"
CONTENT_PATH = ROOT / "data" / "evidence" / "collection_content.json"
WALLET_IDENTITIES_PATH = ROOT / "data" / "evidence" / "wallet_identities.json"
WALLET_OVERRIDES_PATH = ROOT / "data" / "evidence" / "wallet_overrides.json"
WEB3BIO_PROFILES_PATH = ROOT / "data" / "evidence" / "web3bio_profiles.json"
OPENSEA_PROFILES_PATH = ROOT / "data" / "evidence" / "opensea_profiles.json"
MEDIA_INDEX = ROOT / "data" / "media_index"
UTILITY_PRODUCTS_PATH = ROOT / "data" / "evidence" / "utility_products.json"
UTILITY_MEDIA_PATH = MEDIA_INDEX / "utility.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)


def sanitize_summary(summary: dict, eth_price_usd: float) -> dict:
    """Site contract for summary.json: USD loss figures (`total_loss_usd`,
    `unrealized_loss_usd`) come straight from analyze.py, valued AT-EVENT
    (cost basis at purchase date, current floor at today's price)"""
    out = {k: v for k, v in summary.items() if k not in ("bankruptcy", "disclaimer")}
    out["eth_price_usd"] = round(eth_price_usd, 2)
    return out


_COLLECTION_FIELDS = ("collection", "name", "contract", "standard", "total_transfers",
                      "total_mints", "unique_minters", "mint_revenue_eth", "mint_revenue_usd",
                      "secondary_sales", "secondary_volume_eth", "royalty_eth", "floor_eth",
                      "include_in_loss_calc")


def collection_art(art, slug):
    """(image_url, video_url) for a collection's art. A manifest value is either a
    bare image URL (the usual case) or {"image", "video"}"""
    v = (art or {}).get(slug)
    if isinstance(v, dict):
        return v.get("image"), v.get("video")
    return v, None


def synth_collection_stats(slug, transfers, sales, mint_values, floor_eth, token_ids=None):
    """Build a Collection-shaped stats dict from raw records, optionally filtered
    to `token_ids` (for subset collections like Mothman inside `aoki`)."""
    ids = set(str(i) for i in token_ids) if token_ids else None

    def keep(rec):
        return ids is None or str(rec.get("token_id")) in ids

    trs = [t for t in transfers if keep(t)]
    sls = [s for s in sales if keep(s) and not s.get("is_phantom")]
    mints = [t for t in trs if t.get("is_mint")]
    minter_wallets = {t["to"] for t in mints}
    mint_cost = econ.mint_cost_per_token(trs, mint_values, MINT_PRICES.get(slug))
    return {
        "collection": slug,
        "name": slug,
        "contract": CONTRACTS.get(slug, {}).get("address")
                    or (trs[0].get("contract") if trs else None) or "",
        "standard": CONTRACTS.get(slug, {}).get("standard", "erc1155"),
        "total_transfers": len(trs),
        "total_mints": len(mints),
        "unique_minters": len(minter_wallets),
        "mint_revenue_eth": round(sum(mint_cost.values()), 6),
        "mint_revenue_usd": 0.0,
        "secondary_sales": len(sls),
        "secondary_volume_eth": round(float(sum(float(s.get("price_eth") or 0.0) for s in sls)), 6),
        "royalty_eth": round(float(sum(float(s.get("royalty_eth") or 0.0) for s in sls)), 6),
        "floor_eth": float(floor_eth or 0.0),
        "include_in_loss_calc": False,
    }


def filter_raw_to_tokens(transfers, sales, token_ids):
    """Filter raw transfers/sales down to a subset collection's token_ids"""
    ids = set(str(i) for i in token_ids)
    return ([t for t in transfers if str(t.get("token_id")) in ids],
            [s for s in sales if str(s.get("token_id")) in ids])


def _placeholder_stats(slug):
    return {"collection": slug, "name": slug, "contract": CONTRACTS.get(slug, {}).get("address") or "",
            "standard": CONTRACTS.get(slug, {}).get("standard", "erc1155"),
            "total_transfers": 0, "total_mints": 0, "unique_minters": 0,
            "mint_revenue_eth": 0.0, "mint_revenue_usd": 0.0, "secondary_sales": 0,
            "secondary_volume_eth": 0.0, "royalty_eth": 0.0, "floor_eth": 0.0,
            "include_in_loss_calc": False}


def build_collections(analyze_collections, eth_price_usd, per_slug_raw, art=None):
    """Return the 10 site collections in SITE_COLLECTIONS order."""
    by_slug = {c["collection"]: c for c in analyze_collections}
    art = art or {}
    out = []
    for reg in SITE_COLLECTIONS:
        slug, src = reg["slug"], reg["source"]
        synthesized = True
        if src == "own":
            if slug in by_slug:
                base = dict(by_slug[slug])                     # analyze.py's entry
                synthesized = False
            elif slug in per_slug_raw:                          # own raw but not in analyze
                pr = per_slug_raw[slug]
                base = synth_collection_stats(slug, pr["transfers"], pr["sales"],
                                              pr["mint_values"], pr["floor_eth"])
            else:
                base = _placeholder_stats(slug)
        elif src == "subset":
            pr = per_slug_raw.get(reg["parent"])
            parent_floor = (0.0 if CONTRACTS.get(reg["parent"], {}).get("third_party")
                            else (pr["floor_eth"] if pr else 0.0))
            base = (synth_collection_stats(slug, pr["transfers"], pr["sales"], pr["mint_values"],
                                           parent_floor, token_ids=reg["token_ids"])
                    if pr else _placeholder_stats(slug))
        else:  
            base = _placeholder_stats(slug)
        base = {k: base.get(k) for k in _COLLECTION_FIELDS}
        base["name"] = reg["name"]
        base["floor_usd"] = round(float(base.get("floor_eth") or 0.0) * eth_price_usd, 2)
        base["image"], base["video"] = collection_art(art, slug)
        if synthesized:
            base["mint_revenue_usd"] = round(float(base["mint_revenue_eth"]) * eth_price_usd, 2)

        for src_key in merge_sources_for(slug):
            pr_src = per_slug_raw.get(src_key)
            if not pr_src:
                continue
            keep_ids = mzg_token_ids() if src_key == "mintable_early" else None
            src_transfers, src_sales = pr_src["transfers"], pr_src["sales"]
            if keep_ids is not None:
                if not keep_ids:
                    continue
                src_transfers, src_sales = filter_raw_to_tokens(src_transfers, src_sales, keep_ids)
            extra = synth_collection_stats(src_key, src_transfers, src_sales,
                                           pr_src["mint_values"], pr_src["floor_eth"])
            issued, claimers = distributor_issuance(
                src_transfers, CONTRACTS.get(src_key, {}).get("distributor"))
            if not extra["total_mints"] and issued:
                extra["total_mints"] = len(issued)
            for f in ("total_transfers", "total_mints", "secondary_sales"):
                base[f] += extra[f]
            for f in ("mint_revenue_eth", "secondary_volume_eth", "royalty_eth"):
                base[f] = round(base[f] + extra[f], 6)
            base["mint_revenue_usd"] = round(base["mint_revenue_usd"]
                                             + extra["mint_revenue_eth"] * eth_price_usd, 2)
            own_pr = per_slug_raw.get(slug, {"transfers": []})
            minters = {t["to"] for t in own_pr["transfers"] + src_transfers
                       if t.get("is_mint") or t.get("from") == econ.ZERO} | claimers
            if minters:
                base["unique_minters"] = len(minters)
        out.append(base)
    return out


def distributor_issuance(transfers, distributor):
    """(token ids the distributor handed out, the wallets that received them)"""
    if not distributor:
        return set(), set()
    d = distributor.lower()
    out = [t for t in transfers if str(t.get("from", "")).lower() == d]
    return {str(t["token_id"]) for t in out}, {t["to"] for t in out}


def usd_at_month(eth, month, daily_usd, fallback):
    """RAW (unrounded) USD value of `eth` at `month`'s ("YYYY-MM") first-of-month
    Binance close, falling back to `fallback` (current price) when the month is
    unknown/missing."""
    price = daily_usd.get(f"{month}-01") if month else None
    return eth * (price if price is not None else fallback)


def usd_at_day(eth, date, daily_usd, fallback):
    """USD value of `eth` on an exact "YYYY-MM-DD", falling back to that month's
    close and then to `fallback`."""
    price = (daily_usd or {}).get(date) if date else None
    if price is not None:
        return eth * price
    return usd_at_month(eth, (date or "")[:7], daily_usd or {}, fallback)


def build_volume_series(sales_by_slug, block_month, daily_usd, eth_price_usd):
    def usd_for(eth, month):
        return round(usd_at_month(eth, month, daily_usd, eth_price_usd), 2)

    by_collection = {}
    eco = defaultdict(float)
    for slug, sales in sales_by_slug.items():
        months = defaultdict(float)
        for s in sales:
            if s.get("is_phantom"):
                continue
            month = block_month.get(s["block"])
            if month is None:
                continue
            months[month] += float(s.get("price_eth") or 0.0)
            eco[month] += float(s.get("price_eth") or 0.0)
        by_collection[slug] = [
            {"month": m, "eth": round(months[m], 4), "usd": usd_for(months[m], m)}
            for m in sorted(months)
        ]
    ecosystem = [
        {"month": m, "eth": round(eco[m], 4), "usd": usd_for(eco[m], m)}
        for m in sorted(eco)
    ]
    return {"ecosystem": ecosystem, "by_collection": by_collection}


def erc1155_edition_count(transfers, distributor):
    """Total ERC-1155 editions minted = the sum of quantity over "mint-like"
    transfers: 0x0 mints (is_mint) for real drops like Valentines, OR the
    distributor's out-transfers for lazy-mint airdrops (genesis-reissue,
    tournament) that have no 0x0 hop."""
    d = (distributor or "").lower()
    n = 0
    for t in transfers:
        if t.get("is_mint") or (d and (t.get("from") or "").lower() == d):
            n += int(t.get("quantity", 1))
    return n


def enrich_collections_display(collections, vol_by_collection, authored, eth_price_usd, piece_counts):
    """Add display fields the frontend needs, in place: `secondary_volume_usd`
    (at-event, summed from the volume series), `royalty_usd` (royalty ETH valued at
    the same blended rate the volume traded), `loss_pct` (off-chain basis when the
    collection has one."""
    vol_usd = {slug: round(sum(p["usd"] for p in pts), 2)
               for slug, pts in (vol_by_collection or {}).items()}
    for c in collections:
        slug = c["collection"]
        is_1155 = c.get("standard") == "erc1155"
        if piece_counts.get(slug) is not None and (is_1155 or not c.get("total_mints")):
            c["total_mints"] = piece_counts[slug]
        sv_eth = float(c.get("secondary_volume_eth") or 0.0)
        sv_usd = vol_usd.get(slug)
        if sv_usd is None:
            sv_usd = round(sv_eth * eth_price_usd, 2)
        c["secondary_volume_usd"] = sv_usd
        rate = (sv_usd / sv_eth) if sv_eth > 0 else eth_price_usd
        c["royalty_usd"] = round(float(c.get("royalty_eth") or 0.0) * rate, 2)

        ob = (authored.get(slug) or {}).get("off_chain_basis")
        floor_usd = float(c.get("floor_usd") or 0.0)
        if ob and ob.get("unit_cost_usd"):
            c["loss_pct"] = round((floor_usd - ob["unit_cost_usd"]) / ob["unit_cost_usd"] * 100, 1)
        else:
            avg = (float(c["mint_revenue_eth"]) / c["total_mints"]
                   if c.get("total_mints") and c.get("mint_revenue_eth") else 0.0)
            c["loss_pct"] = round((float(c.get("floor_eth") or 0.0) - avg) / avg * 100, 1) if avg > 0 else None
    return collections


def build_wallet_index(wallets, offchain_usd_by_wallet=None):
    """Global per-wallet P&L. `net_pnl_eth`/`net_pnl_usd` are on-chain. `all_in_net_usd`
    folds in each wallet's off-chain physical-box cost (`offchain_cost_usd`, from
    build_global_offchain_usd) so the frontend can rank by an overall-USD figure."""
    off = {k.lower(): v for k, v in (offchain_usd_by_wallet or {}).items()}
    out = []
    for w in wallets:
        d = dict(w)
        d["net_pnl_eth"] = round(
            float(w.get("realized_pnl_eth") or 0.0) - float(w.get("unrealized_loss") or 0.0)
            - float(w.get("gas_spent_eth") or 0.0), 6
        )
        d["net_pnl_usd"] = round(
            float(w.get("realized_pnl_usd") or 0.0) - float(w.get("unrealized_loss_usd") or 0.0)
            - float(w.get("gas_spent_usd") or 0.0), 2
        )
        oc = round(float(off.get(str(w["wallet"]).lower(), 0.0)), 2)
        d["offchain_cost_usd"] = oc
        d["all_in_net_usd"] = round(d["net_pnl_usd"] - oc, 2)
        d["loss_rank"] = None
        out.append(d)
    out.sort(key=lambda d: d["net_pnl_eth"])
    rank = 0
    for d in out:
        if d["net_pnl_eth"] < 0:
            rank += 1
            d["loss_rank"] = rank
    return out


def collection_wallet_pnls(transfers, mint_values, sales, floor_eth, collection_key=None,
                           prices=None, now_price=0.0):
    """Per-wallet P&L scoped to ONE collection, mirroring analyze.py's call
    sequence (econ.mint_cost_per_token -> econ.wallet_pnl) so the per-collection
    slice here is computed the same way analyze.py computes it."""
    if collection_key is not None:
        transfers = [dict(t, collection=collection_key) for t in transfers]
        sales = [dict(s, collection=collection_key) for s in sales]
    non_phantom = [s for s in sales if not s.get("is_phantom")]
    gas = econ.gas_by_wallet(transfers, non_phantom)
    collections = {t["collection"] for t in transfers if t.get("collection")}
    collections |= {s["collection"] for s in non_phantom if s.get("collection")}
    mint_cost = {}
    for key in collections:
        coll_transfers = [t for t in transfers if t.get("collection") == key]
        mint_cost.update(
            econ.mint_cost_per_token(coll_transfers, mint_values, MINT_PRICES.get(key))
        )
    floor_by_collection = {c: floor_eth for c in collections}
    pnl_map = econ.wallet_pnl(transfers, mint_cost, non_phantom, floor_by_collection,
                              prices=prices, now_price=now_price, gas=gas)
    return list(pnl_map.values())


def build_holders(wallet_pnls, metazoo_addrs):
    """One ranked holders table (replaces the split losers/flippers leaderboards).
    Includes EVERY wallet that ever held, bought, or sold in the collection"""
    def net_eth(w):
        return (float(w.get("realized_pnl_eth") or 0.0)
                - float(w.get("unrealized_loss") or 0.0)
                - float(w.get("gas_spent_eth") or 0.0))

    def entry(w):
        return {
            "wallet": w["wallet"],
            "tokens_held": w.get("tokens_held", 0),
            "tokens_bought": w.get("tokens_bought", 0),
            "tokens_sold": w.get("tokens_sold", 0),
            "unrealized_loss": round(float(w.get("unrealized_loss") or 0.0), 6),
            "unrealized_loss_usd": round(float(w.get("unrealized_loss_usd") or 0.0), 2),
            "realized_pnl_eth": round(float(w.get("realized_pnl_eth") or 0.0), 6),
            "realized_pnl_usd": round(float(w.get("realized_pnl_usd") or 0.0), 2),
            "eth_spent": round(float(w.get("eth_spent") or 0.0), 6),
            "eth_received": round(float(w.get("eth_received") or 0.0), 6),
            "metazoo": w["wallet"].lower() in metazoo_addrs,
            "tokens_minted": w.get("tokens_minted", 0),
            "tokens_received": w.get("tokens_received", 0),
            "tokens_sent": w.get("tokens_sent", 0),
            "gas_spent_eth": round(float(w.get("gas_spent_eth") or 0.0), 6),
            "gas_spent_usd": round(float(w.get("gas_spent_usd") or 0.0), 2),
            "net_pnl_eth": round(net_eth(w), 6),
            "net_pnl_usd": round(float(w.get("realized_pnl_usd") or 0.0)
                                 - float(w.get("unrealized_loss_usd") or 0.0)
                                 - float(w.get("gas_spent_usd") or 0.0), 2),
        }

    active = [w for w in wallet_pnls
              if (w.get("tokens_held") or w.get("tokens_bought")
                  or w.get("tokens_sold") or w.get("tokens_minted")
                  or w.get("tokens_received") or w.get("tokens_sent"))]
    active.sort(key=net_eth)                                    # default: most lost first
    return {"holders": [entry(w) for w in active]}


def offchain_box_counts(transfers, token_ids=None):
    """Per-wallet count of PRIMARY-mint boxes (a from==0x0 transfer, quantity-weighted
    for ERC-1155), optionally restricted to a set of `token_ids`."""
    ids = {str(t) for t in token_ids} if token_ids is not None else None
    counts = defaultdict(int)
    for t in transfers:
        if t.get("from") != econ.ZERO:            # a box == a primary mint
            continue
        if ids is not None and str(t.get("token_id")) not in ids:
            continue
        try:
            q = int(t.get("quantity") or 1)
        except (TypeError, ValueError):
            q = 1
        counts[t["to"]] += q
    return dict(counts)


def apply_offchain(holder_rows, unit_cost_usd, mint_count_by_wallet=None):
    """Fold an off-chain physical-box cost into per-wallet all-in P&L."""
    revenue = 0.0
    out = []
    for r in holder_rows:
        r = dict(r)
        boxes = (mint_count_by_wallet.get(r["wallet"], 0) if mint_count_by_wallet is not None
                 else (r.get("tokens_minted", 0) or 0))
        if not r.get("metazoo") and boxes:
            box = boxes * unit_cost_usd
            revenue += box
            r["all_in_net_usd"] = round(float(r.get("net_pnl_usd") or 0.0) - box, 2)
        out.append(r)
    return {"holders": out, "offchain_revenue_usd": round(revenue, 2)}


VALENTINES_PROPER_IDS = tuple(CONTRACTS["valentines"]["valentines_token_ids"])

AIRDROP_DROPS = {"valentines", "wilderness"}


def child_subset_ids(slug):
    """Token IDs on `slug`'s contract that some child subset collection claims
    (e.g. wilderness IDs 7-11 inside the valentines contract)."""
    return {str(tid) for other in SITE_COLLECTIONS
            if other.get("parent") == slug and other.get("token_ids")
            for tid in other["token_ids"]}


def offchain_scope_for(slug):
    """(raw source slug, token-id scope tuple|None) for a physical-box drop, else None.
    PFP 2.0 = its own contract, all IDs; Valentines = its own raw scoped to IDs 1-6;
    Wilderness = the Valentines raw scoped to the config subset (7-11)."""
    if slug == "pfp_2":
        return ("pfp_2", None)
    if slug == "valentines":
        return ("valentines", VALENTINES_PROPER_IDS)
    if slug == "wilderness":
        return ("valentines", tuple(CONTRACTS["wilderness"].get("token_ids") or ()))
    return None


def build_global_offchain_usd(per_slug_raw, authored, metazoo_addrs):
    """Per-wallet total off-chain physical-box cost (USD) across every box drop, keyed
    by LOWERCASE wallet, excluding team/MetaZoo wallets."""
    out = defaultdict(float)
    for slug in ("pfp_2", "valentines", "wilderness"):
        scope = offchain_scope_for(slug)
        unit = ((authored.get(slug) or {}).get("off_chain_basis") or {}).get("unit_cost_usd")
        pr = per_slug_raw.get(scope[0]) if scope else None
        if not pr or not unit:
            continue
        for w, n in offchain_box_counts(pr["transfers"], scope[1]).items():
            if w.lower() not in metazoo_addrs:
                out[w.lower()] += n * unit
    return {w: round(v, 2) for w, v in out.items()}


def build_tokens(transfers, sales, mint_values, floor_eth, block_month, daily_usd,
                  eth_price_usd, slug=None, media=None, traits=None):
    latest_sale = {}
    for s in sales:
        if s.get("is_phantom"):
            continue
        tid = s["token_id"]
        if tid not in latest_sale or s["block"] > latest_sale[tid]["block"]:
            latest_sale[tid] = s
    order = []
    seen = set()
    for t in transfers:
        tid = t["token_id"]
        if tid not in seen:
            seen.add(tid)
            order.append(tid)
    ZERO = econ.ZERO
    placeholder_collection = slug or "_unknown"
    transfers_with_collection = []
    for t in transfers:
        t_copy = dict(t)
        if "collection" not in t_copy:
            t_copy["collection"] = placeholder_collection
        if "from" not in t_copy and t.get("is_mint"):
            t_copy["from"] = ZERO
        transfers_with_collection.append(t_copy)
    mint_cost = econ.mint_cost_per_token(transfers_with_collection, mint_values, MINT_PRICES.get(slug))
    mint_cost_by_tid = {k[1]: v for k, v in mint_cost.items()}

    floor_usd = round(float(floor_eth or 0.0) * eth_price_usd, 2)

    cfg1155 = CONTRACTS.get(slug or "", {})
    supply_by_tid = {}
    if cfg1155.get("standard") == "erc1155":
        dist = (cfg1155.get("distributor") or "").lower()
        for t in transfers:
            if t.get("is_mint") or (dist and (t.get("from") or "").lower() == dist):
                supply_by_tid[t["token_id"]] = (supply_by_tid.get(t["token_id"], 0)
                                                + int(t.get("quantity", 1)))

    def usd_for(eth, month):
        return round(usd_at_month(eth, month, daily_usd, eth_price_usd), 2)

    out = []
    for tid in order:
        sale = latest_sale.get(tid)
        if sale is not None:
            eth = float(sale.get("price_eth") or 0.0)
            date = block_month.get(sale["block"])
        else:
            eth = float(mint_cost_by_tid.get(str(tid), 0.0))
            date = None
        entry = (media or {}).get(tid)
        out.append({
            "token_id": tid,
            "name": entry["name"] if entry else None,
            "type": (traits or {}).get(str(tid)),   # filter dimension 
            "image": f"{MEDIA_CDN_BASE}/tokens/{slug}/{entry['file']}" if entry else None,
            "video": (f"{MEDIA_CDN_BASE}/tokens/{slug}/{entry['video']}"
                      if entry and entry.get("video") else None),
            "last_paid_eth": round(eth, 6),
            "last_paid_date": date,
            "last_paid_usd": usd_for(eth, date),
            "floor_eth": round(float(floor_eth or 0.0), 6),
            "floor_usd": floor_usd,
            "supply": supply_by_tid.get(tid),
        })
    out.sort(key=lambda t: t["last_paid_eth"], reverse=True)
    return out


def merge_sources_for(slug):
    """CONTRACTS keys whose tokens merge into `slug`'s site page (Plan 5:
    mintable_early's MZG tokens -> genesis_2021)."""
    return [k for k, m in CONTRACTS.items() if m.get("merge_into") == slug]


def merge_pnl_lists(a, b):
    """Adapt merge_wallet_pnls (dict-keyed) to collection_wallet_pnls' actual
    return shape (a list of per-wallet dicts, each carrying its own "wallet"
    key)"""
    ad = {p["wallet"]: p for p in a}
    bd = {p["wallet"]: p for p in b}
    return list(merge_wallet_pnls(ad, bd).values())


def merge_wallet_pnls(a, b):
    """Merge two per-wallet P&L maps: numeric fields sum, list fields concatenate,
    wallets present in only one side pass through unchanged."""
    out = {w: dict(v) for w, v in a.items()}
    for w, v in b.items():
        if w not in out:
            out[w] = dict(v)
            continue
        for k, val in v.items():
            if isinstance(val, list):
                out[w][k] = list(out[w].get(k, [])) + list(val)
            elif isinstance(val, (int, float)):
                out[w][k] = out[w].get(k, 0) + val
            else:
                out[w].setdefault(k, val)
    return out


MZG_CLASSIFICATION_PATH = ROOT / "data" / "evidence" / "mintable_mzg_classification.json"


def mzg_token_ids():
    """Token IDs classified MZG (Genesis) in the tracked evidence map; [] if the
    classification map hasn't been generated yet (Task 2 output)."""
    if not MZG_CLASSIFICATION_PATH.exists():
        return []
    doc = load_json(MZG_CLASSIFICATION_PATH)
    return [t for t, e in doc.get("tokens", {}).items() if e.get("mzg")]


def tracked_token_ids(parent_slug):
    """Token ids on `parent_slug`'s contract that some other config key tracks as a
    subset (mothman_1of1 -> token 1017 on the aoki contract)."""
    out = set()
    for meta in CONTRACTS.values():
        if meta.get("address") != CONTRACTS.get(parent_slug, {}).get("address"):
            continue
        if meta.get("token_id"):
            out.add(str(meta["token_id"]))
        for t in meta.get("token_ids") or []:
            out.add(str(t))
    return out


def raw_slugs_for(site_collections):
    """Slugs that need raw data loaded from data/raw/: every 'own' slug plus every
    'subset' slug's parent, plus every merge-source key (e.g. mintable_early ->
    genesis_2021), deduped."""
    own = [c["slug"] for c in site_collections if c["source"] == "own"]
    parents = [c["parent"] for c in site_collections if c["source"] == "subset" and c["parent"]]
    merge_keys = [k for c in site_collections for k in merge_sources_for(c["slug"])]
    return list(dict.fromkeys(own + parents + merge_keys))


def build_sandbox3d(entries):
    """Filter out any entry with `model: None`"""
    out = []
    for e in entries:
        if e.get("model") is None:
            continue
        model = "/sandbox3d/" + e["model"].rsplit("/", 1)[-1]
        out.append({**e, "model": model,
                    "supply": SANDBOX_ASSET_SUPPLY.get(e["token_id"])})
    return out


def build_usd_audit(audit):
    """site/data passthrough of the treasury USD audit; None -> null on disk so
    the frontend's static import always resolves."""
    return audit


def merge_profiles(web3bio=None, opensea=None):
    """Field-level merge of the two identity sources into one {addr: {username, pfp}}.
    Per field, OpenSea (classic Data API key) wins when set, else web3.bio"""
    w_by = {k.lower(): (v or {}) for k, v in (web3bio or {}).items()}
    o_by = {k.lower(): (v or {}) for k, v in (opensea or {}).items()}
    out = {}
    for a in w_by.keys() | o_by.keys():
        w, o = w_by.get(a, {}), o_by.get(a, {})
        username = o.get("username") or w.get("username")
        pfp = o.get("pfp") or w.get("pfp")
        if username or pfp:
            out[a] = {"username": username, "pfp": pfp}
    return out


def curated_overrides(raw):
    """Address-keyed curated presentation entries from data/evidence/wallet_overrides.json,
    lowercased."""
    return {a.lower(): e for a, e in (raw or {}).items()
            if a.startswith("0x") and isinstance(e, dict)}


def build_wallet_names(identities, opensea=None, overrides=None):
    """Compact {address: display_name} map for the frontend, from the ENS/curated
    identity evidence ({addr: {ens, ens_verified, label, source}}) layered with
    OpenSea account usernames ({addr: {username, pfp}})."""
    opensea = opensea or {}
    out = {}
    for addr, e in (identities or {}).items():
        a = addr.lower()
        label = e.get("label")
        is_ens = "ENS" in (e.get("source") or "")
        os_name = (opensea.get(a) or {}).get("username")
        if label and not is_ens:
            out[a] = label                       # curated label wins
        elif os_name:
            out[a] = os_name                     # OpenSea username
        elif label:
            out[a] = label                       # verified ENS primary
    for a, p in opensea.items():                 # OpenSea usernames for wallets not in ENS evidence
        a = a.lower()
        if a not in out and p.get("username"):
            out[a] = p["username"]
    for a, e in curated_overrides(overrides).items():
        if e.get("name"):
            out[a] = e["name"]                   # hand-curated name beats every source
    return out


def build_wallet_avatars(opensea=None, overrides=None):
    """OpenSea profile pictures, with curated overrides on top (their 
    `avatar_file` names a file in data/media/wallets/, served from the CDN)."""
    out = {}
    for a, p in (opensea or {}).items():
        pfp = p.get("pfp")
        if pfp:
            out[a.lower()] = pfp
    for a, e in curated_overrides(overrides).items():
        if e.get("avatar_file"):
            out[a] = f"{MEDIA_CDN_BASE}/wallets/{e['avatar_file']}"
    return out


def build_flippers(flippers_list, identities, total_gains_eth, total_gains_usd,
                   realized_losses_eth, count_profitable, top=10):
    """The counterparty to holder loss: the traders who realized the biggest ETH
    gains, joined to their ENS/curated identity (data/evidence/wallet_identities.json,
    keyed by lowercased address; {} if not yet resolved)."""
    ids = identities or {}
    rows = []
    for f in flippers_list:
        if float(f.get("realized_pnl_eth") or 0.0) <= 0:
            continue
        net = (float(f.get("realized_pnl_eth") or 0.0)
               - float(f.get("unrealized_loss") or 0.0)
               - float(f.get("gas_spent_eth") or 0.0))
        if net <= 0:
            continue
        ident = ids.get(f["wallet"].lower(), {})
        rows.append({
            "wallet": f["wallet"],
            "label": ident.get("label"),
            "ens": ident.get("ens"),
            "ens_verified": bool(ident.get("ens_verified")),
            "eth_spent": round(float(f.get("eth_spent") or 0.0), 4),
            "eth_received": round(float(f.get("eth_received") or 0.0), 4),
            "realized_pnl_eth": round(float(f.get("realized_pnl_eth") or 0.0), 4),
            "realized_pnl_usd": round(float(f.get("realized_pnl_usd") or 0.0), 2),
            "tokens_held": f.get("tokens_held", 0),
        })
        if len(rows) >= top:
            break
    identified = sum(1 for r in rows if r["label"])
    return {
        "total_gains_eth": round(float(total_gains_eth), 2),
        "total_gains_usd": round(float(total_gains_usd), 2),
        "realized_losses_eth": round(float(realized_losses_eth), 2),
        "count_profitable": count_profitable,
        "identified_in_top": identified,
        "top": rows,
    }


def load_utility():
    """(products, media) from the authored catalogue + its media manifest.

    Both are optional: a checkout without them builds with no utility tiles, the
    same graceful degrade as the token art and wallet identities."""
    products = load_json(UTILITY_PRODUCTS_PATH) if UTILITY_PRODUCTS_PATH.exists() else []
    media = load_json(UTILITY_MEDIA_PATH) if UTILITY_MEDIA_PATH.exists() else {}
    return products, media


ID_RE = re.compile(r"^[a-z0-9_]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_products(products, known_slugs):
    """Every product must name a real collection (a typo would silently drop the
    product from the site) and carry a clean `id`: it doubles as the CDN filename
    stem, so a duplicate silently shares one image between two products, and a
    space/punctuation character makes the unencoded upload path and the
    percent-encoded fetch URL disagree."""
    seen_ids = set()
    for p in products:
        pid = p.get("id")
        if p.get("collection") not in known_slugs:
            raise ValueError(f"utility_products.json: {pid!r} names unknown "
                             f"collection {p.get('collection')!r}")
        if not isinstance(pid, str) or not ID_RE.match(pid):
            raise ValueError(f"utility_products.json: id {pid!r} must match "
                             f"^[a-z0-9_]+$ (it is used as the CDN filename stem)")
        if pid in seen_ids:
            raise ValueError(f"utility_products.json: duplicate id {pid!r}")
        seen_ids.add(pid)
        for field in ("price_usd", "price_eth"):
            price = p.get(field)
            if price is not None and not isinstance(price, (int, float)):
                raise ValueError(f"utility_products.json: {pid!r} has a non-numeric "
                                 f"{field} {price!r}")
        if p.get("price_eth") is not None and not p.get("date"):
            raise ValueError(f"utility_products.json: {pid!r} is priced in ETH but "
                             f"has no date to value it at")
        date = p.get("date")
        if date is not None and not (isinstance(date, str) and DATE_RE.match(date)):
            raise ValueError(f"utility_products.json: {pid!r} has date {date!r}, "
                             f"which must be YYYY-MM-DD")


def utility_image_url(entry):
    """CDN URL for a product's art, carrying the file's content hash."""
    if not entry:
        return None
    url = f"{MEDIA_CDN_BASE}/utility/{entry['file']}"
    return f"{url}?v={entry['hash']}" if entry.get("hash") else url


def build_utility(slug, products, media, daily_usd=None, eth_price_usd=None):
    """This collection's products, oldest first, with their CDN art."""
    rows = []
    for p in sorted(products or [], key=lambda x: (x.get("date") is None, x.get("date") or "")):
        if p.get("collection") != slug:
            continue
        entry = (media or {}).get(p["id"])
        if p.get("image_file") and not entry:
            print(f"  [warn] utility product {p['id']!r} has image_file "
                  f"{p['image_file']!r} but no media manifest entry; run "
                  f"python -m scripts.index_utility_media")
        eth_price = p.get("price_eth")
        usd_price = p.get("price_usd")
        if eth_price is not None and usd_price is None:
            usd_price = round(usd_at_day(eth_price, p.get("date"), daily_usd,
                                         eth_price_usd or 0), 2)
        rows.append({
            "id": p["id"],
            "name": p["name"],
            "price_usd": usd_price,
            "price_eth": eth_price,
            "note": p.get("note", ""),
            "image": utility_image_url(entry),
        })
    return rows


def build_content(slug, authored, floor_usd=None, products=None, media=None,
                  daily_usd=None, eth_price_usd=None):
    content = dict(authored.get(slug) or {"overview": []})
    content["utility"] = build_utility(slug, products, media, daily_usd, eth_price_usd)
    basis = content.get("off_chain_basis")
    if basis and floor_usd is not None:
        unit = float(basis.get("unit_cost_usd") or 0.0)
        loss_pct = round((floor_usd - unit) / unit * 100, 1) if unit else None
        content = {**content,
                   "off_chain_basis": {**basis, "floor_usd": floor_usd, "loss_pct": loss_pct}}
    img = content.get("overview_image")
    if img:
        if img.startswith("http"):
            url = img
        elif "/" in img:
            url = f"{MEDIA_CDN_BASE}/{img}"
        else:
            url = f"{MEDIA_CDN_BASE}/overview/{img}"
        content = {**content, "overview_image": url}
    return content


def build_coin_strip(limit=12):
    """One representative MetaZoo Coin Token per DESIGN for the home wallet-lookup
    card's coin row."""
    media_p = MEDIA_INDEX / "tokens" / "coin_tokens.json"
    if not media_p.exists():
        return []
    media = load_json(media_p)
    traits_p = MEDIA_INDEX / "traits" / "coin_tokens.json"
    traits = load_json(traits_p) if traits_p.exists() else {}
    seen, out = set(), []
    for tid, e in media.items():
        f = e.get("file")
        if not f:
            continue
        key = traits.get(str(tid)) or f          # one per design type
        if key in seen:
            continue
        seen.add(key)
        out.append({"token_id": tid, "image": f"{MEDIA_CDN_BASE}/tokens/coin_tokens/{f}"})
        if len(out) >= limit:
            break
    return out


BLUECHIP_TILE_ORDER = [
    "0x8a90cab2b38dba80c64b7734e58ee1db38b8992e",  # Doodles
    "0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb",  # CryptoPunks
    "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d",  # BoredApeYachtClub
    "0x3bf2922f4520a8ba0c2efc3d2a1539678dad5e9d",  # 0N1 Force
    "0x22c36bfdcef207f9c0cc941936eff94d4246d14a",  # Bored Ape Chemistry Club
]


def _top_example_per_bluechip(top_items, with_image):
    """One specific NFT example per blue-chip collection, in BLUECHIP_TILE_ORDER
    (Doodles, CryptoPunks, BAYC, 0N1, Chemistry Club) so the example tiles line up
    with the underwater/logo tiles above them."""
    out = []
    for c in BLUECHIP_TILE_ORDER:
        ex = next((i for i in top_items if (i.get("contract") or "").lower() == c), None)
        if ex:
            out.append(with_image(ex))
    return out


def _acquisitions_block(acquisitions, with_holdings, with_image):
    """The acquisitions payload: every collection folded with holdings + logo, the
    5 ordered blue-chip 'underwater' tiles (BLUECHIP_TILE_ORDER, so each stat tile
    lines up with its collection image), one marquee NFT example per blue-chip
    (same order), and the top-item art tiles."""
    by_collection = [with_holdings(b) for b in acquisitions["by_collection"]]
    by_contract = {(b.get("contract") or "").lower(): b for b in by_collection}
    underwater = [by_contract[c] for c in BLUECHIP_TILE_ORDER
                  if c in by_contract and by_contract[c].get("loss_pct") is not None]
    return {
        "total_eth": acquisitions["total_eth"],
        "total_usd": acquisitions["total_usd"],
        "total_purchases": acquisitions["total_purchases"],
        "by_collection": by_collection,
        "underwater": underwater,
        "top_examples": _top_example_per_bluechip(acquisitions["top_items"], with_image),
        "top_items": [with_image(i) for i in acquisitions["top_items"][:24]],
    }


def build_findings(flow_summary, summary, acquisitions, payout_ledger,
                   acq_media=None, eth_price_usd=0.0, holdings=None, audit=None,
                   secondary_volume_usd=0.0, royalties_usd=0.0, flippers=None,
                   acq_collection_art=None, pfp2_offchain_revenue_usd=0.0):
    insider_rows = [r for r in payout_ledger if r.get("kind") == "insider"]
    insider_eth = round(sum(r["eth"] for r in insider_rows), 2)
    insider_usd = round(sum(r.get("usd", 0.0) for r in insider_rows), 2)

    coll_art = acq_collection_art or {}

    def coll_image(contract):
        e = coll_art.get((contract or "").lower())
        return f"{MEDIA_CDN_BASE}/acq_collections/{e['file']}" if e else None

    def with_image(item):
        key = f"{(item.get('contract') or '').lower()}_{item['token_id']}"
        e = (acq_media or {}).get(key)
        return {**item, "image": f"{MEDIA_CDN_BASE}/acquisitions/{e['file']}" if e else None}

    hold_map = (holdings or {}).get("holdings", {})

    def with_holdings(b):
        h = hold_map.get((b.get("contract") or "").lower()) or {}
        return {**b, "image": coll_image(b.get("contract")), "held_now": h.get("held_now"),
                "avg_paid_eth": h.get("avg_paid_eth"), "floor_eth": h.get("floor_eth"),
                "loss_pct": h.get("loss_pct")}

    royalties_eth = summary["royalties_to_metazoo_eth"]
    aoki_eth = flow_summary["metazoo_to_aoki_eth"]
    aoki_out = ((audit or {}).get("by_class", {}).get("out", {}).get("aoki") or {})
    aoki_usd = aoki_out.get("usd", round(aoki_eth * eth_price_usd, 2))
    return {
        "legs": {
            "secondary_volume_eth": summary["secondary_volume_eth"],
            "secondary_volume_usd": secondary_volume_usd,   # at-event (sale-date prices)
            "royalties_eth": royalties_eth,
            "royalties_usd": royalties_usd,                 # at-event (sale-date prices)
            "aoki_eth": aoki_eth,
            "aoki_usd": aoki_usd,                           # at-spend (from audit)
            "insider_eth": insider_eth,
            "insider_usd": insider_usd,                     # at-spend (payout-ledger dates)
            "eth_price_usd": round(eth_price_usd, 2),
        },
        "flippers": flippers or {"total_gains_eth": 0.0, "total_gains_usd": 0.0,
                                 "realized_losses_eth": 0.0, "count_profitable": 0,
                                 "identified_in_top": 0, "top": []},
        "payout_ledger": payout_ledger,
        "pfp2_offchain_revenue_usd": round(pfp2_offchain_revenue_usd, 2),
        "acquisitions": _acquisitions_block(acquisitions, with_holdings, with_image),
        "insider": {
            "eth": insider_eth,
            "exchange": "Coinbase",
            "note": "Fresh MetaZoo-funded wallets, no ENS/history. Traced forward, "
                    "roughly 97% of this ETH cashed out to a centralized exchange "
                    "(overwhelmingly Coinbase, one branch to FTX); the rest commingled "
                    "into an active trading wallet. The personal account behind each "
                    "exchange deposit is KYC-gated and not attributable on-chain.",
        },
    }


def _block_to_month(needed_blocks, block_ts):
    """{block: "YYYY-MM"} for every block in `needed_blocks`, derived OFFLINE
    from `block_ts` ({block: unix_timestamp}, built from already-loaded raw
    transfer records)."""
    anchors = sorted(block_ts)
    if not anchors:
        return {}

    def month_of(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")

    out = {}
    for blk in set(needed_blocks):
        if blk in block_ts:
            out[blk] = month_of(block_ts[blk])
            continue
        i = bisect.bisect_left(anchors, blk)
        lo = anchors[i - 1] if i > 0 else None
        hi = anchors[i] if i < len(anchors) else None
        if lo is not None and hi is not None:
            ts_lo, ts_hi = block_ts[lo], block_ts[hi]
            est_ts = ts_lo + (blk - lo) * (ts_hi - ts_lo) / (hi - lo)
        elif lo is not None:
            est_ts = block_ts[lo]
        else:
            est_ts = block_ts[hi]
        out[blk] = month_of(est_ts)
    return out


def main():
    summary = load_json(PUBLIC_DATA / "summary.json")
    analyze_collections = load_json(PUBLIC_DATA / "collections.json")
    daily_usd = eth_daily_usd()
    eth_price_usd = daily_usd[max(daily_usd)]
    prices = price_table()

    write_json(SITE_DATA / "summary.json", sanitize_summary(summary, eth_price_usd))

    raw_slugs = raw_slugs_for(SITE_COLLECTIONS)

    per_slug_raw = {}
    needed_blocks, block_ts = [], {}
    for slug in raw_slugs:
        paths = {k: RAW / f"{slug}_{k}.json" for k in ("sales", "transfers", "mintvalues", "floor")}
        missing = [p.name for p in paths.values() if not p.exists()]
        if missing:
            print(f"[skip] {slug}: missing raw file(s): {', '.join(missing)}")
            continue
        sales = load_json(paths["sales"]); transfers = load_json(paths["transfers"])
        if CONTRACTS.get(slug, {}).get("third_party"):
            keep = tracked_token_ids(slug)
            if keep:
                transfers, sales = filter_raw_to_tokens(transfers, sales, keep)
        for s in sales:
            s.setdefault("collection", slug)
        sales = econ.dedupe_sale_legs(sales)
        per_slug_raw[slug] = {"sales": sales, "transfers": transfers,
                              "mint_values": load_json(paths["mintvalues"]),
                              "floor_eth": load_json(paths["floor"]).get("floor_eth", 0.0)}
        needed_blocks += [s["block"] for s in sales if not s.get("is_phantom")]
        for t in transfers:
            if t.get("timestamp") is not None:
                block_ts[t["block"]] = t["timestamp"]
    block_month = _block_to_month(needed_blocks, block_ts)

    art_path = MEDIA_INDEX / "collection_art.json"
    art = load_json(art_path) if art_path.exists() else None

    site_collections = build_collections(analyze_collections, eth_price_usd, per_slug_raw, art=art)
    write_json(SITE_DATA / "coin_strip.json", build_coin_strip())

    sales_by_slug = {s: per_slug_raw[s]["sales"] for s in raw_slugs if s in per_slug_raw}
    volume = build_volume_series(sales_by_slug, block_month, daily_usd, eth_price_usd)
    write_json(SITE_DATA / "volume_series.json", volume)

    authored_content = load_json(CONTENT_PATH) if CONTENT_PATH.exists() else {}
    sandbox3d = load_json(MEDIA_INDEX / "sandbox3d.json") if (MEDIA_INDEX / "sandbox3d.json").exists() else []
    piece_counts = {}
    for reg in SITE_COLLECTIONS:
        s = reg["slug"]
        src = s if reg["source"] == "own" else reg.get("parent")
        pr = per_slug_raw.get(src)
        if not pr:
            continue
        ids = set(map(str, reg["token_ids"])) if reg.get("token_ids") else None
        child_ids = child_subset_ids(s)
        ts = [t for t in pr["transfers"]
              if (ids is None or str(t.get("token_id")) in ids)
              and str(t.get("token_id")) not in child_ids]
        if CONTRACTS.get(src, {}).get("standard") == "erc1155":
            piece_counts[s] = erc1155_edition_count(ts, CONTRACTS.get(src, {}).get("distributor"))
        else:
            piece_counts[s] = len({str(t.get("token_id")) for t in ts})
    if sandbox3d:
        # Sandbox ASSET has no on-chain totalSupply
        piece_counts["sandbox"] = sum(SANDBOX_ASSET_SUPPLY.get(m["token_id"], 1)
                                      for m in sandbox3d)
    enrich_collections_display(site_collections, volume["by_collection"],
                               authored_content, eth_price_usd, piece_counts)
    write_json(SITE_DATA / "collections.json", site_collections)
    floor_usd_by_slug = {c["collection"]: c.get("floor_usd") for c in site_collections}
    wallet_pnls = load_json(PUBLIC_DATA / "wallet_pnl.json")
    metazoo_addrs = {a.lower() for a in (METAZOO_WALLETS + AOKI_WALLETS)}
    global_offchain_usd = build_global_offchain_usd(per_slug_raw, authored_content, metazoo_addrs)
    write_json(SITE_DATA / "wallet_index.json",
               build_wallet_index(wallet_pnls, global_offchain_usd))

    def _load_media(slug):
        p = MEDIA_INDEX / "tokens" / f"{slug}.json"
        return load_json(p) if p.exists() else None

    def _load_traits(slug):
        p = MEDIA_INDEX / "traits" / f"{slug}.json"
        return load_json(p) if p.exists() else None

    acq_media_path = MEDIA_INDEX / "acquisitions.json"
    acq_media = load_json(acq_media_path) if acq_media_path.exists() else None
    pfp2_offchain_revenue_usd = 0.0

    utility_products, utility_media = load_utility()
    validate_products(utility_products, {c["slug"] for c in SITE_COLLECTIONS})

    for reg in SITE_COLLECTIONS:
        slug, src = reg["slug"], reg["source"]
        holders = {"holders": []}
        tokens = []
        pnls = []
        child_ids = child_subset_ids(slug)
        if src in ("own", "subset"):
            source_slug = slug if src == "own" else reg["parent"]
            pr = per_slug_raw.get(source_slug)
            if pr:
                transfers, sales = pr["transfers"], pr["sales"]
                if src == "subset":
                    transfers, sales = filter_raw_to_tokens(transfers, sales, reg["token_ids"])
                elif child_ids:   # own parent: exclude child-subset IDs -> disjoint drop
                    transfers = [t for t in transfers if str(t.get("token_id")) not in child_ids]
                    sales = [s for s in sales if str(s.get("token_id")) not in child_ids]
                floor_eth = (0.0 if (src == "subset"
                                     and CONTRACTS.get(source_slug, {}).get("third_party"))
                             else pr["floor_eth"])
                if transfers:  # a subset with no matching tokens stays empty
                    pnls = collection_wallet_pnls(transfers, pr["mint_values"], sales, floor_eth,
                                                  collection_key=source_slug,
                                                  prices=prices, now_price=eth_price_usd)
                    tokens = build_tokens(transfers, sales, pr["mint_values"], floor_eth,
                                          block_month, daily_usd, eth_price_usd,
                                          slug=slug, media=_load_media(slug),
                                          traits=_load_traits(slug))

        for src_key in merge_sources_for(slug):
            pr_src = per_slug_raw.get(src_key)
            keep_ids = mzg_token_ids() if src_key == "mintable_early" else None
            if not pr_src or keep_ids == []:
                continue                      # not fetched / nothing classified yet
            m_transfers, m_sales = pr_src["transfers"], pr_src["sales"]
            if keep_ids is not None:
                m_transfers, m_sales = filter_raw_to_tokens(m_transfers, m_sales, keep_ids)
            if not m_transfers:
                continue
            src_contract = CONTRACTS[src_key]["address"]
            m_pnls = collection_wallet_pnls(m_transfers, pr_src["mint_values"], m_sales,
                                            pr_src["floor_eth"], collection_key=src_key,
                                            prices=prices, now_price=eth_price_usd)
            pnls = merge_pnl_lists(pnls, m_pnls) if pnls else m_pnls
            m_tokens = build_tokens(m_transfers, m_sales, pr_src["mint_values"], pr_src["floor_eth"],
                                    block_month, daily_usd, eth_price_usd, slug=src_key,
                                    media=_load_media(src_key))
            for row in m_tokens:
                row["contract"] = src_contract    # OpenSea links point at the real host
            tokens = tokens + m_tokens

        if pnls:
            holders = build_holders(pnls, metazoo_addrs)

        scope = offchain_scope_for(slug)
        unit = ((authored_content.get(slug) or {}).get("off_chain_basis") or {}).get("unit_cost_usd", 0)
        if scope and unit and holders["holders"] and scope[0] in per_slug_raw:
            box_map = offchain_box_counts(per_slug_raw[scope[0]]["transfers"], scope[1])
            enriched = apply_offchain(holders["holders"], unit, mint_count_by_wallet=box_map)
            holders["holders"] = enriched["holders"]
            if slug == "pfp_2":
                pfp2_offchain_revenue_usd = enriched["offchain_revenue_usd"]

        if slug in AIRDROP_DROPS:
            for r in holders["holders"]:
                m = r.get("tokens_minted", 0) or 0
                if m:
                    r["tokens_received"] = (r.get("tokens_received", 0) or 0) + m
                    r["tokens_minted"] = 0

        write_json(SITE_DATA / "collections" / slug / "holders.json", holders)
        write_json(SITE_DATA / "collections" / slug / "tokens.json", tokens)
        write_json(SITE_DATA / "collections" / slug / "content.json",
                   build_content(slug, authored_content, floor_usd=floor_usd_by_slug.get(slug),
                                 products=utility_products, media=utility_media,
                                 daily_usd=daily_usd, eth_price_usd=eth_price_usd))

    audit_path = PUBLIC_DATA / "treasury_usd_audit.json"
    audit = load_json(audit_path) if audit_path.exists() else None

    def _at_event_leg_usd():
        price_usd = royalty_usd = 0.0
        for sales in sales_by_slug.values():
            for s in sales:
                if s.get("is_phantom"):
                    continue
                m = block_month.get(s["block"])
                price_usd += usd_at_month(float(s.get("price_eth") or 0.0), m, daily_usd, eth_price_usd)
                royalty_usd += usd_at_month(float(s.get("royalty_eth") or 0.0), m, daily_usd, eth_price_usd)
        return round(price_usd, 2), round(royalty_usd, 2)

    secondary_volume_usd, royalties_usd = _at_event_leg_usd()
    holdings_path = ROOT / "data" / "evidence" / "aoki_holdings.json"
    holdings = load_json(holdings_path) if holdings_path.exists() else None
    acq_coll_art_path = MEDIA_INDEX / "acquisition_collections.json"
    acq_collection_art = load_json(acq_coll_art_path) if acq_coll_art_path.exists() else None

    flippers_list = load_json(PUBLIC_DATA / "flippers.json")
    identities = load_json(WALLET_IDENTITIES_PATH) if WALLET_IDENTITIES_PATH.exists() else {}
    web3bio = load_json(WEB3BIO_PROFILES_PATH) if WEB3BIO_PROFILES_PATH.exists() else {}
    opensea = load_json(OPENSEA_PROFILES_PATH) if OPENSEA_PROFILES_PATH.exists() else {}
    profiles = merge_profiles(web3bio, opensea)
    count_profitable = sum(1 for w in wallet_pnls if float(w.get("realized_pnl_eth") or 0.0) > 0)
    flippers_block = build_flippers(flippers_list, identities,
                                    summary.get("realized_gains_eth", 0.0),
                                    summary.get("realized_gains_usd", 0.0),
                                    summary.get("realized_losses_eth", 0.0),
                                    count_profitable)

    write_json(SITE_DATA / "findings.json",
               build_findings(load_json(PUBLIC_DATA / "flow_summary.json"), summary,
                              load_json(PUBLIC_DATA / "acquisitions.json"),
                              load_json(PAYOUT_LEDGER_PATH), acq_media=acq_media,
                              eth_price_usd=eth_price_usd, holdings=holdings, audit=audit,
                              secondary_volume_usd=secondary_volume_usd,
                              royalties_usd=royalties_usd, flippers=flippers_block,
                              acq_collection_art=acq_collection_art,
                              pfp2_offchain_revenue_usd=pfp2_offchain_revenue_usd))

    write_json(SITE_DATA / "usd_audit.json", build_usd_audit(audit))

    overrides = load_json(WALLET_OVERRIDES_PATH) if WALLET_OVERRIDES_PATH.exists() else {}
    write_json(SITE_DATA / "wallet_identities.json",
               build_wallet_names(identities, profiles, overrides))
    write_json(SITE_DATA / "wallet_avatars.json", build_wallet_avatars(profiles, overrides))

    sb3d_path = MEDIA_INDEX / "sandbox3d.json"
    write_json(SITE_DATA / "sandbox3d.json",
               build_sandbox3d(load_json(sb3d_path)) if sb3d_path.exists() else [])


if __name__ == "__main__":
    main()
