"""Minimal CRI CPK reader (UTF table parser + TOC)."""
import struct, io, sys

class UTF:
    TYPES = {0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'Q',7:'q',8:'f',9:'d',0xA:'str',0xB:'data'}
    SIZES = {0:1,1:1,2:2,3:2,4:4,5:4,6:8,7:8,8:4,9:8,0xA:4,0xB:8}

    def __init__(self, buf):
        assert buf[:4] == b'@UTF', buf[:4]
        self.buf = buf
        size = struct.unpack('>I', buf[4:8])[0]
        body = buf[8:8+size]
        self.body = body
        rows_off, strings_off, data_off = struct.unpack('>III', body[0:12])
        table_name_off, num_cols, row_len, num_rows = struct.unpack('>IHHI', body[12:24])
        self.rows_off, self.strings_off, self.data_off = rows_off, strings_off, data_off
        self.num_rows = num_rows
        self.row_len = row_len

        def s(off):
            e = body.index(b'\x00', strings_off + off)
            return body[strings_off+off:e].decode('utf-8', 'replace')

        self.name = s(table_name_off)
        # --- columns ---
        p = 24
        cols = []
        for _ in range(num_cols):
            flags = body[p]; p += 1
            nameoff = struct.unpack('>I', body[p:p+4])[0]; p += 4
            cname = s(nameoff)
            storage = flags & 0xF0
            typ = flags & 0x0F
            const = None
            if storage == 0x30:  # constant, value stored here
                const = self._read(body, p, typ, s)
                p += self.SIZES.get(typ, 8)
            cols.append((cname, typ, storage, const))
        self.cols = cols

        # --- rows ---
        self.rows = []
        for r in range(num_rows):
            p = rows_off + r * row_len
            row = {}
            for cname, typ, storage, const in cols:
                if storage == 0x30:
                    row[cname] = const
                elif storage == 0x10:
                    row[cname] = None
                else:
                    row[cname] = self._read(body, p, typ, s)
                    p += self.SIZES.get(typ, 8)
            self.rows.append(row)

    def _read(self, body, p, typ, s):
        if typ == 0xA:
            return s(struct.unpack('>I', body[p:p+4])[0])
        if typ == 0xB:
            o, l = struct.unpack('>II', body[p:p+8])
            return (self.data_off + o, l)
        fmt = '>' + self.TYPES[typ]
        return struct.unpack(fmt, body[p:p+self.SIZES[typ]])[0]


def read_chunk(f, off, magic):
    f.seek(off)
    hdr = f.read(16)
    if hdr[:4] != magic:
        return None
    size = struct.unpack('<Q', hdr[8:16])[0]
    return UTF(f.read(size))


class SubFile:
    """Read-only window into a larger file, so we can parse the CPK in-place inside the ISO."""
    def __init__(self, f, base):
        self.f, self.base, self.pos = f, base, 0
    def seek(self, off, whence=0):
        assert whence == 0
        self.pos = off
    def read(self, n):
        self.f.seek(self.base + self.pos)
        d = self.f.read(n)
        self.pos += len(d)
        return d


class CPK:
    def __init__(self, path, base=0):
        self.path = path
        self.f = open(path, 'rb') if isinstance(path, str) else path
        if base:
            self.f = SubFile(self.f, base)
        hdr = read_chunk(self.f, 0, b'CPK ')
        self.header = hdr.rows[0]
        self.files = []
        toc_off = self.header.get('TocOffset') or 0
        content_off = self.header.get('ContentOffset') or 0
        if toc_off:
            toc = read_chunk(self.f, toc_off, b'TOC ')
            base = min(toc_off, content_off) if content_off else toc_off
            for r in toc.rows:
                self.files.append({
                    'dir': r.get('DirName') or '',
                    'name': r.get('FileName') or '',
                    'size': r.get('FileSize') or 0,
                    'extract': r.get('ExtractSize') or 0,
                    'offset': base + (r.get('FileOffset') or 0),
                    'id': r.get('ID'),
                })

    def read(self, entry):
        self.f.seek(entry['offset'])
        data = self.f.read(entry['size'])
        if data[:8] == b'CRILAYLA':
            data = crilayla(data)
        return data


def crilayla(src):
    """CRILAYLA decompressor."""
    usize = struct.unpack('<I', src[8:12])[0]
    hoff = struct.unpack('<I', src[12:16])[0]
    prefix = src[16+hoff:16+hoff+0x100]
    out = bytearray(prefix) + bytearray(usize)
    # backwards bit reader over compressed block
    comp = src[16:16+hoff]
    bitpos = 0
    total_bits = len(comp) * 8

    def get_bits(n):
        nonlocal bitpos
        v = 0
        for _ in range(n):
            byte_i = len(comp) - 1 - (bitpos >> 3)
            bit_i = 7 - (bitpos & 7)
            v = (v << 1) | ((comp[byte_i] >> bit_i) & 1)
            bitpos += 1
        return v

    dest = len(out) - 1
    end = 0x100
    VLE = [2, 3, 5, 8]
    while dest >= end:
        if get_bits(1):
            offset = get_bits(13) + 3
            ref = dest + offset
            length = 3
            for i, bits in enumerate(VLE):
                d = get_bits(bits)
                length += d
                if d != (1 << bits) - 1:
                    break
            else:
                while True:
                    d = get_bits(8)
                    length += d
                    if d != 255:
                        break
            for _ in range(length):
                out[dest] = out[ref]
                dest -= 1
                ref -= 1
        else:
            out[dest] = get_bits(8)
            dest -= 1
    return bytes(out)


if __name__ == '__main__':
    c = CPK(sys.argv[1] if len(sys.argv) > 1 else r"D:\psp\tt_extract\TT1_PSP.CPK")
    print("Files:", len(c.files))
    for e in c.files:
        print("%-24s %-40s %10d %10d  @%d" % (e['dir'], e['name'], e['size'], e['extract'], e['offset']))
