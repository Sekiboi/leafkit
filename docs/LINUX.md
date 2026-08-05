# Sekikit on Linux

**Windows is the primary supported install** (Setup.exe).  
Linux is available for **CLI**, **run-from-source GUI**, and **package scripts**.

> **Untested on real hardware:** Linux installs have **not** been validated on physical machines by the maintainer. Scripts and CI may pass; expect rough edges. Prefer Windows Setup for a known-good install, or report issues if you try Linux.

Everything stays **offline**, **MIT**, and **free forever**.

## Quick start (from source)

```bash
git clone https://github.com/Sekiboi/sekikit.git
cd sekikit
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
python -m sekikit.cli --help        # CLI
```

### System packages

```bash
# Debian / Ubuntu
sudo apt install python3 python3-venv python3-tk python3-pip

# Fedora
sudo dnf install python3 python3-tkinter
```

Optional: install Ghostscript from your distro for smaller compress output (local only).

## Packaged GUI builds

### Build on your machine

```bash
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
```

Linux outputs under `dist/` / `dist/release/`:

| Artifact | Notes |
|----------|--------|
| `Sekikit-linux-<arch>.tar.gz` | onedir + `sekikit-run.sh` |
| `Sekikit-<arch>.AppImage` | when `appimagetool` is available |

### GitHub Actions

Workflow **Package Unix** (`.github/workflows/package-unix.yml`):

- Runs on **tag** `v*` or **workflow_dispatch**
- Uploads **sekikit-linux** artifacts (among others)

### Run packaged Linux

```bash
tar -xzf Sekikit-linux-x86_64.tar.gz
cd Sekikit
./sekikit-run.sh
# or
./Sekikit
```

AppImage (if present):

```bash
chmod +x Sekikit-x86_64.AppImage
./Sekikit-x86_64.AppImage
```

## What works (expected)

| Feature | Linux |
|---------|--------|
| CLI (full toolkit) | Yes |
| Core PDF ops + pytest | Yes (CI) |
| GUI from source | Yes (needs Tk) |
| Packaged GUI | Scripts exist; **untested** on real hardware |
| Drag-and-drop | Best-effort (`tkinterdnd2`) |

## Still free forever

No cloud, no accounts, no paid tier. Same MIT license on every OS.
