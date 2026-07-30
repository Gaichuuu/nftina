import time, requests
from scripts.config import ETHERSCAN_V2_API, ETHERSCAN_CHAIN_ID

ZERO = "0x0000000000000000000000000000000000000000"
_ACTIONS = {"erc721": "tokennfttx", "erc1155": "token1155tx"}
# Etherscan free tier caps results at 1000 per request regardless of `offset`
# Pagination must treat a full 1000-record page as "there may be more".
_PAGE_SIZE = 1000


def normalize_transfer(r: dict, collection: str, standard: str) -> dict:
    return {
        "collection": collection,
        "standard": standard,
        "token_id": r.get("tokenID") or r.get("tokenId", ""),
        "from": r.get("from", "").lower(),
        "to": r.get("to", "").lower(),
        "hash": r.get("hash", ""),
        "block": int(r.get("blockNumber", 0)),
        "timestamp": int(r.get("timeStamp", 0)),
        "quantity": int(r.get("tokenValue", 1) or 1),
        "is_mint": r.get("from", "").lower() == ZERO,
        "gas_used": int(r.get("gasUsed", 0) or 0),
        "gas_price": int(r.get("gasPrice", 0) or 0),
    }


class Etherscan:
    def __init__(self, api_key: str, rate_delay: float = 0.40):  # key is 3 req/sec
        self.key = api_key
        self.rate = rate_delay
        self._code_cache = {}

    def _get(self, params: dict, tries: int = 6) -> dict:
        params.update({"chainid": ETHERSCAN_CHAIN_ID, "apikey": self.key})
        last_exc = None
        for attempt in range(tries):
            time.sleep(self.rate)
            try:
                resp = requests.get(ETHERSCAN_V2_API, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                time.sleep(1.0 + attempt)
                continue
            res = data.get("result")
            if isinstance(res, str) and "rate limit" in res.lower():
                time.sleep(1.0)
                continue
            return data
        if last_exc is not None:
            raise last_exc
        return {"result": []}

    def detect_standard(self, contract: str) -> str:
        """Probe which transfer endpoint returns data. Returns 'erc721' or 'erc1155'
        (defaults to 'erc721'). Note: shared multi-standard contracts may return both;
        callers should prefer a known-correct config value when available."""
        for std, action in _ACTIONS.items():
            d = self._get({"module": "account", "action": action,
                           "contractaddress": contract, "page": 1, "offset": 1, "sort": "asc"})
            res = d.get("result")
            if isinstance(res, list) and res:
                return std
        return "erc721"

    def _paginate_by_block(self, base: dict, label: str) -> list:
        out, seen, start = [], set(), 0
        while True:
            p = dict(base, startblock=start, endblock=99999999,
                     page=1, offset=_PAGE_SIZE, sort="asc")
            res = self._get(p).get("result", [])
            if not isinstance(res, list) or not res:
                break
            new = [r for r in res if (r["hash"], r.get("tokenID"), r.get("to")) not in seen]
            for r in new:
                seen.add((r["hash"], r.get("tokenID"), r.get("to")))
            out.extend(new)
            if len(res) < _PAGE_SIZE:
                break  
            last_block = int(res[-1]["blockNumber"])
            if last_block == start:
                print(f"  [warn] {label}: >{_PAGE_SIZE} events in block {last_block}; "
                      f"possible truncation")
                break
            start = last_block
        return out

    def token_transfers(self, contract: str, standard: str) -> list:
        action = _ACTIONS[standard]
        raw = self._paginate_by_block(
            {"module": "account", "action": action, "contractaddress": contract},
            f"{action}:{contract[:10]}")
        return [normalize_transfer(r, contract, standard) for r in raw]

    def token_transfers_for_holder(self, contract: str, standard: str, holder: str,
                                   token_ids=None) -> list:
        """Transfers of `contract` that involve `holder` (as from OR to). This is how
        we isolate a MetaZoo collection inside a SHARED lazy-mint contract (OPENSTORE,
        Sandbox, Mintable): the whole contract is millions of transfers, but the
        MetaZoo tokens were all distributed by one MetaZoo wallet, so filtering by that
        wallet's address bounds the query. When `token_ids` is given, keep only those
        IDs (drops tokens the holder merely received from unrelated creators)."""
        action = _ACTIONS[standard]
        raw = self._paginate_by_block(
            {"module": "account", "action": action,
             "contractaddress": contract, "address": holder.lower()},
            f"{action}:{contract[:10]}:{holder[:8]}")
        if token_ids is not None:
            wanted = {str(t) for t in token_ids}
            raw = [r for r in raw if str(r.get("tokenID") or r.get("tokenId", "")) in wanted]
        return [normalize_transfer(r, contract, standard) for r in raw]

    def _paginate_account(self, address: str, action: str, max_records=None) -> list:
        """Block-window paginate account txns (free tier caps 1000/request). Dedup
        the 1-block overlap; internal txns share a hash so key includes from/to/value.
        Stops early once `max_records` rows are collected (None = no limit) so a single
        exchange-scale wallet can't force an unbounded number of requests."""
        out, seen, start = [], set(), 0
        while True:
            res = self._get({"module": "account", "action": action, "address": address,
                             "startblock": start, "endblock": 99999999,
                             "page": 1, "offset": _PAGE_SIZE, "sort": "asc"}).get("result", [])
            if not isinstance(res, list) or not res:
                break
            new = []
            for r in res:
                key = (r.get("hash") or r.get("transactionHash"), r.get("from"),
                       r.get("to"), r.get("value"))
                if key in seen:
                    continue
                seen.add(key)
                new.append(r)
            out.extend(new)
            if max_records is not None and len(out) >= max_records:
                break
            if len(res) < _PAGE_SIZE:
                break
            last_block = int(res[-1]["blockNumber"])
            if last_block == start:
                print(f"  [warn] account {action} {address[:10]}: >{_PAGE_SIZE} in "
                      f"block {last_block}; possible truncation")
                break
            start = last_block
        return out

    def account_txns(self, address: str, max_records=None) -> list:
        a = address.lower()
        out = []
        for action, kind in (("txlist", "normal"), ("txlistinternal", "internal")):
            if max_records is not None and len(out) >= max_records:
                break
            remaining = None if max_records is None else max_records - len(out)
            for t in self._paginate_account(a, action, remaining):
                out.append({
                    "from": (t.get("from") or "").lower(),
                    "to": (t.get("to") or "").lower(),
                    "eth": int(t.get("value", 0)) / 1e18,
                    "hash": (t.get("hash") or t.get("transactionHash") or "").lower(),
                    "timestamp": int(t.get("timeStamp", 0)),
                    "kind": kind,
                    "is_error": t.get("isError") == "1",
                })
        return out

    def is_contract(self, address: str) -> bool:
        a = address.lower()
        if a in self._code_cache:
            return self._code_cache[a]
        code = self._get({"module": "proxy", "action": "eth_getCode",
                          "address": a, "tag": "latest"}).get("result", "0x")
        val = bool(code) and code != "0x"
        self._code_cache[a] = val
        return val

    def contract_creator(self, contract: str) -> dict:
        res = self._get({"module": "contract", "action": "getcontractcreation",
                         "contractaddresses": contract}).get("result")
        if isinstance(res, list) and res:
            return {"creator": (res[0].get("contractCreator") or "").lower() or None,
                    "tx_hash": res[0].get("txHash")}
        return {"creator": None, "tx_hash": None}

    def tx_values(self, hashes) -> dict:
        vals = {}
        hashes = list(hashes)
        for i, h in enumerate(hashes):
            d = self._get({"module": "proxy", "action": "eth_getTransactionByHash", "txhash": h})
            res = d.get("result") or {}
            wei = int(res.get("value", "0x0"), 16) if res.get("value") else 0
            vals[h] = wei / 1e18
            if i and i % 100 == 0:
                print(f"    tx_values {i}/{len(hashes)}…")
        return vals
