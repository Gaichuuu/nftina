"""Classify the 0x3dd341-created tokens on the Mintable Gasless Store.

Reads data/raw/mintable_early_transfers.json (produced by fetch_shared), resolves
each distinct token's metadata name via Alchemy, and writes the TRACKED evidence
map data/evidence/mintable_mzg_classification.json:

    {"source": {...}, "tokens": {token_id: {"name": str|None, "mzg": bool}}}

Run as a module after fetch_shared:  python -m scripts.classify_mintable
"""
import os
import re
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
from scripts.config import CONTRACTS

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
OUT_PATH = ROOT / "data" / "evidence" / "mintable_mzg_classification.json"

ARTICLE_COUNTS = {
    "Sinkhole Sam": 10, "Mothman": 16, "Sewer Gator": 25, "Jersey Devil": 25,
    "Quetzalcoathlus": 25, "Flatwoods Monster": 25, "Batsquatch": 25,
    "Joint Snake": 49, "Hoop Snake": 50, "Squonk": 50, "Gee-Gee Bird": 50,
    "Salem's Witches": 50, "River Dino": 75, "Piasa Bird": 100, "Hodag": 100,
    "Bigfoot": 100, "Chupacabra": 100,
}

_MZG_RE = re.compile(r"^\s*MZG\b", re.IGNORECASE)


def is_mzg(name) -> bool:
    return bool(name) and bool(_MZG_RE.match(name))


def cryptid_of(name):
    """'MZG Sewer Gator #12' -> 'Sewer Gator'; None for non-MZG names."""
    if not is_mzg(name):
        return None
    rest = _MZG_RE.sub("", name).strip()
    rest = re.sub(r"\s*#?\d+\s*$", "", rest).strip()
    return rest or None


def summarize_counts(tokens: dict) -> dict:
    counts = {}
    for entry in tokens.values():
        c = cryptid_of(entry.get("name")) if entry.get("mzg") else None
        if c:
            counts[c] = counts.get(c, 0) + 1
    return counts


def main() -> None:
    from scripts.clients.alchemy import Alchemy
    al_key = os.environ.get("ALCHEMY_API_KEY")
    if not al_key:
        print("ERROR: ALCHEMY_API_KEY must be set")
        sys.exit(1)
    transfers_path = RAW / "mintable_early_transfers.json"
    if not transfers_path.exists():
        print("ERROR: run `python -m scripts.fetch_shared --contract mintable_early` first")
        sys.exit(1)
    contract = CONTRACTS["mintable_early"]["address"]
    ids = sorted({t["token_id"] for t in json.loads(transfers_path.read_text())})
    print(f"[classify] {len(ids)} distinct 0x3dd341-created tokens on the gasless store")

    al = Alchemy(al_key)
    tokens = {}
    if OUT_PATH.exists():
        tokens = json.loads(OUT_PATH.read_text()).get("tokens", {})
    for i, tid in enumerate(ids):
        if tid in tokens:
            continue
        meta = al.token_metadata(contract, tid) or {}
        name = meta.get("name")
        tokens[tid] = {"name": name, "mzg": is_mzg(name)}
        if i and i % 25 == 0:
            OUT_PATH.write_text(json.dumps(_doc(tokens), indent=1))
            print(f"  {i}/{len(ids)}…")
    OUT_PATH.write_text(json.dumps(_doc(tokens), indent=1))

    mzg = {t: e for t, e in tokens.items() if e["mzg"]}
    other_names = sorted({e["name"] or "<no name>" for e in tokens.values() if not e["mzg"]})
    counts = summarize_counts(tokens)
    print(f"[classify] MZG: {len(mzg)} tokens across {len(counts)} cryptids; "
          f"non-MZG: {len(tokens) - len(mzg)} ({', '.join(other_names) or 'none'})")
    print("cryptid            found  article")
    for c in sorted(set(counts) | set(ARTICLE_COUNTS)):
        print(f"  {c:<18} {counts.get(c, 0):>5}  {ARTICLE_COUNTS.get(c, '—'):>7}")


def _doc(tokens: dict) -> dict:
    return {
        "source": {
            "contract": CONTRACTS["mintable_early"]["address"],
            "creator": CONTRACTS["mintable_early"]["distributor"],
            "method": "fetch_shared distributor sweep + creator-encoded filter; "
                      "names via Alchemy getNFTMetadata; mzg = name starts with the word MZG",
        },
        "tokens": dict(sorted(tokens.items())),
    }


if __name__ == "__main__":
    main()
