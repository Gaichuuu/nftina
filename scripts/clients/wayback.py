"""Wayback Machine client: recover deleted tweets. Two endpoints via `requests`:
  - CDX API: enumerate archived snapshots (timestamp, original url, status)
  - snapshot fetch: `/web/<ts>id_/<url>` returns the raw archived page
"""
import re
import time
import html as _html
import requests

CDX = "http://web.archive.org/cdx/search/cdx"
_ID = re.compile(r"/status(?:es)?/(\d+)")
_STATUS_URL = re.compile(r"https?://(?:twitter|x)\.com/([^/]+)/status", re.I)


def tweet_id_from_url(url: str):
    m = _ID.search(url or "")
    return m.group(1) if m else None


def handle_from_url(url: str):
    m = _STATUS_URL.search(url or "")
    return m.group(1).lower() if m else None


def _og(html: str, prop: str):
    for tag in re.findall(r"<meta\b[^>]*>", html or "", re.I):
        if re.search(r'property=["\']og:%s["\']' % prop, tag, re.I):
            m = re.search(r'content=["\'](.*?)["\']', tag, re.I | re.S)
            if m:
                return _html.unescape(m.group(1)).strip()
    return None


_TWEET_BLOCK = re.compile(r'data-testid="tweet"')
_TL_ANCHOR = re.compile(r'href="/([A-Za-z0-9_]+)/status/(\d+)"[^>]*><time dateTime="([^"]+)"')
_TL_TEXT = re.compile(r'data-testid="tweetText"[^>]*>(.*?)</div></div>', re.S)
_TL_SOCIAL = re.compile(r'data-testid="socialContext"[^>]*>(.*?)</span>\s*</a>', re.S)
_RETWEETED_BY = re.compile(r"^(.*?)\s+Retweeted$")
_TL_MEDIA = re.compile(
    r"https://pbs\.twimg\.com/(media|ext_tw_video_thumb|amplify_video_thumb)/"
    r"([A-Za-z0-9_-]+)(?:\.(jpg|jpeg|png|gif))?(?:\?format=(jpg|jpeg|png|gif))?")


