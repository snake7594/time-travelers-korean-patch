# -*- coding: utf-8 -*-
"""Overwrite every CJK ideograph glyph of a font with one Hangul letter.

Sizes are preserved end to end (the Huffman block is re-encoded with the
original tree and zero-padded back to its original length), so the patched
.xi / .xf / CPK / ISO all keep byte-identical layout -- the ISO is patched
in place rather than rebuilt.
"""
import struct, os
import numpy as np
from PIL import Image, ImageFont, ImageDraw

import fnt, imgp, xpck, l5enc

FONT_DIR = r'D:\psp\타임트레블러즈\extract\fnt'
TTF = r'C:\Windows\Fonts\malgunbd.ttf'
CJK = lambda c: 0x4E00 <= c <= 0x9FFF or 0x3400 <= c <= 0x4DBF

_mask_cache = {}


def hangul_mask(ch, w, h):
    """Return an (h, w) array of 4-bit coverage for `ch`, scaled to fit."""
    key = (ch, w, h)
    if key in _mask_cache:
        return _mask_cache[key]
    size = max(h * 2, 8)
    f = ImageFont.truetype(TTF, size)
    tmp = Image.new('L', (size * 2, size * 2), 0)
    ImageDraw.Draw(tmp).text((size // 2, size // 2), ch, font=f, fill=255, anchor='mm')
    bb = tmp.getbbox()
    if bb is None:
        return np.zeros((h, w), np.uint8)
    g = tmp.crop(bb).resize((w, h), Image.LANCZOS)
    m = (np.asarray(g, np.uint8).astype(np.uint16) * 15 // 255).astype(np.uint8)
    _mask_cache[key] = m
    return m


def unswizzle(sw, wb, H):
    lin = bytearray(len(sw)); si = 0
    for by in range(H // 8):
        for bx in range(wb // 16):
            for y in range(8):
                d = (by * 8 + y) * wb + bx * 16
                lin[d:d + 16] = sw[si:si + 16]; si += 16
    return lin


def swizzle(lin, wb, H):
    sw = bytearray(len(lin)); si = 0
    for by in range(H // 8):
        for bx in range(wb // 16):
            for y in range(8):
                s = (by * 8 + y) * wb + bx * 16
                sw[si:si + 16] = lin[s:s + 16]; si += 16
    return sw


def patch_xi(data, boxes, ch):
    """boxes: list of (x, y, w, h) atlas rectangles to overwrite with `ch`."""
    w, _ = struct.unpack('<HH', data[0x10:0x14])
    t_off, t_sz, p_off, p_sz = struct.unpack('<IIII', data[0x40:0x50])
    tiles = imgp.l5_decompress(data[0x58 + t_off:0x58 + t_off + t_sz])
    pblk = data[0x58 + p_off:0x58 + p_off + p_sz]
    pix = bytearray(imgp.l5_decompress(pblk))
    idx = struct.unpack('<%dH' % (len(tiles) // 2), tiles)

    sw = bytearray()
    for i in idx:
        sw += bytes(32) if i == 0xFFFF else pix[i * 32:i * 32 + 32]
    wb, H = w // 2, len(sw) // (w // 2)
    lin = unswizzle(sw, wb, H)

    a = np.frombuffer(bytes(lin), np.uint8)
    nib = np.empty(a.size * 2, np.uint8)
    nib[0::2] = a & 0xF; nib[1::2] = a >> 4
    nib = nib.reshape(H, w)

    for (x, y, gw, gh) in boxes:
        if gw <= 0 or gh <= 0 or y + gh > H or x + gw > w:
            continue
        nib[y:y + gh, x:x + gw] = hangul_mask(ch, gw, gh)

    flat = nib.reshape(-1)
    packed = (flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes()
    sw2 = swizzle(bytearray(packed), wb, H)

    lost = 0
    for i, t in enumerate(idx):
        chunk = sw2[i * 32:i * 32 + 32]
        if t == 0xFFFF:
            if any(chunk):
                lost += 1
            continue
        pix[t * 32:t * 32 + 32] = chunk

    newblk = l5enc.block(bytes(pix), l5enc.tree_of(pblk))
    if len(newblk) > p_sz:
        raise RuntimeError('recompressed pixel block too big: %d > %d' % (len(newblk), p_sz))
    newblk += bytes(p_sz - len(newblk))
    out = bytearray(data)
    out[0x58 + p_off:0x58 + p_off + p_sz] = newblk
    return bytes(out), len(newblk) - (p_sz - (p_sz - len(newblk))), lost, p_sz


def build(name, ch):
    base = os.path.join(FONT_DIR, name)
    meta = fnt.parse(open(os.path.join(base, 'FNT.bin'), 'rb').read())
    per_tex = {}
    n = 0
    for table in ('large', 'small'):
        for c in meta[table]:
            if not CJK(c['code']):
                continue
            ox, oy, gw, gh = meta['sizes'][c['size']]
            if not gw or not gh:
                continue
            per_tex.setdefault(c['tex'], []).append((c['x'], c['y'], gw, gh))
            n += 1
    print('  %s -> %r : %d glyph boxes across textures %s'
          % (name, ch, n, sorted(per_tex)))
    result = {}
    for t, boxes in sorted(per_tex.items()):
        f = os.path.join(base, '%03d.xi' % t)
        data = open(f, 'rb').read()
        new, used, lost, slot = patch_xi(data, boxes, ch)
        print('     %03d.xi: %d boxes, block %d/%d bytes%s'
              % (t, len(boxes), used, slot, ', %d chunks lost' % lost if lost else ''))
        result[t] = new
    return result
