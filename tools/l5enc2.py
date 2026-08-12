# -*- coding: utf-8 -*-
"""Level-5 block compression, methods 2 and 4.

`l5enc` covers stored, LZ10 and Huffman-over-bytes. The menu textures also use
two the encoder could not produce, and writing one of those blocks back in a
method the original did not use gives a file the PSP refuses -- the game dies
just before the title screen while PPSSPP shows it happily. These two fill the
gap.

    method 2   Huffman, but the leaves are nibbles: two of them make a byte,
               the first one landing in the low half. The tree is the same
               shape as method 3's, so the original block's tree is reused --
               a nibble alphabet is only sixteen symbols and a real tree
               carries all of them.
    method 4   Run-length. A flag byte with the top bit set repeats the byte
               after it (0x80 | n) means n + 3 copies; without it, f + 1 raw
               bytes follow.
"""
import collections
import heapq
import struct

import l5enc


def code_lengths(data):
    """Huffman code lengths, {symbol: bits}."""
    freq = collections.Counter(data)
    if len(freq) < 2:
        raise ValueError('a Huffman tree needs at least two symbols')
    bits = dict.fromkeys(freq, 0)
    heap = [(n, i, [s]) for i, (s, n) in enumerate(sorted(freq.items()))]
    heapq.heapify(heap)
    tie = len(heap)
    while len(heap) > 1:
        n1, _, g1 = heapq.heappop(heap)
        n2, _, g2 = heapq.heappop(heap)
        for s in g1 + g2:
            bits[s] += 1
        heapq.heappush(heap, (n1 + n2, tie, g1 + g2))
        tie += 1
    return bits


CAP = 0x3F + 1          # internal nodes a level may hold, see build_tree


def _levels(bits, freq):
    """Which symbols sit at each depth, as a list of rows of leaves.

    Huffman's own depths are the starting point, but a level that would need
    more than CAP internal nodes gets extra leaves instead, taken from the
    symbols that would otherwise have gone deeper. That shortens the level's
    internal run back to something an offset can reach.

    Pulling symbols up leaves room below them, and a slot with nothing to put
    in it still costs a group -- a tree may only have 256, which is exactly
    what a full byte alphabet already needs, so there is nothing to spare.
    Hence the second floor: keep enough symbols in hand to fill the width the
    level's internal nodes are about to open up.
    """
    order = sorted(bits, key=lambda s: (bits[s], -freq[s], s))
    spare = max(freq, key=lambda s: (freq[s], -s))   # dead slots decode to this
    rows, wide, i = [], 1, 0
    while True:
        left = len(order) - i
        if left <= 0:
            rows.append([spare] * wide)
            break
        natural = sum(1 for s in order[i:] if bits[s] == len(rows))
        take = max(wide - CAP, natural, 2 * wide - left, 0)
        take = min(take, wide, left)
        if take == wide and left > take:
            take -= 1                    # something has to carry the rest down
        row = order[i:i + take]
        i += len(row)
        rows.append(row + [spare] * (take - len(row)))
        wide = (wide - take) * 2
        if not wide:
            break
    return rows


def build_tree(data):
    """A fresh tree over `data`, or None if it will not lay out.

    A node points at its children with a six-bit group offset, so a child
    pair has to land within 63 groups of its parent -- laying the levels out
    in the obvious order blows that limit as soon as a level is wide. Putting
    each level's leaves before its internal nodes fixes it: leaves claim no
    group of their own, so the internal nodes sit at the end of their level,
    right up against the children they point at, and the offset is bounded by
    how many internal nodes the level has rather than how many nodes. That
    bound is what _levels then holds down to CAP.
    """
    freq = collections.Counter(data)
    if len(freq) < 2:
        return None
    at = _levels(code_lengths(data), freq)
    deepest = len(at) - 1

    wide = {0: 1}
    start = {0: 0, 1: 1}
    for L in range(deepest):
        wide[L + 1] = (wide[L] - len(at[L])) * 2
        if L:
            start[L + 1] = start[L] + wide[L] // 2
    ngroups = start[deepest] + wide[deepest] // 2
    if ngroups > 256:
        return None

    tree = bytearray(ngroups * 2)
    tree[0] = ngroups - 1
    for L in range(1, deepest + 1):
        for j, sym in enumerate(at[L]):
            tree[2 * (start[L] + j // 2) + j % 2] = sym
    for L in range(deepest):
        for j in range(len(at[L]), wide[L]):
            i = j - len(at[L])
            group = 0 if L == 0 else start[L] + j // 2
            here = 1 if L == 0 else 2 * group + j % 2
            off = start[L + 1] + i - group - 1
            if not 0 <= off <= 0x3F:
                return None
            tree[here] = (off | (0x80 if 2 * i < len(at[L + 1]) else 0)
                              | (0x40 if 2 * i + 1 < len(at[L + 1]) else 0))
    return bytes(tree)


def rle_body(data):
    """Method 4's body: alternating literal runs and repeats."""
    out = bytearray()
    i, n = 0, len(data)
    lit = bytearray()

    def flush():
        while lit:
            take = lit[:128]
            out.append(len(take) - 1)
            out.extend(take)
            del lit[:len(take)]

    while i < n:
        run = 1
        while run < 130 and i + run < n and data[i + run] == data[i]:
            run += 1
        if run >= 3:
            flush()
            out.append(0x80 | (run - 3))
            out.append(data[i])
            i += run
        else:
            lit.append(data[i])
            i += 1
            if len(lit) == 128:
                flush()
    flush()
    return bytes(out)


def rle_block(data):
    return struct.pack('<I', (len(data) << 3) | 4) + rle_body(data)


def nibbles(data):
    """The nibble stream method 2 codes, low half of each byte first."""
    out = bytearray()
    for b in data:
        out.append(b & 0xF)
        out.append(b >> 4)
    return bytes(out)


def _huff(data, method, tree):
    stream = nibbles(data) if method == 2 else data
    if tree is None:
        tree = build_tree(stream)
        if tree is None:
            raise ValueError('no tree lays out within the six-bit offsets')
    return (struct.pack('<I', (len(data) << 3) | method) +
            l5enc.encode_with_tree(stream, tree))


def huff4_block(data, tree=None):
    """Method 2: the nibble stream, under `tree` or a tree built for it."""
    return _huff(data, 2, tree)


def huff8_block(data, tree=None):
    """Method 3, but free to build its own tree where `l5enc.block` reuses one.

    Reusing the tree already in the file is what keeps a lightly-edited block
    near its original size, and it is the first thing to try. Once the data
    changes shape the old frequencies stop fitting -- navi.xa's pixels came
    out 26 kB against a 21 kB slot -- and a tree built for the new bytes puts
    it back under 17 kB.
    """
    return _huff(data, 3, tree)


def block(data, method, orig=None):
    """One block in `method`, borrowing `orig`'s tree when there is one to use."""
    if method == 4:
        return rle_block(data)
    if method in (2, 3):
        tree = l5enc.tree_of(orig) if orig is not None else None
        try:
            return _huff(data, method, tree)
        except ValueError:
            if tree is None:
                raise
            return _huff(data, method, None)   # the old tree lacked a symbol
    raise ValueError('method %d is not ours' % method)
