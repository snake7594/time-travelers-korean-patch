# -*- coding: utf-8 -*-
"""Export Time Travelers (.xf) fonts as viewable PNGs.

Produces, per font, into <out>/:
  <font>_atlas<N>.png   the raw glyph atlas, black on white
  <font>_specimen.png   every character drawn in code order using the real
                        metrics, with a light cell grid
"""
import os, sys, struct
from PIL import Image, ImageDraw

import fnt, imgp

FONT_DIR = r'D:\psp\타임트레블러즈\extract\fnt'


def load(name):
    base = os.path.join(FONT_DIR, name)
    meta = fnt.parse(open(os.path.join(base, 'FNT.bin'), 'rb').read())
    atlas = []
    for i in range(meta['textures']):
        w, h, rgba, real_h = imgp.decode(open(os.path.join(base, '%03d.xi' % i), 'rb').read())
        im = Image.frombytes('RGBA', (w, h), rgba).crop((0, 0, w, real_h))
        atlas.append(im.split()[3])          # alpha channel = the glyph coverage
    return meta, atlas


def ink_on_white(alpha):
    return Image.eval(alpha, lambda v: 255 - v)


def specimen(meta, atlas, table, cols=32, scale=1):
    chars = meta[table]
    if not chars:
        return None
    line = max(meta['fields'][0], 8) + 6
    cw = max((c['advance'] for c in chars), default=16) + 6
    rows = (len(chars) + cols - 1) // cols
    W, H = cols * cw + 1, rows * line + 1
    canvas = Image.new('L', (W, H), 0)          # accumulate coverage

    for i, c in enumerate(chars):
        ox, oy, gw, gh = meta['sizes'][c['size']]
        if not gw or not gh:
            continue
        cx = (i % cols) * cw + 3 + ox
        cy = (i // cols) * line + 3 + oy
        g = atlas[c['tex']].crop((c['x'], c['y'], c['x'] + gw, c['y'] + gh))
        canvas.paste(g, (cx, cy))

    out = ink_on_white(canvas).convert('RGB')
    d = ImageDraw.Draw(out)
    for r in range(rows + 1):
        d.line([(0, r * line), (W, r * line)], fill=(220, 224, 232))
    for col in range(cols + 1):
        d.line([(col * cw, 0), (col * cw, H)], fill=(220, 224, 232))
    if scale != 1:
        out = out.resize((W * scale, H * scale), Image.NEAREST)
    return out


def main(out_dir, names):
    os.makedirs(out_dir, exist_ok=True)
    for name in names:
        meta, atlas = load(name)
        for i, a in enumerate(atlas):
            p = os.path.join(out_dir, '%s_atlas%d.png' % (name, i))
            ink_on_white(a).save(p)
            print('  %-28s %dx%d' % (os.path.basename(p), a.width, a.height))
        for table in ('large', 'small'):
            im = specimen(meta, atlas, table)
            if im is None:
                continue
            suffix = '_specimen' if table == 'large' else '_specimen_small'
            p = os.path.join(out_dir, '%s%s.png' % (name, suffix))
            im.save(p)
            print('  %-28s %dx%d  (%d chars)'
                  % (os.path.basename(p), im.width, im.height, len(meta[table])))


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else r'D:\psp\타임트레블러즈\extract\png\view'
    main(out, sys.argv[2:] or ['nrm_main', 'nrm_sub', 'dbg'])
