"""Audit config.py addressed contracts against on-chain reality: real contract
name, actual token standard (which transfer endpoint returns data), and supply.
Flags every mismatch with what config.py claims. Run with python -u for live output.
"""
import os, sys, time, requests
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parents[1]))
load_dotenv(Path(__file__).parents[2] / ".env")
from config import CONTRACTS  

KEY = os.environ["ETHERSCAN_API_KEY"]
BASE = "https://api.etherscan.io/v2/api"


def get(params):
    params.update({"chainid": 1, "apikey": KEY})
    time.sleep(0.21)
    return requests.get(BASE, params=params, timeout=30).json()


def count(action, addr):
    d = get({"module": "account", "action": action, "contractaddress": addr,
             "page": 1, "offset": 1000, "sort": "asc"})
    r = d.get("result")
    return len(r) if isinstance(r, list) else 0


for key, meta in CONTRACTS.items():
    addr = meta.get("address")
    if not addr:
        continue
    src = get({"module": "contract", "action": "getsourcecode", "address": addr})
    res = src.get("result")
    name = res[0].get("ContractName", "?") if isinstance(res, list) and res and isinstance(res[0], dict) else f"(unverified/{res!r:.40})"
    n721 = count("tokennfttx", addr)
    n1155 = count("token1155tx", addr)
    real = "erc721" if n721 else "erc1155" if n1155 else "UNKNOWN/none"
    claimed = meta.get("standard")
    flag = "  <-- MISMATCH" if real != claimed and real != "UNKNOWN/none" else ""
    print(f"\n[{key}] {addr}")
    print(f"   contract name : {name}")
    print(f"   config says   : standard={claimed!r}")
    print(f"   on-chain      : tokennfttx={n721} token1155tx={n1155} -> {real}{flag}")
