# -*- coding: utf-8 -*-
"""Cut a film's subtitle band into cues, one per line of dialogue.

    python op_band.py name.pmf [y0 y1]

Looking only at the strip the subtitles occupy is far steadier than scanning
the whole picture: nothing else in the band holds still, so a simple count of
lit pixels says whether a line is up.

Where one line ends and the next begins comes from how the films write them.
A line is typed out a character at a time, so while it is arriving the lit
pixels only ever grow. The moment a large number of them go away, the line has
been taken down -- that, not a change in the count, is the boundary. Cues cut
by mask-similarity alone came out split mid-sentence, which left the Korean on
screen for a fraction of the time the Japanese was.
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
BAND = (214, 272)        # rows the dialogue and its furigana use
K = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
ON = 90                  # lit pixels that mean a line is up
DROP = 45                # per cent of the run peak below which the line is gone
JOIN = 5                 # frames of flicker that do not end a line
HOLD = 8                 # shortest cue worth keeping


def lit(band):
    """The lettering in the band, with everything else thrown away.

    Brightness alone is not enough -- the films are lit, and a boot, a sleeve
    or a panel edge lights up the strip just as a subtitle does. What separates
    them is shape: characters come as a row of blobs of much the same size
    sitting on one baseline, and nothing else in the band does.
    """
    t = cv2.morphologyEx(band, cv2.MORPH_TOPHAT, K)
    m = ((t > 40) & (band > 140)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    box = [(i, st[i]) for i in range(1, n)
           if 2 <= st[i][2] <= 26 and 4 <= st[i][3] <= 24 and st[i][4] >= 8]
    out = np.zeros_like(m, bool)
    for i, b in box:
        mid, h = b[1] + b[3] / 2.0, b[3]
        row = [j for j, c in box
               if abs(c[1] + c[3] / 2.0 - mid) <= 4 and 0.55 <= c[3] / h <= 1.8]
        if len(row) >= 4:
            out |= (lab == i)
    return out


def masks(pmf, y0, y1, tmp='.'):
    p = os.path.join(tmp, '_band.264')
    open(p, 'wb').write(op_mux.video_es(pmf))
    cap = cv2.VideoCapture(p)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(lit(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)[y0:y1]))
    cap.release()
    os.remove(p)
    return out


def cues(m):
    """Split the band into one cue per line.

    A line only ever gains pixels while it is being typed, so the boundary is
    where the count collapses against the most the run has held -- not where it
    merely wobbles. Comparing each frame with the one before it split a single
    sentence into five, because the shape filter drops and re-admits a stroke
    as its neighbours arrive.
    """
    cov = np.array([int(x.sum()) for x in m])
    out, i, n = [], 0, len(m)
    while i < n:
        if cov[i] < ON:
            i += 1
            continue
        j, peak = i + 1, i
        while j < n and cov[j] >= ON and cov[j] * 100 >= DROP * cov[peak]:
            if cov[j] > cov[peak]:
                peak = j
            j += 1
        if j - i >= HOLD:
            out.append([i, j - 1, peak])
        i = j
    # a line that flickers off for a frame or two is still the same line
    merged = []
    for a, b, p in out:
        if merged and a - merged[-1][1] <= JOIN and \
                int((m[p] & m[merged[-1][2]]).sum()) > 0.5 * min(cov[p], cov[merged[-1][2]]):
            merged[-1][1] = b
            if cov[p] > cov[merged[-1][2]]:
                merged[-1][2] = p
        else:
            merged.append([a, b, p])
    return merged, cov


def main(name, y0=BAND[0], y1=BAND[1]):
    c = cpk.CPK(P.SRC, base=P.CPK_LBA * P.SEC)
    pmf = c.read([x for x in c.files if x['name'] == name][0])
    m = masks(pmf, y0, y1)
    found, cov = cues(m)
    os.makedirs(OUT, exist_ok=True)
    rows = [{'a': int(a), 'b': int(b), 'mid': int(p),
             'lit': int(cov[p]), 'sec': [round(a / 29.97, 2), round(b / 29.97, 2)]}
            for a, b, p in found]
    json.dump({'name': name, 'frames': len(m), 'band': [y0, y1], 'cues': rows},
              open(os.path.join(OUT, name + '.band.json'), 'w'), indent=1)
    print('%s  %d 프레임, 자막 %d개' % (name, len(m), len(rows)))
    return rows


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], *(int(x) for x in a[1:3]))