def _text_of(fragment: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", fragment or "")).strip()


def _media_in(fragment: str) -> list:
    """Full-size URLs for the images in one span of markup, deduped in page order.

    An extensionless pbs.twimg URL serves the ORIGINAL, so dropping the query is
    also what upgrades a `name=small` thumbnail back to full resolution."""
    out, seen = [], set()
    for path, mid, ext1, ext2 in _TL_MEDIA.findall(fragment or ""):
        if mid in seen:
            continue
        seen.add(mid)
        ext = (ext1 or ext2 or "jpg").lower().replace("jpeg", "jpg")
        out.append(f"https://pbs.twimg.com/{path}/{mid}.{ext}")
    return out


def extract_timeline_tweets(html: str, page_handle: str = None) -> list:
    """Every tweet rendered inline in an archived PROFILE page.

    A tweet only gets its own `/status/<id>` snapshot if a crawler happened to hit
    that URL, but a single capture of `twitter.com/<handle>` server-renders dozens
    of tweets in full (2022-era Twitter put the text in `data-testid="tweetText"`
    for crawlers). That makes profile captures a second, independent source, and
    the ONLY one that reaches retweets: `twitter.com/<retweeter>/status/<rt id>`
    redirects to the original, so a retweet's own URL is never archived under the
    retweeter, while a timeline capture labels it "<Name> Retweeted".

    Returns [{tweet_id, author, timestamp, text, retweeted_by, quoted_id, media}], with
    quoted/retweeted tweets captured under their OWN author and id. A capture that
    is only a JavaScript shell yields [] rather than raising.
    """
    if not html:
        return []
    marks = [m.start() for m in _TWEET_BLOCK.finditer(html)] + [len(html)]
    out, seen = [], set()
    for start, end in zip(marks, marks[1:]):
        block = html[start:end]
        social = _TL_SOCIAL.search(block)
        rt = _RETWEETED_BY.match(_text_of(social.group(1))) if social else None
        retweeted_by = rt.group(1) if rt else None
        anchors = list(_TL_ANCHOR.finditer(block))
        quoted_id = anchors[1].group(2) if len(anchors) > 1 else None
        for n, a in enumerate(anchors):
            author, tid, ts = a.groups()
            if tid in seen:
                continue
            seen.add(tid)
            body = _TL_TEXT.search(block, a.end())
            stop = anchors[n + 1].start() if n + 1 < len(anchors) else len(block)
            out.append({
                "tweet_id": tid,
                "author": author.lower(),
                "timestamp": ts,
                "text": _text_of(body.group(1)) if body else None,
                "retweeted_by": retweeted_by if n == 0 else None,
                "quoted_id": quoted_id if n == 0 else None,
                "media": _media_in(block[a.end():stop]),
                "page_handle": (page_handle or "").lower() or None,
            })
    return out


def extract_tweet(html: str) -> dict:
    """Pull tweet text/author/image from an archived page's OG tags.
    og:description on a tweet page is like:  “Author on Twitter: "the tweet text"”.
    """
    desc = _og(html, "description") or ""
    title = _og(html, "title") or ""
    image = _og(html, "image")
    text = desc
    m = re.search(r'["“](.*)["”]\s*$', desc, re.S)   
    if m:
        text = m.group(1).strip()
    return {"text": text, "raw_description": desc, "author_title": title,
            "image": image if image and "profile_images" not in (image or "") else None}


class Wayback:
    def __init__(self, rate_delay: float = 0.5):
        self.rate = rate_delay

    def _get(self, url, params=None, tries=6, timeout=90):
        last = None
        for i in range(tries):
            try:
                time.sleep(self.rate)
                return requests.get(url, params=params, timeout=timeout,
                                    headers={"User-Agent": "Mozilla/5.0 (research archive)"})
            except requests.exceptions.RequestException as e:
                last = e
                time.sleep(3 * (i + 1))   
        raise last

    def snapshots(self, url_pattern: str, from_date=None, to_date=None) -> list:
        """Unique archived snapshots for a URL pattern -> [{timestamp, original, tweet_id}].
        Deduped to one snapshot per tweet id (earliest 200)."""
        params = {"url": url_pattern, "output": "json", "filter": "statuscode:200",
                  "fl": "timestamp,original", "collapse": "urlkey"}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        r = self._get(CDX, params)
        rows = r.json()[1:] if r.text.strip() else []
        seen, out = set(), []
        for ts, original in rows:
            tid = tweet_id_from_url(original)
            if tid and tid not in seen:
                seen.add(tid)
                out.append({"timestamp": ts, "original": original, "tweet_id": tid})
        return out

    def page_snapshots(self, url: str, from_date=None, to_date=None) -> list:
        """Every archived capture of a single page -> [{timestamp, original}].

        Deduped by CAPTURE TIMESTAMP, not by tweet id: `snapshots()` above keys on
        an id parsed out of the URL, which a profile URL has none of, so reusing it
        for a timeline would silently return nothing. Each capture is a different
        point in time showing a different slice of the timeline, so they are all
        worth fetching.
        """
        params = {"url": url, "output": "json", "filter": "statuscode:200",
                  "fl": "timestamp,original", "collapse": "timestamp:8"}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        r = self._get(CDX, params)
        rows = r.json()[1:] if r is not None and r.text.strip() else []
        seen, out = set(), []
        for ts, original in rows:
            if ts in seen:
                continue
            seen.add(ts)
            out.append({"timestamp": ts, "original": original})
        return out

    def fetch(self, timestamp: str, original: str) -> str:
        r = self._get(f"http://web.archive.org/web/{timestamp}id_/{original}")
        return r.text if r is not None else ""
