"""Level-5 Huffman8 encoder that re-uses an existing tree from the file.

Keeping the original tree means the byte->code mapping is unchanged, so
re-encoding lightly-edited data lands within a few bytes of the original
compressed size -- which is what lets us patch in place.
"""
import struct


def tree_codes(tree):
    """Walk the Nintendo-style tree and return {symbol: bitstring}."""
    codes = {}
    stack = [(1, '')]
    while stack:
        pos, code = stack.pop()
        if len(code) > 32:
            continue
        node = tree[pos]
        for bit in (0, 1):
            nxt = ((pos >> 1) + (node & 0x3F) + 1) * 2 + bit
            if nxt >= len(tree):
                continue
            if node & (0x40 if bit else 0x80):
                sym = tree[nxt]
                cur = codes.get(sym)
                if cur is None or len(cur) > len(code) + 1:
                    codes[sym] = code + str(bit)
            else:
                stack.append((nxt, code + str(bit)))
    return codes


def encode_with_tree(data, tree):
    """Return the compressed body (tree + bitstream words)."""
    codes = tree_codes(tree)
    missing = set(data) - set(codes)
    if missing:
        raise ValueError('symbols not in tree: %s' % sorted(missing)[:8])
    bits = ''.join(codes[b] for b in data)
    pad = (-len(bits)) % 32
    bits += '0' * pad
    out = bytearray(tree)
    for i in range(0, len(bits), 32):
        out += struct.pack('<I', int(bits[i:i + 32], 2))
    return bytes(out)


def block(data, tree):
    """Full Level-5 block: header + tree + bitstream, method 3 (Huffman8)."""
    return struct.pack('<I', (len(data) << 3) | 3) + encode_with_tree(data, tree)


def lz10_block(data, window=4096, effort=64):
    """Level-5 block using method 1 (LZ10).

    The Huffman path above is bound to the tree already in the file, which
    packs badly once the data changes shape. LZ10 carries no such baggage and
    the character and texture tables contain enough repetition to fit their
    original slots.
    """
    out = bytearray()
    table = {}
    i = 0
    n = len(data)
    while i < n:
        flags_at = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len, best_dist = 0, 0
            if i + 3 <= n:
                key = data[i:i + 3]
                for cand in reversed(table.get(key, ())[-effort:]):
                    dist = i - cand
                    if dist > window:
                        break
                    length = 0
                    while (length < 18 and i + length < n and
                           data[cand + length] == data[i + length]):
                        length += 1
                    if length > best_len:
                        best_len, best_dist = length, dist
                        if length == 18:
                            break
            if best_len >= 3:
                flags |= 0x80 >> bit
                out.append(((best_len - 3) << 4) |
                           (((best_dist - 1) >> 8) & 0xF))
                out.append((best_dist - 1) & 0xFF)
                step = best_len
            else:
                out.append(data[i])
                step = 1
            for k in range(i, i + step):
                if k + 3 <= n:
                    table.setdefault(data[k:k + 3], []).append(k)
            i += step
        out[flags_at] = flags
    return struct.pack('<I', (len(data) << 3) | 1) + bytes(out)


def tree_of(block_bytes):
    """Extract the tree from an existing Level-5 Huffman block."""
    body = block_bytes[4:]
    return body[:(body[0] + 1) * 2]
