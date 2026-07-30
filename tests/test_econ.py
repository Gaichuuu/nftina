from scripts.econ import (eth_to_usd, mint_revenue_usd, mint_cost_per_token, wallet_pnl,
                          gas_by_wallet, normalize_sale_parties, ZERO)
from scripts.econ import dedupe_sale_legs as econ_dedupe

PRICES = {"2021-11-29": 4200, "2021-12-01": 4500}


# --- mint_revenue_usd (prices each mint at its own date) ---

def test_mint_revenue_usd_prices_each_mint_at_its_date():
    transfers = [{"from": ZERO, "hash": "0xa", "timestamp": 1638144000},
                 {"from": ZERO, "hash": "0xb", "timestamp": 1638316800}]
    mint_values = {"0xa": 1.0, "0xb": 2.0}
    assert mint_revenue_usd(transfers, mint_values, PRICES) == 13200.0


def test_mint_revenue_usd_ignores_free_mints_and_unknown_hashes():
    transfers = [{"from": ZERO, "hash": "0xfree", "timestamp": 1638144000}]
    assert mint_revenue_usd(transfers, {"0xfree": 0.0, "0xghost": 5.0}, PRICES) == 0.0


def _t(collection, token_id, frm, to, hash_, block=1, ts=1):
    return {"collection": collection, "token_id": token_id, "from": frm, "to": to,
            "hash": hash_, "block": block, "timestamp": ts}


# --- eth_to_usd ---

def test_eth_to_usd_nearest_date():
    ts = 1638230400  # 2021-11-30, between the two price points
    assert eth_to_usd(1.0, ts, PRICES) in (4200, 4500)


def test_eth_to_usd_zero_and_empty():
    assert eth_to_usd(0, 1638230400, PRICES) == 0.0
    assert eth_to_usd(1.0, 1638230400, {}) == 0.0


# --- mint_cost_per_token ---

def test_mint_cost_divides_batch_value_across_tokens_in_tx():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa"),
                 _t("coin_tokens", "2", ZERO, "0xb", "0xaa")]
    costs = mint_cost_per_token(transfers, {"0xaa": 0.2}, None)
    assert costs[("coin_tokens", "1")] == 0.1
    assert costs[("coin_tokens", "2")] == 0.1


def test_mint_cost_resolved_zero_is_free_not_fallback():
    transfers = [_t("coin_tokens", "9", ZERO, "0xb", "0xbb")]
    costs = mint_cost_per_token(transfers, {"0xbb": 0.0}, 0.1)
    assert costs[("coin_tokens", "9")] == 0.0


def test_mint_cost_fallback_only_when_hash_unresolved():
    transfers = [_t("coin_tokens", "9", ZERO, "0xb", "0xbb")]
    costs = mint_cost_per_token(transfers, {}, 0.1)
    assert costs[("coin_tokens", "9")] == 0.1


def test_mint_cost_keys_are_collection_scoped_no_collision():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa"),
                 _t("beasties_s1", "1", ZERO, "0xc", "0xdd")]
    costs = mint_cost_per_token(transfers, {"0xaa": 0.1, "0xdd": 0.5}, None)
    assert costs[("coin_tokens", "1")] == 0.1
    assert costs[("beasties_s1", "1")] == 0.5


# --- wallet_pnl ---

def test_wallet_pnl_unrealized_loss_uses_per_collection_floor():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa")]
    pnl = wallet_pnl(transfers, {("coin_tokens", "1"): 0.1}, {}, {"coin_tokens": 0.02})
    assert round(pnl["0xb"]["unrealized_loss"], 6) == 0.08
    assert pnl["0xb"]["tokens_held"] == 1
    assert pnl["0xb"]["eth_spent"] == 0.1


def _sale(collection, token_id, seller, buyer, price, proceeds, block):
    return {"collection": collection, "token_id": token_id, "from": seller,
            "to": buyer, "price_eth": price, "proceeds_eth": proceeds, "block": block}


def test_wallet_pnl_realized_loss_on_sale_below_cost():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa", block=1),
                 _t("coin_tokens", "1", "0xb", "0xc", "0xsale", block=2)]
    mint_cost = {("coin_tokens", "1"): 0.1}
    sales = [_sale("coin_tokens", "1", "0xb", "0xc", 0.03, 0.027, block=2)]
    pnl = wallet_pnl(transfers, mint_cost, sales, {"coin_tokens": 0.0})
    assert round(pnl["0xb"]["realized_loss"], 6) == 0.073      # 0.1 - 0.027
    assert round(pnl["0xb"]["realized_pnl_eth"], 6) == -0.073
    assert pnl["0xb"]["tokens_held"] == 0
    assert round(pnl["0xb"]["eth_received"], 6) == 0.027       # proceeds, not full price
    assert pnl["0xc"]["tokens_held"] == 1
    assert round(pnl["0xc"]["eth_spent"], 6) == 0.03           # buyer paid full price


