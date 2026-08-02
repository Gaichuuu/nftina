from datetime import datetime, timezone

from scripts import build_site_data as b

def test_erc1155_edition_count_sums_distributor_quantity():
    dist = "0xDIST"
    transfers = [
        {"token_id": "1", "from": dist, "quantity": 6},        # counted
        {"token_id": "1", "from": dist, "quantity": 4},        # counted (same token, more editions)
        {"token_id": "2", "from": dist, "quantity": 3},        # counted (different token)
        {"token_id": "1", "from": "0xBUYER", "quantity": 5},   # secondary, not from distributor
        {"token_id": "2", "from": dist.lower(), "quantity": 2},  # case-insensitive match
    ]
    assert b.erc1155_edition_count(transfers, dist) == 15
    assert b.erc1155_edition_count([{"from": dist}], dist) == 1
    assert b.erc1155_edition_count(transfers, None) == 0


def test_erc1155_edition_count_sums_0x0_mints_without_distributor():
    transfers = [
        {"token_id": "1", "is_mint": True, "quantity": 150},   # counted
        {"token_id": "2", "is_mint": True, "quantity": 200},   # counted
        {"token_id": "1", "from": "0xBUYER", "quantity": 5},   # secondary, not a mint
    ]
    assert b.erc1155_edition_count(transfers, None) == 350
    mixed = transfers + [{"token_id": "3", "from": "0xdist", "quantity": 4}]
    assert b.erc1155_edition_count(mixed, "0xDIST") == 354


def test_sanitize_summary_drops_bankruptcy_and_disclaimer():
    s = {"total_loss_eth": 1.0, "bankruptcy": {"case_number": "x"}, "disclaimer": "alleged"}
    out = b.sanitize_summary(s, eth_price_usd=2000.0)
    assert "bankruptcy" not in out
    assert "disclaimer" not in out
    assert out["total_loss_eth"] == 1.0


def test_sanitize_summary_passes_through_at_event_loss_usd():
    s = {"total_loss_eth": 100.0, "unrealized_loss_eth": 80.0,
         "total_loss_usd": 500000.0, "unrealized_loss_usd": 420000.0}
    out = b.sanitize_summary(s, eth_price_usd=1500.0)
    assert out["total_loss_usd"] == 500000.0          # from analyze, not 100*1500
    assert out["unrealized_loss_usd"] == 420000.0     # from analyze, not 80*1500
    assert out["eth_price_usd"] == 1500.0

def test_build_flippers_joins_identities_and_totals():
    flippers = [
        {"wallet": "0xAAA", "eth_spent": 0.2, "eth_received": 27.16,
         "realized_pnl_eth": 26.96, "realized_pnl_usd": 62000.0, "tokens_held": 3},
        {"wallet": "0xBBB", "eth_spent": 13.0, "eth_received": 33.8,
         "realized_pnl_eth": 20.8, "realized_pnl_usd": 55000.0, "tokens_held": 1},
        {"wallet": "0xCCC", "eth_spent": 1.0, "eth_received": 0.5,   # a LOSER, must be dropped
         "realized_pnl_eth": -0.5, "realized_pnl_usd": -1000.0, "tokens_held": 0},
    ]
    identities = {"0xbbb": {"ens": "neo808.eth", "ens_verified": True,
                            "label": "neo808.eth", "source": "ENS primary (verified)"}}
    out = b.build_flippers(flippers, identities, total_gains_eth=1084.29,
                           total_gains_usd=2609301.04, realized_losses_eth=145.86,
                           count_profitable=1819, top=12)
    assert out["total_gains_eth"] == 1084.29
    assert out["total_gains_usd"] == 2609301.04
    assert out["count_profitable"] == 1819
    assert [r["wallet"] for r in out["top"]] == ["0xAAA", "0xBBB"]   # loser excluded
    assert out["top"][0]["label"] is None                            # anon
    assert out["top"][1]["label"] == "neo808.eth"                    # ENS joined
    assert out["top"][1]["ens_verified"] is True
    assert out["identified_in_top"] == 1


def test_build_flippers_empty_identities():
    flippers = [{"wallet": "0xAAA", "eth_spent": 0.2, "eth_received": 1.0,
                 "realized_pnl_eth": 0.8, "realized_pnl_usd": 100.0, "tokens_held": 0}]
    out = b.build_flippers(flippers, {}, 1.0, 100.0, 0.0, 1)
    assert out["top"][0]["label"] is None
    assert out["identified_in_top"] == 0


def test_build_collections_adds_floor_usd():
    cols = [{"collection": "coin_tokens", "floor_eth": 0.005, "name": "Coin",
             "contract": "0x2d36", "standard": "erc721", "total_transfers": 1,
             "total_mints": 1, "unique_minters": 1, "mint_revenue_eth": 0.1,
             "mint_revenue_usd": 240.0, "secondary_sales": 0,
             "secondary_volume_eth": 0.0, "royalty_eth": 0.0,
             "include_in_loss_calc": True}]
    out = b.build_collections(cols, eth_price_usd=2400.0, per_slug_raw={})
    ct = next(c for c in out if c["collection"] == "coin_tokens")
    assert ct["floor_usd"] == 12.0
    assert ct["floor_eth"] == 0.005
    assert ct["name"] == "MetaZoo Coin Tokens"   # registry display name, not analyze's "Coin"
    assert ct["image"] is None                   # no art passed

def test_build_collections_handles_zero_floor():
    out = b.build_collections([], eth_price_usd=2400.0, per_slug_raw={})
    ct = next(c for c in out if c["collection"] == "coin_tokens")
    assert ct["floor_usd"] == 0.0
    assert ct["floor_eth"] == 0.0

def test_build_volume_series_groups_by_month_and_skips_phantom():
    sales_by_slug = {
        "coin_tokens": [
            {"block": 100, "price_eth": 1.0, "settled_eth": 0.9, "is_phantom": False},
            {"block": 101, "price_eth": 2.0, "settled_eth": 1.9, "is_phantom": False},
            {"block": 200, "price_eth": 5.0, "settled_eth": 4.9, "is_phantom": False},
            {"block": 201, "price_eth": 9.9, "settled_eth": 9.8, "is_phantom": True},   # dropped
        ],
        "aoki": [{"block": 100, "price_eth": 0.5, "settled_eth": 0.4, "is_phantom": False}],
    }
    block_month = {100: "2021-11", 101: "2021-11", 200: "2021-12", 201: "2021-12"}
    daily_usd = {"2021-11-01": 4000.0, "2021-12-01": 3000.0}
    out = b.build_volume_series(sales_by_slug, block_month, daily_usd, eth_price_usd=2400.0)
    assert out["by_collection"]["coin_tokens"] == [
        {"month": "2021-11", "eth": 3.0, "usd": 12000.0},   # 3.0 * 4000
        {"month": "2021-12", "eth": 5.0, "usd": 15000.0},   # 5.0 * 3000
    ]
    assert out["ecosystem"] == [
        {"month": "2021-11", "eth": 3.5, "usd": 14000.0},   # 3.5 * 4000
        {"month": "2021-12", "eth": 5.0, "usd": 15000.0},
    ]

def test_raw_slugs_for_includes_parent_only_slugs():
    site_collections = [
        {"slug": "coin_tokens", "source": "own", "parent": None},
        {"slug": "mothman_1of1", "source": "subset", "parent": "aoki"},
    ]
    out = b.raw_slugs_for(site_collections)
    assert out == ["coin_tokens", "aoki"]


def test_main_sales_by_slug_reaches_parent_only_slug(monkeypatch):
    site_collections = [
        {"slug": "coin_tokens", "name": "Coin", "source": "own", "parent": None, "token_ids": None, "note": None},
        {"slug": "mothman_1of1", "name": "Mothman", "source": "subset", "parent": "aoki",
         "token_ids": ["1"], "note": None},
    ]
    monkeypatch.setattr(b, "SITE_COLLECTIONS", site_collections)
    raw_slugs = b.raw_slugs_for(site_collections)
    per_slug_raw = {
        "coin_tokens": {"sales": [{"block": 1, "price_eth": 1.0, "is_phantom": False}]},
        "aoki": {"sales": [{"block": 1, "price_eth": 271.0, "is_phantom": False}]},
    }
    sales_by_slug = {s: per_slug_raw[s]["sales"] for s in raw_slugs if s in per_slug_raw}
    assert set(sales_by_slug) == {"coin_tokens", "aoki"}
    out = b.build_volume_series(sales_by_slug, {1: "2022-01"}, {}, eth_price_usd=2400.0)
    total = sum(m["eth"] for m in out["ecosystem"])
    assert total == 272.0   # 1.0 (coin_tokens) + 271.0 (aoki, the parent-only slug)


