# -*- coding: utf-8 -*-
"""Find the burnt-in lettering in a movie and cut it into cues.

    python op_scan.py [name.pmf ...]

Writes a contact sheet per film -- one strip per cue, so the Japanese can be
read off it -- and a cue table to _scan/<name>.json for op_subs to be written
from. Detection is by shape: a top-hat leaves the thin bright strokes of
lettering behind, and only blobs the size of a character are counted, which
keeps starfields, glints and foliage out. A cue ends when the surviving mask
stops matching the frame before it.
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
K = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))


def strokes(gray):
    """Character-sized bright blobs, as a mask."""
    t = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, K)
    m = (t > 50).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    out = np.zeros_like(m)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 2 <= w <= 28 and 3 <= h <= 28 and a >= 6:
            out[lab == i] = 1
    return out


def frames_of(pmf, tmp):
    p = os.path.join(tmp, '_scan.264')
    open(p, 'wb').write(op_mux.video_es(pmf))
    cap = cv2.VideoCapture(p)
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield f
    cap.release()
    os.remove(p)


SPAN = 7            # how far either side a mask has to survive to count
FLOOR = 110         # surviving pixels that mean lettering rather than line art
HOLD = 12           # shortest cue worth keeping


def stable(masks, n):
    """Per frame, the stroke pixels that are also there a moment either side.

    Lettering is nailed to the screen for a second or more; drawn line art
    moves every frame. Intersecting a frame with its neighbours leaves the
    first and almost none of the second, which separates a subtitle from a
    character's outline far better than counting strokes ever did.
    """
    out = np.zeros(n, np.int32)
    for t in range(n):
        a, b = max(0, t - SPAN), min(n - 1, t + SPAN)
        out[t] = int((masks[t] & masks[a] & masks[b]).sum())
    return out


def lined(mask, axis=0):
    """Longest run of like-sized blobs sharing a baseline -- i.e. a line of text.

    Held-still strokes alone are not enough: a montage of faces holds a cut for
    a second or two and its eyes and mouths survive the intersection just as
    lettering does. Characters, unlike faces, come in a row of near-identical
    boxes, so that is what gets counted. `axis` 0 reads across, 1 reads down,
    for the cards set vertically.
    """
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    box = [st[i] for i in range(1, n) if st[i][4] >= 6]
    if len(box) < 3:
        return 0
    best = 0
    for b in box:
        h = b[3] if axis == 0 else b[2]
        mid = (b[1] + b[3] / 2) if axis == 0 else (b[0] + b[2] / 2)
        run = 0
        for c in box:
            ch = c[3] if axis == 0 else c[2]
            cm = (c[1] + c[3] / 2) if axis == 0 else (c[0] + c[2] / 2)
            if abs(cm - mid) <= 4 and 0.6 <= ch / max(1, h) <= 1.7:
                run += 1
        best = max(best, run)
    return best


def is_text(mask):
    return max(lined(mask, 0), lined(mask, 1)) >= 4


def cues(masks, score):
    out, i, n = [], 0, len(score)
    while i < n:
        if score[i] < FLOOR:
            i += 1
            continue
        j = i + 1
        while j < n and score[j] >= FLOOR:
            a, b = masks[j - 1], masks[j]
            u = int((a | b).sum())
            if u and (a & b).sum() / u < 0.55:
                break
            j += 1
        if j - i >= HOLD:
            mid = (i + j - 1) // 2
            a, b = max(0, mid - SPAN), min(n - 1, mid + SPAN)
            if is_text(masks[mid] & masks[a] & masks[b]):
                out.append((i, j - 1))
        i = max(j, i + 1)
    return merge(out, score)


GAP = 22            # frames that may separate two halves of the same line


def merge(runs, score):
    """Join runs that are one line arriving a character at a time.

    Several films type their subtitles out rather than cutting them in, so the
    mask changes on almost every frame and a single line comes back as three
    or four runs a few frames apart. Anything that close is the same line.
    """
    out = []
    for a, b in runs:
        if out and a - out[-1][1] <= GAP:
            out[-1][1] = b
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def fullest(masks, a, b):
    """The frame in [a, b] carrying the most lettering -- the finished line."""
    best, at = -1, (a + b) // 2
    for t in range(a, b + 1):
        v = int(masks[t].sum())
        if v > best:
            best, at = v, t
    return at


def scan(name, tmp='.'):
    """Two passes: measure, then fetch only the frames worth looking at.

    avant_title is a quarter of a million frames; holding them all would want
    six gigabytes, and all that is needed from the first pass is a count and a
    thumbnail of the mask.
    """
    c = cpk.CPK(P.SRC, base=P.CPK_LBA * P.SEC)
    pmf = c.read([x for x in c.files if x['name'] == name][0])
    masks = [strokes(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)).astype(bool)
             for f in frames_of(pmf, tmp)]
    found = cues(masks, stable(masks, len(masks)))
    pick = {(a, b): fullest(masks, a, b) for a, b in found}
    want = set(pick.values())
    keep = {}
    for i, f in enumerate(frames_of(pmf, tmp)):
        if i in want:
            keep[i] = f
    rows = []
    for a, b in found:
        mid = pick[(a, b)]
        ys, xs = np.where(strokes(cv2.cvtColor(keep[mid], cv2.COLOR_BGR2GRAY)))
        rows.append({'a': a, 'b': b,
                     'x0': int(xs.min()), 'x1': int(xs.max()) + 1,
                     'y0': int(ys.min()), 'y1': int(ys.max()) + 1,
                     'mid': int(mid),
                     'sec': [round(a / 29.97, 2), round(b / 29.97, 2)]})
    os.makedirs(OUT, exist_ok=True)
    json.dump({'name': name, 'frames': len(masks), 'cues': rows},
              open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
    if rows:
        sheet = np.concatenate([keep[r['mid']] for r in rows], 0)
        for i, r in enumerate(rows):
            cv2.putText(sheet, '%d' % i, (4, i * 272 + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.imwrite(os.path.join(OUT, name.replace('.pmf', '') + '.png'), sheet)
    return rows, len(masks)


if __name__ == '__main__':
    for n in sys.argv[1:]:
        r, f = scan(n)
        print('%-30s %5d 프레임  자막 %d개' % (n, f, len(r)))
