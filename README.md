# Sekikit

**Offline PDF page toolkit.** Merge, extract, split, organize, and compress PDFs on your PC — no accounts, no uploads.  
Primary GUI target: **Windows**. Linux and macOS are available but **untested** on real hardware ([Linux](docs/LINUX.md), [macOS](docs/MAC.md)).

### Status: public beta (`0.15.0-beta.1`)

Works for real offline PDF work; still wants feedback and polish.

**Download (Windows):** [Latest Release — Setup installer](https://github.com/Sekiboi/sekikit/releases/latest)  
*(Use the `Sekikit-*-Setup.exe` asset. SmartScreen may warn on unsigned freeware*

### Free forever

**There will never be paid features.** Everything we build is free for everyone — no freemium, no trials, no watermarks, no accounts. MIT-licensed freeware.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Offline](https://img.shields.io/badge/privacy-100%25%20offline-brightgreen)
![Beta](https://img.shields.io/badge/status-public%20beta-orange)

<p align="center">
  <img src="assets/sekikit.png" width="96" height="96" alt="Sekikit icon — leaf / folded page">
</p>

## What it does

Sekikit is a small offline app for everyday **page structure** work: put pages together, take them apart, clean them up for sharing, keep files on this computer.

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

Minimal **leaf / folded page** mark on open-sky blue (same blue/white palette). Used for:

- Window title bar + taskbar  
- In-app header  
- Packaged `.exe`  
- Desktop / Start Menu shortcuts  
- GitHub README  

Assets: `assets/sekikit.png`, `assets/sekikit.ico`  
Regenerate: `python scripts/make_icon.py`

## Requirements

- **Windows 10/11** (primary GUI + packaged `.exe`)
- **Linux** *(untested on real hardware)*: CLI, run-from-source GUI, package scripts — [docs/LINUX.md](docs/LINUX.md)
- **macOS** *(untested on real hardware)*: CLI, run-from-source GUI, package scripts — [docs/MAC.md](docs/MAC.md)
- Python 3.10+ **or** a Windows release binary from [Releases](https://github.com/Sekiboi/sekikit/releases)

## Does a git commit make it a real app?

**No.** Committing only saves source code on GitHub. It does **not** install an app on Windows.

To get a normal app (app icon, no `.vbs`):

```powershell
cd path\to\sekikit
.\.venv\Scripts\Activate.ps1   # first time: create venv + pip install -r requirements.txt
.\scripts\build_exe.ps1        # builds dist\Sekikit\Sekikit.exe with our icon
.\scripts\install_shortcuts.ps1  # Desktop + Start Menu shortcuts with bird icon
```

Then open **Sekikit** from the Desktop or Start Menu like any other program.

| What | What you get |
|------|----------------|
| GitHub commit/push | Source only |
| `dist\Sekikit\Sekikit.exe` | Real standalone app + our icon |
| Desktop/Start shortcuts | One-click launch with bird icon |
| `launch.vbs` / `launch.bat` | Dev helpers only (optional) |

## Run from source (Windows)

| Launcher | Notes |
|----------|--------|
| **`Sekikit.lnk`** | After `install_shortcuts.ps1` — defaults to **source** (current version) |
| **`launch.bat`** | Defaults to **source** via venv; set `SEKIKIT_USE_EXE=1` for packaged |
| **`run.pyw`** | Double-click no-console entry (needs venv deps) |
| PowerShell + `pythonw run.py` | Dev |

> **Version mismatch?** Desktop/Start shortcuts or `launch.bat` used to prefer an old `dist\` build. They now prefer source. For a packaged build: `.\scripts\build_exe.ps1` then `.\scripts\install_shortcuts.ps1 -UsePackagedExe`.
```powershell
git clone https://github.com/Sekiboi/sekikit.git
cd sekikit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pythonw run.py
```

> **Important:** use the project venv. Plain system `python run.py` will miss packages.

Drag-and-drop PDFs (or a folder of PDFs) onto the window to add them.

### Install (Windows install-and-play)

```powershell
.\scripts\build_installer.ps1   # needs Inno Setup 6; produces dist\installer\Sekikit-*-Setup.exe
```

Or use the portable folder `dist\Sekikit\` after `.\scripts\build_exe.ps1`.  
See [docs/INSTALLER.md](docs/INSTALLER.md).

### If it crashes or something is wrong

1. **Anonymous diagnostics** are optional (off by default; asked once on first launch; Settings anytime).  
2. If enabled: **About (F1) → Copy diagnostics** (or Save). Reports have no name, account, or device ID.  
3. Open a [GitHub Issue](https://github.com/Sekiboi/sekikit/issues/new/choose) and paste the report.  

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
sekikit info file.pdf
sekikit merge a.pdf b.pdf -o out.pdf --page-size letter --bookmarks
sekikit mix a.pdf b.pdf -o mixed.pdf --reverse-second
sekikit insert base.pdf extra.pdf --at-page 2 -o out.pdf
sekikit extract in.pdf --pages 1-3 -o out.pdf
sekikit split in.pdf --mode every_n --n 2 -d outdir
sekikit assemble a.pdf:1 b.pdf:3 a.pdf:2 -o out.pdf
sekikit images photo1.jpg photo2.png -o album.pdf
sekikit compress in.pdf --preset email -o small.pdf
sekikit nup in.pdf -n 4 -o handout.pdf
sekikit grayscale in.pdf -o gray.pdf
sekikit page-numbers in.pdf -o numbered.pdf --format "{n} / {total}" --position footer
sekikit renumber merged.pdf -o continuous.pdf
sekikit flatten form.pdf -o flat.pdf
sekikit text in.pdf -o out.txt
sekikit text in.pdf --stdout
sekikit crop-box in.pdf --x0 36 --y0 36 --x1 576 --y1 756 --hard -o out.pdf
sekikit stamp-image in.pdf logo.png -o out.pdf --position bottom-right --scale 0.2
sekikit watch ./inbox -o ./outbox --action compress --once
sekikit gui
sekikit --help
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

Prefer the **onedir** build (`dist\Sekikit\Sekikit.exe`).

## Linux

> **Untested on real hardware.** Prefer Windows Setup for a known-good install.

From source (after venv + `pip install -r requirements.txt`):

```bash
./scripts/run_linux_mac.sh          # GUI
./scripts/run_linux_mac.sh cli info file.pdf
./scripts/run_linux_mac.sh test
```

Packaged build on a Linux machine:

```bash
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
# → dist/release/Sekikit-linux-*.tar.gz  (+ AppImage if appimagetool present)
```

Full notes: **[docs/LINUX.md](docs/LINUX.md)**.

## macOS

> **Untested on real hardware.** Prefer Windows Setup for a known-good install.

From source (after venv + `pip install -r requirements.txt`):

```bash
./scripts/run_linux_mac.sh          # GUI
./scripts/run_linux_mac.sh cli info file.pdf
./scripts/run_linux_mac.sh test
```

Packaged build on a Mac:

```bash
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
# → dist/release/Sekikit-macos-*.tar.gz
```

Full notes: **[docs/MAC.md](docs/MAC.md)**.

GitHub Actions workflow **Package Unix** (tag `v*` or Run workflow) builds Linux and macOS artifacts separately.

PRs welcome. Keep the scope small.

## License

MIT — free for personal and commercial use. See [LICENSE](LICENSE).

**No paid edition. No dual licensing tricks. Features stay free.**

## Privacy

Sekikit never phones home. Your PDFs never leave your machine unless *you* copy them somewhere.

### Optional anonymous diagnostics (you will be asked)

On **first launch**, Sekikit may ask whether to enable **anonymous diagnostics export**. The checkbox **defaults off**.

| If you leave it **off** (default) | If you turn it **on** |
|-----------------------------------|------------------------|
| No Copy/Save diagnostics in About | About can build a **local** text report |
| App still works fully offline | Still **offline** — nothing is uploaded by the app |

**Anonymous means:** no name, account, email, device ID, or hostname. Crash/job tails redact home paths and similar. No PDF content or passwords.

**Important:** Sekikit does **not** send diagnostics anywhere. Enabling only lets *you* copy or save a report. Only if *you* paste it into a GitHub Issue (or email, etc.) does it leave your PC.

You can change this anytime in **Settings**. Details: [docs/PRIVACY.md](docs/PRIVACY.md) and [docs/REPORTING.md](docs/REPORTING.md).

See **[docs/PRIVACY.md](docs/PRIVACY.md)** and **[docs/LIMITS.md](docs/LIMITS.md)** for the full honesty list (RAM, signatures, scan-compress, unsigned builds, etc.).

## Translations (community)

The application interface is written in **English**.

**Other languages can be added** if there is interest:

- **Request a language** by opening a GitHub Issue (describe the language you need).
- **Contribute a translation yourself** by following **[docs/TRANSLATING.md](docs/TRANSLATING.md)** and sending a Pull Request.
- You can test a language with: `$env:SEKIKIT_LANG = "fr"` (example), then run the app.
- If a translation is missing or incomplete, the app shows **English** for those parts.

This project is free software. Community translations are welcome and remain free for everyone.

## Local release package (no publish)

```powershell
.\scripts\package_local_release.ps1
```

Creates `release\Sekikit-<version>\` with the app, LICENSE, docs, and `SHA256SUMS.txt`, plus a zip. **Does not upload or push anything.**