def test_wallet_pnl_usd_losses_valued_at_event():
    prices = {"2021-11-29": 4200, "2021-12-01": 4500}
    ts1, ts2 = 1638144000, 1638316800   # 2021-11-29 / 2021-12-01 (UTC)
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa", block=1, ts=ts1),
                 _t("coin_tokens", "1", "0xb", "0xc", "0xsale", block=2, ts=ts2)]
    mint_cost = {("coin_tokens", "1"): 0.1}
    sales = [_sale("coin_tokens", "1", "0xb", "0xc", 0.03, 0.027, block=2)]
    pnl = wallet_pnl(transfers, mint_cost, sales, {"coin_tokens": 0.0},
                     prices=prices, now_price=1885)
    assert pnl["0xb"]["realized_loss_usd"] == 298.5
    assert pnl["0xc"]["unrealized_loss_usd"] == 135.0


def test_wallet_pnl_realized_pnl_usd_signed_gain_at_event():
    prices = {"2021-11-29": 4200, "2021-12-01": 4500}
    ts1, ts2 = 1638144000, 1638316800
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa", block=1, ts=ts1),
                 _t("coin_tokens", "1", "0xb", "0xc", "0xsale", block=2, ts=ts2)]
    mint_cost = {("coin_tokens", "1"): 0.1}
    sales = [_sale("coin_tokens", "1", "0xb", "0xc", 0.5, 0.45, block=2)]
    pnl = wallet_pnl(transfers, mint_cost, sales, {"coin_tokens": 0.0},
                     prices=prices, now_price=1885)
    assert pnl["0xb"]["realized_pnl_usd"] == 1605.0     # signed, positive
    assert pnl["0xb"]["realized_loss_usd"] == 0.0       # no loss on a gain


def test_wallet_pnl_no_usd_fields_without_prices():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa")]
    pnl = wallet_pnl(transfers, {("coin_tokens", "1"): 0.1}, {}, {"coin_tokens": 0.02})
    assert "realized_loss_usd" not in pnl["0xb"]   # ETH-only when no price table given


def test_wallet_pnl_realized_gain_on_profitable_flip():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa", block=1),
                 _t("coin_tokens", "1", "0xb", "0xc", "0xsale", block=2)]
    mint_cost = {("coin_tokens", "1"): 0.1}
    sales = [_sale("coin_tokens", "1", "0xb", "0xc", 0.5, 0.45, block=2)]
    pnl = wallet_pnl(transfers, mint_cost, sales, {"coin_tokens": 0.0})
    assert round(pnl["0xb"]["realized_pnl_eth"], 6) == 0.35    # 0.45 - 0.1
    assert pnl["0xb"]["realized_loss"] == 0.0
    assert round(pnl["0xc"]["unrealized_loss"], 6) == 0.5


def test_wallet_pnl_sale_counted_once_despite_multihop_transfers():
    transfers = [_t("coin_tokens", "1", ZERO, "0xseller", "0xaa", block=1),
                 _t("coin_tokens", "1", "0xseller", "0xexchange", "0xsale", block=2),
                 _t("coin_tokens", "1", "0xexchange", "0xbuyer", "0xsale", block=2)]
    mint_cost = {("coin_tokens", "1"): 0.1}
    sales = [_sale("coin_tokens", "1", "0xseller", "0xbuyer", 0.4, 0.36, block=2)]
    pnl = wallet_pnl(transfers, mint_cost, sales, {"coin_tokens": 0.0})
    assert round(pnl["0xbuyer"]["eth_spent"], 6) == 0.4        # once, not 0.8
    assert pnl["0xbuyer"]["tokens_held"] == 1                  # final owner
    assert "0xexchange" not in pnl                             # intermediate isn't a holder/spender
    assert round(pnl["0xseller"]["eth_received"], 6) == 0.36


def test_wallet_pnl_excludes_zero_address():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa")]
    pnl = wallet_pnl(transfers, {("coin_tokens", "1"): 0.1}, {}, {})
    assert ZERO not in pnl


# --- ERC-1155: quantity-aware holdings (a token_id has many edition-holders) ---

