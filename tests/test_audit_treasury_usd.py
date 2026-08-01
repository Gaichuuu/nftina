import json
from pathlib import Path

import pytest

from scripts.audit_treasury_usd import (usd_at_date, build_ledger,
                                        weekly_balances, week_start, reconcile)

DAILY = {"2021-11-01": 4000.0, "2021-12-01": 4500.0, "2022-06-01": 1000.0,
         "2022-07-01": 1100.0}
TREASURY = {"0xaaa", "0xbbb"}


def _tx(frm, to, eth, ts, kind="normal", err=False, h="0x1"):
    return {"from": frm, "to": to, "eth": eth, "hash": h,
            "timestamp": ts, "kind": kind, "is_error": err}

TS_NOV21 = 1635768000   # 2021-11-01 12:00 UTC
TS_JUN22 = 1654084800   # 2022-06-01 12:00 UTC


def kind_of(addr):
    return {"0xc01": "nft_contract", "0x05e4": "marketplace",
            "0xa0k": "aoki", "0xexc": "exchange"}.get(addr, "other")


def test_usd_at_date_exact_and_nearest():
    assert usd_at_date(2.0, "2021-11-01", DAILY) == 8000.0
    assert usd_at_date(1.0, "2021-11-15", DAILY) == 4000.0   # nearest earlier
    assert usd_at_date(1.0, "2021-01-01", DAILY) == 4000.0   # before table -> nearest overall


def test_build_ledger_classifies_and_nets_intra_treasury():
    txns = {"0xaaa": [
        _tx("0xc01", "0xaaa", 10.0, TS_NOV21, kind="internal", h="0xm"),  # mint proceeds in
        _tx("0x05e4", "0xaaa", 1.0, TS_NOV21, h="0xr"),                    # royalties in
        _tx("0xaaa", "0xa0k", 4.0, TS_JUN22, h="0xo"),                     # aoki out
        _tx("0xaaa", "0xbbb", 3.0, TS_JUN22, h="0xi"),                     # intra-treasury: dropped
        _tx("0xaaa", "0xexc", 2.0, TS_JUN22, h="0xe"),                     # exchange deposit out
        _tx("0xaaa", "0xzz", 0.0, TS_JUN22, h="0xz"),                      # zero: dropped
        _tx("0xzz", "0xaaa", 5.0, TS_JUN22, h="0xf", err=True),            # error: dropped
    ], "0xbbb": [
        _tx("0xaaa", "0xbbb", 3.0, TS_JUN22, h="0xi"),                     # intra (other side): dropped
    ]}
    ledger = build_ledger(txns, TREASURY, kind_of, DAILY)
    by_cls = {}
    for e in ledger:
        by_cls.setdefault(e["cls"], 0)
        by_cls[e["cls"]] += e["eth"]
    assert by_cls == {"mint_proceeds": 10.0, "royalties": 1.0,
                      "aoki": 4.0, "exchange_deposit": 2.0}
    mint = next(e for e in ledger if e["cls"] == "mint_proceeds")
    assert mint["date"] == "2021-11-01" and mint["usd"] == 40000.0


def test_build_ledger_dedups_same_tx_seen_twice():
    tx = _tx("0xzz", "0xaaa", 5.0, TS_NOV21, h="0xd")
    ledger = build_ledger({"0xaaa": [tx, dict(tx)]}, TREASURY, kind_of, DAILY)
    assert len(ledger) == 1


def test_week_start_snaps_to_monday():
    assert week_start("2022-06-15") == "2022-06-13"   # Wednesday -> Monday
    assert week_start("2022-06-13") == "2022-06-13"   # Monday is its own start
    assert week_start("2022-06-19") == "2022-06-13"   # Sunday -> same week


def test_weekly_balances_marks_to_week_end():
    txns = {"0xaaa": [_tx("0xzz", "0xaaa", 10.0, TS_NOV21, h="0x1"),
                      _tx("0xaaa", "0xyy", 4.0, TS_JUN22, h="0x2")]}
    series = weekly_balances(build_ledger(txns, TREASURY, kind_of, DAILY), DAILY)
    assert series[0]["eth_balance"] == 10.0 and series[0]["usd_mark"] == 40000.0
    assert series[-1]["eth_balance"] == 6.0 and series[-1]["usd_mark"] == 6000.0


def test_weekly_balances_emits_quiet_weeks_so_the_axis_is_even():
    """A gap with no activity must still produce points, else the chart compresses
    time and a long dormant stretch looks like a short one."""
    txns = {"0xaaa": [_tx("0xzz", "0xaaa", 10.0, TS_NOV21, h="0x1"),
                      _tx("0xaaa", "0xyy", 4.0, TS_JUN22, h="0x2")]}
    series = weekly_balances(build_ledger(txns, TREASURY, kind_of, DAILY), DAILY)
    weeks = [w["week"] for w in series]
    assert len(weeks) == len(set(weeks)) and weeks == sorted(weeks)
    assert len(series) > 25                       # ~7 months of weeks, not 2 points
    assert all(series[i]["eth_balance"] == 10.0 for i in range(len(series) - 1))


