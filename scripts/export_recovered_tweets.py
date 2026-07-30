"""Export the timeline-capture recoveries to tracked evidence.

Sources, both optional:
  data/raw/tweets_timeline_recovered.json   the sweep (scripts/fetch_timelines.py)
  data/raw/tweets_timeline_manual.json      the first capture, read by hand

Run: python -m scripts.export_recovered_tweets
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.config import METAZOO_PROMO_TERMS

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "evidence" / "recovered_tweets.json"
RELEVANT_OUT = ROOT / "data" / "evidence" / "recovered_tweets_metazoo.json"
SOURCES = ["tweets_timeline_recovered.json", "tweets_timeline_manual.json"]
HEADLINE_ID = "1547039229795962880"
METAZOO_ACCOUNT_HANDLES = {"metazoogames", "metazoohq", "metazoo_games",
                           "metazooxyz", "metazoomarket"}


def _load(name):
    p = RAW / name
    return json.loads(p.read_text()) if p.exists() else []


def prior_ids():
    """Every tweet id the pre-existing archives already hold, so the export can say
    honestly how many of these are genuinely new rather than re-found."""
    ids = set()
    for name in ("tweets_aoki_deleted.json", "tweets_metazoo_archived.json",
                 "tweets_metazoo.json", "tweets_influencers.json"):
        for r in _load(name):
            t = r.get("tweet_id") or r.get("id")
            if t:
                ids.add(str(t))
    return ids


FILLABLE = ("text", "media")


def collect(rows, known=None):
    """Dedupe by tweet id and sort by post time. The same tweet appears in many
    captures of the same timeline, and two rows for it are partial observations of
    one thing rather than rivals."""
    known = known or set()
    by_id = {}
    for r in rows:
        tid = r.get("tweet_id")
        if not tid:
            continue
        prev = by_id.get(tid)
        if prev is None:
            by_id[tid] = dict(r)
            continue
        for f in FILLABLE:
            if not prev.get(f) and r.get(f):
                prev[f] = r[f]
    out = []
    for tid, r in by_id.items():
        out.append({**r, "new_to_archive": tid not in known})
    return sorted(out, key=lambda r: r.get("timestamp") or "")


def is_relevant(row) -> bool:
    """Uses the BROAD recall term list, not the tight classifier one: this file
    selects evidence to read, where a false positive costs a skim and a false
    negative loses the tweet."""
    text = (row.get("text") or "").lower()
    if any(t in text for t in METAZOO_PROMO_TERMS):
        return True
    if (row.get("author") or "").lower() in METAZOO_ACCOUNT_HANDLES:
        return True
    return "metazoo" in (row.get("retweeted_by") or "").lower()


def select_relevant(tweets):
    """Relevant rows plus the other half of any quote pair, so a quote-tweet keeps
    the tweet it quotes (and vice versa)."""
    by_id = {r["tweet_id"]: r for r in tweets}
    keep = {r["tweet_id"] for r in tweets if is_relevant(r)}
    for tid in list(keep):
        quoted = by_id[tid].get("quoted_id")
        if quoted in by_id:
            keep.add(quoted)
    for r in tweets:
        if r.get("quoted_id") in keep:
            keep.add(r["tweet_id"])
    return [r for r in tweets if r["tweet_id"] in keep]


def build():
    rows = []
    for name in SOURCES:
        rows += _load(name)
    known = prior_ids()
    tweets = collect(rows, known)
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": ("Read out of archived Wayback captures of profile timelines "
                   "(twitter.com/<handle>), which server-render dozens of tweets per "
                   "page, rather than one tweet per /status/ snapshot."),
        "counts": {
            "tweets": len(tweets),
            "retweets": sum(1 for t in tweets if t.get("retweeted_by")),
            "quotes": sum(1 for t in tweets if t.get("quoted_id")),
            "new_to_archive": sum(1 for t in tweets if t["new_to_archive"]),
            "captures_read": len({t.get("capture") for t in tweets if t.get("capture")}),
        },
        "headline": next((t for t in tweets if t["tweet_id"] == HEADLINE_ID), None),
        "tweets": tweets,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False))

    rel = select_relevant(tweets)
    rel_doc = {
        "generated_at": doc["generated_at"],
        "source": OUT.name,
        "relevance": ("Rows whose text carries a MetaZoo recall term, or written by "
                      "a MetaZoo account, or retweeted by MetaZoo, plus the other "
                      "half of any quote pair. Derived from the full export; regenerate "
                      "both with python -m scripts.export_recovered_tweets."),
        "counts": {
            "tweets": len(rel),
            "retweets": sum(1 for t in rel if t.get("retweeted_by")),
            "new_to_archive": sum(1 for t in rel if t["new_to_archive"]),
        },
        "tweets": rel,
    }
    RELEVANT_OUT.write_text(json.dumps(rel_doc, indent=1, ensure_ascii=False))

    c = doc["counts"]
    print(f"  {c['tweets']} tweets from {c['captures_read']} captures "
          f"({c['retweets']} retweets, {c['quotes']} quotes); "
          f"{c['new_to_archive']} not in any prior archive")
    print(f"  headline recovery present: {doc['headline'] is not None}")
    print(f"  wrote {OUT.relative_to(ROOT)}")
    rc = rel_doc["counts"]
    print(f"  {rc['tweets']} MetaZoo-relevant ({rc['new_to_archive']} new, "
          f"{rc['retweets']} retweets) -> {RELEVANT_OUT.relative_to(ROOT)}")
    return doc


if __name__ == "__main__":
    build()
