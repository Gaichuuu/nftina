from scripts.export_recovered_tweets import collect, is_relevant, select_relevant


def _r(tid, text="hi", **kw):
    return {"tweet_id": tid, "text": text, "timestamp": kw.pop("ts", "2022-01-01T00:00:00.000Z"), **kw}


def test_collect_dedupes_a_tweet_seen_in_several_captures():
    rows = [_r("1", capture="A"), _r("1", capture="B"), _r("2", capture="B")]
    assert [t["tweet_id"] for t in collect(rows)] == ["1", "2"]


def test_collect_prefers_the_row_that_actually_has_text():
    rows = [_r("1", text=None, capture="A"), _r("1", text="real", capture="B")]
    assert collect(rows)[0]["text"] == "real"


def test_collect_merges_partial_rows_rather_than_picking_one_whole():
    rows = [_r("1", text=None, media=["img"]), _r("1", text="real")]
    got = collect(rows)[0]
    assert (got["text"], got["media"]) == ("real", ["img"])


def test_collect_does_not_let_a_later_row_blank_out_a_filled_field():
    rows = [_r("1", text="real", media=["img"]), _r("1", text=None, media=[])]
    got = collect(rows)[0]
    assert (got["text"], got["media"]) == ("real", ["img"])


def test_collect_sorts_by_post_time_not_capture_order():
    rows = [_r("2", ts="2022-07-13T02:04:29.000Z"), _r("1", ts="2021-03-01T00:00:00.000Z")]
    assert [t["tweet_id"] for t in collect(rows)] == ["1", "2"]


def test_collect_flags_which_tweets_the_old_archives_already_had():
    rows = [_r("1"), _r("2")]
    out = {t["tweet_id"]: t["new_to_archive"] for t in collect(rows, known={"1"})}
    assert out == {"1": False, "2": True}


def test_collect_skips_a_row_with_no_id():
    assert collect([{"text": "orphan"}]) == []


def test_relevance_reads_text_author_and_retweeter():
    assert is_relevant(_r("1", text="gm @MetaZooGames beasties"))
    assert is_relevant(_r("2", text="unrelated", author="metazoogames"))
    assert is_relevant(_r("3", text="unrelated", retweeted_by="MetaZoo Games"))
    assert not is_relevant(_r("4", text="gm nfts", author="farokh"))


def test_relevance_keeps_a0k1verse_which_the_promo_classifier_drops():
    assert is_relevant(_r("1", text="A0K1VERSE Passport holders can sign up"))


def test_select_keeps_both_halves_of_a_quote_pair():
    quoter = _r("2", text="see u there @MetaZooGames", quoted_id="1")
    quoted = _r("1", text="GM NFTs, Wednesday 10:30 AM")
    offtopic_quoter = _r("4", text="nice", quoted_id="3")
    ontopic_quoted = _r("3", text="mothman drop")
    got = {t["tweet_id"] for t in select_relevant([quoted, quoter, ontopic_quoted, offtopic_quoter])}
    assert got == {"1", "2", "3", "4"}


def test_select_drops_the_off_topic_bulk_of_a_profile_sweep():
    rows = [_r("1", text="gm"), _r("2", text="metazoo mint"), _r("3", text="lunch")]
    assert [t["tweet_id"] for t in select_relevant(rows)] == ["2"]
