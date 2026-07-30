"""Alchemy NFT API v3 client — secondary sales (getNFTSales) + floor price
(getFloorPrice). 

A sale's economics split three ways (each `{amount: wei-string, decimals}`):
  sellerFee   -> what the seller RECEIVES (proceeds)
  royaltyFee  -> the creator/collection royalty (MetaZoo)
  protocolFee -> the marketplace fee
The buyer pays the sum. We surface all three so downstream can compute realized
P&L (proceeds vs cost) and total royalties to MetaZoo.
"""
import time
import requests
from scripts.config import ALCHEMY_NFT_BASE


def _fee_eth(fee) -> float:
    if not fee or not fee.get("amount"):
        return 0.0
    decimals = fee.get("decimals")
    decimals = 18 if decimals is None else int(decimals)   # explicit null -> default 18
    return int(fee["amount"]) / (10 ** decimals)


def parse_sales(payload: dict, collection: str) -> list:
    """Normalize an Alchemy getNFTSales payload into per-sale dicts."""
    out = []
    for s in payload.get("nftSales", []):
        proceeds = _fee_eth(s.get("sellerFee"))
        royalty = _fee_eth(s.get("royaltyFee"))
        protocol = _fee_eth(s.get("protocolFee"))
        out.append({
            "collection": collection,
            "token_id": str(s.get("tokenId", "")),
            "from": (s.get("sellerAddress") or "").lower(),
            "to": (s.get("buyerAddress") or "").lower(),
            "hash": s.get("transactionHash", ""),
            "block": int(s.get("blockNumber", 0)),
            "marketplace": s.get("marketplace", ""),
            "price_eth": round(proceeds + royalty + protocol, 10),
            "proceeds_eth": round(proceeds, 10),
            "royalty_eth": round(royalty, 10),
            "protocol_eth": round(protocol, 10),
        })
    return out


def parse_floor(payload: dict) -> dict:
    """Lowest current floor across the marketplaces Alchemy reports (ETH)."""
    floors = []
    for mp, data in (payload or {}).items():
        if not isinstance(data, dict):
            continue
        fp = data.get("floorPrice")
        if isinstance(fp, (int, float)) and fp > 0:
            floors.append(fp)
    return {"floor_eth": round(min(floors), 10) if floors else 0.0}


def normalize_ipfs(url: str) -> str:
    """ipfs://CID/path -> https gateway; pass through http(s); '' for empty."""
    if not url:
        return ""
    if url.startswith("ipfs://"):
        return "https://ipfs.io/ipfs/" + url[len("ipfs://"):].lstrip("/")
    return url


def pick_image_url(nft: dict) -> str:
    """Best image URL from an Alchemy v3 nft object (getNFTsForContract /
    getNFTMetadata). Prefer Alchemy's own cached copy, then a rendered png,
    then thumbnail, then the original, then raw token metadata."""
    img = nft.get("image") or {}
    for key in ("cachedUrl", "pngUrl", "thumbnailUrl", "originalUrl"):
        val = img.get(key)
        if val:
            return normalize_ipfs(val)
    raw_img = ((nft.get("raw") or {}).get("metadata") or {}).get("image")
    return normalize_ipfs(raw_img or "")


class Alchemy:
    def __init__(self, api_key: str, rate_delay: float = 0.1):
        self.base = f"{ALCHEMY_NFT_BASE}/{api_key}"
        self.rate = rate_delay

    def _get(self, path: str, params: dict, tries: int = 5) -> dict:
        last_exc = None
        for attempt in range(tries):
            time.sleep(self.rate)
            try:
                resp = requests.get(f"{self.base}/{path}", params=params, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                time.sleep(1.0 + attempt)
        raise last_exc

    def sales(self, contract: str) -> list:
        """All secondary sales for a contract, paginated via pageKey."""
        out, page_key = [], None
        while True:
            params = {"contractAddress": contract, "order": "asc", "limit": 1000}
            if page_key:
                params["pageKey"] = page_key
            data = self._get("getNFTSales", params)
            out.extend(parse_sales(data, contract))
            page_key = data.get("pageKey")
            if not page_key:
                break
        return out

    def sales_for_tokens(self, contract: str, token_ids) -> list:
        """Secondary sales for specific token IDs of a contract. Used for SHARED
        contracts (OPENSTORE etc.) where whole-contract sales() would return the entire
        storefront's millions of sales. getNFTSales accepts an optional tokenId filter,
        so we query per token and concatenate."""
        out = []
        for tid in token_ids:
            page_key = None
            while True:
                params = {"contractAddress": contract, "tokenId": str(tid),
                          "order": "asc", "limit": 1000}
                if page_key:
                    params["pageKey"] = page_key
                data = self._get("getNFTSales", params)
                out.extend(parse_sales(data, contract))
                page_key = data.get("pageKey")
                if not page_key:
                    break
        return out

    def floor(self, contract: str) -> dict:
        return parse_floor(self._get("getFloorPrice", {"contractAddress": contract}))

    def nfts_for_contract(self, contract: str, page_key: str | None = None) -> dict:
        """One page (<=100) of a contract's NFTs with metadata."""
        params = {"contractAddress": contract, "withMetadata": "true", "limit": 100}
        if page_key:
            params["pageKey"] = page_key
        return self._get("getNFTsForContract", params)

    def token_metadata(self, contract: str, token_id: str) -> dict:
        """Metadata for a single (contract, tokenId)."""
        return self._get("getNFTMetadata",
                         {"contractAddress": contract, "tokenId": token_id,
                          "refreshCache": "false"})

    def contract_metadata(self, contract: str) -> dict:
        """getContractMetadata (v3): contract-level info incl. openSeaMetadata
        (imageUrl logo, bannerImageUrl). Returns the raw response dict."""
        return self._get("getContractMetadata", {"contractAddress": contract})
