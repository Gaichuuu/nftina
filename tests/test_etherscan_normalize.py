from scripts.clients.etherscan import normalize_transfer

def test_normalize_transfer_captures_gas_fields():
    raw = {"tokenID": "5", "from": "0xAaA", "to": "0xBbB", "hash": "0xh",
           "blockNumber": "100", "timeStamp": "1638", "tokenValue": "1",
           "gasUsed": "293402", "gasPrice": "155183059836"}
    t = normalize_transfer(raw, "coin_tokens", "erc721")
    assert t["gas_used"] == 293402
    assert t["gas_price"] == 155183059836

def test_normalize_transfer_gas_defaults_zero_when_absent():
    raw = {"tokenID": "5", "from": "0xAaA", "to": "0xBbB", "hash": "0xh",
           "blockNumber": "100", "timeStamp": "1638", "tokenValue": "1"}
    t = normalize_transfer(raw, "coin_tokens", "erc721")
    assert t["gas_used"] == 0 and t["gas_price"] == 0
