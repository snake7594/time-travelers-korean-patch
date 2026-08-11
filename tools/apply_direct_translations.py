"""Apply Codex-authored translations from script_json/direct_ko.jsonl."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "script_json"
MAP = SCRIPT_DIR / "direct_ko.jsonl"


def main() -> int:
    translations: dict[str, str] = {}
    for line_number, line in enumerate(MAP.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if set(row) != {"id", "ko"}:
            raise ValueError(f"line {line_number}: expected id and ko")
        if row["id"] in translations:
            raise ValueError(f"duplicate id: {row['id']}")
        translations[row["id"]] = row["ko"]

    applied = 0
    for path in sorted(SCRIPT_DIR.glob("*.json")):
        if path.name == "manifest.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if "entries" not in data:
            continue
        changed = False
        for entry in data["entries"]:
            if entry["id"] in translations:
                entry["ko"] = translations[entry["id"]]
                applied += 1
                changed = True
        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"applied {applied} translations from {len(translations)} map entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
