# -*- coding: utf-8 -*-
"""Montage cue frames, cropped to their lettering, so they can be read.

    python op_sheet.py out.png name.pmf [name.pmf ...]

One strip per cue, cut to the box the scan found and scaled up, which fits far
more of them on a page than whole frames do.
"""
import json
import os
import sys

import cv2
import numpy as np

OUT = '_scan'
WIDE = 760          # strips are scaled to this width


def rows(names):
    out = []
    for n in names:
        j = json.load(open(os.path.join(OUT, n + '.json'), encoding='utf-8'))
        img = cv2.imread(os.path.join(OUT, n.replace('.pmf', '') + '.png'))
        for i, c in enumerate(j['cues']):
            f = img[i * 272:(i + 1) * 272]
            # full width: the detected box often clips the first or last
            # character, and a subtitle is centred anyway
            y0 = max(0, c['y0'] - 5)
            y1 = min(f.shape[0], c['y1'] + 5)
            out.append((n, i, c, f[y0:y1]))
    return out


def montage(items, path, per=10):
    for page in range((len(items) + per - 1) // per):
        chunk = items[page * per:(page + 1) * per]
        strips = []
        for n, i, c, crop in chunk:
            if crop.size == 0:
                crop = np.zeros((20, 60, 3), np.uint8)
            k = min(3.0, WIDE / max(1, crop.shape[1]))
            s = cv2.resize(crop, (int(crop.shape[1] * k), int(crop.shape[0] * k)),
                           interpolation=cv2.INTER_LANCZOS4)
            if s.shape[1] < WIDE:
                s = np.pad(s, ((0, 0), (0, WIDE - s.shape[1]), (0, 0)))
            bar = np.zeros((18, WIDE, 3), np.uint8)
            cv2.putText(bar, '%s #%d  %d-%d' % (n.replace('.pmf', ''), i,
                                                c['a'], c['b']),
                        (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
            strips += [bar, s[:, :WIDE]]
        p = path if page == 0 else path.replace('.png', '_%d.png' % page)
        cv2.imwrite(p, np.concatenate(strips, 0))
        print(p)


if __name__ == '__main__':
    montage(rows(sys.argv[2:]), sys.argv[1])
