# -*- coding: utf-8 -*-
"""The 8-bit variant of the Level-5 IMGP texture.

The fonts are 4bpp with a 16-colour RGBA4444 palette; the menu art is 8bpp
with 256 colours of RGBA8888. Everything else -- the tile table, the shared
64-byte chunks, the PSP swizzle of 16-byte by 8-row blocks -- is the same.

  bpp is taken from the palette count at 0x38: 16 -> 4bpp, 256 -> 8bpp.
"""
import struct
import numpy as np
from imgp import l5_decompress


def info(data):
    w, h = struct.unpack('<HH', data[0x10:0x14])
    ncol = struct.unpack('<H', data[0x38:0x3A])[0]
    t_off, t_sz, p_off, p_sz = struct.unpack('<IIII', data[0x40:0x50])
    return w, h, ncol, (t_off, t_sz, p_off, p_sz)


def palette(data):
    w, h, ncol, (t_off, _, _, _) = info(data)
    raw = l5_decompress(data[0x58:0x58 + t_off])
    if ncol == 16:
        out = []
        for i in range(16):
            v = struct.unpack('<H', raw[i * 2:i * 2 + 2])[0]
            out.append(((v & 0xF) * 17, ((v >> 4) & 0xF) * 17,
                        ((v >> 8) & 0xF) * 17, ((v >> 12) & 0xF) * 17))
        return out
    return [tuple(raw[i * 4:i * 4 + 4]) for i in range(ncol)]


def unswizzle(sw, w, bpp):
    """PSP order back to scanlines. Blocks are 16 bytes wide by 8 rows."""
    wb = w * bpp // 8
    H = len(sw) // wb
    lin = bytearray(len(sw))
    si = 0
    for by in range(H // 8):
        for bx in range(wb // 16):
            for y in range(8):
                dst = (by * 8 + y) * wb + bx * 16
                lin[dst:dst + 16] = sw[si:si + 16]
                si += 16
    return bytes(lin), H


def swizzle(lin, w, bpp):
    wb = w * bpp // 8
    H = len(lin) // wb
    out = bytearray(len(lin))
    si = 0
    for by in range(H // 8):
        for bx in range(wb // 16):
            for y in range(8):
                src = (by * 8 + y) * wb + bx * 16
                out[si:si + 16] = lin[src:src + 16]
                si += 16
    return bytes(out)


def indices(data):
    """The palette index of every pixel, as a height x width array."""
    w, h, ncol, (t_off, t_sz, p_off, p_sz) = info(data)
    bpp = 4 if ncol == 16 else 8
    chunk = 32 if bpp == 4 else 64
    tiles = l5_decompress(data[0x58 + t_off:0x58 + t_off + t_sz])
    pix = l5_decompress(data[0x58 + p_off:0x58 + p_off + p_sz])
    idx = struct.unpack('<%dH' % (len(tiles) // 2), tiles)
    sw = bytearray()
    for i in idx:
        sw += bytes(chunk) if i == 0xFFFF else pix[i * chunk:(i + 1) * chunk]
    lin, H = unswizzle(sw, w, bpp)
    a = np.frombuffer(lin, np.uint8)
    if bpp == 8:
        return a.reshape(H, w).copy(), h
    n = np.empty(a.size * 2, np.uint8)
    n[0::2] = a & 0xF
    n[1::2] = a >> 4
    return n.reshape(H, w).copy(), h


def rgba(data):
    ind, real_h = indices(data)
    pal = np.array(palette(data), np.uint8)
    return pal[ind], real_h