def test_build_volume_series_skips_undated_blocks():
    out = b.build_volume_series(
        {"x": [{"block": 999, "price_eth": 1.0, "settled_eth": 0.9, "is_phantom": False}]},
        {}, daily_usd={}, eth_price_usd=2400.0,
    )
    assert out["by_collection"]["x"] == []
    assert out["ecosystem"] == []

def test_build_wallet_index_ranks_net_losers():
    wallets = [
        {"wallet": "0xa", "eth_spent": 5, "eth_received": 0, "realized_pnl_eth": 0.0,
         "realized_loss": 0.0, "unrealized_loss": 5.0, "tokens_held": 1},   # net -5 -> rank 1
        {"wallet": "0xb", "eth_spent": 2, "eth_received": 1, "realized_pnl_eth": 0.0,
         "realized_loss": 0.0, "unrealized_loss": 1.0, "tokens_held": 1},   # net -1 -> rank 2
        {"wallet": "0xc", "eth_spent": 1, "eth_received": 9, "realized_pnl_eth": 8.0,
         "realized_loss": 0.0, "unrealized_loss": 0.0, "tokens_held": 0},   # net +8 -> no rank
    ]
    out = b.build_wallet_index(wallets)
    ranks = {w["wallet"]: w["loss_rank"] for w in out}
    assert ranks == {"0xa": 1, "0xb": 2, "0xc": None}
    assert out[0]["wallet"] == "0xa"  # sorted most-negative first
    assert out[0]["net_pnl_eth"] == -5.0

def test_build_holders_single_table_ranked_by_net_with_counts_and_usd():
    pnls = [
        {"wallet": "0xLoser", "unrealized_loss": 10.0, "unrealized_loss_usd": 20000.0,
         "realized_pnl_eth": 0.0, "realized_pnl_usd": 0.0,
         "eth_spent": 10, "eth_received": 0, "tokens_held": 3,
         "tokens_bought": 3, "tokens_sold": 0},
        {"wallet": "0xFlip", "unrealized_loss": 0.0, "unrealized_loss_usd": 0.0,
         "realized_pnl_eth": 8.0, "realized_pnl_usd": 16000.0,
         "eth_spent": 2, "eth_received": 10, "tokens_held": 0,
         "tokens_bought": 5, "tokens_sold": 5},
        {"wallet": "0x77B9", "unrealized_loss": 0.0, "unrealized_loss_usd": 0.0,
         "realized_pnl_eth": 5.0, "realized_pnl_usd": 9000.0,
         "eth_spent": 1, "eth_received": 6, "tokens_held": 0,
         "tokens_bought": 2, "tokens_sold": 2},
    ]
    out = b.build_holders(pnls, metazoo_addrs={"0x77b9"})
    rows = out["holders"]
    assert [w["wallet"] for w in rows] == ["0xLoser", "0x77B9", "0xFlip"]
    assert rows[0]["net_pnl_eth"] == -10.0 and rows[0]["net_pnl_usd"] == -20000.0
    assert rows[-1]["net_pnl_eth"] == 8.0 and rows[-1]["net_pnl_usd"] == 16000.0
    assert (rows[0]["tokens_held"], rows[0]["tokens_bought"], rows[0]["tokens_sold"]) == (3, 3, 0)
    m = {w["wallet"]: w for w in rows}
    assert m["0x77B9"]["metazoo"] is True and m["0xLoser"]["metazoo"] is False

def test_build_tokens_uses_latest_sale_then_mint_then_free():
    transfers = [
        {"token_id": "1", "hash": "0xmint1", "is_mint": True},
        {"token_id": "1", "hash": "0xsaleA", "is_mint": False},
        {"token_id": "2", "hash": "0xmint2", "is_mint": True},   # never resold -> mint price
        {"token_id": "3", "hash": "0xmint3", "is_mint": True},   # free mint -> 0
    ]
    sales = [
        {"token_id": "1", "block": 100, "price_eth": 4.0, "settled_eth": 3.9, "is_phantom": False},
        {"token_id": "1", "block": 90,  "price_eth": 1.0, "settled_eth": 0.9, "is_phantom": False},  # older
        {"token_id": "1", "block": 110, "price_eth": 9.0, "settled_eth": 8.9, "is_phantom": True},   # phantom, ignored
    ]
    mint_values = {"0xmint1": 0.1, "0xmint2": 0.2, "0xmint3": 0.0}
    block_month = {100: "2021-12"}
    daily_usd = {"2021-12-01": 4000.0}
    out = b.build_tokens(transfers, sales, mint_values, floor_eth=0.005,
                         block_month=block_month, daily_usd=daily_usd, eth_price_usd=2400.0)
    by_id = {t["token_id"]: t for t in out}
    assert by_id["1"]["last_paid_eth"] == 4.0          # latest non-phantom sale
    assert by_id["1"]["last_paid_date"] == "2021-12"
    assert by_id["1"]["last_paid_usd"] == 16000.0      # 4.0 * 4000
    assert by_id["2"]["last_paid_eth"] == 0.2          # mint price fallback
    assert by_id["2"]["last_paid_date"] is None
    assert by_id["2"]["last_paid_usd"] == 480.0        # 0.2 * 2400 (current fallback)
    assert by_id["3"]["last_paid_eth"] == 0.0          # free mint
    assert out[0]["token_id"] == "1"                   # sorted by last_paid_eth desc
    assert by_id["1"]["floor_usd"] == 12.0

def test_collection_wallet_pnls_matches_econ():
    transfers = [
        {"collection": "c", "token_id": "1", "from": "0x0", "to": "0xminter",
         "hash": "0xh1", "is_mint": True, "timestamp": 1, "block": 1},
        {"collection": "c", "token_id": "1", "from": "0xminter", "to": "0xbuyer",
         "hash": "0xh2", "is_mint": False, "timestamp": 2, "block": 2},
    ]
    mint_values = {"0xh1": 0.1}
    sales = [{"collection": "c", "token_id": "1", "from": "0xminter", "to": "0xbuyer",
              "block": 5, "settled_eth": 0.4, "price_eth": 0.4, "proceeds_eth": 0.4,
              "royalty_eth": 0.0, "is_phantom": False}]
    out = b.collection_wallet_pnls(transfers, mint_values, sales, floor_eth=0.005)
    wallets = {w["wallet"] for w in out}
    assert "0xminter" in wallets and "0xbuyer" in wallets
    minter = next(w for w in out if w["wallet"] == "0xminter")
    assert minter["realized_pnl_eth"] > 0
    for w in out:
        assert set(w.keys()) == {
            "wallet", "eth_spent", "eth_received", "realized_pnl_eth",
            "realized_loss", "unrealized_loss", "tokens_held",
            "tokens_bought", "tokens_sold", "tokens_minted",
            "tokens_received", "tokens_sent", "gas_spent_eth",
        }


def test_collection_wallet_pnls_normalizes_address_tagged_sales():
    ZERO = "0x0000000000000000000000000000000000000000"
    transfers = [
        {"collection": "genesis_2021", "token_id": "1", "from": ZERO, "to": "0xa",
         "hash": "0xm1", "is_mint": True, "block": 1, "timestamp": 1},
        {"collection": "genesis_2021", "token_id": "1", "from": "0xa", "to": "0xb",
         "hash": "0xsale1", "is_mint": False, "block": 5, "timestamp": 5},
    ]
    mint_values = {"0xm1": 0.01}
    sales = [
        {"collection": "0xa0529c325e2594dcc599ba6e39aa4d6b28834c53",  # ADDRESS, not slug
         "token_id": "1", "from": "0xa", "to": "0xb",
         "price_eth": 2.0, "proceeds_eth": 1.9, "block": 5, "is_phantom": False},
    ]
    out = b.collection_wallet_pnls(transfers, mint_values, sales, floor_eth=0.005,
                                    collection_key="genesis_2021")
    buyer = next(w for w in out if w["wallet"] == "0xb")
    assert buyer["unrealized_loss"] > 1.9


def test_tracked_token_ids_finds_the_subset_living_on_a_host_contract():
    assert "1017" in b.tracked_token_ids("aoki")