def _t1155(collection, token_id, frm, to, hash_, qty, block=1, ts=1):
    d = _t(collection, token_id, frm, to, hash_, block=block, ts=ts)
    d["quantity"] = qty
    return d


def test_wallet_pnl_erc1155_each_edition_holder_counted():
    D = "0xd15719"  # distributor
    transfers = [
        _t1155("reissue", "9", D, "0xaa", "0x1", 1, block=1),
        _t1155("reissue", "9", D, "0xbb", "0x2", 1, block=2),
    ]
    pnl = wallet_pnl(transfers, {}, [], {"reissue": 0.0})
    assert pnl["0xaa"]["tokens_held"] == 1
    assert pnl["0xbb"]["tokens_held"] == 1


def test_wallet_pnl_erc1155_quantity_counts_editions_and_scales_loss():
    transfers = [_t1155("c", "1", ZERO, "0xb", "0x1", 3, block=1)]
    pnl = wallet_pnl(transfers, {("c", "1"): 0.1}, {}, {"c": 0.02})
    assert pnl["0xb"]["tokens_held"] == 3
    assert round(pnl["0xb"]["unrealized_loss"], 6) == 0.24


def test_wallet_pnl_carry_forward_basis_on_non_sale_transfer():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xmint", block=1),
                 _t("coin_tokens", "1", "0xb", "0xc", "0xsalehop", block=2),  # sale hop (block 2)
                 _t("coin_tokens", "1", "0xc", "0xd", "0xmove", block=5)]      # plain transfer
    mint_cost = {("coin_tokens", "1"): 0.1}
    sales = [_sale("coin_tokens", "1", "0xb", "0xc", 0.5, 0.45, block=2)]
    pnl = wallet_pnl(transfers, mint_cost, sales, {"coin_tokens": 0.0})
    assert pnl["0xd"]["tokens_held"] == 1
    assert round(pnl["0xd"]["unrealized_loss"], 6) == 0.5   # carried B->C->D, not reset to 0.1


def test_wallet_pnl_airdrop_holder_has_zero_basis_not_shared_token_price():
    D = "0xd15719"
    transfers = [_t1155("reissue", "9", D, "0xaa", "0x1", 1, block=1),
                 _t1155("reissue", "9", "0xzz", "0xyy", "0xsalehop", 1, block=3)]
    sales = [_sale("reissue", "9", "0xzz", "0xyy", 0.3, 0.28, block=3)]
    pnl = wallet_pnl(transfers, {}, sales, {"reissue": 0.0})
    assert pnl["0xaa"]["tokens_held"] == 1
    assert pnl["0xaa"]["unrealized_loss"] == 0.0           # free airdrop, not 0.3


def test_wallet_pnl_erc1155_partial_sale_leaves_remaining_editions_held():
    D = "0xd15719"
    transfers = [
        _t1155("c", "1", D, "0xb", "0x1", 2, block=1),
        _t1155("c", "1", "0xb", "0xc", "0xsale", 1, block=2),
    ]
    sales = [_sale("c", "1", "0xb", "0xc", 0.05, 0.045, block=2)]
    pnl = wallet_pnl(transfers, {}, sales, {"c": 0.0})
    assert pnl["0xb"]["tokens_held"] == 1
    assert pnl["0xc"]["tokens_held"] == 1


# --- gas_by_wallet ---

def _tg(coll, tid, frm, to, h, gu, gp, block=1, ts=1):
    return {"collection": coll, "token_id": tid, "from": frm, "to": to, "hash": h,
            "block": block, "timestamp": ts, "quantity": 1, "gas_used": gu, "gas_price": gp}

def test_gas_by_wallet_mint_charged_to_minter():
    tr = [_tg("c", "1", ZERO, "0xb", "0xh1", 100000, 10**9)]
    g = gas_by_wallet(tr, [])
    assert round(sum(e for e, _ in g["0xb"]), 8) == 0.0001

def test_gas_by_wallet_sale_charged_to_buyer_deduped_per_hash():
    tr = [_tg("c", "1", "0xs", "0xex", "0xh2", 200000, 10**9),
          _tg("c", "1", "0xex", "0xbuyer", "0xh2", 200000, 10**9)]
    sales = [{"collection": "c", "token_id": "1", "from": "0xs", "to": "0xbuyer",
              "hash": "0xh2", "block": 2, "price_eth": 0.3, "proceeds_eth": 0.28}]
    g = gas_by_wallet(tr, sales)
    assert round(sum(e for e, _ in g["0xbuyer"]), 8) == 0.0002
    assert "0xs" not in g and "0xex" not in g

