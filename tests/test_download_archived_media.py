from scripts.download_archived_media import archived_media_url, pick_ext


def test_archived_media_url():
    assert archived_media_url("20200702235701", "https://pbs.twimg.com/media/x.jpg") == \
        "http://web.archive.org/web/20200702235701id_/https://pbs.twimg.com/media/x.jpg"


def test_pick_ext_from_format_param():
    assert pick_ext("https://pbs.twimg.com/card_img/1/QjdNE-By?format=jpg&name=600x314") == ".jpg"
    assert pick_ext("https://pbs.twimg.com/x?format=png") == ".png"
    assert pick_ext("https://pbs.twimg.com/x?format=jpeg") == ".jpg"  # normalized


def test_pick_ext_from_url_suffix():
    assert pick_ext("https://pbs.twimg.com/media/EcBzymUWkAEPjzh.jpg:large") == ".jpg"
    assert pick_ext("https://pbs.twimg.com/media/abc.png") == ".png"


def test_pick_ext_from_content_type():
    assert pick_ext("https://pbs.twimg.com/media/noext", "image/webp") == ".webp"
    assert pick_ext("https://x/y", "image/jpeg") == ".jpg"