def test_tracked_token_ids_is_empty_for_a_contract_with_no_subset():
    assert b.tracked_token_ids("coin_tokens") == set()


def test_aoki_is_marked_third_party_and_excluded_from_loss():
    from scripts.config import CONTRACTS
    assert CONTRACTS["aoki"].get("third_party") is True
    assert CONTRACTS["aoki"].get("include_in_loss_calc") is False
    assert CONTRACTS["mothman_1of1"]["address"] == CONTRACTS["aoki"]["address"]


def test_distributor_issuance_reads_the_delivery_hop_not_a_0x0_mint():
    d = "0xD1"
    transfers = [
        {"token_id": "1", "from": "0xd1", "to": "0xaaa", "is_mint": False},
        {"token_id": "2", "from": "0xD1", "to": "0xbbb", "is_mint": False},
        {"token_id": "1", "from": "0xaaa", "to": "0xccc", "is_mint": False},  # resale
    ]
    ids, claimers = b.distributor_issuance(transfers, d)
    assert ids == {"1", "2"}
    assert claimers == {"0xaaa", "0xbbb"}


def test_distributor_issuance_is_empty_without_a_distributor():
    transfers = [{"token_id": "1", "from": "0x0", "to": "0xaaa", "is_mint": True}]
    assert b.distributor_issuance(transfers, None) == (set(), set())


def test_merge_pnl_lists_adapts_list_shape_through_dict_merge():
    a = [{"wallet": "0xa", "eth_spent": 1.0, "eth_received": 0.0, "tokens_held": 1}]
    b_list = [
        {"wallet": "0xa", "eth_spent": 0.5, "eth_received": 0.0, "tokens_held": 1},
        {"wallet": "0xb", "eth_spent": 2.0, "eth_received": 0.0, "tokens_held": 1},
    ]
    out = b.merge_pnl_lists(a, b_list)
    by_wallet = {p["wallet"]: p for p in out}
    assert by_wallet["0xa"]["eth_spent"] == 1.5   # summed across both sources
    assert by_wallet["0xa"]["tokens_held"] == 2   # summed too (both int fields)
    assert by_wallet["0xb"]["eth_spent"] == 2.0   # wallet only in b passes through


def test_build_findings_assembles_legs_and_insider_sum():
    flow_summary = {"metazoo_to_aoki_eth": 210.37}
    summary = {"secondary_volume_eth": 1776.4, "royalties_to_metazoo_eth": 123.63}
    acquisitions = {"total_eth": 2811.6, "total_usd": 8122371, "total_purchases": 757,
                    "by_collection": [{"name": "CRYPTOPUNKS", "eth": 652.79}],
                    "top_items": [{"name": "Doodles", "token_id": "2238"}] * 30}
    ledger = [
        {"date": "2022-01-11", "eth": 89.77, "usd": 290824, "recipient": "Aoki (main)", "kind": "aoki"},
        {"date": "2022-07-27", "eth": 130.0, "usd": 212646, "recipient": "insider", "kind": "insider"},
        {"date": "2024-01-29", "eth": 9.5,  "usd": 22017,  "recipient": "insider", "kind": "insider"},
    ]
    out = b.build_findings(flow_summary, summary, acquisitions, ledger)
    assert out["legs"]["aoki_eth"] == 210.37
    assert out["legs"]["secondary_volume_eth"] == 1776.4
    assert out["legs"]["insider_eth"] == 139.5      # 130 + 9.5
    assert out["insider"]["eth"] == 139.5
    assert out["insider"]["exchange"] == "Coinbase"
    assert out["payout_ledger"] == ledger
    assert len(out["acquisitions"]["top_items"]) == 24   # capped


def test_build_findings_legs_usd_and_holdings():
    flow = {"metazoo_to_aoki_eth": 100.0}
    summary = {"secondary_volume_eth": 1000.0, "royalties_to_metazoo_eth": 50.0}
    acq = {"total_eth": 5.0, "total_usd": 10.0, "total_purchases": 2,
           "by_collection": [{"contract": "0xPUNK", "name": "CRYPTOPUNKS", "purchases": 7, "eth": 1.0},
                             {"contract": "0xSHARE", "name": "Shared", "purchases": 16, "eth": 1.0}],
           "top_items": [{"name": "X", "token_id": "1", "contract": "0xPUNK"}]}
    holdings = {"holdings": {"0xpunk": {"held_now": 5}, "0xshare": {"held_now": None}}}
    out = b.build_findings(flow, summary, acq, [], eth_price_usd=2000.0, holdings=holdings,
                           secondary_volume_usd=3000000.0, royalties_usd=90000.0)
    assert out["legs"]["aoki_usd"] == 200000.0
    assert out["legs"]["secondary_volume_usd"] == 3000000.0
    assert out["legs"]["royalties_usd"] == 90000.0
    assert out["legs"]["eth_price_usd"] == 2000.0
    by = {c["name"]: c for c in out["acquisitions"]["by_collection"]}
    assert by["CRYPTOPUNKS"]["held_now"] == 5         # 5 of 7 still held
    assert by["Shared"]["held_now"] is None           # multi-tenant → not comparable


def test_build_findings_blue_chip_logos_and_ordered_underwater():
    from scripts.build_site_data import BLUECHIP_TILE_ORDER
    doodles, punks = BLUECHIP_TILE_ORDER[0], BLUECHIP_TILE_ORDER[1]
    flow = {"metazoo_to_aoki_eth": 1.0}
    summary = {"secondary_volume_eth": 1.0, "royalties_to_metazoo_eth": 1.0}
    acq = {"total_eth": 1.0, "total_usd": 1.0, "total_purchases": 1, "top_items": [],
           "by_collection": [
               {"contract": punks, "name": "CryptoPunks", "purchases": 1, "eth": 2.0},
               {"contract": doodles, "name": "Doodles", "purchases": 1, "eth": 1.0}]}
    holdings = {"holdings": {punks: {"loss_pct": -65.7}, doodles: {"loss_pct": -99.1}}}
    art = {punks: {"file": "punks.avif"}, doodles: {"file": "doodles.avif"}}
    out = b.build_findings(flow, summary, acq, [], holdings=holdings, acq_collection_art=art)
    a = out["acquisitions"]
    assert a["by_collection"][0]["image"].endswith("/acq_collections/punks.avif")
    assert [u["name"] for u in a["underwater"]] == ["Doodles", "CryptoPunks"]
    assert a["underwater"][0]["image"].endswith("/acq_collections/doodles.avif")


def test_build_findings_top_examples_one_per_bluechip_ordered():
    from scripts.build_site_data import BLUECHIP_TILE_ORDER
    doodles, punks, bayc = BLUECHIP_TILE_ORDER[0], BLUECHIP_TILE_ORDER[1], BLUECHIP_TILE_ORDER[2]
    flow = {"metazoo_to_aoki_eth": 1.0}
    summary = {"secondary_volume_eth": 1.0, "royalties_to_metazoo_eth": 1.0}
    top_items = [
        {"name": "Doodles", "token_id": "2238", "contract": doodles, "eth": 269.7,
         "usd": 1.0, "date": "2022-01-07", "marketplace": "wyvern"},
        {"name": "CRYPTOPUNKS", "token_id": "8705", "contract": punks, "eth": 150.0,
         "usd": 1.0, "date": "2021-08-28", "marketplace": "cryptopunks"},
        {"name": "CRYPTOPUNKS", "token_id": "9192", "contract": punks, "eth": 109.9,
         "usd": 1.0, "date": "2021-08-28", "marketplace": "cryptopunks"},
        {"name": "BoredApeYachtClub", "token_id": "4698", "contract": bayc, "eth": 105.0,
         "usd": 1.0, "date": "2022-03-16", "marketplace": "wyvern"},
    ]
    acq = {"total_eth": 1.0, "total_usd": 1.0, "total_purchases": 1,
           "by_collection": [], "top_items": top_items}
    media = {f"{punks}_8705": {"file": "punk.png"}}
    out = b.build_findings(flow, summary, acq, [], acq_media=media)
    ex = out["acquisitions"]["top_examples"]

    assert [(e["name"], e["token_id"]) for e in ex] == [
        ("Doodles", "2238"), ("CRYPTOPUNKS", "8705"), ("BoredApeYachtClub", "4698")]
    assert ex[1]["image"].endswith("/acquisitions/punk.png")   # art folded via with_image
    assert ex[0]["image"] is None                              # no media entry → null


