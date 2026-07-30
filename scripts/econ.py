"""Pure economics math for the MetaZoo pipeline.

Tokens are keyed by (collection, token_id) everywhere so identical token IDs in
different collections never collide. All ETH amounts are floats in ETH.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone

ZERO = "0x0000000000000000000000000000000000000000"


def _key(t: dict) -> tuple:
    return (t["collection"], str(t["token_id"]))


def eth_to_usd(eth: float, timestamp: int, prices: dict) -> float:
    """Convert ETH to USD using the nearest-dated snapshot in `prices`
    ({'YYYY-MM-DD': usd_per_eth}). Returns 0.0 for zero eth or empty table."""
    if eth == 0 or not prices:
        return 0.0
    d = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    if d in prices:  # daily tables almost always hit exactly; skip the O(n) scan
        return round(eth * prices[d], 2)
    target = datetime.strptime(d, "%Y-%m-%d")
    closest = min(prices, key=lambda k: abs(datetime.strptime(k, "%Y-%m-%d") - target))
    return round(eth * prices[closest], 2)


def mint_revenue_usd(transfers: list, mint_values: dict, prices: dict) -> float:
    """USD value of a collection's primary mint revenue, pricing EACH mint tx at its
    own date's ETH/USD (nearest snapshot in `prices`) rather than one blanket rate."""
    hash_ts: dict = {}
    for t in transfers:
        if t.get("from") == ZERO and t.get("hash"):
            hash_ts.setdefault(t["hash"], int(t.get("timestamp", 0)))
    total = 0.0
    for h, eth in mint_values.items():
        if eth and h in hash_ts:
            total += eth_to_usd(eth, hash_ts[h], prices)
    return round(total, 2)


def mint_cost_per_token(transfers: list, mint_values: dict, mint_price_fallback) -> dict:
    """Per-token mint cost, keyed by (collection, token_id).

    For each mint tx, divide the transaction's ETH value across the tokens minted
    in that same tx (batch mints). `mint_values` maps tx hash -> ETH value."""
    per_tx = defaultdict(list)
    for t in transfers:
        if t.get("from") == ZERO:
            per_tx[t["hash"]].append(_key(t))
    costs = {}
    for h, keys in per_tx.items():
        if h in mint_values:
            each = mint_values[h] / len(keys)   # resolved value (0.0 == genuinely free)
        else:
            each = mint_price_fallback or 0.0   # unknown price
        for k in keys:
            costs[k] = each
    return costs


def dedupe_sale_legs(sales: list) -> list:
    """Drop Alchemy's duplicate legs of a single trade"""
    groups = defaultdict(list)
    for s in sales:
        groups[(s["collection"], str(s["token_id"]), int(s.get("block", 0)))].append(s)

    def ident(s):
        return (s.get("hash"), s["collection"], str(s["token_id"]),
                int(s.get("block", 0)), s["from"], s["to"],
                s.get("price_eth"), s.get("proceeds_eth"))

    drop = set()
    for rows in groups.values():
        if len(rows) < 2:
            continue
        usable = [s for s in rows
                  if s["from"] != s["to"] and ZERO not in (s["from"], s["to"])]
        if usable:
            keep = {ident(s) for s in usable}
            drop |= {ident(s) for s in rows if ident(s) not in keep}
    return [s for s in sales if ident(s) not in drop]


def normalize_sale_parties(sales: list, transfers: list) -> list:
    """Repair each sale's counterparties from the transfer chain at its own
    (token, block), leaving every ETH amount untouched."""
    hops = defaultdict(list)
    for t in transfers:
        hops[(_key(t), int(t.get("block", 0)))].append(t)
    per_key = Counter((s["collection"], str(s["token_id"]), int(s.get("block", 0)))
                      for s in sales)

    out = []
    for s in sales:
        coll, tid, blk = s["collection"], str(s["token_id"]), int(s.get("block", 0))
        if per_key[(coll, tid, blk)] > 1:
            out.append(s)
            continue
        chain = hops.get(((coll, tid), blk)) or []
        froms = {t["from"] for t in chain}
        tos = {t["to"] for t in chain}
        starts = froms - tos - {ZERO}
        ends = tos - froms - {ZERO}
        if len(starts) == 1 and len(ends) == 1:
            seller, buyer = starts.pop(), ends.pop()
            if (seller, buyer) != (s["from"], s["to"]):
                s = {**s, "from": seller, "to": buyer}
        out.append(s)
    return out


