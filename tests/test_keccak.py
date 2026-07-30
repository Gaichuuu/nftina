from scripts.keccak import keccak256, namehash


def test_keccak256_known_vectors():
    assert keccak256(b"").hex() == \
        "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert keccak256(b"abc").hex() == \
        "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"


def test_keccak256_multiblock_is_32_bytes_and_deterministic():
    data = b"a" * 200
    d = keccak256(data)
    assert len(d) == 32
    assert keccak256(data) == d          # deterministic
    assert keccak256(b"a" * 199) != d    # sensitive to input length


def test_namehash_root_and_eth():
    assert namehash("") == b"\x00" * 32
    assert namehash("eth").hex() == \
        "93cdeb708b7545dc668eb9280176169d1c33cfd8ed6f04690a0bcc88a93fc4ae"