def test_build_findings_insider_usd_at_spend_from_ledger():
    flow = {"metazoo_to_aoki_eth": 100.0}
    summary = {"secondary_volume_eth": 1.0, "royalties_to_metazoo_eth": 2.0}
    acq = {"total_eth": 0.0, "total_usd": 0.0, "total_purchases": 0,
           "by_collection": [], "top_items": []}
    ledger = [{"eth": 130.0, "usd": 212646.0, "kind": "insider"},
              {"eth": 9.5, "usd": 22017.0, "kind": "insider"},
              {"eth": 5.0, "usd": 15000.0, "kind": "splitter"}]  # non-insider ignored
    out = b.build_findings(flow, summary, acq, ledger)
    assert out["legs"]["insider_eth"] == 139.5        # 130 + 9.5
    assert out["legs"]["insider_usd"] == 234663.0     # 212646 + 22017 (at-spend)


def test_build_findings_top_items_include_contract():
    from scripts.build_site_data import build_findings
    flow = {"metazoo_to_aoki_eth": 210.37}
    summary = {"secondary_volume_eth": 1.0, "royalties_to_metazoo_eth": 2.0}
    acq = {
        "total_eth": 5.0, "total_usd": 10.0, "total_purchases": 1,
        "by_collection": [{"contract": "0xabc", "name": "X", "purchases": 1, "eth": 5.0, "usd": 10.0}],
        "top_items": [{"name": "Doodles", "token_id": "2238", "contract": "0xaaa",
                       "eth": 5.0, "usd": 10.0, "date": "2022-01-07", "marketplace": "wyvern"}],
    }
    out = build_findings(flow, summary, acq, [])
    assert out["acquisitions"]["top_items"][0]["contract"] == "0xaaa"


def test_trace_acquisitions_top_items_carry_contract():
    from scripts.trace_acquisitions import build_output
    purchases = [{"contract": "0xAAA", "token_id": "1", "eth": 9.0, "usd": 18.0,
                  "date": "2022-01-01", "marketplace": "seaport"}]
    out = build_output(purchases, ncache={"0xAAA": "BoredApes"})
    assert out["top_items"][0]["contract"] == "0xAAA".lower() or out["top_items"][0]["contract"] == "0xAAA"


def test_block_to_month_interpolation():
    ts_small = datetime(2023, 1, 15, tzinfo=timezone.utc).timestamp()
    ts_lo = datetime(2023, 10, 31, 18, 0, 0, tzinfo=timezone.utc).timestamp()
    ts_hi = datetime(2023, 11, 1, 13, 0, 0, tzinfo=timezone.utc).timestamp()
    block_ts = {50: ts_small, 100: ts_lo, 200: ts_hi}

    needed_blocks = [50, 10, 500, 140]
    out = b._block_to_month(needed_blocks, block_ts)

    assert out[50] == "2023-01"    # (a) exact-hit block returns its own month
    assert out[10] == "2023-01"    # (b) below smallest anchor -> clamp to it
    assert out[500] == "2023-11"   # (c) above largest anchor -> clamp to it
    assert out[140] == "2023-11"   # (d) boundary-straddling linear interpolation


def test_build_tokens_uses_media_manifest(monkeypatch):
    import scripts.build_site_data as b
    monkeypatch.setattr(b, "MEDIA_CDN_BASE", "https://cdn/nftina")
    transfers = [{"token_id": "1", "is_mint": True, "hash": "0xh", "block": 1, "timestamp": 1}]
    tokens = b.build_tokens(transfers, [], {"0xh": 0.1}, 0.005, {1: "2021-11"},
                            {"2021-11-01": 4000.0}, 4000.0, slug="coin_tokens",
                            media={"1": {"name": "Bigfoot", "file": "1.png", "source": "s"}})
    t = tokens[0]
    assert t["name"] == "Bigfoot"
    assert t["image"] == "https://cdn/nftina/tokens/coin_tokens/1.png"


def test_build_tokens_folds_type_from_traits():
    import scripts.build_site_data as b
    transfers = [{"token_id": "83", "is_mint": True, "hash": "0xh", "block": 1, "timestamp": 1}]
    tokens = b.build_tokens(transfers, [], {"0xh": 0.1}, 0.005, {1: "2021-11"},
                            {"2021-11-01": 4000.0}, 4000.0, slug="coin_tokens",
                            media=None, traits={"83": "Mothman Gold"})
    assert tokens[0]["type"] == "Mothman Gold"
    t2 = b.build_tokens(transfers, [], {"0xh": 0.1}, 0.005, {1: "2021-11"},
                        {"2021-11-01": 4000.0}, 4000.0, slug="coin_tokens")
    assert t2[0]["type"] is None


def test_build_tokens_null_when_no_manifest(monkeypatch):
    import scripts.build_site_data as b
    transfers = [{"token_id": "1", "is_mint": True, "hash": "0xh", "block": 1, "timestamp": 1}]
    tokens = b.build_tokens(transfers, [], {"0xh": 0.1}, 0.005, {1: "2021-11"},
                            {"2021-11-01": 4000.0}, 4000.0, slug="coin_tokens", media=None)
    assert tokens[0]["name"] is None and tokens[0]["image"] is None


def test_build_tokens_divides_batch_mint_value_across_tokens():
    from scripts.build_site_data import build_tokens
    transfers = [
        {"collection": "beasties_s1", "token_id": "1", "from": "0x0000000000000000000000000000000000000000",
         "to": "0xa", "hash": "0xbatch", "is_mint": True, "block": 10, "timestamp": 1657},
        {"collection": "beasties_s1", "token_id": "2", "from": "0x0000000000000000000000000000000000000000",
         "to": "0xa", "hash": "0xbatch", "is_mint": True, "block": 10, "timestamp": 1657},
        {"collection": "beasties_s1", "token_id": "3", "from": "0x0000000000000000000000000000000000000000",
         "to": "0xa", "hash": "0xbatch", "is_mint": True, "block": 10, "timestamp": 1657},
    ]
    mint_values = {"0xbatch": 0.3}
    rows = build_tokens(transfers, sales=[], mint_values=mint_values, floor_eth=0.0,
                        block_month={}, daily_usd={}, eth_price_usd=3000.0, slug="beasties_s1")
    by_id = {r["token_id"]: r for r in rows}
    assert by_id["1"]["last_paid_eth"] == 0.1   # NOT 0.3
    assert by_id["2"]["last_paid_eth"] == 0.1
    assert by_id["3"]["last_paid_eth"] == 0.1
    assert by_id["1"]["last_paid_date"] is None  # mint-fallback branch (no sale)


def test_build_findings_sets_acquisition_image(monkeypatch):
    import scripts.build_site_data as b
    monkeypatch.setattr(b, "MEDIA_CDN_BASE", "https://cdn/nftina")
    flow = {"metazoo_to_aoki_eth": 1.0}
    summary = {"secondary_volume_eth": 1.0, "royalties_to_metazoo_eth": 1.0}
    acq = {"total_eth": 1.0, "total_usd": 1.0, "total_purchases": 1, "by_collection": [],
           "top_items": [{"name": "Doodles", "token_id": "2238", "contract": "0xaaa",
                          "eth": 1.0, "usd": 1.0, "date": "d", "marketplace": "m"}]}
    acq_media = {"0xaaa_2238": {"name": "Doodles #2238", "file": "0xaaa_2238.png",
                                "source": "s", "contract": "0xaaa", "token_id": "2238"}}
    out = b.build_findings(flow, summary, acq, [], acq_media=acq_media)
    assert out["acquisitions"]["top_items"][0]["image"] == "https://cdn/nftina/acquisitions/0xaaa_2238.png"


def test_build_wallet_names_precedence_label_opensea_ens():
    identities = {
        "0xLABEL": {"label": "MetaZoo: Deployer", "source": "labels.json"},
        "0xENS":   {"label": "neo808.eth", "source": "ENS primary (verified)"},
        "0xBOTH":  {"label": "cat42.eth", "source": "ENS primary (verified)"},
    }
    opensea = {
        "0xboth": {"username": "CatWhale", "pfp": "https://p"},   # OpenSea beats ENS
        "0xnew":  {"username": "FreshTrader", "pfp": None},        # not in ENS evidence
        "0xlabel": {"username": "ShouldLose", "pfp": None},        # curated label wins
    }
    out = b.build_wallet_names(identities, opensea)
    assert out["0xlabel"] == "MetaZoo: Deployer"    # curated label wins
    assert out["0xens"] == "neo808.eth"             # ENS kept (no OpenSea name)
    assert out["0xboth"] == "CatWhale"              # OpenSea username beats ENS
    assert out["0xnew"] == "FreshTrader"            # OpenSea-only wallet included