def test_gas_by_wallet_airdrop_recipient_pays_no_mint_gas():
    tr = [_tg("c", "1", "0xdistrib", "0xuser", "0xh3", 90000, 10**9)]
    g = gas_by_wallet(tr, [])
    assert "0xuser" not in g

def test_gas_by_wallet_bulk_airdrop_charges_none_of_its_recipients():
    tr = [_tg("c", "1", ZERO, "0xa", "0xh4", 200000, 10**9),
          _tg("c", "2", ZERO, "0xb", "0xh4", 200000, 10**9)]
    g = gas_by_wallet(tr, [])
    assert "0xa" not in g and "0xb" not in g

def test_gas_by_wallet_batch_self_mint_still_pays_its_full_gas():
    tr = [_tg("c", "1", ZERO, "0xa", "0xh5", 200000, 10**9),
          _tg("c", "2", ZERO, "0xa", "0xh5", 200000, 10**9)]
    g = gas_by_wallet(tr, [])
    assert round(sum(e for e, _ in g["0xa"]), 8) == 0.0002


def test_wallet_pnl_mint_not_counted_as_bought():
    transfers = [_t("c", "1", ZERO, "0xb", "0xmint", block=1),
                 _t("c", "1", "0xb", "0xc", "0xsale", block=2)]
    sales = [_sale("c", "1", "0xb", "0xc", 0.3, 0.28, block=2)]
    pnl = wallet_pnl(transfers, {("c", "1"): 0.1}, sales, {"c": 0.0})
    assert pnl["0xb"]["tokens_minted"] == 1
    assert pnl["0xb"]["tokens_bought"] == 0      # minted, NOT bought
    assert pnl["0xc"]["tokens_bought"] == 1      # a real purchase
    assert pnl["0xc"]["tokens_minted"] == 0


def test_wallet_pnl_received_and_sent_non_sale_transfers():
    transfers = [
        _t("c", "1", ZERO, "0xb", "0xm1", block=1),      # mint
        _t("c", "2", ZERO, "0xb", "0xm1", block=1),      # mint (same tx)
        _t("c", "9", "0xdonor", "0xb", "0xair", block=2),  # airdrop IN (non-sale)
        _t("c", "1", "0xb", "0xfriend", "0xgift", block=3),  # gift OUT (non-sale)
    ]
    pnl = wallet_pnl(transfers, {("c", "1"): 0.1, ("c", "2"): 0.1}, [], {"c": 0.0})
    b = pnl["0xb"]
    assert b["tokens_minted"] == 2
    assert b["tokens_bought"] == 0
    assert b["tokens_received"] == 1     # the airdrop
    assert b["tokens_sent"] == 1         # the gift
    assert b["tokens_sold"] == 0
    assert (b["tokens_held"]
            == b["tokens_minted"] + b["tokens_bought"] + b["tokens_received"]
            - b["tokens_sold"] - b["tokens_sent"] == 2)


def test_wallet_pnl_tokens_minted_counts_zero_address_mints():
    transfers = [_t("c", "1", ZERO, "0xb", "0xh1", block=1),
                 _t("c", "2", ZERO, "0xb", "0xh1", block=1)]
    pnl = wallet_pnl(transfers, {("c", "1"): 0.1, ("c", "2"): 0.1}, [], {"c": 0.0})
    assert pnl["0xb"]["tokens_minted"] == 2


def test_wallet_pnl_folds_gas_into_spend_and_usd_at_event():
    prices = {"2021-11-29": 4200}
    ts = 1638144000
    transfers = [_t("c", "1", ZERO, "0xb", "0xh1", block=1, ts=ts)]
    gas = {"0xb": [(0.05, ts)]}
    pnl = wallet_pnl(transfers, {("c", "1"): 0.1}, [], {"c": 0.0},
                     prices=prices, now_price=1885, gas=gas)
    assert pnl["0xb"]["gas_spent_eth"] == 0.05
    assert pnl["0xb"]["gas_spent_usd"] == 210.0


def test_wallet_pnl_no_gas_arg_leaves_output_unchanged():
    transfers = [_t("c", "1", ZERO, "0xb", "0xh1")]
    pnl = wallet_pnl(transfers, {("c", "1"): 0.1}, [], {"c": 0.02})
    assert "gas_spent_eth" not in pnl["0xb"]
    assert pnl["0xb"]["tokens_minted"] == 1