def test_reconcile_headline():
    txns = {"0xaaa": [_tx("0xc01", "0xaaa", 10.0, TS_NOV21, h="0x1"),   # +10 @ $4000
                      _tx("0xaaa", "0xa0k", 4.0, TS_JUN22, h="0x2")]}   # -4 @ $1000
    r = reconcile(build_ledger(txns, TREASURY, kind_of, DAILY), current_price=2000.0,
                  gas_eth=0.0, gas_usd_at_spend=0.0, held_eth=6.0)
    assert r["received_eth"] == 10.0 and r["received_usd_at_receipt"] == 40000.0
    assert r["paid_eth"] == 4.0 and r["paid_usd_at_spend"] == 4000.0
    assert r["residual_eth"] == 6.0
    assert r["still_held_eth"] == 6.0 and r["still_held_usd_now"] == 12000.0
    assert r["gas_eth"] == 0.0 and r["gas_usd_at_spend"] == 0.0
    assert r["reconciles_eth"] == 0.0            # residual − gas − held = 0
    assert r["depreciation_gap_usd"] == 24000.0  # 40000 - 4000 - 0 - 12000


def test_reconcile_splits_residual_into_gas_and_held():
    txns = {"0xaaa": [_tx("0xc01", "0xaaa", 10.0, TS_NOV21, h="0x1"),
                      _tx("0xaaa", "0xa0k", 4.0, TS_JUN22, h="0x2")]}
    r = reconcile(build_ledger(txns, TREASURY, kind_of, DAILY), current_price=2000.0,
                  gas_eth=5.5, gas_usd_at_spend=9000.0, held_eth=0.5)
    assert r["gas_eth"] == 5.5 and r["still_held_eth"] == 0.5
    assert r["still_held_usd_now"] == 1000.0     # 0.5 * 2000
    assert r["reconciles_eth"] == 0.0            # 6 − 5.5 − 0.5
    assert r["depreciation_gap_usd"] == 26000.0


def test_classify_counterparty_precedence():
    from scripts.audit_treasury_usd import classify_counterparty
    labels = {"0xdef1": {"label": "Coinbase", "type": "exchange"},
              "0x7f26": {"label": "OpenSea: Wallet", "type": "marketplace"},
              "0x37ec": {"label": "insider chain", "type": "insider"}}
    nft = {"0xc0117ac75"}
    aoki = {"0xa0k1"}
    assert classify_counterparty("0xC0117AC75", labels, nft, aoki) == "nft_contract"
    assert classify_counterparty("0xa0k1", labels, nft, aoki) == "aoki"
    assert classify_counterparty("0xdef1", labels, nft, aoki) == "exchange"
    assert classify_counterparty("0x7f26", labels, nft, aoki) == "marketplace"
    assert classify_counterparty("0x37ec", labels, nft, aoki) == "insider"
    assert classify_counterparty("0xzzz", labels, nft, aoki) == "other"


def test_classify_counterparty_insider_wallet_and_unlabeled():
    from scripts.audit_treasury_usd import classify_counterparty, INSIDER_WALLETS
    insider_addr = next(iter(INSIDER_WALLETS))
    assert classify_counterparty(insider_addr.upper(), {}, set(), set()) == "insider"
    assert classify_counterparty("0xsomeunlabeledeoa", {}, set(), set()) == "other"


def test_royalty_source_classifies_and_buckets_as_royalties():
    from scripts.audit_treasury_usd import (classify_counterparty, ROYALTY_SOURCES,
                                            build_ledger, IN_CLS)
    roy = next(iter(ROYALTY_SOURCES))
    assert classify_counterparty(roy.upper(), {}, set(), set()) == "royalty"
    assert IN_CLS["royalty"] == "royalties"
    treasury = {"0x77b9"}
    txns = {"0x77b9": [{"hash": "0x1", "from": roy, "to": "0x77b9", "eth": 5.0,
                        "timestamp": 1650000000, "kind": "normal", "is_error": False}]}
    kind_of = lambda a: classify_counterparty(a, {}, set(), set())
    ledger = build_ledger(txns, treasury, kind_of, {"2022-04-15": 3000.0})
    assert ledger[0]["cls"] == "royalties"


def test_two_labeled_insiders_now_in_insider_set():
    from scripts.audit_treasury_usd import classify_counterparty, INSIDER_WALLETS
    for a in ("0xe693fbc0df4db03d3b75017b7a423dd38d49487c",
              "0x08b96fad98c2366f6e483de584167dd695d30c27"):
        assert a in INSIDER_WALLETS
        assert classify_counterparty(a.upper(), {}, set(), set()) == "insider"


