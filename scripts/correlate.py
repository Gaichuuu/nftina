"""Merge every tweet source into one chronological record, flag undisclosed
promotion, and correlate each tweet with the nearest mint event.

Sources (whichever exist in data/raw/):
  tweets_influencers.json        live influencer/Aoki promo (GetXAPI)
  tweets_metazoo.json            live MetaZoo-account timelines (GetXAPI)
  tweets_metazoo_archived.json   deleted @MetaZooGames, recovered (Wayback)
  tweets_aoki_deleted.json       deleted Aoki MetaZoo tweets (Wayback)
  tweets_timeline_recovered.json tweets read out of archived PROFILE captures
                                 (Wayback), the only source that reaches retweets
                                 and tweets whose own status URL was never
                                 snapshotted. See FINDINGS F44.

Outputs public/data/tweets_timeline.json and tweets_summary.json."""
import json
from pathlib import Path
from datetime import datetime, timezone

from scripts.config import TIMELINE_EVENTS, METAZOO_CORE_TERMS, METAZOO_DELETED_HANDLE
from scripts.clients.wayback import handle_from_url

RAW = Path(__file__).parent.parent / "data" / "raw"
OUT = Path(__file__).parent.parent / "public" / "data"

_HYPE = ("need", "mint", "don't miss", "buy", "grab", "get these", "get your",
         "🚀", "lfg", "must", "presale", "don't sleep", "last chance", "now live",
         "cop", "ape in", "hurry")
_DISCLOSURE = ("#ad", "#partner", "#paid", "#sponsored", "#promotion", "paid partnership")
_SNOWFLAKE_EPOCH = 1288834974657   # Twitter epoch (ms)


def is_undisclosed_promo(text: str) -> bool:
    t = (text or "").lower()
    if not any(term in t for term in METAZOO_CORE_TERMS):
        return False
    if any(d in t for d in _DISCLOSURE):
        return False
    return any(h in t for h in _HYPE)


def days_to_nearest_event(date: str, events) -> int:
    d = datetime.strptime(date[:10], "%Y-%m-%d")
    dated = [e for e in events if len(e["date"]) == 10]
    return min(abs((d - datetime.strptime(e["date"], "%Y-%m-%d")).days) for e in dated)


def snowflake_to_date(tweet_id: str):
    """Twitter IDs embed creation time; derive the post date (for archived tweets
    that only have an id)."""
    try:
        ms = (int(tweet_id) >> 22) + _SNOWFLAKE_EPOCH
    except (ValueError, TypeError):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _load(name):
    p = RAW / name
    return json.loads(p.read_text()) if p.exists() else []


def _normalize(raw: list, source: str) -> list:
    out = []
    for t in raw:
        tid = str(t.get("id") or t.get("tweet_id") or "")
        date = t.get("date") or snowflake_to_date(tid)
        if not date:
            continue
        url = t.get("url", "")
        author = t.get("author") or handle_from_url(url) or t.get("author_title", "")
        out.append({
            "id": tid,
            "date": date[:10],
            "text": t.get("text", ""),
            "author": author,
            "url": url,
            "record": t.get("record", source),
            "source": t.get("source", "getxapi"),
            "deleted": source in ("metazoo_archived", "aoki_deleted"),
            "has_media": bool(t.get("media") or t.get("image")),
        })
    return out


def build() -> dict:
    tweets = []
    tweets += _normalize(_load("tweets_influencers.json"), "influencer")
    tweets += _normalize(_load("tweets_metazoo.json"), "metazoo_live")
    tweets += _normalize(_load("tweets_metazoo_archived.json"), "metazoo_archived")
    tweets += _normalize([t for t in _load("tweets_aoki_deleted.json") if t.get("matched")], "aoki_deleted")

    timeline = _normalize(_load("tweets_timeline_recovered.json"), "timeline")
    for t in timeline:
        t["deleted"] = t["author"].lower() == METAZOO_DELETED_HANDLE.lower()
    tweets += timeline

    by_id = {}
    for t in tweets:
        if t["id"] not in by_id or (by_id[t["id"]]["deleted"] and not t["deleted"]):
            by_id[t["id"]] = t
    tweets = list(by_id.values())

    for t in tweets:
        t["is_undisclosed_promo"] = is_undisclosed_promo(t["text"])
        t["days_to_nearest_mint"] = days_to_nearest_event(t["date"], TIMELINE_EVENTS)

    events = [{"type": "mint_event", **e} for e in TIMELINE_EVENTS]
    timeline = sorted(tweets + events, key=lambda x: x.get("date", ""))

    undis = [t for t in tweets if t["is_undisclosed_promo"]]
    from collections import Counter
    by_author = Counter(t["author"] for t in undis)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tweets": len(tweets),
        "deleted_recovered": sum(1 for t in tweets if t["deleted"]),
        "undisclosed_promo_count": len(undis),
        "undisclosed_promo_deleted": sum(1 for t in undis if t["deleted"]),
        "undisclosed_by_author": dict(by_author.most_common(20)),
        "aoki_undisclosed_promo": sum(1 for t in undis if t["author"] == "steveaoki"),
        "undisclosed_examples": [
            {"date": t["date"], "author": t["author"], "deleted": t["deleted"],
             "text": t["text"][:200], "days_to_mint": t["days_to_nearest_mint"]}
            for t in sorted(undis, key=lambda x: x["days_to_nearest_mint"])[:30]],
        "disclaimer": ("Figures are estimates from public/archived data; Aoki payment "
                       "amounts are alleged, not proven."),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tweets_timeline.json").write_text(json.dumps(timeline, indent=2))
    (OUT / "tweets_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  {len(tweets)} tweets ({summary['deleted_recovered']} recovered-deleted) | "
          f"{len(undis)} undisclosed-promo ({summary['undisclosed_promo_deleted']} of them deleted)")
    print(f"  Aoki undisclosed-promo tweets: {summary['aoki_undisclosed_promo']}")
    print(f"  wrote public/data/tweets_timeline.json + tweets_summary.json")
    return summary


if __name__ == "__main__":
    build()
