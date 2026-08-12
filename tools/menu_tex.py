# -*- coding: utf-8 -*-
"""Redraw the Korean into a menu texture's label sprites.

The label rectangles come from the .pvb vertex buffer (see xpvb). Each one
already contains its furigana, so clearing the whole rectangle and centring
the Korean in it takes the ruby away for free.

The art is 8bpp: a label is one grey with an alpha ramp spread over its own
palette entries, so the Korean is drawn as coverage and mapped onto the ramp
the label already uses. No palette entry is added.
"""
import struct
import numpy as np
from PIL import Image, ImageFont, ImageDraw

import imgp8, l5enc, l5enc2

TTF = r'D:\gc\rom\SRW_GC\NanumSquareNeo-cBd.ttf'
_font = {}


def font(size):
    if size not in _font:
        _font[size] = ImageFont.truetype(TTF, size)
    return _font[size]


def ramp(pal, ind, box):
    """The alpha ramp this label is drawn with, as (alpha, index) pairs."""
    x0, y0, x1, y1 = box
    used = np.unique(ind[y0:y1, x0:x1])
    rgb = {}
    for i in used:
        r, g, b, a = pal[i]
        if a:
            rgb.setdefault((r, g, b), []).append((a, int(i)))
    if not rgb:
        return None
    # The lettering, not the backdrop: take the family holding the brightest
    # opaque colour in the box. Picking the largest family instead worked
    # where the background was transparent, but on the menu strip the dark
    # backdrop outnumbers the white text and the labels came out unreadable.
    def peak(entries):
        a, i = max(entries)
        return (a > 200, sum(pal[i][:3]))
    best = max(rgb.values(), key=peak)
    return sorted(best)


def clip(ind, box):
    """`box` cut down to the part that is actually on the texture.

    A quad's uv rectangle can reach past the edge of the sheet -- several of
    the operation-guide labels do -- and writing the drawn text at its full
    height then runs off the array.
    """
    h, w = ind.shape
    x0, y0, x1, y1 = box
    return max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)


def around(ind, box, band=2):
    """The commonest index in a ring just outside `box` -- its background."""
    h, w = ind.shape
    x0, y0, x1, y1 = box
    ox0, oy0 = max(x0 - band, 0), max(y0 - band, 0)
    ox1, oy1 = min(x1 + band, w), min(y1 + band, h)
    ring = np.concatenate([
        ind[oy0:y0, ox0:ox1].ravel(), ind[y1:oy1, ox0:ox1].ravel(),
        ind[y0:y1, ox0:x0].ravel(), ind[y0:y1, x1:ox1].ravel()])
    if not ring.size:
        ring = ind[y0:y1, x0:x1].ravel()
    vals, freq = np.unique(ring, return_counts=True)
    return vals[freq.argmax()]


