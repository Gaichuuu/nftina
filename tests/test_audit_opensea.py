from scripts.audit_opensea import creator_fee, pct_delta, reconcile


def test_creator_fee_excludes_opensea_protocol_fee():
    fees = [{"fee": 0.5, "recipient": "0x0000a26b00c1f0df003000390027140000faa719", "required": True},
            {"fee": 10.0, "recipient": "0xCBBEcd9d102299EF022aDEE17daAe3DcB779aa43", "required": False}]
    pct, recip = creator_fee(fees)
    assert pct == 10.0
    assert recip == "0xcbbecd9d102299ef022adee17daae3dcb779aa43"   # lowercased


def test_creator_fee_none_when_only_protocol():
    fees = [{"fee": 0.5, "recipient": "0x0000a26b00c1f0df003000390027140000faa719"}]
    assert creator_fee(fees) == (0.0, None)
    assert creator_fee([]) == (0.0, None)
    assert creator_fee(None) == (0.0, None)


def test_pct_delta():
    assert pct_delta(100, 100) == 0.0
    assert pct_delta(90, 100) == 0.1
    assert pct_delta(0, 0) is None       # both ~0 -> undefined


def test_reconcile_flags_configured_royalty_with_zero_captured():
    ours = {"supply": 100, "volume_eth": 50, "sales": 20, "owners": 40,
            "royalty_eth": 0.0, "floor_eth": 0.01}
    os_detail = {"total_supply": 100, "fees": [{"fee": 5.0, "recipient": "0xabc"}]}
    os_stats = {"volume": 48, "sales": 19, "num_owners": 41, "floor": 0.01}
    rec = reconcile("x", ours, os_detail, os_stats, comparable=True, label_lookup={})
    assert rec["royalty_pct"] == 5.0
    assert any("royalty configured" in f for f in rec["flags"])
    assert any("UNLABELED" in f for f in rec["flags"])          # 0xabc not in labels


def test_reconcile_supply_mismatch_flagged():
    ours = {"supply": 2305, "volume_eth": 961, "sales": 2255, "owners": 971,
            "royalty_eth": 79.6, "floor_eth": 0.005}
    os_detail = {"total_supply": 2000, "fees": []}   # 15% supply gap
    os_stats = {"volume": 920, "sales": 2255, "num_owners": 971, "floor": 0.005}
    rec = reconcile("coin", ours, os_detail, os_stats, comparable=True, label_lookup={})
    assert any("supply" in f for f in rec["flags"])


def test_reconcile_volume_below_opensea_is_flagged():
    ours = {"supply": 100, "volume_eth": 10, "sales": 5, "owners": 30,
            "royalty_eth": 1.0, "floor_eth": 0.01}
    os_detail = {"total_supply": 100, "fees": []}
    os_stats = {"volume": 50, "sales": 20, "num_owners": 30, "floor": 0.01}
    rec = reconcile("x", ours, os_detail, os_stats, comparable=True, label_lookup={})
    assert any("missing sales" in f for f in rec["flags"])


def test_reconcile_volume_above_opensea_is_expected_not_flagged():
    ours = {"supply": 100, "volume_eth": 60, "sales": 25, "owners": 30,
            "royalty_eth": 1.0, "floor_eth": 0.01}
    os_detail = {"total_supply": 100, "fees": []}
    os_stats = {"volume": 50, "sales": 20, "num_owners": 30, "floor": 0.01}
    rec = reconcile("x", ours, os_detail, os_stats, comparable=True, label_lookup={})
    assert not any("volume" in f for f in rec["flags"])


def test_reconcile_not_comparable_skips_stats_checks():
    ours = {"supply": 3, "volume_eth": 0, "sales": 0, "owners": 1,
            "royalty_eth": 0.0, "floor_eth": 0.0}
    os_detail = {"total_supply": 90000, "fees": []}   # shared storefront's whole supply
    os_stats = {"volume": 9999, "sales": 5000, "num_owners": 8000, "floor": 1.0}
    rec = reconcile("tournament_prizes", ours, os_detail, os_stats,
                    comparable=False, label_lookup={})
    assert not rec["flags"]                                   # no false supply/volume flags
    stat_checks = {c["metric"]: c for c in rec["checks"]}
    assert stat_checks["supply"]["status"] == "not_comparable"
    assert stat_checks["current_owners"]["status"] == "not_comparable"


def test_reconcile_known_royalty_recipient_not_flagged():
    ours = {"supply": 100, "volume_eth": 50, "sales": 20, "owners": 40,
            "royalty_eth": 5.0, "floor_eth": 0.01}
    os_detail = {"total_supply": 100, "fees": [{"fee": 5.0, "recipient": "0xTREASURY"}]}
    os_stats = {"volume": 48, "sales": 19, "num_owners": 41, "floor": 0.01}
    rec = reconcile("x", ours, os_detail, os_stats, comparable=True,
                    label_lookup={"0xtreasury": {"label": "MetaZoo: Treasury"}})
    assert not any("UNLABELED" in f for f in rec["flags"])
