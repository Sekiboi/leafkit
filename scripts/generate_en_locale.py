"""Generate locales/en.json from _(\"...\") markers and remaining text= attributes."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
found: set[str] = set()

for path in (ROOT / "sekikit").glob("*.py"):
    text = path.read_text(encoding="utf-8")
    found |= set(re.findall(r'_\(\s*"([^"]+)"\s*\)', text))
    found |= set(re.findall(r"_\(\s*'([^']+)'\s*\)", text))
    for m in re.finditer(r'_\(\s*((?:"[^"]*"\s*)+)\)', text):
        parts = re.findall(r'"([^"]*)"', m.group(1))
        if parts:
            found.add("".join(parts))
    found |= set(re.findall(r'(?<!_)\btext="([^"]{2,160})"', text))

extra = [
    "Merge",
    "Mix",
    "Extract",
    "Delete",
    "Insert",
    "Split",
    "Rotate",
    "Organize",
    "Share",
    "Compress",
    "Clean metadata",
    "Encrypt",
    "Crop margins",
    "Images → PDF",
    "N-up",
    "Grayscale",
    "Sekikit",
]
found |= set(extra)

cat = {s: s for s in sorted(found) if any(c.isalpha() for c in s)}
out = ROOT / "locales" / "en.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {out} ({len(cat)} strings)")
