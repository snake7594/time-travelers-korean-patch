"""Level-5 XPCK archive reader.

Header (0x14):
  0x00 char[4] "XPCK"
  0x04 u16     fileCount (& 0x0FFF)
  0x06 u16     fileInfoOffset   >> 2
  0x08 u16     filenameTableOffset >> 2
  0x0A u16     dataOffset       >> 2
  0x0C u16     fileInfoSize     >> 2
  0x0E u16     filenameTableSize >> 2
  0x10 u32     dataSize         >> 2

FileInfo (0x0C each):
  u32 crc32(name)
  u16 nameOffset  (into filename table)
  u16 offsetLo    (offset = (offsetHi<<16 | offsetLo) << 2, relative to dataOffset)
  u16 sizeLo      (size   = sizeHi<<16 | sizeLo)
  u8  offsetHi
  u8  sizeHi
"""
import struct, sys, os


def l5_decompress(buf):
    """Level-5 compression: u32 header = (decompressedSize << 3) | method."""
    hdr = struct.unpack('<I', buf[:4])[0]
    method, size = hdr & 7, hdr >> 3
    body = buf[4:]
    if method == 0:                       # stored
        return body[:size]
    if method == 1:                       # LZ10 (LZSS, Nintendo style)
        out = bytearray()
        p = 0
        while len(out) < size and p < len(body):
            flags = body[p]; p += 1
            for bit in range(8):
                if len(out) >= size:
                    break
                if flags & (0x80 >> bit):
                    b0, b1 = body[p], body[p + 1]; p += 2
                    length = (b0 >> 4) + 3
                    disp = (((b0 & 0xF) << 8) | b1) + 1
                    for _ in range(length):
                        out.append(out[-disp])
                else:
                    out.append(body[p]); p += 1
        return bytes(out[:size])
    raise NotImplementedError('L5 compression method %d' % method)


def parse(data):
    assert data[:4] == b'XPCK', data[:4]
    cnt = struct.unpack('<H', data[4:6])[0] & 0x0FFF
    info_off, name_off, data_off, info_sz, name_sz = [
        v << 2 for v in struct.unpack('<HHHHH', data[6:16])]
    name_tbl = l5_decompress(data[name_off:name_off + name_sz])

    files = []
    for i in range(cnt):
        p = info_off + i * 0x0C
        h, noff, olo, slo, ohi, shi = struct.unpack('<IHHHBB', data[p:p + 0x0C])
        end = name_tbl.index(b'\x00', noff)
        name = name_tbl[noff:end].decode('ascii')
        off = ((ohi << 16) | olo) << 2
        size = (shi << 16) | slo
        files.append({
            'name': name, 'hash': h,
            'offset': data_off + off, 'size': size,
            'data': data[data_off + off: data_off + off + size],
        })
    return files


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    data = open(src, 'rb').read()
    for e in parse(data):
        out = os.path.join(dst, e['name'])
        open(out, 'wb').write(e['data'])
        print('  %-12s %8d bytes  @0x%06X  magic=%s' % (
            e['name'], e['size'], e['offset'],
            e['data'][:4].hex(' ')))