def test_wallet_pnl_counts_erc1155_editions_not_transfer_rows():
    transfers = [
        {"collection": "w", "token_id": "7", "from": ZERO, "to": "0xb", "hash": "0xm",
         "block": 1, "timestamp": 1, "quantity": 3},
        {"collection": "w", "token_id": "7", "from": "0xb", "to": "0xc", "hash": "0xs1",
         "block": 2, "timestamp": 2, "quantity": 1},
        {"collection": "w", "token_id": "7", "from": "0xb", "to": "0xc", "hash": "0xs2",
         "block": 3, "timestamp": 3, "quantity": 1},
        {"collection": "w", "token_id": "7", "from": "0xb", "to": "0xd", "hash": "0xs3",
         "block": 4, "timestamp": 4, "quantity": 1},
    ]
    sales = [_sale("w", "7", "0xb", "0xc", 0.01, 0.0097, 2),
             _sale("w", "7", "0xb", "0xc", 0.01, 0.0097, 3),
             _sale("w", "7", "0xb", "0xd", 0.01, 0.0097, 4)]
    b = wallet_pnl(transfers, {("w", "7"): 0.0}, sales, {"w": 0.0})["0xb"]
    assert b["tokens_minted"] == 3          # editions, not the single transfer row
    assert b["tokens_sold"] == 3
    assert b["tokens_received"] == 0
    assert b["tokens_held"] == 0
    assert (b["tokens_minted"] + b["tokens_bought"] + b["tokens_received"]
            - b["tokens_sent"] - b["tokens_sold"] == b["tokens_held"] == 0)


def test_wallet_pnl_counts_editions_on_a_plain_1155_transfer():
    transfers = [
        {"collection": "w", "token_id": "7", "from": ZERO, "to": "0xdist", "hash": "0xm",
         "block": 1, "timestamp": 1, "quantity": 5},
        {"collection": "w", "token_id": "7", "from": "0xdist", "to": "0xb", "hash": "0xx",
         "block": 2, "timestamp": 2, "quantity": 5},
    ]
    b = wallet_pnl(transfers, {("w", "7"): 0.0}, [], {"w": 0.0})["0xb"]
    assert b["tokens_received"] == 5 and b["tokens_held"] == 5
    assert wallet_pnl(transfers, {("w", "7"): 0.0}, [], {"w": 0.0})["0xdist"]["tokens_sent"] == 5


def test_wallet_pnl_sale_with_no_transfer_hop_still_moves_the_token():
    transfers = [
        {"collection": "g", "token_id": "9", "from": "0xdist", "to": "0xclaim",
         "hash": "0xc", "block": 1, "timestamp": 1, "quantity": 1},
    ]
    sales = [_sale("g", "9", "0xclaim", "0xbuyer", 0.09, 0.087, 5)]
    out = wallet_pnl(transfers, {}, sales, {"g": 0.0})
    buyer = out["0xbuyer"]
    assert buyer["tokens_bought"] == 1
    assert buyer["tokens_held"] == 1                  # was 0
    assert abs(buyer["unrealized_loss"] - 0.09) < 1e-9
    assert out["0xclaim"]["tokens_held"] == 0         # the seller no longer holds it
    for r in (buyer, out["0xclaim"]):
        assert (r["tokens_minted"] + r["tokens_bought"] + r["tokens_received"]
                - r["tokens_sent"] - r["tokens_sold"]) == r["tokens_held"]


def test_wallet_pnl_does_not_re_move_a_sale_the_transfers_already_record():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xaa", block=1),
                 _t("coin_tokens", "1", "0xb", "0xc", "0xsale", block=2)]
    sales = [_sale("coin_tokens", "1", "0xb", "0xc", 0.3, 0.27, 2)]
    out = wallet_pnl(transfers, {("coin_tokens", "1"): 0.1}, sales, {"coin_tokens": 0.0})
    assert out["0xc"]["tokens_held"] == 1             # exactly one, not two
    assert out["0xb"]["tokens_held"] == 0
    assert sum(v["tokens_held"] for v in out.values()) == 1     # never exceeds supply


def test_normalize_sale_parties_repairs_a_zero_address_counterparty():
    transfers = [_t("coin_tokens", "1", "0xseller", "0xbuyer", "0xh", block=5)]
    sales = [_sale("coin_tokens", "1", "0xseller", ZERO, 0.14, 0.13, 5)]
    fixed = normalize_sale_parties(sales, transfers)
    assert (fixed[0]["from"], fixed[0]["to"]) == ("0xseller", "0xbuyer")
    assert sales[0]["to"] == ZERO                     # input never mutated
    assert fixed[0]["price_eth"] == 0.14              # economics untouched


