"""Joining recovered images back onto recovered tweets.

The join is the whole risk here: the sweep and the backfill are separate passes over
the same captures, so a mismatch silently drops images or files them on the wrong
tweet. These tests pin the join and the resume rule; the extraction itself is covered
by tests/test_timeline_extract.py against real markup.
"""
from scripts.backfill_timeline_media import apply_media, captures_needing_media


def _r(tid, capture="20220713175134", handle="steveaoki", **kw):
    return {"tweet_id": tid, "capture": capture, "page_handle": handle, **kw}


def test_only_captures_with_unfilled_rows_are_re_read():
    rows = [_r("1", media=[]), _r("2", capture="B"), _r("3", capture="B")]
    pending = captures_needing_media(rows)
    assert list(pending) == [("steveaoki", "B")]
    assert sorted(pending[("steveaoki", "B")]) == ["2", "3"]


def test_media_joins_by_tweet_id_not_by_position():
    rows = [_r("1"), _r("2")]
    found = [{"tweet_id": "2", "media": ["u2"]}, {"tweet_id": "1", "media": ["u1"]}]
    apply_media(rows, found)
    assert [r["media"] for r in rows] == [["u1"], ["u2"]]


def test_a_tweet_with_no_image_is_marked_looked_at_not_left_pending():
    rows = [_r("1")]
    apply_media(rows, [{"tweet_id": "1", "media": []}])
    assert rows[0]["media"] == []
    assert captures_needing_media(rows) == {}


def test_already_filled_rows_are_never_overwritten():
    rows = [_r("1", media=["kept"])]
    filled, images = apply_media(rows, [{"tweet_id": "1", "media": ["other"]}])
    assert rows[0]["media"] == ["kept"]
    assert (filled, images) == (0, 0)


def test_tweets_in_the_capture_but_not_in_our_rows_are_ignored():
    rows = [_r("1")]
    apply_media(rows, [{"tweet_id": "1", "media": []}, {"tweet_id": "999", "media": ["x"]}])
    assert [r["tweet_id"] for r in rows] == ["1"]
