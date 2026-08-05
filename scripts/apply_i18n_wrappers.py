"""Wrap text=\"...\" in app.py with _() when the string is in en.json.

Idempotent: skips already-wrapped _("...").
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
app_path = ROOT / "leafkit" / "app.py"
en = json.loads((ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
keys = set(en.keys())

text = app_path.read_text(encoding="utf-8")

if "from leafkit.i18n import" not in text:
    text = text.replace(
        "from leafkit import render as pdf_render\n",
        "from leafkit import render as pdf_render\n"
        "from leafkit.i18n import _, init_i18n\n",
        1,
    )

if "init_i18n()" not in text:
    text = text.replace(
        "def main() -> None:\n    try:\n        app = LeafkitApp()\n",
        "def main() -> None:\n    try:\n        init_i18n()\n        app = LeafkitApp()\n",
        1,
    )


def repl_text_kw(m: re.Match[str]) -> str:
    s = m.group(1)
    if s not in keys:
        return m.group(0)
    return f'text=_("{s}")'


pattern = re.compile(r'(?<!_)\btext="([^"]*)"')
new_text, n = pattern.subn(repl_text_kw, text)

app_path.write_text(new_text, encoding="utf-8")
print(f"Wrapped text= attributes where possible ({n} total pattern hits processed)")
