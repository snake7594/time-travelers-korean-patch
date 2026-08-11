# -*- coding: utf-8 -*-
"""CRILAYLA compressor.

The decoder fills its output buffer from the end downwards and reads its
bitstream from the last byte backwards.  Reversing the data turns both into
ordinary forward operations: compress rev = data[::-1] with plain LZ77, emit
the symbols in order, then reverse the packed bytes at the end.

Layout:  "CRILAYLA" | u32 usize | u32 comp_len | comp | data[0:0x100]
         where usize = len(data) - 0x100 and the first 0x100 bytes are raw.

Match:   1 | dist-3 (13 bits) | length      (dist 3..8194, length >= 3)
Literal: 0 | byte (8 bits)
Length:  base 3, then fields of 2/3/5/8 bits; a field of all-ones means
         "continue", after the 8-bit field further 8-bit chunks follow.
"""
import struct

RAW = 0x100
MAX_DIST = 8194
MIN_DIST = 3
MIN_LEN = 3


class _Bits:
    __slots__ = ('acc', 'n', 'out')

    def __init__(self):
        self.acc = 0
        self.n = 0
        self.out = bytearray()

    def put(self, v, nb):
        self.acc = (self.acc << nb) | (v & ((1 << nb) - 1))
        self.n += nb
        while self.n >= 8:
            self.n -= 8
            self.out.append((self.acc >> self.n) & 0xFF)

    def finish(self):
        if self.n:
            self.out.append((self.acc << (8 - self.n)) & 0xFF)
            self.n = 0
        self.out.reverse()          # decoder reads from the last byte back
        return bytes(self.out)


def _put_len(b, length):
    v = length - MIN_LEN
    for nb in (2, 3, 5, 8):
        m = (1 << nb) - 1
        if v < m:
            b.put(v, nb)
            return
        b.put(m, nb)
        v -= m
    while True:
        if v < 255:
            b.put(v, 8)
            return
        b.put(255, 8)
        v -= 255


def compress(data, effort=64):
    L = len(data)
    if L <= RAW:
        raise ValueError('input must be larger than 0x100 bytes')
    n = L - RAW
    rev = data[::-1]
    b = _Bits()
    table = {}
    r = 0
    while r < n:
        best_len = 0
        best_dist = 0
        if r + MIN_LEN <= n:
            key = rev[r:r + MIN_LEN]
            lst = table.get(key)
            if lst:
                tried = 0
                for cand in reversed(lst):
                    d = r - cand
                    if d < MIN_DIST:
                        continue
                    if d > MAX_DIST:
                        break
                    tried += 1
                    if tried > effort:
                        break
                    maxl = n - r
                    l = 0
                    while l < maxl and rev[cand + l] == rev[r + l]:
                        l += 1
                    if l > best_len:
                        best_len, best_dist = l, d
        if best_len >= MIN_LEN:
            b.put(1, 1)
            b.put(best_dist - MIN_DIST, 13)
            _put_len(b, best_len)
            step = best_len
        else:
            b.put(0, 1)
            b.put(rev[r], 8)
            step = 1
        for i in range(r, r + step):
            if i + MIN_LEN <= n:
                table.setdefault(rev[i:i + MIN_LEN], []).append(i)
        r += step

    comp = b.finish()
    return b'CRILAYLA' + struct.pack('<II', n, len(comp)) + comp + data[:RAW]
