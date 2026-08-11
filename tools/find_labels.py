# -*- coding: utf-8 -*-
"""Locate the text blocks in a menu texture.

Rows of ink become bands; inside a band, runs of columns separated by a gap
are the individual labels. Each label carries its furigana on the line above,
so a band pairs with the small one over it.
"""
import sys
import numpy as np
from PIL import Image
import cpk, dnsfile, xpck, imgp8


def runs(mask, gap):
    """[(start, end)] of True runs, merging holes narrower than `gap`."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        hole = 0
        while j < n and (mask[j] or hole < gap):
            hole = 0 if mask[j] else hole + 1
            j += 1
        out.append((i, j - hole))
        i = j
    return out


def blocks(alpha, row_gap=3, col_gap=6):
    for a, b in runs(alpha.any(axis=1), row_gap):
        band = alpha[a:b]
        for x, y in runs(band.any(axis=0), col_gap):
            sub = band[:, x:y]
            ys = np.where(sub.any(axis=1))[0]
            yield (x, a + int(ys.min()), y, a + int(ys.max()) + 1)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'navi.xa'
    xi = sys.argv[2] if len(sys.argv) > 2 else '000.xi'
    c = cpk.CPK(dnsfile.DNSFile())
    d = c.read([x for x in c.files if x['name'] == name][0])
    part = {p['name']: p for p in xpck.parse(d)}[xi]['data']
    img, real = imgp8.rgba(part)
    alpha = img[:real, :, 3] > 8
    out = np.array(img[:real])
    got = list(blocks(alpha))
    print('%s %s: %d blocks' % (name, xi, len(got)))
    for i, (x0, y0, x1, y1) in enumerate(got):
        print('  %2d  x %3d..%-3d y %3d..%-3d  %dx%d'
              % (i, x0, x1, y0, y1, x1 - x0, y1 - y0))
        out[y0:y0 + 1, x0:x1] = (255, 0, 0, 255)
        out[y1 - 1:y1, x0:x1] = (255, 0, 0, 255)
    Image.fromarray(out).save('boxes_%s.png' % name.split('.')[0])


if __name__ == '__main__':
    main()