def test_project_cost_addrs_bucket_as_project_costs_on_out():
    from scripts.audit_treasury_usd import (classify_counterparty, PROJECT_COST_ADDRS,
                                            build_ledger, OUT_CLS)
    dex = next(iter(PROJECT_COST_ADDRS))
    assert classify_counterparty(dex.upper(), {}, set(), set()) == "project_cost"
    assert OUT_CLS["project_cost"] == "project_costs"
    treasury = {"0x77b9"}
    txns = {"0x77b9": [{"hash": "0x1", "from": "0x77b9", "to": dex, "eth": 3.0,
                        "timestamp": 1650000000, "kind": "normal", "is_error": False}]}
    kind_of = lambda a: classify_counterparty(a, {}, set(), set())
    ledger = build_ledger(txns, treasury, kind_of, {"2022-04-15": 3000.0})
    assert ledger[0]["cls"] == "project_costs"


def test_royalty_source_out_leg_is_intra_cluster():
    from scripts.audit_treasury_usd import (classify_counterparty, ROYALTY_SOURCES,
                                            build_ledger, OUT_CLS)
    roy = next(iter(ROYALTY_SOURCES))
    assert OUT_CLS["royalty"] == "intra_cluster"
    treasury = {"0x77b9"}
    txns = {"0x77b9": [{"hash": "0x2", "from": "0x77b9", "to": roy, "eth": 16.0,
                        "timestamp": 1650000000, "kind": "normal", "is_error": False}]}
    kind_of = lambda a: classify_counterparty(a, {}, set(), set())
    ledger = build_ledger(txns, treasury, kind_of, {"2022-04-15": 3000.0})
    assert ledger[0]["cls"] == "intra_cluster"


def test_count_cross_kind_collisions():
    from scripts.audit_treasury_usd import count_cross_kind_collisions
    colliding = {"0xaaa": [
        _tx("0xc01", "0xaaa", 10.0, TS_NOV21, kind="normal", h="0xsame"),
        _tx("0xc01", "0xaaa", 10.0, TS_NOV21, kind="internal", h="0xsame"),
    ]}
    assert count_cross_kind_collisions(colliding) == 1
    legit = {"0xaaa": [
        _tx("0xbuyer", "0xcontract", 1.0, TS_NOV21, kind="normal", h="0xh"),
        _tx("0xcontract", "0xaaa", 1.0, TS_NOV21, kind="internal", h="0xh"),
    ]}
    assert count_cross_kind_collisions(legit) == 0
    dup = {"0xaaa": [
        _tx("0xc01", "0xaaa", 5.0, TS_NOV21, kind="normal", h="0xd"),
        _tx("0xc01", "0xaaa", 5.0, TS_NOV21, kind="normal", h="0xd"),
    ]}
    assert count_cross_kind_collisions(dup) == 0


def test_insider_wallets_match_payout_ledger():
    """Drift guard (F42): the audit's hardcoded INSIDER_WALLETS is kept separate from
    labels.json on purpose (labels.json `type` drives trace-recursion)."""
    from scripts.audit_treasury_usd import INSIDER_WALLETS
    ledger_path = Path(__file__).resolve().parents[1] / "data" / "evidence" / "payout_ledger.json"
    if not ledger_path.exists():
        pytest.skip("payout_ledger.json not present in this checkout")
    raw = json.loads(ledger_path.read_text())
    rows = raw if isinstance(raw, list) else raw.get("rows", raw.get("ledger", []))
    ledger_insiders = {r["recipient_addr"].lower() for r in rows
                       if r.get("kind") == "insider" and r.get("recipient_addr")}
    assert ledger_insiders, "expected insider rows in the payout ledger"
    assert {a.lower() for a in INSIDER_WALLETS} == ledger_insiders, (
        "INSIDER_WALLETS drifted from the payout ledger's insider recipients; "
        "sync scripts/audit_treasury_usd.py::INSIDER_WALLETS with data/evidence/payout_ledger.json"
    )


def test_treasury_set_is_the_three_eoas_not_every_metazoo_wallet():
    """The USD audit reconciles received = paid + gas + still-held over the THREE
    treasury EOAs. METAZOO_WALLETS is the display-flag/trace-seed list and grows
    whenever any MetaZoo-controlled wallet is identified; deriving the treasury from
    it silently broke the reconciliation to +2.48 ETH when the Genesis ops wallet
    0x3dd341 was added. Keep the two lists independent."""
    from scripts.config import TREASURY_WALLETS, METAZOO_DEPLOYER, METAZOO_WALLETS
    assert len(TREASURY_WALLETS) == 3
    assert METAZOO_DEPLOYER.lower() in {a.lower() for a in TREASURY_WALLETS}
    genesis_ops = "0x3dd341664b2ffeedf9be108d4fa926dedfa9a0d6"
    assert genesis_ops in {a.lower() for a in METAZOO_WALLETS}       # flagged on the site
    assert genesis_ops not in {a.lower() for a in TREASURY_WALLETS}  # but not a treasury EOA
