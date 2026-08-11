"""Wrap direct Korean translations to the game's two-line display budget.

This is a mechanical layout pass only: it never changes wording or tags.
Entries whose translated text is longer than two 30-character lines are left
alone for a later, human shortening pass.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


MAP = Path("script_json/direct_ko.jsonl")
TAG = re.compile(r"<[^>]*>")
LIMIT = 30


def units(text: str):
    """Return (text, visible_length, break_ok, preferred) units."""
    out = []
    i = 0
    tip_depth = 0
    while i < len(text):
        if text.startswith("\\n", i):
            i += 2
            continue
        m = TAG.match(text, i)
        if m:
            token = m.group(0)
            if token.startswith("<TIP") and not token.startswith("</"):
                tip_depth += 1
            elif token == "</TIP>" and tip_depth:
                tip_depth -= 1
            out.append((token, 0, False, False))
            i = m.end()
            continue
        ch = text[i]
        protected = tip_depth > 0
        preferred = (not protected and (ch.isspace() or ch in "。！？!?….,，、:：;；"))
        out.append((ch, 1, not protected, preferred))
        i += 1
    return out


def wrap(text: str) -> str:
    if not text or "\\n" not in text:
        original = text
    else:
        original = text
    us = units(original)
    total = sum(u[1] for u in us)
    existing = original.count("\\n") + 1
    current_max = max((sum(u[1] for u in units(part)) for part in original.split("\\n")), default=0)
    if total <= LIMIT and existing <= 2 and current_max <= LIMIT:
        return original
    if total > LIMIT * 2:
        return original

    visible_before = 0
    candidates = []
    for idx, unit in enumerate(us[:-1], 1):
        visible_before += unit[1]
        if visible_before <= LIMIT and unit[2]:
            candidates.append((idx, visible_before, unit[3]))

    valid = [c for c in candidates if total - c[1] <= LIMIT and c[1] > 0]
    if not valid:
        return original

    preferred = [c for c in valid if c[2]]
    pool = preferred or valid
    idx, _, _ = min(pool, key=lambda c: abs(LIMIT - c[1]))
    left = "".join(u[0] for u in us[:idx]).rstrip()
    right = "".join(u[0] for u in us[idx:]).lstrip()
    return left + "\\n" + right


def main() -> None:
    rows = []
    changed = 0
    still_long = []
    for raw in MAP.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        # The JSON source uses the two literal characters backslash+n.  Some
        # earlier hand patches were parsed as real newlines; normalize those
        # before applying the layout pass.
        before = row["ko"].replace("\n", r"\n")
        after = wrap(before)
        if after != before:
            changed += 1
        row["ko"] = after
        body_lens = [len(TAG.sub("", part)) for part in after.split("\\n")]
        if max(body_lens, default=0) > LIMIT or len(body_lens) > 2:
            still_long.append((row["id"], max(body_lens, default=0), len(body_lens)))
        rows.append(row)
    MAP.write_text("\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows) + "\n", encoding="utf-8")
    print(f"wrapped {changed} entries; manual layout cases remaining: {len(still_long)}")
    for item in still_long[:20]:
        print(item)


if __name__ == "__main__":
    main()
