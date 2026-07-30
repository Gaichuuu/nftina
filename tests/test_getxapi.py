import json
from pathlib import Path
from scripts.clients.getxapi import parse_tweets, _iso_date

FIX = Path(__file__).parent / "fixtures"


def test_iso_date_parses_twitter_format():
    assert _iso_date("Mon Nov 29 15:30:01 +0000 2021") == "2021-11-29"
    assert _iso_date("") is None


def test_parse_tweets_shape():
    payload = json.loads((FIX / "getxapi_search_2021.json").read_text())
    rows = parse_tweets(payload)
    assert len(rows) == len(payload["tweets"])
    r0 = rows[0]
    assert r0["id"]
    assert r0["date"].startswith("2021")
    assert r0["text"]
    assert r0["author"] == "steveaoki"       # lowercased handle
    assert r0["source"] == "getxapi"
    assert isinstance(r0["media"], list)
    assert r0["url"].startswith("http")


def test_parse_tweets_extracts_media_urls():
    payload = json.loads((FIX / "getxapi_search_2021.json").read_text())
    rows = parse_tweets(payload)
    with_media = [r for r in rows if r["media"]]
    assert with_media, "fixture has at least one tweet with media"
    m = with_media[0]["media"][0]
    assert m["url"].startswith("http")
    assert "type" in m