def test_normalize_sale_parties_takes_the_chain_ends_through_an_aggregator():
    transfers = [_t("coin_tokens", "1", "0xseller", "0xrouter", "0xh", block=5),
                 _t("coin_tokens", "1", "0xrouter", "0xfinal", "0xh", block=5)]
    sales = [_sale("coin_tokens", "1", "0xseller", "0xrouter", 0.19, 0.17, 5)]
    fixed = normalize_sale_parties(sales, transfers)
    assert (fixed[0]["from"], fixed[0]["to"]) == ("0xseller", "0xfinal")


def test_normalize_sale_parties_leaves_ambiguous_or_unfetched_sales_alone():
    sales = [_sale("g", "9", "0xa", "0xb", 0.09, 0.087, 5)]
    assert normalize_sale_parties(sales, [])[0]["to"] == "0xb"
    cyc = [_t("g", "9", "0xa", "0xb", "0xh", block=5),
           _t("g", "9", "0xb", "0xa", "0xh", block=5)]
    assert normalize_sale_parties(sales, cyc)[0]["to"] == "0xb"


def test_wallet_pnl_credits_the_real_seller_when_the_sale_names_zero():
    transfers = [_t("coin_tokens", "1", ZERO, "0xb", "0xm", block=1),
                 _t("coin_tokens", "1", "0xb", "0xc", "0xs", block=2)]
    sales = [_sale("coin_tokens", "1", "0xb", ZERO, 0.3, 0.27, 2)]
    out = wallet_pnl(transfers, {("coin_tokens", "1"): 0.1}, sales, {"coin_tokens": 0.0})
    assert out["0xb"]["tokens_sold"] == 1
    assert abs(out["0xb"]["eth_received"] - 0.27) < 1e-9
    assert out["0xc"]["tokens_bought"] == 1 and out["0xc"]["tokens_held"] == 1
    assert ZERO not in out


def _leg(collection, token_id, seller, buyer, price, proceeds, block, protocol=0.0):
    s = _sale(collection, token_id, seller, buyer, price, proceeds, block)
    s["protocol_eth"] = protocol
    return s


def test_dedupe_sale_legs_drops_the_mis_split_twin_of_one_trade():
    clean = _leg("coin_tokens", "677", "0x7d99", "0xc32b", 0.16081, 0.16001, 9, 0.0008)
    twin = _leg("coin_tokens", "677", "0x7d99", "0x7d99", 0.15921, 0.01520, 9, 0.14401)
    assert econ_dedupe([clean, twin]) == [clean]
    twin_zero = _leg("coin_tokens", "1795", "0x9561", ZERO, 0.14200, 0.01356, 9, 0.12844)
    clean2 = _leg("coin_tokens", "1795", "0x668a", "0xc32b", 0.14639, 0.14566, 9, 0.00073)
    assert econ_dedupe([twin_zero, clean2]) == [clean2]


def test_dedupe_sale_legs_keeps_a_lone_unresolved_sale():
    lone = _leg("coin_tokens", "1", "0x9561", ZERO, 0.14, 0.13, 9)
    assert econ_dedupe([lone]) == [lone]
    lone_self = _leg("coin_tokens", "2", "0xa", "0xa", 0.14, 0.13, 9)
    assert econ_dedupe([lone_self]) == [lone_self]


def test_dedupe_sale_legs_keeps_both_halves_of_a_genuine_flip():
    a = _leg("genesis_2021", "59", "0x311e", "0x9e93", 0.4, 0.39, 7)
    b = _leg("genesis_2021", "59", "0x9e93", "0x457d", 0.48, 0.47, 7)
    assert econ_dedupe([a, b]) == [a, b]


def test_normalize_leaves_a_genuine_flip_pair_uncollapsed():
    transfers = [_t("genesis_2021", "59", "0x311e", "0x9e93", "0xh", block=7),
                 _t("genesis_2021", "59", "0x9e93", "0x457d", "0xh", block=7)]
    sales = [_leg("genesis_2021", "59", "0x311e", "0x9e93", 0.4, 0.39, 7),
             _leg("genesis_2021", "59", "0x9e93", "0x457d", 0.48, 0.47, 7)]
    fixed = normalize_sale_parties(sales, transfers)
    assert [(s["from"], s["to"]) for s in fixed] == [("0x311e", "0x9e93"),
                                                     ("0x9e93", "0x457d")]
