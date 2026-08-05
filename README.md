# Sekikit

Offline PDF tools for Windows. Merge, split, organize, compress, and more — **on your PC only**. No accounts, no uploads, no paid tier.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Offline](https://img.shields.io/badge/privacy-100%25%20offline-brightgreen)
![Beta](https://img.shields.io/badge/status-public%20beta-orange)

<p align="center">
  <img src="assets/sekikit.png" width="96" height="96" alt="Sekikit">
</p>

**Public beta** `0.15.0-beta.1` · Free forever (MIT)

---

## Download (Windows)

[**Latest release — Setup installer**](https://github.com/Sekiboi/sekikit/releases/latest)

Use the `Sekikit-*-Setup.exe` asset. The installer is **unsigned**, so Windows SmartScreen may warn; choose **More info → Run anyway** if you trust the build. Prefer verifying against `SHA256SUMS.txt` on the release page when present.

After install: Start Menu → **Sekikit**. Settings and logs live under `%LOCALAPPDATA%\Sekikit` (not Program Files).

Linux and macOS are supported from source / package scripts but are **untested on real hardware**. See [docs/LINUX.md](docs/LINUX.md) and [docs/MAC.md](docs/MAC.md).

---

## Features

| Area | Tools |
|------|--------|
| **Organize** | Multi-PDF page tray: load, reorder, preview, extract, remove, rotate, save |
| **Share** | Compress, clean metadata, encrypt/unlock, crop, resize, reverse, stamp image, text extract, images→PDF, N-up, grayscale, page numbers, flatten |
| **Structure** | Merge, mix, extract, delete, insert, split, rotate |
| **Watch** | Local folder batch (compress, clean, grayscale, page numbers, …) |
| **CLI** | Same toolkit from the command line |

Password-protected PDFs open with a session password only; nothing is uploaded.

Not a full PDF editor (no OCR, no in-document text rewrite). See [docs/LIMITS.md](docs/LIMITS.md).

---

## Using the app

1. **Add PDFs…** or drop files onto the window (list order matters for merge).
2. Select a file in the list (↑/↓). Double-click opens **Organize**.
3. Use **Quick** chips for Organize / Merge / Compress / Split.
4. Leave output paths blank to auto-name next to the source (never overwrites; adds `_1`, `_2`, …).
5. Page ranges are **1-based**: `1-3`, `2,5,9`, `1,4-6,10-`.
6. **Share → All listed files** runs some tools on every file in the list (Esc cancels between files).
7. **Settings → Review before save**: Off / Risk only (default) / Always. Preview is on-screen only; Cancel discards the new file.

---

## Privacy

Sekikit does not phone home. PDFs stay on your machine unless you copy them elsewhere.

**Optional anonymous diagnostics** (default **off**): first launch may ask once; change anytime in Settings. If enabled, **About (F1)** can **Copy** or **Save** a local text report — no name, account, device ID, or PDF content. The app never uploads it; you only share it if you paste it into a GitHub issue.

Details: [docs/PRIVACY.md](docs/PRIVACY.md) · [docs/REPORTING.md](docs/REPORTING.md)

---

## Run from source

Requires **Python 3.10+**.

```powershell
git clone https://github.com/Sekiboi/sekikit.git
cd sekikit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pythonw run.py
```

```bash
# Linux / macOS (GUI untested on real hardware)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/run_linux_mac.sh
```

Use the project venv so dependencies resolve correctly.

---

## CLI

After `pip install -e .` (or with `PYTHONPATH` set to the repo root):

```text
sekikit info file.pdf
sekikit merge a.pdf b.pdf -o out.pdf
sekikit extract in.pdf --pages 1-3 -o out.pdf
sekikit split in.pdf --mode every_n --n 2 -d outdir
sekikit compress in.pdf --preset email -o small.pdf
sekikit gui
sekikit --help
```

---

## Build (Windows)

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_exe.ps1          # dist\Sekikit\Sekikit.exe (onedir)
.\scripts\build_installer.ps1    # Setup.exe (needs Inno Setup 6)
```

See [docs/INSTALLER.md](docs/INSTALLER.md). Local zip without publishing: `.\scripts\package_local_release.ps1`.

---

## Develop

```powershell
pip install -r requirements.txt pytest
pytest -q
```

- Icon assets: `assets/sekikit.png`, `assets/sekikit.ico` (`python scripts/make_icon.py` to regenerate)
- Translations: English UI; community locales welcome — [docs/TRANSLATING.md](docs/TRANSLATING.md)
- Issues: [Bug / Crash templates](https://github.com/Sekiboi/sekikit/issues/new/choose)

---

## License

[MIT](LICENSE) — free for personal and commercial use. **No paid edition.**
