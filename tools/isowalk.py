# -*- coding: utf-8 -*-
"""Minimal ISO9660 directory walk, importable."""
import struct

SEC = 2048


def walk(iso):
    """[(path, lba, size)] for every file, sorted by offset."""
    out = []
    with open(iso, 'rb') as f:
        def sect(lba, n=1):
            f.seek(lba * SEC)
            return f.read(SEC * n)

        pvd = sect(16)
        assert pvd[1:6] == b'CD001'
        root = pvd[156:190]
        stack = [(struct.unpack('<I', root[2:6])[0],
                  struct.unpack('<I', root[10:14])[0], '')]
        while stack:
            lba, ln, path = stack.pop()
            data = sect(lba, (ln + SEC - 1) // SEC)
            off = 0
            while off < ln:
                rl = data[off]
                if rl == 0:
                    off = (off // SEC + 1) * SEC
                    continue
                rec = data[off:off + rl]
                e_lba = struct.unpack('<I', rec[2:6])[0]
                e_len = struct.unpack('<I', rec[10:14])[0]
                isdir = bool(rec[25] & 0x02)
                name = rec[33:33 + rec[32]]
                off += rl
                if len(name) == 1 and name in (b'\x00', b'\x01'):
                    continue
                nm = name.decode('latin-1').split(';')[0]
                full = path + '/' + nm
                if isdir:
                    stack.append((e_lba, e_len, full))
                else:
                    out.append((full, e_lba, e_len))
    out.sort(key=lambda x: x[1])
    return out
