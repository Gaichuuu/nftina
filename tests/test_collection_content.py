import json
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


def test_new_collections_present_and_clean():
    import json, pathlib, re
    data = json.load(open(pathlib.Path("data/evidence/collection_content.json")))
    for slug in ["wilderness", "tournament_prizes", "mothman_1of1", "sandbox"]:
        assert slug in data, f"missing authored content: {slug}"
        blob = json.dumps(data[slug]).lower()
        for banned in ["bankruptcy", "chapter 7", "lawsuit", "complaint", "plaintiff", "class action"]:
            assert banned not in blob, f"{slug} contains banned term: {banned}"
        assert data[slug]["overview"], f"{slug} overview empty"
    tp = json.dumps(data["tournament_prizes"]).lower()
    assert "trophy" in tp or "trophies" in tp
