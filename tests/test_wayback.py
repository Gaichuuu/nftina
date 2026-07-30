from scripts.clients.wayback import tweet_id_from_url, handle_from_url, extract_tweet, _og


def test_tweet_id_and_handle_from_url():
    u = "https://twitter.com/steveaoki/status/1465342289039925257"
    assert tweet_id_from_url(u) == "1465342289039925257"
    assert handle_from_url(u) == "steveaoki"
    assert tweet_id_from_url("https://twitter.com/steveaoki") is None


def test_og_extraction():
    html = ('<meta property="og:description" content="Steve Aoki on Twitter: '
            '&quot;You NEED these @MetaZooGames NFTs!&quot;">'
            '<meta content="https://pbs.twimg.com/media/abc.jpg" property="og:image">')
    assert "MetaZooGames" in _og(html, "description")
    assert _og(html, "image").endswith("abc.jpg")


def test_extract_tweet_strips_wrapper_and_unescapes():
    html = ('<meta property="og:title" content="Steve Aoki">'
            '<meta property="og:description" content="Steve Aoki on Twitter: '
            '&quot;Mint the MetaZoo Mothman 1/1 on @Sothebys&quot;">'
            '<meta property="og:image" content="https://pbs.twimg.com/media/x.jpg">')
    t = extract_tweet(html)
    assert t["text"] == "Mint the MetaZoo Mothman 1/1 on @Sothebys"
    assert t["image"].endswith("x.jpg")
    assert t["author_title"] == "Steve Aoki"


def test_extract_tweet_ignores_profile_image():
    html = ('<meta property="og:description" content="x">'
            '<meta property="og:image" content="https://pbs.twimg.com/profile_images/1/a.jpg">')
    assert extract_tweet(html)["image"] is None
