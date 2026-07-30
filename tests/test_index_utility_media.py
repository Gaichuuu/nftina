import hashlib
import os

from scripts import index_utility_media as m
from scripts.index_utility_media import target_name, build_manifest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


def test_target_name_uses_magic_bytes_not_the_source_extension():
    assert target_name("valentines_box", JPG, "MetaZoo Valentine's Day NFT.png") == "valentines_box.jpg"


def test_target_name_falls_back_to_the_source_extension_when_unrecognized():
    assert target_name("odd", b"not-an-image", "Some Poster.WEBP") == "odd.webp"


def test_build_manifest_keys_by_id_and_keeps_the_source_name():
    products = [{"id": "valentines_box", "image_file": "MetaZoo Valentine's Day NFT.jpg"}]
    out = build_manifest(products, lambda name: JPG)
    assert out == {"valentines_box": {"file": "valentines_box.jpg",
                                      "hash": hashlib.sha1(JPG).hexdigest()[:8],
                                      "source_name": "MetaZoo Valentine's Day NFT.jpg"}}


def test_build_manifest_skips_a_product_whose_file_is_missing_and_keeps_the_rest():
    products = [{"id": "gone", "image_file": "absent.png"},
                {"id": "here", "image_file": "present.png"}]
    out = build_manifest(products, lambda name: None if name == "absent.png" else PNG)
    assert list(out) == ["here"]


def test_build_manifest_records_a_content_hash_that_tracks_the_bytes():
    one = build_manifest([{"id": "a", "image_file": "a.png"}], lambda n: PNG)
    two = build_manifest([{"id": "a", "image_file": "a.png"}], lambda n: PNG + b"x")
    assert one["a"]["hash"] != two["a"]["hash"]
    assert one["a"]["file"] == two["a"]["file"]     # same filename, different hash


def test_source_path_reads_a_bare_name_from_the_drop_folder():
    assert m.source_path("UFO box.jpg") == os.path.join(m.SRC_DIR, "UFO box.jpg")


def test_source_path_treats_a_slashed_name_as_repo_relative():
    got = m.source_path("data/media/tokens/coin_tokens/b867049a78650f37.gif")
    assert got == os.path.join(m.REPO, "data/media/tokens/coin_tokens/b867049a78650f37.gif")


def test_build_manifest_skips_a_product_with_no_image_file():
    assert build_manifest([{"id": "textonly"}], lambda name: PNG) == {}
