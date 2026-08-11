# -*- coding: utf-8 -*-
"""Render numbered frame strips from a raw H.264 movie for subtitle review.

Usage:
    python op_framegrid.py INPUT.264 OUT_PREFIX START END STEP [Y0 Y1]

Frames are numbered from zero.  Output is split into pages of ten strips so
that short Japanese captions and their exact appearance/disappearance frames
can be checked without relying on OCR.
"""
from __future__ import annotations

import os
import sys

import cv2
import numpy as np


PER_PAGE = 10
SCALE = 3


def render(source: str, prefix: str, start: int, end: int, step: int,
           y0: int = 190, y1: int = 272) -> None:
    wanted = set(range(start, end + 1, step))
    frames: list[tuple[int, np.ndarray]] = []

    cap = cv2.VideoCapture(source)
    index = 0
    while index <= end:
        ok, frame = cap.read()
        if not ok:
            break
        if index in wanted:
            crop = frame[max(0, y0):min(frame.shape[0], y1)]
            crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE,
                              interpolation=cv2.INTER_LANCZOS4)
            frames.append((index, crop))
        index += 1
    cap.release()

    os.makedirs(os.path.dirname(prefix) or '.', exist_ok=True)
    for page_at in range(0, len(frames), PER_PAGE):
        rows = []
        for frame_no, crop in frames[page_at:page_at + PER_PAGE]:
            bar = np.zeros((24, crop.shape[1], 3), np.uint8)
            cv2.putText(bar, 'frame %d  %.3f s' %
                        (frame_no, frame_no * 1001 / 30000),
                        (5, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (0, 220, 255), 1, cv2.LINE_AA)
            rows.extend((bar, crop))
        page = page_at // PER_PAGE
        path = '%s_%02d.png' % (prefix, page)
        cv2.imwrite(path, np.concatenate(rows, axis=0))
        print(path)


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) not in (5, 7):
        raise SystemExit(__doc__)
    render(args[0], args[1], *(int(x) for x in args[2:]))
