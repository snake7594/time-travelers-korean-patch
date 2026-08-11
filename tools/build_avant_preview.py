# -*- coding: utf-8 -*-
"""Render a Korean subtitle preview for the extracted avant-title cues.

This is a review movie, not a PSP PMF rebuild.  The source H.264 already has
Japanese burnt into the picture, so Korean is drawn in a separate upper band
and the original Japanese remains visible underneath for direct comparison.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
SOURCE_H264 = ROOT / "tools" / "_sony_probe" / "avant_dump.264"
SOURCE_WAV = ROOT / "tools" / "_sony_probe" / "avant_audio.wav"
CUE_JSON = ROOT / "movie" / "subtitles" / "avant_title.ja.json"
SOURCE_SCRIPT_JSON = ROOT / "script_json" / "A01.json"
SCRIPT_JSON = ROOT / "script_fix" / "A01.json"
OUT_DIR = ROOT / "movie" / "subtitles"
OUT_MP4 = OUT_DIR / "avant_title.ko.preview.mp4"
OUT_SRT = OUT_DIR / "avant_title.ko.srt"
FONT_PATH = ROOT / "NanumSquareNeo-cBd.ttf"
FFMPEG = Path(r"C:\vc2work\tools\ffmpeg\ffmpeg.exe")
FPS = "30000/1001"
W, H = 480, 272

TAG_RE = re.compile(r"<[^>]*>")

CARD_KO = {
    "opening_card": [
        "사람이 이 세계의 진짜 모습을 알게 되었을 때,",
        "그것은 사람에게 행복한 것일까? 불행한 것일까?",
    ],
    "ending_card": {
        "空に穴が開いた日。": ["하늘에 구멍이 뚫린 날."],
        "この現象は後に「ロストホール」と名付けられる。": [
            "이 현상은 훗날 「로스트 홀」이라 불리게 된다."
        ],
        "自然災害、爆発事故、そしてテロとも噂されたが、原因は今もって謎とされている。": [
            "자연재해, 폭발 사고, 그리고 테러라는 소문도 있었지만,",
            "원인은 지금도 수수께끼로 남아 있다.",
        ],
    },
    "time_overlay": ["―18년 후―"],
}

# avant_title has no burnt-in Japanese captions during the opening-credit
# conversation.  The video does not play these A01 entries in JSON order:
# entry 0 is followed by 26-30, then 1-24.  These boundaries were read from
# the extracted audio's Japanese speech, so the cue timing follows the voice
# rather than an estimate based on character count.  Entry 25 is only a
# background murmur and is intentionally left without a text subtitle.
VOICE_TIMINGS = [
    (0, 24.48, 29.80),
    (26, 33.50, 37.32),
    (27, 37.32, 41.32),
    (28, 41.32, 46.80),
    (29, 46.80, 49.44),
    (30, 49.44, 53.94),
    (1, 54.44, 57.34),
    (2, 57.34, 62.08),
    (3, 62.96, 63.24),
    (4, 63.64, 67.90),
    (5, 67.90, 68.32),
    (6, 69.06, 74.42),
    (7, 74.42, 77.58),
    (8, 77.58, 79.80),
    (9, 79.80, 80.74),
    (10, 80.98, 84.10),
    (11, 85.60, 88.72),
    (12, 88.72, 90.32),
    (13, 90.66, 95.00),
    (14, 95.00, 96.18),
    (15, 96.18, 96.62),
    (16, 96.62, 98.08),
    (17, 98.08, 100.46),
    (18, 100.46, 103.96),
    (19, 103.96, 104.56),
    (20, 104.76, 108.58),
    (21, 108.58, 109.22),
    (22, 109.66, 110.72),
    (23, 111.80, 112.36),
    (24, 116.86, 117.80),
]


def plain_script_text(entry: dict) -> str:
    raw = TAG_RE.sub("", entry.get("ja_read", ""))
    raw = raw.replace("\\n", "").replace("\r\n", "").replace("\n", "")
    left, right = raw.find("「"), raw.rfind("」")
    if left >= 0 and right > left:
        raw = raw[left + 1:right]
    return raw


def korean_dialogue(entry: dict) -> list[str]:
    raw = entry["ko"]
    left, right = raw.find("「"), raw.rfind("」")
    if left >= 0 and right > left:
        raw = raw[left + 1:right]
    raw = TAG_RE.sub("", raw)
    raw = raw.replace("\\n", "\n").replace("\r\n", "\n")
    return [line.strip() for line in raw.split("\n") if line.strip()]


def make_voice_cues(source_script: dict, script: dict) -> list[dict]:
    cues = []
    for source_index, start_seconds, end_seconds in VOICE_TIMINGS:
        source_entry = source_script["entries"][source_index]
        entry = script["entries"][source_index]
        ja = plain_script_text(source_entry)
        if not ja:
            raise ValueError(f"voice timing has no source text: {source_index}")
        start = round(start_seconds * 30000 / 1001)
        end = round(end_seconds * 30000 / 1001) - 1
        cues.append({
            "cue": 0,
            "start_frame": start,
            "end_frame": end,
            "kind": "voice_only",
            "ja": ja,
            "ko": "\n".join(korean_dialogue(entry)),
            "lines": korean_dialogue(entry),
            "source_indices": [source_index],
        })
    return cues


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    return box[2] - box[0]


def wrap_lines(lines: list[str], draw: ImageDraw.ImageDraw,
               font: ImageFont.FreeTypeFont, width: int = 456) -> list[str]:
    result: list[str] = []
    for source in lines:
        words = source.split()
        if len(words) <= 1 and text_width(draw, source, font) <= width:
            result.append(source)
            continue
        if not words:
            continue
        current = ""
        for word in words:
            trial = word if not current else current + " " + word
            if current and text_width(draw, trial, font) > width:
                result.append(current)
                current = word
            else:
                current = trial
        if current:
            result.append(current)
    return result or [""]


def make_korean_cues(data: dict, source_script: dict, script: dict) -> list[dict]:
    entries = script["entries"]
    out = make_voice_cues(source_script, script)
    for cue in data["cues"]:
        if cue["kind"] == "dialogue":
            source_index = cue["source_indices"][0]
            lines = korean_dialogue(entries[source_index])
        elif cue["kind"] == "opening_card":
            lines = CARD_KO["opening_card"]
        elif cue["kind"] == "ending_card":
            lines = CARD_KO["ending_card"][cue["ja"]]
        elif cue["kind"] == "time_overlay":
            lines = CARD_KO["time_overlay"]
        else:
            raise ValueError(cue["kind"])
        out.append({
            "cue": cue["cue"],
            "start_frame": cue["start_frame"],
            "end_frame": cue["end_frame"],
            "kind": cue["kind"],
            "ja": cue["ja"],
            "ko": "\n".join(lines),
            "lines": lines,
            "source_indices": cue["source_indices"],
        })
    out.sort(key=lambda cue: (cue["start_frame"], cue["end_frame"]))
    for number, cue in enumerate(out, 1):
        cue["cue"] = number
    return out


def srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def write_srt(cues: list[dict]) -> None:
    blocks = []
    for cue in cues:
        start = cue["start_frame"] * 1001 / 30000
        end = (cue["end_frame"] + 1) * 1001 / 30000
        blocks.append(
            f"{cue['cue']}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n"
            + "\n".join(cue["lines"])
        )
    OUT_SRT.write_text("\n\n".join(blocks) + "\n", encoding="utf-8-sig")


def draw_caption(frame: np.ndarray, lines: list[str], font: ImageFont.FreeTypeFont,
                 draw_probe: ImageDraw.ImageDraw) -> np.ndarray:
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    lines = wrap_lines(lines, draw_probe, font)
    line_height = 20
    total_height = line_height * len(lines)
    y0 = max(3, (70 - total_height) // 2)
    for row, text in enumerate(lines):
        box = draw.textbbox((0, 0), text, font=font, stroke_width=2)
        x = (W - (box[2] - box[0])) // 2 - box[0]
        y = y0 + row * line_height
        draw.text((x, y), text, font=font, fill=(255, 255, 255),
                  stroke_width=2, stroke_fill=(25, 25, 25))
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def main() -> None:
    data = json.loads(CUE_JSON.read_text(encoding="utf-8"))
    source_script = json.loads(SOURCE_SCRIPT_JSON.read_text(encoding="utf-8"))
    script = json.loads(SCRIPT_JSON.read_text(encoding="utf-8"))
    cues = make_korean_cues(data, source_script, script)
    if len(cues) != 125:
        raise AssertionError(len(cues))
    write_srt(cues)

    font = ImageFont.truetype(str(FONT_PATH), 15)
    probe = ImageDraw.Draw(Image.new("RGB", (W, H)))
    active: dict[int, dict] = {}
    for cue in cues:
        for frame in range(cue["start_frame"], cue["end_frame"] + 1):
            active[frame] = cue

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", FPS, "-i", "-",
        "-i", str(SOURCE_WAV),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", str(OUT_MP4),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
    cap = cv2.VideoCapture(str(SOURCE_H264))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {SOURCE_H264}")
    frame_no = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_no in active:
                cue = active[frame_no]
                frame = draw_caption(frame, cue["lines"], font, probe)
            process.stdin.write(np.ascontiguousarray(frame).tobytes())
            frame_no += 1
    finally:
        cap.release()
        process.stdin.close()
    error = process.stderr.read().decode("utf-8", errors="replace")
    code = process.wait()
    if code:
        raise RuntimeError(error or f"ffmpeg exited with {code}")
    if frame_no != data["video"]["frame_count"]:
        raise AssertionError((frame_no, data["video"]["frame_count"]))
    print(OUT_MP4)
    print(OUT_SRT)
    print(f"frames={frame_no} cues={len(cues)} voice_only=30")


if __name__ == "__main__":
    main()
