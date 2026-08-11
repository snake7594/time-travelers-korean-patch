# -*- coding: utf-8 -*-
"""Build the frame-reviewed Japanese subtitle transcript for avant_title.pmf.

The movie has burnt-in Japanese captions, so there is no subtitle stream to
demux.  Text is taken from A01.json only after every cue has been matched to
the original PMF by eye.  Fast type-in phases and cuts inside one caption are
collapsed into one logical cue.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "script_json" / "A01.json"
MOVIE = ROOT / "tools" / "_sony_probe" / "avant_title.pmf"
OUT_DIR = ROOT / "movie" / "subtitles"
FPS_NUM = 30_000
FPS_DEN = 1_001
FRAME_COUNT = 14_916


# (A01 entry index or tuple of simultaneous duplicate entries, first frame,
# last frame).  Frames are inclusive.  These are logical visible runs, not
# OCR fragments; in particular A01 entries 50/51 and the three detector hits
# for entry 101 each form one cue.
DIALOGUE = [
    (114, 4255, 4271),
    (115, 4296, 4358),
    (116, 4380, 4388),
    (117, 4395, 4513),
    (118, 4529, 4598),
    (119, 4611, 4635),
    (120, 4640, 4758),
    (121, 4776, 4860),
    (123, 4879, 4961),
    (124, 4977, 4985),
    (31, 5000, 5025),
    (32, 5063, 5094),
    (33, 5099, 5148),
    (35, 5196, 5224),
    (36, 5232, 5321),
    (37, 5459, 5490),
    (38, 5499, 5545),
    (39, 5555, 5580),
    (40, 5630, 5644),
    (41, 5682, 5747),
    (42, 5748, 5803),
    (43, 5806, 5818),
    (44, 5836, 5881),
    (45, 5903, 5962),
    (46, 5967, 6040),
    (47, 6041, 6194),
    (48, 6210, 6240),
    (49, 6394, 6421),
    ((50, 51), 6450, 6458),
    (52, 6584, 6593),
    (53, 6604, 6635),
    (54, 6661, 6704),
    (55, 6728, 6781),
    (56, 6787, 6837),
    (57, 6862, 6884),
    (58, 7053, 7104),
    (60, 7178, 7196),
    (61, 7205, 7252),
    (62, 7261, 7287),
    (63, 7303, 7362),
    (64, 7368, 7391),
    (65, 7404, 7439),
    (66, 7452, 7509),
    (67, 7522, 7556),
    (68, 7568, 7667),
    (69, 7702, 7757),
    (70, 7872, 7984),
    (71, 8065, 8135),
    (72, 8190, 8205),
    (73, 8350, 8385),
    (74, 8395, 8442),
    (75, 8500, 8543),
    (76, 8557, 8594),
    (77, 8596, 8614),
    (78, 8632, 8669),
    (79, 8683, 8732),
    (80, 8936, 8944),
    (81, 8955, 8977),
    (82, 8987, 9023),
    (83, 9037, 9047),
    (84, 9092, 9145),
    (85, 9156, 9235),
    (86, 9292, 9368),
    (87, 9424, 9434),
    (88, 9465, 9499),
    (89, 9565, 9611),
    (90, 9640, 9668),
    (91, 9692, 9723),
    (92, 9740, 9775),
    (93, 9930, 9987),
    (94, 10080, 10087),
    (95, 10200, 10208),
    (96, 10222, 10247),
    (97, 10499, 10609),
    (98, 10610, 10635),
    (99, 10640, 10654),
    (100, 10855, 10880),
    (101, 10900, 10985),
    (102, 11240, 11268),
    (103, 11426, 11435),
    (104, 11557, 11603),
    (105, 11630, 11674),
    (106, 11717, 11815),
    (107, 11990, 12020),
    (108, 12450, 12492),
    (109, 12502, 12553),
    (110, 12583, 12611),
    (111, 12651, 12676),
    (112, 12855, 12868),
    (113, 12921, 13004),
]


CARDS = [
    {
        "start_frame": 43,
        "end_frame": 270,
        "kind": "opening_card",
        "ja": "ひとが、この世界の、本当の姿を知ったとき、それは、ひとにとって、幸福なのだろうか？",
        "lines": [
            "ひとが、この世界の、",
            "本当の姿を知ったとき、",
            "それは、ひとにとって、",
            "幸福なのだろうか？",
        ],
    },
    {
        "start_frame": 13522,
        "end_frame": 13597,
        "kind": "ending_card",
        "ja": "空に穴が開いた日。",
        "lines": ["空に穴が開いた日。"],
    },
    {
        "start_frame": 13627,
        "end_frame": 13733,
        "kind": "ending_card",
        "ja": "この現象は後に「ロストホール」と名付けられる。",
        "lines": ["この現象は後に", "「ロストホール」と", "名付けられる。"],
    },
    {
        "start_frame": 13762,
        "end_frame": 13908,
        "kind": "ending_card",
        "ja": "自然災害、爆発事故、そしてテロとも噂されたが、原因は今もって謎とされている。",
        "lines": [
            "自然災害、爆発事故、",
            "そしてテロとも",
            "噂されたが、",
            "原因は今もって",
            "謎とされている。",
        ],
    },
    {
        "start_frame": 13986,
        "end_frame": 14170,
        "kind": "time_overlay",
        "ja": "―１８年後―",
        "lines": ["―１８年後―"],
    },
]


# The cinematic normally supplies a terminal full stop where the game script
# line omits punctuation.  Existing question/exclamation marks are preserved.
TAG_RE = re.compile(r"<[^>]*>")


def script_parts(entry: dict) -> tuple[str, str]:
    raw = (TAG_RE.sub("", entry["ja_read"])
           .replace("\\n", "")
           .replace("\n", ""))
    left = raw.find("「")
    right = raw.rfind("」")
    if left < 0 or right <= left:
        raise ValueError(f"not a dialogue line: {entry['id']} {raw!r}")
    return raw[:left], raw[left + 1:right]


def displayed_text(index: int, text: str) -> str:
    text = text.rstrip()
    if not text.endswith(("。", "！", "？")):
        text += "。"
    return text


def frame_seconds(frame: int) -> float:
    return round(frame * FPS_DEN / FPS_NUM, 6)


def srt_timestamp(frame: int) -> str:
    # Round to the nearest millisecond.  Call with end_frame + 1 for an
    # inclusive JSON end frame and an exclusive SRT endpoint.
    milliseconds = round(frame * FPS_DEN * 1000 / FPS_NUM)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    data = json.loads(SCRIPT.read_text(encoding="utf-8"))
    entries = data["entries"]
    cues = []

    for card in CARDS:
        cues.append({
            **card,
            "source_indices": [],
            "source_ids": [],
            "speakers": [],
        })

    for source, start, end in DIALOGUE:
        indices = list(source) if isinstance(source, tuple) else [source]
        parts = [script_parts(entries[index]) for index in indices]
        texts = [text for _, text in parts]
        if len(set(texts)) != 1:
            raise AssertionError(f"simultaneous lines differ: {indices} {texts}")
        cues.append({
            "start_frame": start,
            "end_frame": end,
            "kind": "dialogue",
            "ja": displayed_text(indices[0], texts[0]),
            "lines": [displayed_text(indices[0], texts[0])],
            "source_indices": indices,
            "source_ids": [entries[index]["id"] for index in indices],
            "speakers": [speaker for speaker, _ in parts],
        })

    cues.sort(key=lambda cue: (cue["start_frame"], cue["end_frame"]))
    for number, cue in enumerate(cues, 1):
        cue["cue"] = number
        cue["start_seconds"] = frame_seconds(cue["start_frame"])
        cue["end_seconds"] = frame_seconds(cue["end_frame"] + 1)

    if len(DIALOGUE) != 90 or len(cues) != 95:
        raise AssertionError((len(DIALOGUE), len(cues)))
    used_indices = [index for cue in cues for index in cue["source_indices"]]
    expected_indices = set(range(31, 125)) - {34, 59, 122}
    if len(used_indices) != 91 or set(used_indices) != expected_indices:
        raise AssertionError("A01 dialogue coverage is incomplete or duplicated")
    if len(used_indices) != len(set(used_indices)):
        raise AssertionError("an A01 source entry was mapped more than once")
    for cue in cues:
        if not 0 <= cue["start_frame"] <= cue["end_frame"] < FRAME_COUNT:
            raise AssertionError(f"invalid frame range in cue {cue['cue']}")
        if any(token in cue["ja"] for token in ("<", ">", "\\n", "\n", "�")):
            raise AssertionError(f"unstripped source markup in cue {cue['cue']}")
        if re.search(r"[가-힣]", cue["ja"]):
            raise AssertionError(f"Korean leaked into Japanese cue {cue['cue']}")
    for previous, current in zip(cues, cues[1:]):
        if previous["end_frame"] >= current["start_frame"]:
            raise AssertionError(
                f"overlapping cues {previous['cue']} and {current['cue']}"
            )

    omitted = []
    for index, reason in ((59, "voice only; no burnt-in subtitle"),
                          (122, "voice only; no burnt-in subtitle")):
        speaker, text = script_parts(entries[index])
        omitted.append({
            "source_index": index,
            "source_id": entries[index]["id"],
            "speaker": speaker,
            "ja": displayed_text(index, text),
            "reason": reason,
        })

    result = {
        "schema": "tt1-burnt-subtitles/1",
        "movie": "avant_title.pmf",
        "source_movie": str(MOVIE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(MOVIE),
        "source_script": str(SCRIPT.relative_to(ROOT)).replace("\\", "/"),
        "video": {
            "width": 480,
            "height": 272,
            "fps": "30000/1001",
            "frame_count": FRAME_COUNT,
            "duration_seconds": frame_seconds(FRAME_COUNT),
        },
        "timing": {
            "frame_numbering": "zero-based",
            "end_frame": "inclusive",
            "method": "original PMF frame review; type-in fragments merged per sentence",
        },
        "counts": {
            "total": len(cues),
            "dialogue": sum(cue["kind"] == "dialogue" for cue in cues),
            "cards_and_overlays": sum(cue["kind"] != "dialogue" for cue in cues),
        },
        "special_cases": {
            "simultaneous_duplicate": {
                "source_indices": [50, 51],
                "description": "新道 and 甲斐 say the same countdown; the movie shows one caption",
            },
            "omitted_script_entries": omitted,
            "blank_script_entry": {
                "source_index": 34,
                "source_id": entries[34]["id"],
            },
        },
        "cues": cues,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "avant_title.ja.json"
    srt_path = OUT_DIR / "avant_title.ja.srt"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    srt_blocks = []
    for cue in cues:
        start = srt_timestamp(cue["start_frame"])
        end = srt_timestamp(cue["end_frame"] + 1)
        text = "\n".join(cue["lines"])
        srt_blocks.append(f"{cue['cue']}\n{start} --> {end}\n{text}")
    srt_path.write_text("\n\n".join(srt_blocks) + "\n", encoding="utf-8-sig")

    print(json_path)
    print(srt_path)
    print(json.dumps(result["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