def gas_by_wallet(transfers: list, sales: list) -> dict:
    """Per-wallet gas charges [(gas_eth, timestamp), ...], attributed by the role
    heuristic: a mint tx's gas -> its minter(s) (the `to` of a from==ZERO transfer),
    a sale tx's gas -> its buyer(s) (`sale.to`). """
    sales = normalize_sale_parties(dedupe_sale_legs(sales), transfers)
    gas_per_hash, hash_ts = {}, {}
    for t in transfers:
        h = t.get("hash")
        gu, gp = int(t.get("gas_used", 0) or 0), int(t.get("gas_price", 0) or 0)
        if h and gu and gp:
            gas_per_hash[h] = gu * gp / 1e18
            hash_ts.setdefault(h, int(t.get("timestamp", 0)))
    sale_buyers = defaultdict(set)
    for s in sales:
        if s.get("hash"):
            sale_buyers[s["hash"]].add(s["to"])
    mint_recipients = defaultdict(set)
    for t in transfers:
        if t["from"] == ZERO and t.get("hash"):
            mint_recipients[t["hash"]].add(t["to"])
    mint_recipients = {h: r for h, r in mint_recipients.items() if len(r) == 1}
    charges = defaultdict(list)
    for h, g in gas_per_hash.items():
        recipients = sale_buyers.get(h) or mint_recipients.get(h)
        if recipients:
            share = g / len(recipients)
            for r in recipients:
                charges[r].append((share, hash_ts[h]))
    return dict(charges)