def draw(ind, pal, box, text, pad=1):
    """Clear the rectangle and centre `text` in it."""
    box = clip(ind, box)
    x0, y0, x1, y1 = box
    if x1 - x0 < 6 or y1 - y0 < 6:
        return False
    ramp_ = ramp(pal, ind, box)
    if not ramp_ or not text:
        return False
    w, h = x1 - x0, y1 - y0
    # largest size whose ink fits the box
    for size in range(h, 5, -1):
        f = font(size)
        tmp = Image.new('L', (w * 4, h * 4), 0)
        ImageDraw.Draw(tmp).text((w * 2, h * 2), text, font=f, fill=255,
                                 anchor='mm')
        bb = tmp.getbbox()
        if bb and bb[2] - bb[0] <= w - pad and bb[3] - bb[1] <= h - pad:
            break
    else:
        return False
    cov = np.asarray(tmp.crop((bb[0], bb[1], bb[2], bb[3])), np.uint8)
    ch, cw = cov.shape
    ox, oy = x0 + (w - cw) // 2, y0 + (h - ch) // 2

    alphas = np.array([a for a, _ in ramp_], np.int16)
    idxs = np.array([i for _, i in ramp_], np.uint8)
    top = alphas.max()
    # Clear to whatever this box's background actually is. Index 0 is the
    # transparent one in the button bar but not everywhere -- on the save
    # screen it is opaque, and clearing to it drew a dark block behind
    # every label. Read it from a ring just outside the box rather than from
    # the box itself: on the operation-guide sheets the rectangles hug the
    # lettering, so inside them the commonest colour is the text and clearing
    # to that painted a solid white slab where the words had been.
    ind[y0:y1, x0:x1] = around(ind, (x0, y0, x1, y1))
    # At these sizes a stroke is barely a pixel wide and the rasteriser never
    # reaches full coverage, so mapping it straight onto the ramp gave hollow
    # letters. Stretch the coverage so its peak is the ramp's top.
    peak = int(cov.max()) or 255
    want = (cov.astype(np.int32) * top // peak).clip(0, top)
    pick = idxs[np.abs(alphas[None, None, :] - want[:, :, None]).argmin(2)]
    ind[oy:oy + ch, ox:ox + cw] = np.where(cov > 8, pick,
                                           ind[oy:oy + ch, ox:ox + cw])
    return True


def draw_over(ind, pal, box, text, bg_col, pad=2):
    """Replace the text inside a box that has artwork behind it.

    The title buttons are white lettering on a coloured pill, so clearing the
    box would take the pill with it. The background is rebuilt from a column
    of the pill the lettering does not reach -- the gradient runs top to
    bottom, so one clean column carries every row -- and the Korean is then
    composited over it and matched back to the palette.
    """
    x0, y0, x1, y1 = clip(ind, box)
    if x1 - x0 < 6 or y1 - y0 < 6:
        return False
    p = np.array(pal, np.int16)
    area = ind[y0:y1, x0:x1]
    lum = p[:, :3].sum(1)
    # The pill's own colour for a row is simply the commonest index in it --
    # the lettering never covers a whole row. Taking one fixed column instead
    # picked up the glow at the pill's edge and washed the whole thing out.
    back = np.empty_like(area)
    for r in range(area.shape[0]):
        vals, freq = np.unique(area[r], return_counts=True)
        back[r] = vals[freq.argmax()]

    seen = np.unique(area)
    opaque = seen[p[seen, 3] > 128]
    if not len(opaque):
        return False
    white = int(opaque[lum[opaque].argmax()])
    dark = int(opaque[lum[opaque].argmin()])

    w, h = x1 - x0, y1 - y0
    for size in range(h, 5, -1):
        f = font(size)
        tmp = Image.new('L', (w * 4, h * 4), 0)
        edge = Image.new('L', (w * 4, h * 4), 0)
        ImageDraw.Draw(tmp).text((w * 2, h * 2), text, font=f, fill=255,
                                 anchor='mm')
        # The lettering on these plates carries a dark edge; white on a pale
        # plate without one is barely legible.
        ImageDraw.Draw(edge).text((w * 2, h * 2), text, font=f, fill=255,
                                  anchor='mm', stroke_width=1,
                                  stroke_fill=255)
        bb = edge.getbbox()
        if bb and bb[2] - bb[0] <= w - pad and bb[3] - bb[1] <= h - pad:
            break
    else:
        return False
    cov = np.zeros((h, w), np.float32)
    out = np.zeros((h, w), np.float32)
    c = np.asarray(tmp.crop(bb), np.uint8)
    e = np.asarray(edge.crop(bb), np.uint8)
    oy, ox = (h - c.shape[0]) // 2, (w - c.shape[1]) // 2
    cov[oy:oy + c.shape[0], ox:ox + c.shape[1]] = c / 255.0
    out[oy:oy + e.shape[0], ox:ox + e.shape[1]] = e / 255.0

    fg = p[white][:3].astype(np.float32)
    dk = p[dark][:3].astype(np.float32)
    bg = p[back][:, :, :3].astype(np.float32)
    mix = bg + (dk - bg) * out[:, :, None]          # edge first
    mix = mix + (fg - mix) * cov[:, :, None]        # then the letter
    alpha = p[back][:, :, 3].astype(np.float32)
    want = np.concatenate([mix, alpha[:, :, None]], 2)
    d = ((p[None, None, :, :].astype(np.float32) - want[:, :, None, :]) ** 2)
    ind[y0:y1, x0:x1] = d.sum(3).argmin(2).astype(np.uint8)
    return True


def encode(xi, ind):
    """Put the index plane back into the .xi, same block sizes as before."""
    w, h, ncol, (t_off, t_sz, p_off, p_sz) = imgp8.info(xi)
    lin = ind.astype(np.uint8).tobytes()
    sw = imgp8.swizzle(lin, w, 8)
    store, table, blank = {}, [], bytes(64)
    for i in range(len(sw) // 64):
        c = sw[i * 64:(i + 1) * 64]
        if c == blank:
            table.append(0xFFFF)
            continue
        if c not in store:
            store[c] = len(store)
        table.append(store[c])
    tiles = struct.pack('<%dH' % len(table), *table)
    pix = b''.join(store)
    room = t_sz + p_sz
    was_t = xi[0x58 + t_off:0x58 + t_off + t_sz]
    was_p = xi[0x58 + p_off:0x58 + p_off + p_sz]

    # Keep a block exactly as it shipped when its contents did not change,
    # and otherwise re-emit it in the method it arrived in -- writing
    # title_new.xa's tile table back as LZ10 instead of the RLE it shipped
    # with gave a disc the console refuses, dying just before the title
    # screen while PPSSPP showed it.
    a = was_t if imgp8.l5_decompress(was_t) == tiles else _fit(tiles, was_t, room)
    b = was_p if imgp8.l5_decompress(was_p) == pix else _fit(pix, was_p, room)
    if a is None or b is None or len(a) + len(b) > room:
        return None
    for blk, orig in ((a, was_t), (b, was_p)):
        if blk is not orig and (blk[0] & 7) != (orig[0] & 7):
            print('    compression %d -> %d; the console may refuse it'
                  % (orig[0] & 7, blk[0] & 7))
            return None
    out = bytearray(xi)
    out[0x58 + t_off:0x58 + t_off + room] = a + b + bytes(room - len(a) - len(b))
    struct.pack_into('<IIII', out, 0x40, t_off, len(a), t_off + len(a),
                     room - len(a))
    return bytes(out)


def _fit(raw, orig, room):
    """The smallest block holding `raw` that fits, keeping `orig`'s method.

    Only if nothing in that method fits does this hand back a block in
    another one; the caller checks and skips the texture rather than ship
    something the console might refuse.
    """
    out = []
    for enc in (lambda: struct.pack('<I', len(raw) << 3) + raw,
                # The save screen's art needs the longer match search: at the
                # default effort it came out 72 bytes over its slot, and these
                # blocks are 70 kB, so the extra work is worth it.
                lambda: l5enc.lz10_block(raw, effort=256),
                lambda: l5enc2.huff4_block(raw, l5enc.tree_of(orig)),
                lambda: l5enc2.huff4_block(raw),
                lambda: l5enc.block(raw, l5enc.tree_of(orig)),
                lambda: l5enc2.huff8_block(raw),
                lambda: l5enc2.rle_block(raw)):
        try:
            blk = enc()
        except Exception:
            continue                 # a tree without every symbol the new data uses
        if len(blk) <= room:
            out.append(blk)
    if not out:
        return None
    same = [x for x in out if (x[0] & 7) == (orig[0] & 7)]
    return min(same or out, key=len)
