"""Classify an address as exchange / marketplace / contract / EOA using a curated
labels.json (git-tracked) plus an eth_getCode contract flag supplied by the caller.
Pure: no network here"""
import json
from pathlib import Path

_TYPE_TO_KIND = {"exchange": "exchange", "marketplace": "marketplace",
                 "contract": "contract", "token": "contract", "defi": "contract",
                 "eoa": "eoa"}


def load_labels(path=None) -> dict:
    p = Path(path) if path else Path(__file__).parent / "labels.json"
    raw = json.loads(p.read_text())
    return {a.lower(): v for a, v in raw.items()}


def classify(address: str, labels: dict, is_contract: bool) -> dict:
    a = address.lower()
    if a in labels:
        e = labels[a]
        return {"address": a, "kind": _TYPE_TO_KIND.get(e["type"], "contract"),
                "label": e["label"], "source": e.get("source", "labels.json")}
    if is_contract:
        return {"address": a, "kind": "contract", "label": "unlabeled contract",
                "source": "eth_getCode"}
    return {"address": a, "kind": "eoa", "label": "unlabeled", "source": None}
