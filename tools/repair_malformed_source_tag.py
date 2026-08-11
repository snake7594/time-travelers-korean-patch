"""Repair the one malformed timing tag in the extracted H04 source."""

import json
from pathlib import Path


path = Path("script_json/H04.json")
doc = json.loads(path.read_text(encoding="utf-8"))
for entry in doc["entries"]:
    if entry["id"] == "H04:4:8":
        entry["ja"] = entry["ja"].replace("<W10]>", "<W10>")
        entry["ja_read"] = entry["ja_read"].replace("<W10]>", "<W10>")
        break
else:
    raise SystemExit("H04:4:8 not found")
path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("repaired H04:4:8 source timing tag")
