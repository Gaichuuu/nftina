"""Pure-Python Keccak-256 (the Ethereum variant). 
Self-contained so ENS namehashing needs no C extension / web3
dependency. Verified against the standard empty-string and "abc" vectors in
tests/test_keccak.py."""

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [
    [0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56], [27, 20, 39, 8, 14],
]
_MASK = (1 << 64) - 1
_RATE = 136   # bytes, for Keccak-256 (r = 1088 bits)


def _rotl(x, n):
    return ((x << n) | (x >> (64 - n))) & _MASK


def _keccak_f(S):
    for rnd in range(24):
        C = [S[x][0] ^ S[x][1] ^ S[x][2] ^ S[x][3] ^ S[x][4] for x in range(5)]
        D = [C[(x - 1) % 5] ^ _rotl(C[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                S[x][y] ^= D[x]
        B = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                B[y][(2 * x + 3 * y) % 5] = _rotl(S[x][y], _ROT[x][y])
        for x in range(5):
            for y in range(5):
                S[x][y] = B[x][y] ^ ((~B[(x + 1) % 5][y]) & B[(x + 2) % 5][y])
        S[0][0] ^= _RC[rnd]
    return S


def keccak256(data: bytes) -> bytes:
    """Keccak-256 digest (32 bytes) of `data`."""
    S = [[0] * 5 for _ in range(5)]
    pad = bytearray(data)
    pad.append(0x01)
    while len(pad) % _RATE != 0:
        pad.append(0x00)
    pad[-1] ^= 0x80
    for off in range(0, len(pad), _RATE):
        blk = pad[off:off + _RATE]
        for i in range(_RATE // 8):
            S[i % 5][i // 5] ^= int.from_bytes(blk[i * 8:i * 8 + 8], "little")
        _keccak_f(S)
    out = bytearray()
    while len(out) < 32:
        for i in range(_RATE // 8):
            out += S[i % 5][i // 5].to_bytes(8, "little")
        if len(out) < 32:
            _keccak_f(S)
    return bytes(out[:32])


def namehash(name: str) -> bytes:
    """ENS namehash of a (already-normalized) dotted name; b'\\x00'*32 for ''."""
    node = b"\x00" * 32
    if name:
        for label in reversed(name.split(".")):
            node = keccak256(node + keccak256(label.encode()))
    return node
