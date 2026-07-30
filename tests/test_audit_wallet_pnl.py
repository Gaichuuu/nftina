"""Invariant checks over wallet P&L rows (scripts/audit_wallet_pnl.py, pure core)."""
from scripts import audit_wallet_pnl as a


def row(w, **kw):
    base = {"wallet": w, "eth_spent": 0.0, "eth_received": 0.0, "realized_pnl_eth": 0.0,
            "realized_loss": 0.0, "unrealized_loss": 0.0, "tokens_held": 0,
            "tokens_bought": 0, "tokens_sold": 0, "tokens_minted": 0,
            "tokens_received": 0, "tokens_sent": 0, "gas_spent_eth": 0.0,
            "realized_pnl_usd": 0.0}
    base.update(kw)
    return base


def test_reconciles_flags_a_buyer_whose_purchase_never_became_a_holding():
    bad = a.check_reconciles([row("0xa", tokens_bought=1)])
    assert len(bad) == 1 and bad[0]["expected"] == 1 and bad[0]["held"] == 0
    assert a.check_reconciles([row("0xb", tokens_minted=2, tokens_sold=1, tokens_held=1)]) == []
    assert a.check_reconciles(
        [row("0xc", tokens_minted=4, tokens_received=2, tokens_sent=1,
             tokens_sold=3, tokens_held=2)]) == []


def test_spent_without_position_needs_all_three_to_be_empty():
    assert len(a.check_spent_without_position([row("0xa", eth_spent=0.09, tokens_bought=1)])) == 1
    assert a.check_spent_without_position(
        [row("0xb", eth_spent=0.09, tokens_bought=1, tokens_sold=1)]) == []
    assert a.check_spent_without_position(
        [row("0xc", eth_spent=0.09, tokens_bought=1, tokens_held=1)]) == []


def test_held_exceeds_supply_only_fires_over_a_known_supply():
    rows = [row("0xa", tokens_held=60), row("0xb", tokens_held=50)]
    assert a.check_held_exceeds_supply(rows, 100)[0]["excess"] == 10
    assert a.check_held_exceeds_supply(rows, 110) == []
    assert a.check_held_exceeds_supply(rows, None) == []       # unknowable supply


def test_realized_without_sale_and_gas_without_activity():
    assert len(a.check_realized_without_sale([row("0xa", realized_pnl_eth=1.5)])) == 1
    assert a.check_realized_without_sale(
        [row("0xb", realized_pnl_eth=1.5, tokens_sold=1)]) == []
    assert len(a.check_gas_without_activity([row("0xa", gas_spent_eth=0.01)])) == 1
    assert a.check_gas_without_activity(
        [row("0xb", gas_spent_eth=0.01, tokens_minted=1)]) == []


def test_transfer_sides_balance_catches_a_one_sided_hop():
    ok = [row("0xa", tokens_received=1), row("0xb", tokens_sent=1),
          row("0xc", tokens_bought=2), row("0xd", tokens_sold=2)]
    assert a.check_transfer_sides_balance(ok) == []
    bad = a.check_transfer_sides_balance([row("0xa", tokens_received=1)])
    assert len(bad) == 1 and bad[0]["side"] == "transfers" and bad[0]["delta"] == 1
    bad = a.check_transfer_sides_balance([row("0xa", tokens_bought=3, tokens_sold=1)])
    assert bad[0]["side"] == "sales" and bad[0]["delta"] == 2


def test_review_checks_are_reported_but_not_defects():
    assert a.CHECKS["sign_divergence"][1] == "review"
    assert a.CHECKS["loss_without_basis"][1] == "review"
    assert a.CHECKS["reconciles"][1] == "defect"
    got = a.check_sign_divergence([row("0xa", realized_pnl_eth=0.6, realized_pnl_usd=-6273.0)])
    assert len(got) == 1


def test_run_checks_returns_every_check_and_defaults_senders_to_the_rows():
    rows = [row("0xa", tokens_bought=1)]
    res = a.run_checks(rows)
    assert set(res) == set(a.CHECKS)
    assert len(res["reconciles"]) == 1


def test_issued_supply_counts_1155_quantity_and_is_none_without_mints():
    z = a.ZERO
    assert a.issued_supply([{"from": z, "quantity": 3}, {"from": z, "quantity": 2}]) == 5
    assert a.issued_supply([{"from": z}]) == 1                       # defaults to 1
    assert a.issued_supply([{"from": "0xd"}]) is None                # lazy-mint store
