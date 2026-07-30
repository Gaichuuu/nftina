import json
from pathlib import Path
from scripts.clients.alchemy import parse_sales, parse_floor, _fee_eth

FIX = Path(__file__).parent / "fixtures"


def test_fee_eth_converts_wei_by_decimals():
    assert _fee_eth({"amount": "105000000000000000", "decimals": 18}) == 0.105
    assert _fee_eth(None) == 0.0
    assert _fee_eth({}) == 0.0
    assert _fee_eth({"amount": "105000000000000000", "decimals": None}) == 0.105


def test_parse_sales_splits_price_proceeds_royalty():
    payload = json.loads((FIX / "alchemy_sales_coin_tokens.json").read_text())
    rows = parse_sales(payload, "coin_tokens")
    assert len(rows) == len(payload["nftSales"])
    r0 = rows[0]
    assert r0["proceeds_eth"] == 0.105
    assert r0["royalty_eth"] == 0.012
    assert round(r0["price_eth"], 6) == 0.12          # buyer paid the sum
    assert r0["from"] == r0["from"].lower()           # seller, lowercased
    assert r0["to"] == r0["to"].lower()               # buyer, lowercased
    assert r0["hash"]
    assert r0["collection"] == "coin_tokens"


def test_parse_sales_price_equals_component_sum():
    payload = json.loads((FIX / "alchemy_sales_coin_tokens.json").read_text())
    for r in parse_sales(payload, "coin_tokens"):
        assert round(r["price_eth"], 8) == round(
            r["proceeds_eth"] + r["royalty_eth"] + r["protocol_eth"], 8)


def test_parse_floor_takes_min_of_present_marketplaces():
    payload = json.loads((FIX / "alchemy_floor_coin_tokens.json").read_text())
    assert parse_floor(payload)["floor_eth"] == 0.00487


def test_parse_floor_empty_when_no_floors():
    assert parse_floor({})["floor_eth"] == 0.0
    assert parse_floor({"openSea": {"floorPrice": None, "error": "x"}})["floor_eth"] == 0.0
