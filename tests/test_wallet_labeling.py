import json
from pathlib import Path
from scripts.wallet_labeling import load_labels, classify

def test_load_labels_lowercases_keys():
    labels = load_labels()
    assert all(k == k.lower() for k in labels)
    assert "0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb" in labels

def test_classify_known_marketplace():
    labels = {"0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb": {"label": "CryptoPunks", "type": "marketplace", "source": "x"}}
    out = classify("0xB47E3Cd837dDF8E4C57F05d70Ab865De6e193BBB", labels, is_contract=True)
    assert out == {"address": "0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb", "kind": "marketplace", "label": "CryptoPunks", "source": "x"}

def test_classify_exchange_type_maps_to_exchange_kind():
    labels = {"0xa": {"label": "Kraken 4", "type": "exchange", "source": "x"}}
    assert classify("0xA", labels, is_contract=False)["kind"] == "exchange"

def test_classify_unlabeled_contract():
    out = classify("0xdead", {}, is_contract=True)
    assert out == {"address": "0xdead", "kind": "contract", "label": "unlabeled contract", "source": "eth_getCode"}

def test_classify_unlabeled_eoa():
    out = classify("0xBEEF", {}, is_contract=False)
    assert out == {"address": "0xbeef", "kind": "eoa", "label": "unlabeled", "source": None}
