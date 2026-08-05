# Leafkit

**Offline PDF page toolkit.** Merge, extract, split, organize, and compress PDFs on your PC — no accounts, no uploads.  
Primary GUI target: **Windows**. CLI + source GUI also work on **Linux/mac** (see [docs/LINUX_MAC.md](docs/LINUX_MAC.md)).

Just the pages you need.  
*(Formerly JustPages — renamed in v0.14.0 for a unique brand.)*

### Status: public beta (`0.15.0-beta.1`)

Works for real offline PDF work; still wants feedback and polish. Prefer filing issues over silent frustration.

**Download (Windows):** [Latest Release — Setup installer](https://github.com/Sekiboi/leafkit/releases/latest)  
*(Use the `Leafkit-*-Setup.exe` asset. SmartScreen may warn on unsigned freeware — expected until reputation builds.)*

### Free forever

**There will never be paid features.** Everything we build is free for everyone — no freemium, no trials, no watermarks, no accounts. MIT-licensed freeware.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Offline](https://img.shields.io/badge/privacy-100%25%20offline-brightgreen)
![Beta](https://img.shields.io/badge/status-public%20beta-orange)

<p align="center">
  <img src="assets/leafkit.png" width="96" height="96" alt="Leafkit icon — bird in flight (freedom)">
</p>

## What it does

Leafkit is a small offline app for everyday **page structure** work: put pages together, take them apart, clean them up for sharing, keep files on this computer.

| Action | What it does |
|--------|----------------|
| **Organize** | Multi-PDF **page tray**: load/add pages, reorder, preview, save combined; extract/remove/rotate |
| **Share** | Compress, clean, encrypt/unlock, crop (margin + interactive), resize, reverse, **stamp image**, extract text, images→PDF, N-up, grayscale, **page numbers**, flatten |
| **Merge** | Combine PDFs; ranges; bookmarks; fit size; optional **renumber after merge** |
| **Watch** | Local folder batch (compress / grayscale / page numbers / renumber / flatten / clean) |
| **Mix / Extract / Delete / Insert / Split / Rotate** | Page structure tools |
| **Password** | Open protected PDFs (stays on your PC) |
| **CLI** | Full toolkit: merge, split, mix, insert, images, assemble, compress, renumber, watch, … |

## Icon

Minimal **bird in flight** on open-sky blue — offline software, free to use. Used for:

- Window title bar + taskbar  
- In-app header  
- Packaged `.exe`  
- Desktop / Start Menu shortcuts  
- GitHub README  

Assets: `assets/leafkit.png`, `assets/leafkit.ico`  
Regenerate: `python scripts/make_icon.py`

## Requirements

- **Windows 10/11** (primary GUI + packaged `.exe`)
- **Linux / macOS**: CLI, run-from-source GUI, and **CI/package builds** (tarball / AppImage / `.app`) — [docs/LINUX_MAC.md](docs/LINUX_MAC.md)
- Python 3.10+ **or** a Windows release binary from [Releases](https://github.com/Sekiboi/leafkit/releases)

## Does a git commit make it a real app?

**No.** Committing only saves source code on GitHub. It does **not** install an app on Windows.

To get a normal app (bird icon, no `.vbs`):

```powershell
cd path\to\leafkit
.\.venv\Scripts\Activate.ps1   # first time: create venv + pip install -r requirements.txt
.\scripts\build_exe.ps1        # builds dist\Leafkit\Leafkit.exe with our icon
.\scripts\install_shortcuts.ps1  # Desktop + Start Menu shortcuts with bird icon
```

Then open **Leafkit** from the Desktop or Start Menu like any other program.

| What | What you get |
|------|----------------|
| GitHub commit/push | Source only |
| `dist\Leafkit\Leafkit.exe` | Real standalone app + our icon |
| Desktop/Start shortcuts | One-click launch with bird icon |
| `launch.vbs` / `launch.bat` | Dev helpers only (optional) |

## Run from source (Windows)

| Launcher | Notes |
|----------|--------|
| **`Leafkit.lnk`** | After `install_shortcuts.ps1` — defaults to **source** (current version) |
| **`launch.bat`** | Defaults to **source** via venv; set `LEAFKIT_USE_EXE=1` for packaged |
| **`run.pyw`** | Double-click no-console entry (needs venv deps) |
| PowerShell + `pythonw run.py` | Dev |

> **Version mismatch?** Desktop/Start shortcuts or `launch.bat` used to prefer an old `dist\` build. They now prefer source. For a packaged build: `.\scripts\build_exe.ps1` then `.\scripts\install_shortcuts.ps1 -UsePackagedExe`.
```powershell
git clone https://github.com/Sekiboi/leafkit.git
cd leafkit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pythonw run.py
```

> **Important:** use the project venv. Plain system `python run.py` will miss packages.

Drag-and-drop PDFs (or a folder of PDFs) onto the window to add them.

### Install (Windows install-and-play)

```powershell
.\scripts\build_installer.ps1   # needs Inno Setup 6; produces dist\installer\Leafkit-*-Setup.exe
```

Or use the portable folder `dist\Leafkit\` after `.\scripts\build_exe.ps1`.  
See [docs/INSTALLER.md](docs/INSTALLER.md).

### If it crashes or something is wrong

1. **Anonymous diagnostics** are optional (off by default; asked once on first launch; Settings anytime).  
2. If enabled: **About (F1) → Copy diagnostics** (or Save). Reports have no name, account, or device ID.  
3. Open a [GitHub Issue](https://github.com/Sekiboi/leafkit/issues/new/choose) and paste the report.  

Nothing is sent automatically — see [docs/REPORTING.md](docs/REPORTING.md) and [docs/PRIVACY.md](docs/PRIVACY.md).

## Usage tips

1. **Add PDFs…** or drop files onto the window (order matters for merge).
2. **Click a file** in the list to select it (↑/↓ also works). Double-click opens **Organize**.
3. **Quick** chips jump to Organize / Merge / Compress / Split.
4. Leave output paths blank to auto-name next to the source (never overwrites — adds `_1`, `_2`, …).
4b. **Share → All listed files**: run compress/clean/encrypt/unlock/resize/grayscale on every PDF in the list (Esc cancels between files; batch skips review).
5. Page ranges are **1-based**. Examples: `1-3`, `2,5,9`, `1,4-6,10-`.
6. After a job finishes, use the **toast** → Open file / Open folder.
7. **Settings → Review before save**: Off / Risk only (default) / Always. Screen preview only — not a print proof. Cancel discards the new file.

Password-protected PDFs: enter the password in the top field (session only, never uploaded).

## CLI

```powershell
leafkit info file.pdf
leafkit merge a.pdf b.pdf -o out.pdf --page-size letter --bookmarks
leafkit mix a.pdf b.pdf -o mixed.pdf --reverse-second
leafkit insert base.pdf extra.pdf --at-page 2 -o out.pdf
leafkit extract in.pdf --pages 1-3 -o out.pdf
leafkit split in.pdf --mode every_n --n 2 -d outdir
leafkit assemble a.pdf:1 b.pdf:3 a.pdf:2 -o out.pdf
leafkit images photo1.jpg photo2.png -o album.pdf
leafkit compress in.pdf --preset email -o small.pdf
leafkit nup in.pdf -n 4 -o handout.pdf
leafkit grayscale in.pdf -o gray.pdf
leafkit page-numbers in.pdf -o numbered.pdf --format "{n} / {total}" --position footer
leafkit renumber merged.pdf -o continuous.pdf
leafkit flatten form.pdf -o flat.pdf
leafkit text in.pdf -o out.txt
leafkit text in.pdf --stdout
leafkit crop-box in.pdf --x0 36 --y0 36 --x1 576 --y1 756 --hard -o out.pdf
leafkit stamp-image in.pdf logo.png -o out.pdf --position bottom-right --scale 0.2
leafkit watch ./inbox -o ./outbox --action compress --once
leafkit gui
leafkit --help
```

## Tests

```powershell
pip install -r requirements.txt pytest
pytest -q
```

## Build a Windows `.exe`

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_exe.ps1
.\scripts\install_shortcuts.ps1
```

Prefer the **onedir** build (`dist\Leafkit\Leafkit.exe`).

## Build Linux / macOS packages

```bash
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
# → dist/release/Leafkit-linux-*.tar.gz  (+ AppImage if appimagetool present)
# → dist/release/Leafkit-macos-*.tar.gz
```

GitHub Actions: workflow **Package Unix** (on tag `v*` or Run workflow). See [docs/LINUX_MAC.md](docs/LINUX_MAC.md).

## Linux / macOS

```bash
# after venv + pip install -r requirements.txt
./scripts/run_linux_mac.sh          # GUI
./scripts/run_linux_mac.sh cli info file.pdf
./scripts/run_linux_mac.sh test
```

Full notes: **[docs/LINUX_MAC.md](docs/LINUX_MAC.md)**. CI runs pytest on Windows, Ubuntu, and macOS.

## Roadmap

See **[ROADMAP.md](ROADMAP.md)** — scope, phases, and free-forever principles (page toolkit, not a full PDF editor; no paid tier).

PRs welcome. Keep the scope small.

## License

MIT — free for personal and commercial use. See [LICENSE](LICENSE).

**No paid edition. No dual licensing tricks. Features stay free.**

## Privacy

Leafkit never phones home. Your PDFs never leave your machine unless *you* copy them somewhere.

See **[docs/PRIVACY.md](docs/PRIVACY.md)** and **[docs/LIMITS.md](docs/LIMITS.md)** for the full honesty list (RAM, signatures, scan-compress, unsigned builds, etc.).

## Translations (community)

The application interface is written in **English**.

**Other languages can be added** if there is interest:

- **Request a language** by opening a GitHub Issue (describe the language you need).
- **Contribute a translation yourself** by following **[docs/TRANSLATING.md](docs/TRANSLATING.md)** and sending a Pull Request.
- You can test a language with: `$env:LEAFKIT_LANG = "fr"` (example), then run the app.
- If a translation is missing or incomplete, the app shows **English** for those parts.

This project is free software. Community translations are welcome and remain free for everyone.

## Local release package (no publish)

```powershell
.\scripts\package_local_release.ps1
```

Creates `release\Leafkit-<version>\` with the app, LICENSE, docs, and `SHA256SUMS.txt`, plus a zip. **Does not upload or push anything.**
