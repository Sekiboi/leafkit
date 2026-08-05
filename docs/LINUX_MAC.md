# Leafkit on Linux and macOS

**Windows remains the primary polished GUI** (signed `.exe` when you have a cert).  
Linux and macOS are first-class for **CLI**, **tests**, **run-from-source GUI**, and **CI-built packages**.

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
python -m leafkit.cli --help      # CLI
```

### System packages

```bash
# Debian / Ubuntu
sudo apt install python3 python3-venv python3-tk python3-pip

# Fedora
sudo dnf install python3 python3-tkinter
```

**macOS:** python.org installer (includes Tk), or Homebrew `python`.  
Optional: [Ghostscript](https://www.ghostscript.com/) for smaller compress output (local only).

## Packaged GUI builds

### Build on your machine

```bash
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
```

Outputs land in `dist/` and `dist/release/`:

| OS | Artifact |
|----|----------|
| **Linux** | `Leafkit-linux-<arch>.tar.gz` (onedir + `leafkit-run.sh`) |
| **Linux** | `Leafkit-<arch>.AppImage` when `appimagetool` is available |
| **macOS** | `Leafkit-macos-<arch>.tar.gz` (`.app` or onedir) |

### GitHub Actions

Workflow **Package Unix** (`.github/workflows/package-unix.yml`):

- Runs on **tag** `v*` or **workflow_dispatch**
- Uploads **leafkit-linux** and **leafkit-macos** artifacts

```bash
# After a release tag:
# Actions → Package Unix → download artifacts
```

### Run packaged Linux

```bash
tar -xzf Leafkit-linux-x86_64.tar.gz
cd Leafkit
./leafkit-run.sh
# or
./Leafkit
```

AppImage (if present):

```bash
chmod +x Leafkit-x86_64.AppImage
./Leafkit-x86_64.AppImage
```

### Run packaged macOS

```bash
tar -xzf Leafkit-macos-arm64.tar.gz   # or x86_64
open Leafkit.app
# If Gatekeeper blocks: right-click → Open (unsigned builds)
```

**Notarization / Apple signing** are optional and require an Apple Developer account — same idea as Windows code signing. Unsigned builds work; macOS may warn once.

## What works cross-platform

| Feature | Linux / mac |
|---------|-------------|
| CLI (full toolkit) | Yes |
| Core PDF ops + pytest | Yes |
| GUI from source | Yes (needs Tk) |
| Packaged GUI (CI / `build_unix.sh`) | Yes |
| Drag-and-drop | Best-effort (`tkinterdnd2`) |
| Code-signed store installers | Not yet (optional later) |

## Still free forever

No cloud, no accounts, no paid tier. Same MIT license on every OS.
