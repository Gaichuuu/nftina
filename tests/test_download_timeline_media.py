"""Scheduling and source-preference for the recovered-image download.

The network path itself is `download_archived_media`'s, already in use; what is new
here is that one tweet can carry several images, so the unit of work is (tweet,
index) rather than the tweet. Getting that wrong silently downloads only the first
image of every multi-image tweet.
"""
import pytest

from scripts import download_timeline_media as dl


def _r(tid, media, capture="20220713175134"):
    return {"tweet_id": tid, "capture": capture, "media": media}


class _Resp:
    def __init__(self, content=b"\xff\xd8\xff body"):
        self.content, self.headers = content, {"content-type": "image/jpeg"}

    def raise_for_status(self):
        pass


def test_each_image_of_a_multi_image_tweet_is_its_own_job():
    jobs = dl.pending([_r("1", ["a", "b", "c"])], done=set())
    assert [(j[1], j[2]) for j in jobs] == [(0, "a"), (1, "b"), (2, "c")]


def test_already_downloaded_images_are_skipped_individually():
    jobs = dl.pending([_r("1", ["a", "b"])], done={("1", 0)})
    assert [(j[0]["tweet_id"], j[1]) for j in jobs] == [("1", 1)]


def test_tweets_without_media_produce_no_jobs():
    assert dl.pending([_r("1", []), {"tweet_id": "2", "capture": "x"}], done=set()) == []


def test_live_cdn_is_preferred_over_the_archive(monkeypatch):
    monkeypatch.setattr(dl.requests, "get", lambda *a, **k: _Resp())
    wb = type("WB", (), {"_get": lambda *a, **k: pytest.fail("archive not needed")})()
    _, _, via, err = dl.fetch_one(wb, "20220713175134", "https://pbs.twimg.com/media/x.jpg")
    assert (via, err) == ("live", None)


def test_a_dead_live_url_falls_back_to_the_capture(monkeypatch):
    def dead(*a, **k):
        raise RuntimeError("404")
    monkeypatch.setattr(dl.requests, "get", dead)
    seen = {}

    class WB:
        def _get(self, url, **k):
            seen["url"] = url
            return _Resp()

    content, _, via, err = dl.fetch_one(WB(), "20220713175134",
                                        "https://pbs.twimg.com/media/x.jpg")
    assert (via, err, bool(content)) == ("wayback", None, True)
    assert seen["url"].endswith("20220713175134id_/https://pbs.twimg.com/media/x.jpg")


def test_both_sources_failing_reports_the_error_rather_than_writing_a_file(monkeypatch):
    def dead(*a, **k):
        raise RuntimeError("404")
    monkeypatch.setattr(dl.requests, "get", dead)

    class WB:
        def _get(self, url, **k):
            raise RuntimeError("refused")

    content, _, via, err = dl.fetch_one(WB(), "2022", "u")
    assert content is None and via is None
    assert "wayback" in err
