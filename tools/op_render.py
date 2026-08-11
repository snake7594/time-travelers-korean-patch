# -*- coding: utf-8 -*-
"""Lay Korean subtitles across the top of a movie.

The Japanese stays where it is. Taking it off meant repainting a wide band of
every frame it appeared on, and those frames then cost far more to code than
the ones they replaced -- which is what made the picture stall wherever a
subtitle came up. Writing over the top of the picture instead touches a strip
that is usually flat sky or ceiling, costs a fraction of the bits, and leaves
the rest of the frame identical to the original.

The lettering is white with a dark edge heavy enough to read against anything,
and a little smaller than the burnt-in Japanese so the two do not compete.
"""
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import op_subs

TTF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'NanumSquareNeo-cBd.ttf')
TOP = 5              # first row's top edge
HEIGHT = 12          # cap height -- smaller than the Japanese underneath
LEAD = 18            # row to row
_font = {}


def font(size):
    if size not in _font:
        _font[size] = ImageFont.truetype(TTF, size)
    return _font[size]


def _size(lines, width):
    probe = ImageDraw.Draw(Image.new('L', (8, 8)))
    for s in range(HEIGHT + 8, 5, -1):
        f = font(s)
        box = [probe.textbbox((0, 0), t, font=f) for t in lines]
        if (max(b[2] - b[0] for b in box) <= width and
                max(b[3] - b[1] for b in box) <= HEIGHT + 1):
            return s
    return 7


def layer(lines, w, h):
    """The Korean as coverage: the outlined shape, and the letter inside it."""
    f = font(_size(lines, w - 24))
    rows = [TOP + i * LEAD for i in range(len(lines))]

    def paint(stroke):
        img = Image.new('L', (w, h), 0)
        d = ImageDraw.Draw(img)
        for t, y in zip(lines, rows):
            d.text((w // 2, y + HEIGHT // 2), t, font=f, fill=255,
                   anchor='mm', stroke_width=stroke, stroke_fill=255)
        a = np.asarray(img, np.float32) / 255.0
        # At this size a thin stroke never reaches full coverage, so letters
        # blended straight from it come out grey rather than white.
        return np.clip(a / max(a.max(), 1e-6), 0.0, 1.0)

    return paint(2), paint(0)


def render(name, frames, progress=None):
    """Write the Korean into `frames` in place and return it.

    In place because avant_title is fifteen thousand frames -- a copy wants six
    gigabytes -- so the caller hands in a memory-mapped array.
    """
    out = frames
    n, h, w = frames.shape[:3]
    cues = op_subs.MOVIES[name]
    for i, cue in enumerate(cues):
        edge, core = layer(cue['ko'], w, h)
        band = np.where(edge.any(1))[0]
        if not len(band):
            continue
        y0, y1 = int(band.min()), int(band.max()) + 1
        e = edge[y0:y1, :, None]
        c = core[y0:y1, :, None]
        for j in range(max(0, cue['a']), min(n, cue['b'] + 1)):
            f = out[j, y0:y1].astype(np.float32)
            f *= 1.0 - e * 0.90          # the dark edging first,
            f = f * (1.0 - c) + 240.0 * c  # then the white letter
            out[j, y0:y1] = np.clip(f, 0, 255).astype(np.uint8)
        if progress:
            progress('draw', i, len(cues))
    return out
