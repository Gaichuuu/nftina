from scripts.correlate import (is_undisclosed_promo, days_to_nearest_event,
                               snowflake_to_date, _normalize)


def test_normalize_canonicalizes_author_from_url():
    rec = {"tweet_id": "123", "date": "2021-12-03", "text": "hi",
           "author_title": "Steve Aoki on Twitter",
           "url": "https://twitter.com/steveaoki/status/123"}
    out = _normalize([rec], "aoki_deleted")[0]
    assert out["author"] == "steveaoki"   # derived from URL, not the OG title


def test_normalize_keeps_explicit_handle():
    rec = {"id": "9", "date": "2021-11-29", "text": "hi", "author": "steveaoki",
           "url": "https://x.com/steveaoki/status/9"}
    out = _normalize([rec], "influencer")[0]
    assert out["author"] == "steveaoki"


def test_promo_flag_true_hype_no_disclosure():
    assert is_undisclosed_promo("You NEED to mint this MetaZoo drop!!") is True
    assert is_undisclosed_promo("Grab the Mothman 1/1 on Sotheby's now 🚀") is True


def test_promo_flag_false_with_disclosure():
    assert is_undisclosed_promo("Love this MetaZoo mint #ad") is False
    assert is_undisclosed_promo("MetaZoo drop, mint now #sponsored") is False


def test_promo_flag_false_without_metazoo_or_hype():
    assert is_undisclosed_promo("gm, big announcement soon") is False       # no metazoo
    assert is_undisclosed_promo("I collected a MetaZoo card years ago") is False  # no hype


def test_days_to_nearest_event():
    events = [{"date": "2021-11-29", "event": "coin mint"}, {"date": "2022-07-15", "event": "beastie"}]
    assert days_to_nearest_event("2021-11-27", events) == 2
    assert days_to_nearest_event("2022-07-15", events) == 0


def test_snowflake_to_date():
    assert snowflake_to_date("1465342289039925257") == "2021-11-29"
    assert snowflake_to_date("") is None
    assert snowflake_to_date("notanid") is None