def wallet_pnl(transfers: list, mint_cost: dict, sales: list,
               floor_by_collection: dict, prices: dict | None = None,
               now_price: float = 0.0, gas: dict | None = None) -> dict:
    """Per-wallet P&L with a dynamic cost basis, driven by authoritative 
    events."""
    sales = normalize_sale_parties(dedupe_sale_legs(sales), transfers)
    spent = defaultdict(float)
    received = defaultdict(float)
    realized = defaultdict(float)          # signed net realized P&L (ETH)
    realized_usd = defaultdict(float)      # signed net realized P&L (USD, at-event)
    bought = defaultdict(int)              # count of tokens acquired via a captured sale (buyer)
    sold = defaultdict(int)                # count of tokens sold (as seller)
    minted = defaultdict(int)              # count of tokens minted (from == ZERO)
    recv = defaultdict(int)                # count of tokens received via a non-sale transfer (airdrop/gift)
    sent = defaultdict(int)                # count of tokens sent via a non-sale transfer (gift/burn)
    basis: dict = {}                       # (wallet, collection, token_id) -> cost basis (ETH)
    basis_ts: dict = {}                    # (wallet, collection, token_id) -> ts basis was set

    block_ts = {int(t["block"]): int(t.get("timestamp", 0))
                for t in transfers if t.get("timestamp") is not None}

    sale_blocks = {((s["collection"], str(s["token_id"])), int(s.get("block", 0))) for s in sales}

    events = []
    for t in transfers:
        q = int(t.get("quantity") or 1)
        if t["from"] == ZERO:
            events.append((int(t.get("block", 0)), 0, "mint", _key(t), t["to"], None,
                           0.0, 0.0, int(t.get("timestamp", 0)), q))
        elif (_key(t), int(t.get("block", 0))) not in sale_blocks:
            events.append((int(t.get("block", 0)), 2, "xfer", _key(t), t["to"], t["from"],
                           0.0, 0.0, int(t.get("timestamp", 0)), q))
    for s in sales:
        k = (s["collection"], str(s["token_id"]))
        blk = int(s.get("block", 0))
        events.append((blk, 1, "sale", k, s["to"], s["from"],
                       s["price_eth"], s["proceeds_eth"], block_ts.get(blk, 0),
                       int(s.get("quantity") or 1)))
    events.sort(key=lambda e: (e[0], e[1]))

    for _block, _pri, kind, k, party, counter, price, proceeds, ts, qty in events:
        if kind == "mint":
            c = mint_cost.get(k, 0.0)
            basis[(party, k)] = c
            basis_ts[(party, k)] = ts
            spent[party] += c                                  # party = minter
            minted[party] += qty                               # a mint is minted, not bought
        elif kind == "xfer":                                   # plain transfer: carry basis
            b = basis.pop((counter, k), mint_cost.get(k, 0.0))  # counter=from (sender)
            bts = basis_ts.pop((counter, k), ts)
            basis[(party, k)] = b                              # party=to (recipient)
            basis_ts[(party, k)] = bts
            recv[party] += qty                                 # recipient got tokens (not minted/bought)
            sent[counter] += qty                               # sender gave them away (not sold)
        else:                                                  # sale: party=buyer, counter=seller
            b = basis.get((counter, k), mint_cost.get(k, 0.0))  # seller's own cost basis
            realized[counter] += proceeds - b
            received[counter] += proceeds
            spent[party] += price
            bought[party] += qty                               # 1155 sales can move several editions
            sold[counter] += qty
            if prices:
                realized_usd[counter] += (eth_to_usd(proceeds, ts, prices)
                                          - eth_to_usd(b, basis_ts.get((counter, k), ts), prices))
            basis[(party, k)] = price                          # buyer's basis = what they paid
            basis_ts[(party, k)] = ts

    balances: dict = defaultdict(int)               # (wallet, key) -> net quantity held
    for t in transfers:
        k = _key(t)
        try:
            q = int(t.get("quantity") or 1)
        except (TypeError, ValueError):
            q = 1
        if t["from"] != ZERO:
            balances[(t["from"], k)] -= q
        balances[(t["to"], k)] += q
    xfer_hops = {(_key(t), int(t.get("block", 0))) for t in transfers}
    for s in sales:
        k = (s["collection"], str(s["token_id"]))
        if (k, int(s.get("block", 0))) in xfer_hops:
            continue
        q = int(s.get("quantity") or 1)
        balances[(s["from"], k)] -= q
        balances[(s["to"], k)] += q

    holdings: dict = defaultdict(dict)              # wallet -> {key: quantity > 0}
    for (w, k), bal in balances.items():
        if w != ZERO and bal > 0:
            holdings[w][k] = bal

    wallets = (set(spent) | set(received) | set(holdings) | set(gas or {})
               | set(recv) | set(sent) | set(minted))
    out = {}
    for w in wallets:
        if w == ZERO:
            continue
        held = holdings.get(w, {})                  # {key: quantity}
        unrealized = 0.0
        unrealized_usd = 0.0
        for kk, qty in held.items():
            floor = floor_by_collection.get(kk[0], 0.0)
            b_eth = basis.get((w, kk), mint_cost.get(kk, 0.0))
            unrealized += qty * max(0.0, b_eth - floor)
            if prices:
                unrealized_usd += qty * max(0.0, eth_to_usd(b_eth, basis_ts.get((w, kk), 0), prices)
                                            - floor * now_price)
        net = realized[w]
        gcharges = (gas or {}).get(w, [])
        gas_eth = sum(g for g, _ in gcharges)
        entry = {
            "wallet": w,
            "eth_spent": round(spent[w], 6),
            "eth_received": round(received[w], 6),
            "realized_pnl_eth": round(net, 6),
            "realized_loss": round(max(0.0, -net), 6),
            "unrealized_loss": round(unrealized, 6),
            "tokens_held": sum(held.values()),      # editions held (ERC-1155 aware)
            "tokens_bought": bought[w],
            "tokens_sold": sold[w],
            "tokens_minted": minted[w],
            "tokens_received": recv[w],      # non-sale transfers in (airdrop/gift)
            "tokens_sent": sent[w],          # non-sale transfers out (gift/burn)
        }
        if prices:
            entry["realized_pnl_usd"] = round(realized_usd[w], 2)   # signed, at-event
            entry["realized_loss_usd"] = round(max(0.0, -realized_usd[w]), 2)
            entry["unrealized_loss_usd"] = round(unrealized_usd, 2)
        if gas is not None:
            entry["gas_spent_eth"] = round(gas_eth, 6)
            if prices:
                entry["gas_spent_usd"] = round(
                    sum(eth_to_usd(g, ts, prices) for g, ts in gcharges), 2)
        out[w] = entry
    return out
