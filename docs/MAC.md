# Leafkit on macOS

**Windows is the primary supported install** (Setup.exe).  
macOS is available for **CLI**, **run-from-source GUI**, and **package scripts**.

> **Untested on real hardware:** macOS installs have **not** been validated on physical machines by the maintainer. Scripts and CI may pass; expect rough edges. Prefer Windows Setup for a known-good install, or report issues if you try macOS.

Everything stays **offline**, **MIT**, and **free forever**.

## Quick start (from source)

```bash
git clone https://github.com/Sekiboi/leafkit.git
cd leafkit
chmod +x scripts/run_linux_mac.sh
./scripts/run_linux_mac.sh          # GUI
./scripts/run_linux_mac.sh cli info file.pdf
./scripts/run_linux_mac.sh test
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py                       # GUI
python -m leafkit.cli --help        # CLI
```

### System packages

Install Python 3.10+ from [python.org](https://www.python.org/) (includes Tk), or Homebrew `python`.

Optional: Ghostscript for smaller compress output (local only).

## Packaged GUI builds

### Build on your machine

```bash
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
```

macOS output under `dist/` / `dist/release/`:

| Artifact | Notes |
|----------|--------|
| `Leafkit-macos-<arch>.tar.gz` | `.app` or onedir |

### GitHub Actions

Workflow **Package Unix** (`.github/workflows/package-unix.yml`):

- Runs on **tag** `v*` or **workflow_dispatch**
- Uploads **leafkit-macos** artifacts (among others)

### Run packaged macOS

```bash
tar -xzf Leafkit-macos-arm64.tar.gz   # or x86_64
open Leafkit.app
# If Gatekeeper blocks: right-click → Open (unsigned builds)
```

**Notarization / Apple signing** are optional and require an Apple Developer account. Unsigned builds work; macOS may warn once.

## What works (expected)

| Feature | macOS |
|---------|--------|
| CLI (full toolkit) | Yes |
| Core PDF ops + pytest | Yes (CI) |
| GUI from source | Yes (needs Tk) |
| Packaged GUI | Scripts exist; **untested** on real hardware |
| Drag-and-drop | Best-effort (`tkinterdnd2`) |

## Still free forever

No cloud, no accounts, no paid tier. Same MIT license on every OS.
