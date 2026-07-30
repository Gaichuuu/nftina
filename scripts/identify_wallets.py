"""Identify every wallet the site DISPLAYS (top ecosystem flippers +
per-collection biggest-losers/flippers tables) by ENS primary name and any
curated labels.json entry, so the site can show a public name instead of a hex
address wherever a holder or flipper appears.

Output: data/evidence/wallet_identities.json (git-tracked evidence) —
{address: {ens, ens_verified, label, source}}.

Run: python -m scripts.identify_wallets [--top N] [--force]
"""
import argparse
import json
import re
import time
from pathlib import Path

import requests

from scripts.keccak import namehash
from scripts.wallet_labeling import load_labels

ROOT = Path(__file__).resolve().parent.parent
FLIPPERS = ROOT / "public" / "data" / "flippers.json"
HOLDERS_GLOB = ROOT / "site" / "data" / "collections"
OUT = ROOT / "data" / "evidence" / "wallet_identities.json"

ENS_REGISTRY = "0x00000000000c2e074ec69a0dfb2997ba6c7d2e1e"
_SEL_RESOLVER = "0x0178b8bf"   # resolver(bytes32)
_SEL_NAME = "0x691f3431"       # name(bytes32)      -> string
_SEL_ADDR = "0x3b3b57de"       # addr(bytes32)      -> address
ALCHEMY_RPC = "https://eth-mainnet.g.alchemy.com/v2/{key}"


def _decode_string(hexresult: str) -> str:
    """ABI-decode a single dynamic `string` return value."""
    if not hexresult or hexresult == "0x":
        return ""
    b = bytes.fromhex(hexresult[2:])
    if len(b) < 64:
        return ""
    length = int.from_bytes(b[32:64], "big")
    return b[64:64 + length].decode("utf-8", "replace")


def _decode_addr(hexresult: str) -> str | None:
    if not hexresult or len(hexresult) < 66:
        return None
    addr = "0x" + hexresult[-40:]
    return None if int(addr, 16) == 0 else addr.lower()


def _resolver_of(node: bytes, call_fn) -> str | None:
    res = call_fn(ENS_REGISTRY, _SEL_RESOLVER + node.hex())
    return _decode_addr(res)


def reverse_name(addr: str, call_fn) -> str | None:
    """ENS primary name for `addr`, or None. NOT yet forward-verified."""
    node = namehash(addr[2:].lower() + ".addr.reverse")
    resolver = _resolver_of(node, call_fn)
    if not resolver:
        return None
    name = _decode_string(call_fn(resolver, _SEL_NAME + node.hex()))
    return name or None


def forward_addr(name: str, call_fn) -> str | None:
    """Resolve an ENS name forward to its address record, or None."""
    node = namehash(name)
    resolver = _resolver_of(node, call_fn)
    if not resolver:
        return None
    return _decode_addr(call_fn(resolver, _SEL_ADDR + node.hex()))


def resolve_identity(addr: str, labels: dict, call_fn) -> dict:
    """Best identity for a flipper wallet. A curated labels.json entry wins (it is
    hand-verified); otherwise a forward-VERIFIED ENS primary name; else no label.
    Returns {ens, ens_verified, label, source}."""
    a = addr.lower()
    ens = reverse_name(a, call_fn)
    verified = False
    if ens:
        fwd = forward_addr(ens, call_fn)
        verified = bool(fwd) and fwd == a
    if a in labels:
        e = labels[a]
        return {"ens": ens, "ens_verified": verified,
                "label": e["label"], "source": e.get("source", "labels.json")}
    if ens and verified:
        return {"ens": ens, "ens_verified": True, "label": ens, "source": "ENS primary (verified)"}
    return {"ens": ens, "ens_verified": verified, "label": None,
            "source": "ENS reverse set but unverified" if ens else None}


def _alchemy_key() -> str:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            m = re.match(r"ALCHEMY_API_KEY=(.*)", line.strip())
            if m and m.group(1).strip():
                return m.group(1).strip()
    import os
    key = os.environ.get("ALCHEMY_API_KEY", "").strip()
    if not key:
        raise SystemExit("ALCHEMY_API_KEY not set (in .env or environment)")
    return key


def _make_call_fn(rate_delay: float = 0.1):
    url = ALCHEMY_RPC.format(key=_alchemy_key())

    def call_fn(to: str, data: str, tries: int = 4) -> str | None:
        last = None
        for attempt in range(tries):
            time.sleep(rate_delay)
            try:
                r = requests.post(url, timeout=30, json={
                    "jsonrpc": "2.0", "id": 1, "method": "eth_call",
                    "params": [{"to": to, "data": data}, "latest"]})
                r.raise_for_status()
                return r.json().get("result")
            except requests.exceptions.RequestException as exc:
                last = exc
                time.sleep(1.0 + attempt)
        raise last

    return call_fn


def displayed_wallets(top: int) -> list:
    """Union (dedup, order-preserving) of the wallets the site shows: the top
    ecosystem flippers, then every wallet in each collection's holders.json
    (the single ranked holders table)."""
    seen, out = set(), []

    def add(addr):
        a = (addr or "").lower()
        if a and a not in seen:
            seen.add(a)
            out.append(a)

    flippers = json.loads(FLIPPERS.read_text()) if FLIPPERS.exists() else []
    for f in flippers[:top]:
        add(f["wallet"])
    for hp in sorted(HOLDERS_GLOB.glob("*/holders.json")):
        doc = json.loads(hp.read_text())
        for e in doc.get("holders", []):
            add(e["wallet"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="ENS-identify displayed wallets (flippers + holders)")
    ap.add_argument("--top", type=int, default=50, help="how many top ecosystem flippers to include")
    ap.add_argument("--force", action="store_true", help="re-resolve already-cached addresses")
    args = ap.parse_args()

    wallets = displayed_wallets(args.top)
    labels = load_labels()
    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    call_fn = _make_call_fn()

    resolved, named = dict(existing), 0
    for i, addr in enumerate(wallets, 1):
        a = addr.lower()
        if a in resolved and not args.force:
            if resolved[a].get("label"):
                named += 1
            continue
        ident = resolve_identity(a, labels, call_fn)
        resolved[a] = ident
        if ident.get("label"):
            named += 1
        print(f"  [{i}/{len(wallets)}] {a} -> {ident.get('label') or '(anon)'}"
              f"{'' if ident.get('ens_verified') or not ident.get('ens') else ' [unverified]'}")
        if i % 10 == 0:
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(resolved, indent=2))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(resolved, indent=2))
    print(f"\n  {named}/{len(wallets)} displayed wallets carry a name (ENS primary or curated label)")
    print(f"  wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