def test_build_wallet_avatars_from_opensea_pfps():
    opensea = {"0xA": {"username": "a", "pfp": "https://i.seadn.io/a.png"},
               "0xB": {"username": "b", "pfp": None}, "0xC": {}}
    out = b.build_wallet_avatars(opensea)
    assert out == {"0xa": "https://i.seadn.io/a.png"}    # only wallets with a real pfp


def test_curated_override_outranks_an_opensea_username_and_pfp():
    identities = {"0xARGOS": {"label": "ignored.eth", "source": "ENS primary (verified)"}}
    opensea = {"0xargos": {"username": "AI_ChatBot", "pfp": "https://i.seadn.io/bot.png"}}
    overrides = {
        "_comment": "not a wallet",
        "0xARGOS": {"name": "Argos Anon", "avatar_file": "argos_anon.jpg"},
    }
    names = b.build_wallet_names(identities, opensea, overrides)
    avatars = b.build_wallet_avatars(opensea, overrides)
    assert names["0xargos"] == "Argos Anon"
    assert avatars["0xargos"] == f"{b.MEDIA_CDN_BASE}/wallets/argos_anon.jpg"
    assert "_comment" not in names and "_comment" not in avatars


def test_curated_overrides_are_optional_and_partial():
    opensea = {"0xA": {"username": "keeps", "pfp": "https://p/a.png"}}
    assert b.build_wallet_names({}, opensea, None)["0xa"] == "keeps"
    assert b.build_wallet_avatars(opensea, None) == {"0xa": "https://p/a.png"}
    only_name = {"0xA": {"name": "Renamed"}}
    assert b.build_wallet_names({}, opensea, only_name)["0xa"] == "Renamed"
    assert b.build_wallet_avatars(opensea, only_name) == {"0xa": "https://p/a.png"}


def test_wallet_maps_are_key_sorted_so_the_tracked_json_stays_stable():
    """merge_profiles unions two key sets, whose iteration order varies per run under
    hash randomization. Without sorting, adding one wallet rewrites every line of the
    tracked site/data map and buries the real change in thousands of reordered ones."""
    opensea = {"0xC": {"username": "c", "pfp": "https://p/c.png"},
               "0xA": {"username": "a", "pfp": "https://p/a.png"},
               "0xB": {"username": "b", "pfp": "https://p/b.png"}}
    overrides = {"0xD": {"name": "d", "avatar_file": "d.png"}}
    names = b.build_wallet_names({}, opensea, overrides)
    avatars = b.build_wallet_avatars(opensea, overrides)
    assert list(names) == sorted(names) == ["0xa", "0xb", "0xc", "0xd"]
    assert list(avatars) == sorted(avatars) == ["0xa", "0xb", "0xc", "0xd"]


def test_enrich_collections_display_off_chain_loss_and_1155_pieces():
    cols = [
        {"collection": "pfp_2", "secondary_volume_eth": 5.0, "royalty_eth": 0.1,
         "floor_eth": 0.001, "floor_usd": 3.58, "mint_revenue_eth": 1.19, "total_mints": 2381},
        {"collection": "coin_tokens", "secondary_volume_eth": 100.0, "royalty_eth": 8.0,
         "floor_eth": 0.005, "floor_usd": 9.4, "mint_revenue_eth": 280.0, "total_mints": 2305},
        {"collection": "genesis_reissue_1155", "secondary_volume_eth": 38.9, "royalty_eth": 1.8,
         "floor_eth": 0.0, "floor_usd": 0.0, "mint_revenue_eth": 0.0, "total_mints": 0},
    ]
    vol = {"coin_tokens": [{"usd": 300000.0}], "pfp_2": [{"usd": 10000.0}]}
    authored = {"pfp_2": {"off_chain_basis": {"unit_cost_usd": 100}}}
    b.enrich_collections_display(cols, vol, authored, 1885.0, {"genesis_reissue_1155": 17})
    by = {c["collection"]: c for c in cols}
    assert by["pfp_2"]["loss_pct"] == -96.4                     # (3.58-100)/100*100
    assert by["pfp_2"]["secondary_volume_usd"] == 10000.0       # at-event from volume series
    assert by["coin_tokens"]["loss_pct"] < -90                  # floor << avg mint price
    assert by["coin_tokens"]["secondary_volume_usd"] == 300000.0
    assert by["genesis_reissue_1155"]["total_mints"] == 17      # 1155 piece count fills in
    assert by["genesis_reissue_1155"]["loss_pct"] is None       # no basis -> no pct


def test_build_wallet_index_adds_net_pnl_usd():
    idx = b.build_wallet_index([
        {"wallet": "0xa", "realized_pnl_eth": 1.0, "unrealized_loss": 3.0,
         "realized_pnl_usd": 2000.0, "unrealized_loss_usd": 9000.0},
    ])
    assert idx[0]["net_pnl_eth"] == -2.0
    assert idx[0]["net_pnl_usd"] == -7000.0


def test_merge_profiles_field_level_keeps_both_sources():
    web3bio = {"0xNEO": {"username": "neo808.eth", "pfp": None},
               "0xONLYW3": {"username": "lens.guy", "pfp": "https://w3.png"}}
    opensea = {"0xneo": {"username": None, "pfp": "https://os.png"},
               "0xONLYOS": {"username": "Ferg", "pfp": "https://os2.png"}}
    out = b.merge_profiles(web3bio, opensea)
    assert out["0xneo"] == {"username": "neo808.eth", "pfp": "https://os.png"}
    assert out["0xonlyw3"] == {"username": "lens.guy", "pfp": "https://w3.png"}
    assert out["0xonlyos"] == {"username": "Ferg", "pfp": "https://os2.png"}


def test_merge_profiles_opensea_username_wins_when_both_have_one():
    web3bio = {"0xX": {"username": "x.eth", "pfp": "https://w.png"}}
    opensea = {"0xX": {"username": "CoolHandle", "pfp": "https://o.png"}}
    out = b.merge_profiles(web3bio, opensea)
    assert out["0xx"] == {"username": "CoolHandle", "pfp": "https://o.png"}


