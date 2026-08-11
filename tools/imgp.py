"""Level-5 IMGP (PSP texture) decoder.

Layout:
  0x00 "IMGP" "00"
  0x10 u16 width, u16 height
  0x40 u32 tileTableOffset, u32 tileTableSize     (offsets relative to 0x58)
  0x48 u32 pixelDataOffset, u32 pixelDataSize
  0x58 L5-compressed 16-entry RGBA4444 palette

The image is built from 8x8 tiles: the tile table holds one u16 index per
tile position (row-major, width/8 per row); the pixel section holds the
unique tiles, 4bpp, 32 bytes each.
"""
import struct


def l5_decompress(buf):
    hdr = struct.unpack('<I', buf[:4])[0]
    method, size = hdr & 7, hdr >> 3
    body = buf[4:]
    if method == 0:
        return body[:size]
    if method == 1:
        return _lz10(body, size)
    if method in (2, 3):
        return _huffman(body, size, 4 if method == 2 else 8)
    if method == 4:
        return _rle(body, size)
    raise NotImplementedError('method %d' % method)


def _lz10(body, size):
    out = bytearray()
    p = 0
    while len(out) < size:
        flags = body[p]; p += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                b0, b1 = body[p], body[p + 1]; p += 2
                length, disp = (b0 >> 4) + 3, (((b0 & 0xF) << 8) | b1) + 1
                for _ in range(length):
                    out.append(out[-disp])
            else:
                out.append(body[p]); p += 1
    return bytes(out[:size])


def _rle(body, size):
    out = bytearray()
    p = 0
    while len(out) < size:
        f = body[p]; p += 1
        if f & 0x80:
            out += bytes([body[p]]) * ((f & 0x7F) + 3); p += 1
        else:
            n = f + 1
            out += body[p:p + n]; p += n
    return bytes(out[:size])


def _huffman(body, size, depth):
    """Nintendo-style Huffman tree walk."""
    tree_size = (body[0] + 1) * 2
    tree = body[:tree_size]
    p = tree_size
    out = bytearray()
    nibbles = []
    root = 1
    pos = root
    node = tree[root]
    while len(out) < size:
        word = struct.unpack('<I', body[p:p + 4])[0]; p += 4
        for i in range(31, -1, -1):
            bit = (word >> i) & 1
            offset = node & 0x3F
            nxt = ((pos >> 1) + offset + 1) * 2 + bit
            leaf = node & (0x40 if bit else 0x80)
            node = tree[nxt]
            if leaf:
                if depth == 8:
                    out.append(node)
                else:
                    nibbles.append(node & 0xF)
                    if len(nibbles) == 2:
                        out.append(nibbles[0] | (nibbles[1] << 4))
                        nibbles.clear()
                pos = root
                node = tree[root]
            else:
                pos = nxt
            if len(out) >= size:
                break
    return bytes(out[:size])


def decode(data):
    """Return (width, height, RGBA bytes)."""
    w, h = struct.unpack('<HH', data[0x10:0x14])
    t_off, t_sz, p_off, p_sz = struct.unpack('<IIII', data[0x40:0x50])
    base = 0x58

    pal_raw = l5_decompress(data[base:])
    pal = []
    for i in range(16):
        v = struct.unpack('<H', pal_raw[i * 2:i * 2 + 2])[0]
        r = (v & 0xF) * 17
        g = ((v >> 4) & 0xF) * 17
        b = ((v >> 8) & 0xF) * 17
        a = ((v >> 12) & 0xF) * 17
        pal.append((r, g, b, a))

    tiles = l5_decompress(data[base + t_off: base + t_off + t_sz])
    pix = l5_decompress(data[base + p_off: base + p_off + p_sz])

    # The tile table indexes 32-byte chunks of the PSP-swizzled 4bpp texture;
    # identical chunks are stored once and 0xFFFF marks an all-transparent one.
    idx = struct.unpack('<%dH' % (len(tiles) // 2), tiles)
    sw = bytearray()
    for i in idx:
        sw += bytes(32) if i == 0xFFFF else pix[i * 32: i * 32 + 32]

    wb = w // 2                      # bytes per row at 4bpp
    H = len(sw) // wb
    lin = bytearray(len(sw))
    si = 0
    for by in range(H // 8):         # PSP unswizzle: 16-byte x 8-row blocks
        for bx in range(wb // 16):
            for y in range(8):
                dst = (by * 8 + y) * wb + bx * 16
                lin[dst:dst + 16] = sw[si:si + 16]
                si += 16

    img = bytearray(w * H * 4)
    for p in range(w * H):
        b = lin[p >> 1]
        v = (b & 0xF) if p % 2 == 0 else (b >> 4)
        img[p * 4:p * 4 + 4] = bytes(pal[v])
    return w, H, bytes(img), h


if __name__ == '__main__':
    import sys, os
    from PIL import Image
    src, dst = sys.argv[1], sys.argv[2]
    data = open(src, 'rb').read()
    W, H, rgba, real_h = decode(data)
    im = Image.frombytes('RGBA', (W, H), rgba).crop((0, 0, W, real_h))
    im.save(dst)
    print('%s -> %s  (%dx%d, real height %d)' % (os.path.basename(src), dst, W, H, real_h))
