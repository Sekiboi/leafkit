# JustPages

**Offline PDF page toolkit for Windows.** Merge, extract, split, and rotate PDFs — no accounts, no uploads, no nagware.

Just the pages you need.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Offline](https://img.shields.io/badge/privacy-100%25%20offline-brightgreen)

## Why

Most “free PDF tools” either:

- upload your files to someone else’s server, or
- bury basic page ops under freemium junk and giant installers

**JustPages** does four jobs well, entirely on your PC:

| Action | What it does |
|--------|----------------|
| **Merge** | Combine PDFs in order |
| **Extract** | Pull a page range into a new PDF (`2-5, 9`) |
| **Split** | One file per page, or every N pages |
| **Rotate** | 90° / 180° / 270° (all pages or a range) |

## Requirements

- Windows 10/11 (primary target)
- Python 3.10+ **or** a release binary from [Releases](https://github.com/Sekiboi/justpages/releases)

## Run from source

```powershell
git clone https://github.com/Sekiboi/justpages.git
cd justpages
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Or:

```powershell
python -m justpages
```

## Usage tips

1. **Add PDFs…** to build the list (order matters for merge).
2. Use **↑ / ↓** and **Selected row** to pick which file Extract / Split / Rotate acts on.
3. Leave output paths blank to auto-name files next to the source (never overwrites — adds `_1`, `_2`, …).
4. Page numbers are **1-based**. Examples: `1-3`, `2,5,9`, `1,4-6,10-`.

Password-protected PDFs are not fully supported yet (empty-password “owner” locks may work).

## Tests

```powershell
pip install -r requirements.txt pytest
pytest -q
```

## Build a Windows `.exe` (optional)

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name JustPages --onefile run.py
```

The binary lands in `dist\JustPages.exe`.

## Roadmap (maybe)

- Drag-and-drop onto the window
- Right-click “Send to JustPages”
- Reorder pages inside a single PDF
- Delete pages
- PDF metadata strip

PRs welcome. Keep the scope small.

## License

MIT — free for personal and commercial use. See [LICENSE](LICENSE).

## Privacy

JustPages never phones home. Your PDFs never leave your machine unless *you* copy them somewhere.
