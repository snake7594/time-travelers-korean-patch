# -*- coding: utf-8 -*-
"""Level-5 .cfg.bin: read it properly instead of writing into fixed slots.

    u32 entry count
    u32 string-table offset
    u32 string-table length
    u32 string count
    entries[]:
        u32 crc32 of the entry name
        u8  parameter count
        u8  types, two bits each, low pair first: 0 string, 1 number
        u16 0xFFFF
        u32 parameters[count]      -- a string one is a table-relative offset,
                                      0xFFFFFFFF for none
    0xFF padding to a 16-byte boundary, then the strings, then 0xFF again.

Knowing where the offsets are means a string may change length: the table is
rebuilt and every offset that pointed into it is moved. `parse` returns None
for anything that does not read back byte for byte, so a file that is not
really this format falls through to the old fixed-slot path.
"""
import struct

NONE = 0xFFFFFFFF


class Cfg(object):
    def __init__(self, head, ents, base, strs, tail):
        self.head = head        # bytes before the entries (16)
        self.ents = ents        # [crc, count, types, [params]]
        self.base = base        # string-table offset in the original
        self.strs = strs        # [(offset, bytes)] in table order
        self.tail = tail        # padding length after the strings

    def index(self):
        """offset -> position in self.strs."""
        return {o: i for i, (o, _) in enumerate(self.strs)}

    def pack(self, strs=None, align=16):
        """Serialise, with `strs` (same order, any lengths) as the table."""
        strs = self.strs if strs is None else strs
        moved, blob = {}, bytearray()
        for (old, _), new in zip(self.strs, strs):
            moved[old] = len(blob)
            blob += (new[1] if isinstance(new, tuple) else new) + b'\x00'
        body = bytearray()
        for crc, cnt, types, params in self.ents:
            body += struct.pack('<IBBH', crc, cnt, types, 0xFFFF)
            body += struct.pack('<%dI' % cnt, *(
                p if (types >> (2 * j)) & 3 or p == NONE else moved[p]
                for j, p in enumerate(params)))
        base = 16 + len(body)
        body += b'\xff' * (-base % align)
        base += -base % align
        out = bytearray(self.head) + body + blob
        struct.pack_into('<III', out, 4, base, len(blob), len(strs))
        return bytes(out) + b'\xff' * (-len(out) % align)


def parse(d):
    if len(d) < 16:
        return None
    try:
        n, base, slen, cnt = struct.unpack('<4I', d[:16])
        if not (0 < n < 1 << 20) or not (16 <= base <= len(d)):
            return None
        if base + slen > len(d) or set(d[base + slen:]) - {0xFF}:
            return None
        p, ents = 16, []
        for _ in range(n):
            crc, c, t, pad = struct.unpack('<IBBH', d[p:p + 8])
            if pad != 0xFFFF:
                return None
            ents.append([crc, c, t,
                         list(struct.unpack('<%dI' % c, d[p + 8:p + 8 + c * 4]))])
            p += 8 + c * 4
        if p > base or set(d[p:base]) - {0xFF}:
            return None
        strs, q = [], base
        while q < base + slen:
            z = d.index(b'\x00', q)
            strs.append((q - base, d[q:z]))
            q = z + 1
        if len(strs) != cnt or q != base + slen:
            return None
        known = {o for o, _ in strs}
        for crc, c, t, params in ents:
            for j in range(c):
                v = params[j]
                if not (t >> (2 * j)) & 3 and v != NONE and v not in known:
                    return None
        cfg = Cfg(d[:16], ents, base, strs, len(d) - base - slen)
        # Compared without the run of 0xFF at the end: a rebuilt file is padded
        # back out to the length the archive already had for it, which is more
        # than the 16-byte alignment here would put there. The strings end in a
        # NUL, so nothing but padding is ever stripped.
        return cfg if cfg.pack().rstrip(b'\xff') == d.rstrip(b'\xff') else None
    except (struct.error, ValueError):
        return None
