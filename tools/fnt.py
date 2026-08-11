"""Level-5 FNTP (.xf font metadata) reader.

Header (0x28 bytes, little-endian):
  0x00 "FNTP" + "01"
  0x08 u32 textureCount            (2 for nrm_*, 5 for dbg -- matches the .xi count)
  0x0C u16 lineHeight, u16 baseline
  0x10 u16 lineHeight2, u16 ?
  0x14 u32 0,  0x18 u32 0
  0x1C u16 sizeTableOffset>>2   0x1E u16 sizeTableCount    (4 bytes/entry)
  0x20 u16 largeTableOffset>>2  0x22 u16 largeTableCount   (8 bytes/entry)
  0x24 u16 smallTableOffset>>2  0x26 u16 smallTableCount   (8 bytes/entry)

Each of the three blocks begins with a Level-5 compression header
((decompressedSize << 3) | method); here method 3 = Huffman8, 1 = LZ10.

Size entry (4 bytes):  int8 offsetX, int8 offsetY, u8 width, u8 height
  Deduplicated glyph bounding boxes, sorted by (height, width) and shared
  by both char tables. offsetX may be negative.

Char entry (8 bytes):  u16 charCode    UTF-16; table sorted ascending (binary search)
                       u16 packed  -> sizeIndex = packed & 0x3FF   (index into size table)
                                      advance   = packed >> 10
                       u32 packed2 -> texture = p & 0xF
                                      x       = (p >> 4)  & 0x1FF
                                      y       = (p >> 18) & 0x1FF
  Bits 13-17 and 27-31 of packed2 are not yet identified.
"""
import struct
from imgp import l5_decompress


def parse(data):
    tex_count = struct.unpack('<I', data[0x08:0x0C])[0]
    f = struct.unpack('<8H', data[0x0C:0x1C])
    h = struct.unpack('<6H', data[0x1C:0x28])
    sz_off, sz_cnt, lg_off, lg_cnt, sm_off, sm_cnt = h

    sizes = []
    if sz_cnt:
        raw = l5_decompress(data[sz_off * 4:])
        for i in range(sz_cnt):
            ox, oy, w, hh = struct.unpack('<bbBB', raw[i * 4:i * 4 + 4])
            sizes.append((ox, oy, w, hh))

    def chars(off, cnt):
        out = []
        if not cnt:
            return out
        raw = l5_decompress(data[off * 4:])
        for i in range(cnt):
            code, packed, p2 = struct.unpack('<HHI', raw[i * 8:i * 8 + 8])
            out.append({
                'code': code,
                'size': packed & 0x3FF,
                'advance': packed >> 10,
                'tex': p2 & 0xF,
                'x': (p2 >> 4) & 0x1FF,
                'y': (p2 >> 18) & 0x1FF,
                'mid': (p2 >> 13) & 0x1F, 'hi': p2 >> 27,
            })
        return out

    return {
        'textures': tex_count,
        'fields': f,
        'sizes': sizes,
        'large': chars(lg_off, lg_cnt),
        'small': chars(sm_off, sm_cnt),
    }


if __name__ == '__main__':
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else 'nrm_main'
    d = open(r'D:\psp\타임트레블러즈\extract\fnt\%s\FNT.bin' % name, 'rb').read()
    r = parse(d)
    print('%s: textures=%d  sizes=%d  large=%d  small=%d  fields=%s'
          % (name, r['textures'], len(r['sizes']), len(r['large']), len(r['small']), r['fields']))
    for label in ('large', 'small'):
        t = r[label]
        if not t:
            continue
        codes = [c['code'] for c in t]
        print('  %s: codes 0x%04X..0x%04X  sorted=%s  tex set=%s  x<=%d y<=%d'
              % (label, min(codes), max(codes), codes == sorted(codes),
                 sorted({c['tex'] for c in t}),
                 max(c['x'] for c in t), max(c['y'] for c in t)))
        s = ''.join(chr(c['code']) for c in t[:60])
        print('   first 60:', s)
