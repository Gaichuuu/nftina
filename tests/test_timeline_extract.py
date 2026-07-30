"""Timeline-capture extraction (F44's second archive source).

The fixture is a trimmed but VERBATIM slice of a real Wayback capture
(web.archive.org/web/20220713175134id_/https://twitter.com/steveaoki): two
`data-testid="tweet"` blocks, one being Aoki's quote-tweet of @farokh promoting the
MetaZoo Spaces, the other a retweet."""
from pathlib import Path

from scripts.clients.wayback import extract_timeline_tweets

FIXTURE = Path(__file__).parent / "fixtures" / "wayback_timeline_steveaoki.html"
HTML = FIXTURE.read_text(encoding="utf-8", errors="replace")

TARGET = "1547039229795962880"


def test_recovers_the_tweet_that_had_no_status_snapshot():
    rows = {r["tweet_id"]: r for r in extract_timeline_tweets(HTML, "steveaoki")}
    t = rows[TARGET]
    assert t["author"] == "steveaoki"
    assert t["timestamp"] == "2022-07-13T02:04:29.000Z"
    assert t["text"] == ("I’ll be on tomorrow at 11am EST with Michael Wadell "
                         "the creator of @MetaZooGames see u there!")


def test_captures_the_quoted_tweet_under_its_own_author():
    rows = {r["tweet_id"]: r for r in extract_timeline_tweets(HTML)}
    quoted_id = rows[TARGET]["quoted_id"]
    assert quoted_id, "Aoki's tweet quotes farokh's Rug Radio announcement"
    quoted = rows[quoted_id]
    assert quoted["author"] == "farokh"
    assert "Rug Radio" in (quoted["text"] or "") or "RugRadio" in (quoted["text"] or "")
    assert quoted["quoted_id"] is None
    assert quoted["timestamp"] < rows[TARGET]["timestamp"]


def test_attached_images_land_on_the_tweet_they_belong_to():
    rows = {r["tweet_id"]: r for r in extract_timeline_tweets(HTML, "steveaoki")}
    assert rows["1546982736170061825"]["media"] == [
        "https://pbs.twimg.com/media/FXf8ma4VUAIDgsY.jpg"]
    assert rows["1546987555958231040"]["media"] == []


def test_media_urls_are_full_size_and_deduped():
    rows = extract_timeline_tweets(HTML, "steveaoki")
    urls = [u for r in rows for u in r["media"]]
    assert len(urls) == len(set(urls))
    assert all("?" not in u and "name=" not in u for u in urls)


def test_tweets_without_an_image_get_an_empty_list():
    rows = {r["tweet_id"]: r for r in extract_timeline_tweets(HTML, "steveaoki")}
    assert rows[TARGET]["media"] == []


def test_retweets_carry_their_retweeter():
    rows = extract_timeline_tweets(HTML, "steveaoki")
    rts = [r for r in rows if r["retweeted_by"]]
    assert rts, "fixture contains a 'Steve Aoki Retweeted' block"
    assert rts[0]["retweeted_by"] == "Steve Aoki"
    assert rts[0]["author"] != "steveaoki"


def test_a_quote_is_not_mislabelled_as_a_retweet():
    rows = {r["tweet_id"]: r for r in extract_timeline_tweets(HTML)}
    assert rows[TARGET]["retweeted_by"] is None


def test_ids_are_unique_across_the_page():
    rows = extract_timeline_tweets(HTML)
    ids = [r["tweet_id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_a_javascript_shell_capture_yields_nothing_rather_than_raising():
    assert extract_timeline_tweets("<html><body><div id='react-root'></div></body></html>") == []
    assert extract_timeline_tweets("") == []
    assert extract_timeline_tweets(None) == []


# --- the sweep itself, with Wayback injected so this stays offline ---

class FakeWayback:
    """Two captures of one handle sharing a tweet, so dedup-across-captures is real."""
    def __init__(self, pages):
        self.pages = pages
        self.fetched = []

    def page_snapshots(self, url, from_date=None, to_date=None):
        return [{"timestamp": ts, "original": url} for ts in sorted(self.pages)]

    def fetch(self, timestamp, original):
        self.fetched.append(timestamp)
        return self.pages[timestamp]


def test_sweep_dedupes_a_tweet_seen_in_two_captures(tmp_path, monkeypatch):
    from scripts import fetch_timelines as ft
    monkeypatch.setattr(ft, "OUT", tmp_path / "out.json")
    wb = FakeWayback({"20220713175134": HTML, "20220714010101": HTML})
    rows = ft.sweep(["steveaoki"], wayback=wb)
    ids = [r["tweet_id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert TARGET in ids
    assert len(wb.fetched) == 2                      # both captures were read
    assert all(r["source"] == "wayback-timeline" for r in rows)
    assert rows[0]["capture"] == "20220713175134"    # provenance kept


def test_sweep_resumes_without_refetching_a_done_capture(tmp_path, monkeypatch):
    from scripts import fetch_timelines as ft
    monkeypatch.setattr(ft, "OUT", tmp_path / "out.json")
    pages = {"20220713175134": HTML}
    ft.sweep(["steveaoki"], wayback=FakeWayback(pages))
    again = FakeWayback(pages)
    ft.sweep(["steveaoki"], wayback=again)
    assert again.fetched == [], "an already-read capture must not be fetched twice"


def test_sweep_survives_a_capture_that_is_a_javascript_shell(tmp_path, monkeypatch):
    from scripts import fetch_timelines as ft
    monkeypatch.setattr(ft, "OUT", tmp_path / "out.json")
    wb = FakeWayback({"20220101000000": "<html><div id='react-root'></div></html>",
                      "20220713175134": HTML})
    rows = ft.sweep(["steveaoki"], wayback=wb)
    assert TARGET in [r["tweet_id"] for r in rows]


def test_enumeration_is_chunked_by_year_not_one_unbounded_request(monkeypatch):
    """An unbounded CDX query against a heavily-archived profile times out and
    degrades to an empty list, silently skipping the handle. Enumerate per year."""
    from scripts import fetch_timelines as ft
    calls = []

    class Rec:
        def page_snapshots(self, url, from_date=None, to_date=None):
            calls.append((from_date, to_date))
            return [{"timestamp": f"{from_date[:4]}0101000000", "original": url}]

    snaps = ft._enumerate(Rec(), "twitter.com/steveaoki")
    assert len(calls) == len(ft.YEARS), "one request per year"
    assert all(f and t for f, t in calls), "every request is date-bounded"
    assert len(snaps) == len(ft.YEARS)


def test_enumeration_honours_an_explicit_range_as_a_single_request():
    from scripts import fetch_timelines as ft
    calls = []

    class Rec:
        def page_snapshots(self, url, from_date=None, to_date=None):
            calls.append((from_date, to_date))
            return []

    ft._enumerate(Rec(), "twitter.com/x", "20220101", "20220131")
    assert calls == [("20220101", "20220131")]


def test_enumeration_survives_one_bad_year(monkeypatch):
    from scripts import fetch_timelines as ft

    class Flaky:
        def page_snapshots(self, url, from_date=None, to_date=None):
            if from_date.startswith("2021"):
                raise RuntimeError("timeout")
            return [{"timestamp": f"{from_date[:4]}0101000000", "original": url}]

    snaps = ft._enumerate(Flaky(), "twitter.com/x")
    assert len(snaps) == len(ft.YEARS) - 1, "a failed year must not abort the rest"
