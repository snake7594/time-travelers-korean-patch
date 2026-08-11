# -*- coding: utf-8 -*-
"""Random-access, on-demand decrypting view of the PGD-encrypted TT1MEM.DNS."""
import pgd

ISO = r'D:\psp\타임트레블러즈\Time Travelers.iso'
DNS_LBA = 285712
SEC = 2048


class DNSFile:
    def __init__(self, iso=ISO, lba=DNS_LBA, cache=4096):
        self.f = open(iso, 'rb')
        self.base = lba * SEC
        self.f.seek(self.base)
        self.pgd = pgd.PGD(self.f.read(0x90), 2)
        self.bs = self.pgd.block_size
        self.size = self.pgd.data_size
        self.pos = 0
        self._cache = {}
        self._order = []
        self._cap = cache

    def _block(self, i):
        b = self._cache.get(i)
        if b is not None:
            return b
        self.f.seek(self.base + self.pgd.data_offset + i * self.bs)
        b = self.pgd.decrypt_block(i, self.f.read(self.bs))
        self._cache[i] = b
        self._order.append(i)
        if len(self._order) > self._cap:
            del self._cache[self._order.pop(0)]
        return b

    def seek(self, off, whence=0):
        assert whence == 0
        self.pos = off

    def read(self, n):
        out = bytearray()
        p = self.pos
        while n > 0 and p < self.size:
            i, o = divmod(p, self.bs)
            chunk = self._block(i)[o:o + n]
            if not chunk:
                break
            out += chunk
            p += len(chunk)
            n -= len(chunk)
        self.pos = p
        return bytes(out)
