"""One-off helper: list likely UI strings from app.py."""
import re
from pathlib import Path

text = Path("sekikit/app.py").read_text(encoding="utf-8")
found = set(re.findall(r'text="([^"]{2,100})"', text))
found |= set(re.findall(r"text='([^']{2,100})'", text))
for s in sorted(found):
    if any(c.isalpha() for c in s) and not s.startswith("http"):
        print(s)