def test_build_coin_strip_dedupes_by_type(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(b, "MEDIA_INDEX", tmp_path)
    monkeypatch.setattr(b, "MEDIA_CDN_BASE", "https://cdn/nftina")
    (tmp_path / "tokens").mkdir()
    (tmp_path / "traits").mkdir()
    (tmp_path / "tokens" / "coin_tokens.json").write_text(json.dumps({
        "1": {"file": "a.gif"}, "2": {"file": "b.gif"}, "3": {"file": "c.gif"}}))
    (tmp_path / "traits" / "coin_tokens.json").write_text(json.dumps({
        "1": "MetaZoo Party Silver", "2": "MetaZoo Party Silver", "3": "Mothman Gold"}))
    out = b.build_coin_strip()
    assert [c["token_id"] for c in out] == ["1", "3"]           # one Silver + Mothman
    assert out[0]["image"] == "https://cdn/nftina/tokens/coin_tokens/a.gif"


def test_build_coin_strip_falls_back_to_file_without_traits(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(b, "MEDIA_INDEX", tmp_path)
    monkeypatch.setattr(b, "MEDIA_CDN_BASE", "https://cdn/nftina")
    (tmp_path / "tokens").mkdir()
    (tmp_path / "tokens" / "coin_tokens.json").write_text(json.dumps({
        "1": {"file": "a.gif"}, "2": {"file": "a.gif"}, "3": {"file": "b.gif"}}))
    out = b.build_coin_strip()   # no traits/ dir -> dedupe by file
    assert [c["token_id"] for c in out] == ["1", "3"]
    assert b.build_coin_strip.__doc__ is not None


def test_build_content_shape():
    from scripts.build_site_data import build_content
    authored = {"coin_tokens": {"overview": ["a"],
                                "utility": {"promised": ["p"], "delivered": ["d"]}}}
    out = build_content("coin_tokens", authored)
    assert out["overview"] == authored["coin_tokens"]["overview"]
    assert out["utility"] == []
    empty = build_content("unknown_slug", authored)
    assert empty == {"overview": [], "utility": []}


def test_build_content_computes_off_chain_basis_loss_pct():
    from scripts.build_site_data import build_content
    authored = {"pfp_2": {"overview": ["a"],
                          "utility": {"promised": [], "delivered": []},
                          "off_chain_basis": {"unit_cost_usd": 100,
                                              "unit_label": "PFP Box", "note": "n"}}}
    out = build_content("pfp_2", authored, floor_usd=3.58)
    b = out["off_chain_basis"]
    assert b["floor_usd"] == 3.58
    assert b["loss_pct"] == -96.4          # (3.58 - 100) / 100 * 100
    assert b["unit_cost_usd"] == 100 and b["note"] == "n"


def test_build_content_off_chain_basis_untouched_without_floor():
    from scripts.build_site_data import build_content
    authored = {"pfp_2": {"overview": [], "utility": {"promised": [], "delivered": []},
                          "off_chain_basis": {"unit_cost_usd": 100,
                                              "unit_label": "PFP Box", "note": "n"}}}
    out = build_content("pfp_2", authored, floor_usd=None)
    assert "loss_pct" not in out["off_chain_basis"]


def _raw_two_token_fixture():
    z = "0x0000000000000000000000000000000000000000"
    transfers = [
        {"collection": "valentines", "token_id": "7", "from": z, "to": "0xa",
         "hash": "0xm7", "is_mint": True, "block": 5, "timestamp": 1676},
        {"collection": "valentines", "token_id": "1", "from": z, "to": "0xb",
         "hash": "0xm1", "is_mint": True, "block": 5, "timestamp": 1676},
    ]
    mint_values = {"0xm7": 0.02, "0xm1": 0.05}
    sales = [{"collection": "valentines", "token_id": "7", "from": "0xa", "to": "0xc",
              "price_eth": 0.1, "proceeds_eth": 0.095, "block": 9, "is_phantom": False}]
    return transfers, sales, mint_values

def test_synth_collection_stats_filters_to_token_ids():
    from scripts.build_site_data import synth_collection_stats
    transfers, sales, mint_values = _raw_two_token_fixture()
    st = synth_collection_stats("wilderness", transfers, sales, mint_values,
                                floor_eth=0.01, token_ids=["7", "8", "9", "10", "11"])
    assert st["total_mints"] == 1                 # only token 7 is in-set
    assert round(st["mint_revenue_eth"], 4) == 0.02
    assert round(st["secondary_volume_eth"], 4) == 0.1
    assert st["secondary_sales"] == 1
    assert st["floor_eth"] == 0.01
    assert st["contract"] == "0xa986559aacf60a82fab3ef59940febea8027be0c"

def test_filter_raw_to_tokens():
    from scripts.build_site_data import filter_raw_to_tokens
    transfers = [{"token_id": "7"}, {"token_id": "1"}, {"token_id": "11"}]
    sales = [{"token_id": "7"}, {"token_id": "2"}]
    ft, fs = filter_raw_to_tokens(transfers, sales, ["7", "8", "9", "10", "11"])
    assert [t["token_id"] for t in ft] == ["7", "11"]
    assert [s["token_id"] for s in fs] == ["7"]


def test_build_collections_returns_ten_in_order_with_names():
    from scripts.build_site_data import build_collections
    transfers, sales, mint_values = _raw_two_token_fixture()
    analyze_collections = [{  # only "own" slugs come from analyze.py; minimal valentines entry
        "collection": "valentines", "name": "MetaZoo Valentines / MZV", "contract": "0xa986",
        "standard": "erc1155", "total_transfers": 2, "total_mints": 2, "unique_minters": 2,
        "mint_revenue_eth": 0.07, "mint_revenue_usd": 100.0, "secondary_sales": 1,
        "secondary_volume_eth": 0.1, "royalty_eth": 0.005, "floor_eth": 0.01,
        "include_in_loss_calc": True,
    }]
    per_slug_raw = {"valentines": {"transfers": transfers, "sales": sales,
                                   "mint_values": mint_values, "floor_eth": 0.01},
                    "aoki": {"transfers": [], "sales": [], "mint_values": {}, "floor_eth": 0.0}}
    out = build_collections(analyze_collections, 3000.0, per_slug_raw, art={"sandbox": "https://cdn/x.png"})
    slugs = [c["collection"] for c in out]
    assert slugs == ["genesis_2021", "genesis_reissue_1155", "coin_tokens", "beasties_s1",
                     "pfp_2", "valentines", "wilderness", "tournament_prizes",
                     "mothman_1of1", "sandbox"]
    names = {c["collection"]: c["name"] for c in out}
    assert names["valentines"] == "MetaZoo Valentines"          # renamed from analyze's name
    assert names["mothman_1of1"] == "MetaZoo Mothman 1/1"
    assert names["tournament_prizes"] == "MetaZoo Tournament Prizes"
    tp = next(c for c in out if c["collection"] == "tournament_prizes")
    assert tp["total_mints"] == 0 and tp["mint_revenue_eth"] == 0.0  # placeholder = zeros
    sb = next(c for c in out if c["collection"] == "sandbox")
    assert sb["image"] == "https://cdn/x.png"                  # art merged in
    for c in out:
        assert "floor_usd" in c and "image" in c
    wl = next(c for c in out if c["collection"] == "wilderness")
    assert wl["mint_revenue_usd"] == round(0.02 * 3000.0, 2)   # synthesized -> latest-price fill
    vt = next(c for c in out if c["collection"] == "valentines")
    assert vt["mint_revenue_usd"] == 100.0   # analyze-sourced "own" entry: untouched, keeps its own USD


def test_build_sandbox3d_drops_null_model_entries():
    entries = [
        {"token_id": "1", "name": "Sam Sinclair", "model": "https://cdn/x.gltf", "image": "https://cdn/x.png"},
        {"token_id": "2", "name": "Broken", "model": None, "image": None},
        {"token_id": "3", "name": "Mothman", "model": "https://cdn/y.gltf", "image": None},
    ]
    out = b.build_sandbox3d(entries)
    assert [e["token_id"] for e in out] == ["1", "3"]
    assert all(e["model"] is not None for e in out)


def test_merge_sources_for_reads_config():
    from scripts.build_site_data import merge_sources_for
    assert merge_sources_for("genesis_2021") == ["mintable_early"]
    assert merge_sources_for("coin_tokens") == []


def test_raw_slugs_for_includes_merge_sources():
    from scripts.build_site_data import raw_slugs_for
    from scripts.config import SITE_COLLECTIONS
    slugs = raw_slugs_for(SITE_COLLECTIONS)
    assert "mintable_early" in slugs          # merge source raw must be loaded
    assert "genesis_2021" in slugs            # its merge target too (own slug)


def test_merge_wallet_pnls_sums_and_concatenates():
    from scripts.build_site_data import merge_wallet_pnls
    a = {"0xa": {"eth_spent": 1.0, "eth_received": 0.5, "realized_eth": -0.5,
                 "unrealized_eth": -0.2, "holdings": [("genesis_2021", "1")]}}
    b = {"0xa": {"eth_spent": 0.3, "eth_received": 0.0, "realized_eth": -0.3,
                 "unrealized_eth": 0.0, "holdings": [("mintable_early", "9")]},
         "0xb": {"eth_spent": 2.0, "eth_received": 0.0, "realized_eth": -2.0,
                 "unrealized_eth": 0.0, "holdings": []}}
    m = merge_wallet_pnls(a, b)
    assert m["0xa"]["eth_spent"] == 1.3
    assert m["0xa"]["holdings"] == [("genesis_2021", "1"), ("mintable_early", "9")]
    assert m["0xb"]["eth_spent"] == 2.0


def test_main_writes_all_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(b, "SITE_DATA", tmp_path / "site")
    monkeypatch.setattr(b, "PUBLIC_DATA", tmp_path / "public")
    monkeypatch.setattr(b, "RAW", tmp_path / "raw")
    (tmp_path / "public").mkdir(); (tmp_path / "raw").mkdir()
    (tmp_path / "evidence").mkdir()
    b.write_json(tmp_path / "public" / "summary.json",
                 {"secondary_volume_eth": 1.0, "royalties_to_metazoo_eth": 0.5})
    b.write_json(tmp_path / "public" / "collections.json",
                 [{"collection": "coin_tokens", "floor_eth": 0.005}])
    b.write_json(tmp_path / "public" / "wallet_pnl.json", [])
    b.write_json(tmp_path / "public" / "flippers.json", [])
    b.write_json(tmp_path / "public" / "flow_summary.json", {"metazoo_to_aoki_eth": 210.0})
    b.write_json(tmp_path / "public" / "acquisitions.json",
                 {"total_eth": 1, "total_usd": 1, "total_purchases": 1,
                  "by_collection": [], "top_items": []})
    b.write_json(tmp_path / "evidence" / "payout_ledger.json", [])
    for slug in ["coin_tokens"]:
        for suf, val in [("transfers", []), ("sales", []), ("mintvalues", {})]:
            b.write_json(tmp_path / "raw" / f"{slug}_{suf}.json", val)
        b.write_json(tmp_path / "raw" / f"{slug}_floor.json", {"floor_eth": 0.005})
    monkeypatch.setattr(b, "PAYOUT_LEDGER_PATH", tmp_path / "evidence" / "payout_ledger.json")
    monkeypatch.setattr(b, "eth_daily_usd", lambda: {"2022-01-01": 2400.0})
    b.main()
    assert (tmp_path / "site" / "summary.json").exists()
    assert (tmp_path / "site" / "collections.json").exists()
    assert (tmp_path / "site" / "volume_series.json").exists()
    assert (tmp_path / "site" / "wallet_index.json").exists()
    assert (tmp_path / "site" / "findings.json").exists()
    assert (tmp_path / "site" / "collections" / "coin_tokens" / "holders.json").exists()
    assert (tmp_path / "site" / "collections" / "coin_tokens" / "tokens.json").exists()


def test_build_usd_audit_passthrough_and_null():
    from scripts.build_site_data import build_usd_audit
    assert build_usd_audit(None) is None
    doc = {"headline": {"received_eth": 1.0}, "by_class": {"in": {}, "out": {}},
           "method": {"wallets": [], "valuation": "x"}}
    assert build_usd_audit(doc) == doc


def test_build_usd_audit_drops_parked_keys():
    """`weekly` (chart) and `method.caveats` (disclosure paragraph) are both parked
    on the frontend, so neither ships in the site contract. Both remain in the full
    record at public/data/treasury_usd_audit.json."""
    from scripts.build_site_data import build_usd_audit
    doc = {"headline": {}, "by_class": {"in": {}, "out": {}},
           "weekly": [{"week": "2021-12-06", "eth_balance": 1.0, "usd_mark": 2.0}],
           "method": {"wallets": [], "valuation": "x", "caveats": ["estimates only"]}}
    out = build_usd_audit(doc)
    assert "weekly" not in out
    assert "caveats" not in out["method"]
    assert out["headline"] == {} and out["method"]["valuation"] == "x"


def test_build_holders_includes_minted_and_gas_and_net_subtracts_gas():
    pnls = [{"wallet": "0xb", "tokens_held": 1, "tokens_bought": 1, "tokens_sold": 0,
             "tokens_minted": 1, "unrealized_loss": 0.10, "unrealized_loss_usd": 200.0,
             "realized_pnl_eth": 0.0, "realized_pnl_usd": 0.0,
             "gas_spent_eth": 0.05, "gas_spent_usd": 100.0,
             "eth_spent": 0.1, "eth_received": 0.0}]
    out = b.build_holders(pnls, set())
    row = out["holders"][0]
    assert row["tokens_minted"] == 1
    assert row["gas_spent_eth"] == 0.05
    assert round(row["net_pnl_eth"], 6) == -0.15
    assert round(row["net_pnl_usd"], 2) == -300.0


def test_apply_offchain_uses_row_mint_count_by_default():
    rows = [{"wallet": "0xminter", "tokens_minted": 3, "net_pnl_usd": -10.0, "metazoo": False},
            {"wallet": "0xteam", "tokens_minted": 5, "net_pnl_usd": -2.0, "metazoo": True}]
    out = b.apply_offchain(rows, unit_cost_usd=100)
    minter = next(r for r in out["holders"] if r["wallet"] == "0xminter")
    team = next(r for r in out["holders"] if r["wallet"] == "0xteam")
    assert minter["all_in_net_usd"] == -310.0
    assert "all_in_net_usd" not in team           # team wallets buy no boxes
    assert out["offchain_revenue_usd"] == 300.0


def test_apply_offchain_map_override_scopes_by_token_id():
    rows = [{"wallet": "0xw", "tokens_minted": 5, "net_pnl_usd": -4.0, "metazoo": False}]
    out = b.apply_offchain(rows, unit_cost_usd=30, mint_count_by_wallet={"0xw": 2})
    w = out["holders"][0]
    assert w["all_in_net_usd"] == -64.0           # -4 - (2 x 30)
    assert out["offchain_revenue_usd"] == 60.0


def test_offchain_box_counts_filters_by_token_id_and_quantity():
    ZERO = "0x0000000000000000000000000000000000000000"
    transfers = [
        {"from": ZERO, "to": "0xw", "token_id": "3", "quantity": 1},   # valentines-proper
        {"from": ZERO, "to": "0xw", "token_id": "5", "quantity": 2},   # 2 editions
        {"from": ZERO, "to": "0xw", "token_id": "9", "quantity": 1},   # wilderness (excluded)
        {"from": "0xother", "to": "0xw", "token_id": "1", "quantity": 1},  # not a mint (excluded)
    ]
    counts = b.offchain_box_counts(transfers, token_ids={"1", "2", "3", "4", "5", "6"})
    assert counts == {"0xw": 3}                    # tokens 3 (x1) + 5 (x2); token 9 excluded
    assert b.offchain_box_counts(transfers) == {"0xw": 4}  # no filter -> all mints incl. token 9


def test_build_flippers_excludes_net_negative_wallets():
    flippers = [
        {"wallet": "0xGOOD", "eth_spent": 0.2, "eth_received": 27.16,
         "realized_pnl_eth": 26.96, "realized_pnl_usd": 62000.0, "tokens_held": 3,
         "unrealized_loss": 0.5, "gas_spent_eth": 0.07},
        {"wallet": "0xBAGS", "eth_spent": 47.58, "eth_received": 17.46,
         "realized_pnl_eth": 14.15, "realized_pnl_usd": 15024.0, "tokens_held": 42,
         "unrealized_loss": 26.16, "gas_spent_eth": 0.12},
    ]
    out = b.build_flippers(flippers, {}, 1084.29, 2609301.04, 145.86, 1819)
    assert [r["wallet"] for r in out["top"]] == ["0xGOOD"]
    assert out["total_gains_eth"] == 1084.29


def test_build_utility_selects_only_this_slugs_products_in_catalogue_order():
    products = [
        {"id": "a", "collection": "coin_tokens", "name": "A", "price_usd": 30, "note": "n1",
         "image_file": "a.jpg"},
        {"id": "b", "collection": "beasties_s1", "name": "B", "note": "n2"},
        {"id": "c", "collection": "coin_tokens", "name": "C", "note": "n3"},
    ]
    media = {"a": {"file": "a.jpg", "source_name": "A.jpg"}}
    out = b.build_utility("coin_tokens", products, media)
    assert [p["id"] for p in out] == ["a", "c"]
    assert out[0]["image"].endswith("/utility/a.jpg")
    assert out[0]["price_usd"] == 30
    assert out[1]["price_usd"] is None       # free to holders
    assert out[1]["image"] is None           # no manifest entry


def test_build_utility_is_empty_without_a_catalogue():
    assert b.build_utility("coin_tokens", [], {}) == []


def test_build_utility_warns_when_image_file_authored_but_not_indexed(capsys):
    products = [{"id": "a", "collection": "coin_tokens", "name": "A", "note": "n",
                 "image_file": "a.jpg"}]
    out = b.build_utility("coin_tokens", products, {})
    assert out[0]["image"] is None
    warning = capsys.readouterr().out
    assert "a" in warning and "index_utility_media" in warning


def test_build_utility_no_warning_without_an_image_file(capsys):
    products = [{"id": "a", "collection": "coin_tokens", "name": "A", "note": "n"}]
    b.build_utility("coin_tokens", products, {})
    assert capsys.readouterr().out == ""


def test_build_utility_no_warning_when_manifest_has_the_entry(capsys):
    products = [{"id": "a", "collection": "coin_tokens", "name": "A", "note": "n",
                 "image_file": "a.jpg"}]
    media = {"a": {"file": "a.jpg", "source_name": "a.jpg"}}
    b.build_utility("coin_tokens", products, media)
    assert capsys.readouterr().out == ""


def test_validate_products_rejects_an_unknown_collection_slug():
    import pytest
    with pytest.raises(ValueError, match="nonesuch"):
        b.validate_products([{"id": "x", "collection": "nonesuch"}], {"coin_tokens"})


def test_validate_products_rejects_a_duplicate_id():
    import pytest
    products = [
        {"id": "valentines_box", "collection": "coin_tokens", "name": "A", "note": "n"},
        {"id": "valentines_box", "collection": "coin_tokens", "name": "B", "note": "n"},
    ]
    with pytest.raises(ValueError, match="valentines_box"):
        b.validate_products(products, {"coin_tokens"})


def test_validate_products_rejects_an_id_with_spaces_or_punctuation():
    import pytest
    products = [{"id": "july 4th promo", "collection": "coin_tokens", "name": "A", "note": "n"}]
    with pytest.raises(ValueError, match="july 4th promo"):
        b.validate_products(products, {"coin_tokens"})


def test_validate_products_allows_a_clean_lowercase_underscore_id():
    b.validate_products([{"id": "valentines_box", "collection": "coin_tokens",
                           "name": "A", "note": "n"}], {"coin_tokens"})


def test_validate_products_rejects_a_non_numeric_price_usd():
    import pytest
    products = [{"id": "valentines_box", "collection": "coin_tokens", "name": "A",
                 "note": "n", "price_usd": "30"}]
    with pytest.raises(ValueError, match="valentines_box"):
        b.validate_products(products, {"coin_tokens"})


def test_validate_products_allows_a_null_or_numeric_price_usd():
    b.validate_products([
        {"id": "a", "collection": "coin_tokens", "name": "A", "note": "n"},
        {"id": "b", "collection": "coin_tokens", "name": "B", "note": "n", "price_usd": 30},
    ], {"coin_tokens"})


def test_utility_image_url_carries_the_content_hash_as_a_cache_buster():
    url = b.utility_image_url({"file": "dim_mak_box.jpg", "hash": "5e709b9a"})
    assert url.endswith("/utility/dim_mak_box.jpg?v=5e709b9a")


def test_utility_image_url_omits_the_query_for_a_pre_hash_manifest():
    assert b.utility_image_url({"file": "x.jpg"}).endswith("/utility/x.jpg")
    assert b.utility_image_url(None) is None


def test_validate_products_rejects_a_non_numeric_price_eth():
    import pytest
    products = [{"id": "mint", "collection": "coin_tokens", "name": "A", "note": "n",
                 "date": "2022-07-15", "price_eth": "0.1"}]
    with pytest.raises(ValueError, match="price_eth"):
        b.validate_products(products, {"coin_tokens"})


def test_validate_products_rejects_an_eth_price_with_no_date_to_value_it_at():
    import pytest
    products = [{"id": "mint", "collection": "coin_tokens", "name": "A", "note": "n",
                 "price_eth": 0.1}]
    with pytest.raises(ValueError, match="no date"):
        b.validate_products(products, {"coin_tokens"})


def test_usd_at_day_prefers_the_exact_date_then_the_month_then_the_fallback():
    import pytest
    daily = {"2022-07-15": 1231.25, "2022-07-01": 1059.73}
    assert b.usd_at_day(0.1, "2022-07-15", daily, 1885) == pytest.approx(123.125)
    assert b.usd_at_day(0.1, "2022-07-20", daily, 1885) == pytest.approx(105.973)
    assert b.usd_at_day(0.1, "2019-01-01", daily, 1885) == pytest.approx(188.5)


def test_build_utility_pairs_an_eth_price_with_usd_at_the_drop_date():
    import pytest
    products = [{"id": "mint", "collection": "coin_tokens", "name": "Allowlist mint",
                 "note": "n", "date": "2022-07-15", "price_eth": 0.1}]
    row = b.build_utility("coin_tokens", products, {},
                          daily_usd={"2022-07-15": 1231.25}, eth_price_usd=1885)[0]
    assert row["price_eth"] == 0.1
    assert row["price_usd"] == pytest.approx(123.12)   # 0.1 x 1231.25, rounded to cents


def test_build_utility_leaves_a_dollar_priced_product_alone():
    products = [{"id": "box", "collection": "coin_tokens", "name": "Box", "note": "n",
                 "price_usd": 30}]
    row = b.build_utility("coin_tokens", products, {}, daily_usd={}, eth_price_usd=1885)[0]
    assert (row["price_usd"], row["price_eth"]) == (30, None)


def test_build_utility_free_product_carries_neither_price():
    row = b.build_utility("coin_tokens",
                          [{"id": "f", "collection": "coin_tokens", "name": "F", "note": "n"}],
                          {})[0]
    assert (row["price_usd"], row["price_eth"]) == (None, None)


def test_build_content_attaches_the_slugs_utility_products():
    authored = {"coin_tokens": {"overview": ["hi"]}}
    products = [{"id": "a", "collection": "coin_tokens", "name": "A", "note": "n"}]
    out = b.build_content("coin_tokens", authored, products=products, media={})
    assert out["overview"] == ["hi"]
    assert [p["id"] for p in out["utility"]] == ["a"]


def test_build_content_of_an_unknown_slug_is_empty_not_missing_keys():
    out = b.build_content("nope", {}, products=[], media={})
    assert out["overview"] == [] and out["utility"] == []


def test_build_utility_sorts_by_hidden_date_and_never_emits_it():
    products = [
        {"id": "later", "collection": "c", "name": "Later", "note": "", "date": "2022-07-04"},
        {"id": "earlier", "collection": "c", "name": "Earlier", "note": "", "date": "2022-02-07"},
    ]
    out = b.build_utility("c", products, {})
    assert [p["id"] for p in out] == ["earlier", "later"]
    assert all("date" not in p for p in out)


def test_build_utility_sorts_undated_products_last_in_catalogue_order():
    products = [
        {"id": "undated_a", "collection": "c", "name": "A", "note": ""},
        {"id": "dated", "collection": "c", "name": "D", "note": "", "date": "2022-02-07"},
        {"id": "undated_b", "collection": "c", "name": "B", "note": ""},
    ]
    assert [p["id"] for p in b.build_utility("c", products, {})] == [
        "dated", "undated_a", "undated_b"]


def test_validate_products_rejects_a_malformed_date():
    import pytest
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        b.validate_products([{"id": "x", "collection": "c", "date": "Feb 7, 2022"}], {"c"})


def test_validate_products_accepts_an_absent_date():
    b.validate_products([{"id": "x", "collection": "c"}], {"c"})


def test_overview_media_url_resolves_three_authored_forms():
    """Absolute URLs pass through, a path with a directory is CDN-relative, and a
    bare filename lives in the CDN's overview/ folder."""
    from scripts.build_site_data import MEDIA_CDN_BASE, overview_media_url

    assert overview_media_url("https://cdn.example/a.png") == "https://cdn.example/a.png"
    assert overview_media_url("tokens/valentines/x.png") == f"{MEDIA_CDN_BASE}/tokens/valentines/x.png"
    assert overview_media_url("w_640.webp") == f"{MEDIA_CDN_BASE}/overview/w_640.webp"


def test_build_content_resolves_overview_video_like_the_image():
    from scripts.build_site_data import MEDIA_CDN_BASE, build_content

    out = build_content("mothman_1of1", {"mothman_1of1": {
        "overview": [], "overview_image": "tokens/m/x.jpg",
        "overview_video": "collections/m.mp4"}})
    assert out["overview_image"] == f"{MEDIA_CDN_BASE}/tokens/m/x.jpg"
    assert out["overview_video"] == f"{MEDIA_CDN_BASE}/collections/m.mp4"


def test_fits_whole_flags_token_art_and_every_gif():
    """Utility tiles fit token art and GIFs, and crop product photos. Both signals come
    from the media manifest, so no per-product authoring is needed."""
    from scripts.build_site_data import fits_whole

    assert fits_whole({"source_name": "data/media/tokens/coin_tokens/x.gif"}) is True
    assert fits_whole({"source_name": "promo.gif", "file": "software_malfunction.gif"}) is True
    assert fits_whole({"source_name": "dim-mak-hq.jpg", "file": "dim_mak_box.jpg"}) is False
    assert fits_whole({"source_name": "data/media/overview/ws_x.webp",
                       "file": "beasties_free_mint.webp"}) is False
    assert fits_whole({}) is False
    assert fits_whole(None) is False
