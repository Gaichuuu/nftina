"""analyze.price_table which ETH/USD table at-event valuation marks against."""
import json

from scripts import analyze
from scripts.config import ETH_PRICES


def test_price_table_prefers_the_cached_daily_close(tmp_path, monkeypatch):
    cache = tmp_path / "eth_usd_daily.json"
    cache.write_text(json.dumps({"2022-05-29": 1813.64, "2022-08-07": 1700.19}))
    monkeypatch.setattr(analyze, "DAILY_USD_CACHE", cache)
    t = analyze.price_table()
    assert t["2022-05-29"] == 1813.64
    assert "2022-05-29" not in ETH_PRICES
    assert t["2021-03-09"] == ETH_PRICES["2021-03-09"]


def test_price_table_falls_back_to_the_sparse_table_without_the_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(analyze, "DAILY_USD_CACHE", tmp_path / "absent.json")
    assert analyze.price_table() == ETH_PRICES


def test_price_table_ignores_an_empty_cache(tmp_path, monkeypatch):
    cache = tmp_path / "eth_usd_daily.json"
    cache.write_text("{}")
    monkeypatch.setattr(analyze, "DAILY_USD_CACHE", cache)
    assert analyze.price_table() == ETH_PRICES
