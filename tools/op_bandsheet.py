# -*- coding: utf-8 -*-
"""Render the subtitle band of each cue, so the Japanese can be read off it.

    python op_bandsheet.py name.pmf out.png [per-page]
"""
import json
import os
import sys

import cv2
import numpy as np

import cpk
import op_mux
import pack_korean as P

OUT = '_scan'


def main(name, path, per=14, scale=2.0):
    j = json.load(open(os.path.join(OUT, name + '.band.json'), encoding='utf-8'))
    y0, y1 = j['band']
    want = {c['mid']: i for i, c in enumerate(j['cues'])}
    c = cpk.CPK(P.SRC, base=P.CPK_LBA * P.SEC)
    pmf = c.read([x for x in c.files if x['name'] == name][0])
    p = '_bs.264'
    open(p, 'wb').write(op_mux.video_es(pmf))
    cap = cv2.VideoCapture(p)
    keep, i = {}, 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i in want:
            keep[want[i]] = f[y0:y1].copy()
        i += 1
    cap.release()
    os.remove(p)

    n = len(j['cues'])
    for page in range((n + per - 1) // per):
        strips = []
        for k in range(page * per, min(n, (page + 1) * per)):
            cue = j['cues'][k]
            img = cv2.resize(keep[k], None, fx=scale, fy=scale,
                             interpolation=cv2.INTER_LANCZOS4)
            bar = np.zeros((16, img.shape[1], 3), np.uint8)
            cv2.putText(bar, '#%d  %d-%d' % (k, cue['a'], cue['b']), (3, 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 255), 1)
            strips += [bar, img]
        out = path if page == 0 else path.replace('.png', '_%d.png' % page)
        cv2.imwrite(out, np.concatenate(strips, 0))
        print(out)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], *(int(x) for x in a[2:3]))
