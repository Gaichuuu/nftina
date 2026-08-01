import json
import re
from pathlib import Path

CONTENT = Path(__file__).parent.parent / "data" / "evidence" / "collection_content.json"
SLUGS = ["coin_tokens", "beasties_s1", "genesis_2021", "pfp_2",
         "valentines", "genesis_reissue_1155", "aoki",
         "wilderness", "tournament_prizes", "mothman_1of1", "sandbox"]
BANNED = ["chapter 7", "bankrupt", "lawsuit", "complaint", "alleged", "class action",
          "trustee", "1:24-bk", "24-10874", "plaintiff", "defendant"]


def test_all_slugs_present():
    data = json.loads(CONTENT.read_text())
    assert set(data) == set(SLUGS)


def test_each_entry_shape():
    data = json.loads(CONTENT.read_text())
    for slug, c in data.items():
        assert isinstance(c["overview"], list) and c["overview"], slug
        assert all(isinstance(p, str) and p.strip() for p in c["overview"]), slug
        assert "utility" not in c, slug


def test_no_banned_terms():
    text = CONTENT.read_text().lower()
    for term in BANNED:
        assert term not in text, f"banned term in content: {term}"


def test_later_collections_present_and_clean():
    data = json.loads(CONTENT.read_text())
    for slug in ["wilderness", "tournament_prizes", "mothman_1of1", "sandbox"]:
        assert slug in data, f"missing authored content: {slug}"
        blob = json.dumps(data[slug]).lower()
        for banned in BANNED:
            assert banned not in blob, f"{slug} contains banned term: {banned}"
        assert data[slug]["overview"], f"{slug} overview empty"


def test_every_overview_ends_with_its_mint_platform():
    """The one structural rule the overviews share. Deliberately checks the PATTERN
    and not the wording of any block: the copy is authored and gets rewritten often,
    so a test that pins a phrase just breaks on the next edit."""
    data = json.loads(CONTENT.read_text())
    for slug, c in data.items():
        last = c["overview"][-1]
        assert last.startswith("**Mint platform:") and last.endswith("**"), \
            f"{slug} overview does not end with its mint-platform callout: {last!r}"


VERBATIM_SOURCE_COPY = {"coin_tokens", "beasties_s1", "pfp_2"}

_MONTH = (r"(?:January|February|March|April|May|June|July|August|September|October"
          r"|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)")
_ANY_DATE = re.compile(
    rf"\b(?:\d{{1,2}}\s+{_MONTH}\.?\s+\d{{4}}"      # 17 Jul 2021
    rf"|{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"  # March 7th, 2021
    rf"|{_MONTH}\s+\d{{4}}"                          # March 2021
    rf"|\d{{1,2}}[/.]\d{{1,2}}[/.]\d{{2,4}})\b")     # 7/15/22
_PROSE_STYLE = re.compile(rf"^{_MONTH} \d{{1,2}}(?:st|nd|rd|th), \d{{4}}$|^{_MONTH} \d{{4}}$")


def _prose_strings(entry):
    yield from entry.get("overview", [])
    for key in ("banner", "overview_image_caption"):
        if entry.get(key):
            yield entry[key]
    if entry.get("off_chain_basis"):
        yield entry["off_chain_basis"].get("note", "")


def test_prose_dates_use_one_style():
    """Our own prose writes dates as 'March 7th, 2021' (or 'March 2021' for a month).
    Quoted mint-page copy is exempt, and data columns keep ISO in the frontend."""
    data = json.loads(CONTENT.read_text())
    for slug, entry in data.items():
        if slug in VERBATIM_SOURCE_COPY:
            continue
        for text in _prose_strings(entry):
            for found in _ANY_DATE.findall(text):
                assert _PROSE_STYLE.match(found), (
                    f"{slug}: date {found!r} should read like 'March 7th, 2021'")
