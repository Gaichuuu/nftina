"""GetXAPI client: historical tweet search (advanced_search) + user timelines.
Each tweet's `media` array carries downloadable image/video URLs.
"""
import time
import requests
from datetime import datetime
from scripts.config import GETXAPI_API, GETXAPI_SEARCH

_TW_FMT = "%a %b %d %H:%M:%S %z %Y"   # e.g. "Mon Nov 29 15:30:01 +0000 2021"


def _iso_date(created_at: str):
    if not created_at:
        return None
    try:
        return datetime.strptime(created_at, _TW_FMT).strftime("%Y-%m-%d")
    except ValueError:
        return created_at[:10] or None


def _media(tw: dict) -> list:
    out = []
    for m in tw.get("media") or []:
        url = m.get("video_url") or m.get("url")
        if url:
            out.append({"type": m.get("type", ""), "url": url,
                        "expanded_url": m.get("expanded_url", "")})
    return out


def parse_tweets(payload: dict) -> list:
    """Normalize a GetXAPI response's tweets into flat records."""
    out = []
    for tw in payload.get("tweets", []):
        author = tw.get("author") or {}
        out.append({
            "id": str(tw.get("id", "")),
            "date": _iso_date(tw.get("createdAt", "")),
            "text": tw.get("text", ""),
            "author": (author.get("userName") or "").lower(),
            "author_name": author.get("name", ""),
            "author_followers": author.get("followers", 0),
            "author_verified": bool(author.get("isVerified") or author.get("isBlueVerified")),
            "url": tw.get("url") or tw.get("twitterUrl", ""),
            "media": _media(tw),
            "is_reply": bool(tw.get("isReply")),
            "like_count": tw.get("likeCount", 0),
            "retweet_count": tw.get("retweetCount", 0),
            "quoted": tw.get("quoted_tweet"),
            "source": "getxapi",
        })
    return out


class GetXAPI:
    def __init__(self, api_key: str, rate_delay: float = 0.3):
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.rate = rate_delay

    def _get(self, path: str, params: dict, tries: int = 6) -> dict:
        for attempt in range(tries):
            time.sleep(self.rate)
            r = requests.get(f"{GETXAPI_API}{path}", params=params,
                             headers=self.headers, timeout=45)
            if r.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        return {"tweets": []}

    def search(self, query: str, max_tweets: int = 100000) -> list:
        """advanced_search over the full archive, paginated via next_cursor."""
        out, cursor = [], None
        while len(out) < max_tweets:
            params = {"q": query}
            if cursor:
                params["cursor"] = cursor
            data = self._get(GETXAPI_SEARCH, params)
            out.extend(parse_tweets(data))
            cursor = data.get("next_cursor")
            if not data.get("has_more") or not cursor:
                break
        return out

    def user_tweets(self, handle: str, since: str = "2021-01-01",
                    until: str = "2024-06-01", max_tweets: int = 100000) -> list:
        """Full timeline for a handle. GetXAPI has no working user-timeline endpoint
        (the last_tweets path 404s), so this uses advanced_search `from:` which is
        equivalent and proven. Returns [] for deleted/nonexistent accounts."""
        return self.search(f"from:{handle} since:{since} until:{until}", max_tweets=max_tweets)
