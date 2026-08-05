#!/usr/bin/env bash
# Build Leafkit GUI packages for Linux (onedir + optional AppImage) and macOS (.app).
# Run on the target OS (or in CI). Offline runtime after build — free forever, MIT.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
echo "Building Leafkit for ${OS}/${ARCH}…"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -U pip
pip install -q -r requirements.txt pyinstaller

python scripts/make_icon.py || true

SEP=":"
if [[ "$OS" == mingw* || "$OS" == msys* || "$OS" == cygwin* ]]; then
  SEP=";"
fi

ICON_PNG="assets/leafkit.png"
ADD_DATA=(
  --add-data "assets/leafkit.png${SEP}assets"
  --add-data "locales${SEP}locales"
)
if [[ -f assets/leafkit.ico ]]; then
  ADD_DATA+=(--add-data "assets/leafkit.ico${SEP}assets")
fi

COMMON=(
  --noconfirm
  --clean
  --name Leafkit
  --collect-all customtkinter
  --collect-all tkinterdnd2
  --hidden-import=pypdf
  --hidden-import=tkinterdnd2
  --hidden-import=fitz
  --hidden-import=leafkit
  --hidden-import=leafkit.app
  --hidden-import=leafkit.pdf_ops
  --hidden-import=leafkit.pdf_ops._core
  --hidden-import=leafkit.pdf_ops.structure
  --hidden-import=leafkit.pdf_ops.compress
  --hidden-import=leafkit.pdf_ops.transform
  --hidden-import=leafkit.pdf_ops.pagenum
  --hidden-import=leafkit.pdf_ops.watch
  --hidden-import=leafkit.render
  --hidden-import=leafkit.cli
  --hidden-import=leafkit.jobs
  --hidden-import=leafkit.batch
  --hidden-import=leafkit.i18n
  --hidden-import=leafkit.prefs
  --hidden-import=leafkit.review_ui
  --hidden-import=leafkit.crop_ui
  --hidden-import=leafkit.ui_organize
  --hidden-import=leafkit.ui_share
  "${ADD_DATA[@]}"
  run.py
)

mkdir -p dist/release

if [[ "$OS" == "darwin" ]]; then
  echo "→ macOS .app (windowed)…"
  pyinstaller "${COMMON[@]}" --windowed --onedir \
    --icon "$ICON_PNG" 2>/dev/null || pyinstaller "${COMMON[@]}" --windowed --onedir
  # PyInstaller places Leafkit.app under dist/
  if [[ -d dist/Leafkit.app ]]; then
    APP="dist/Leafkit.app"
  elif [[ -d dist/Leafkit/Leafkit.app ]]; then
    APP="dist/Leafkit/Leafkit.app"
  else
    # onedir may be dist/Leafkit/Leafkit executable only
    APP=""
    echo "Note: looking for app bundle…"
    find dist -maxdepth 3 -name "Leafkit.app" -type d || true
  fi
  if [[ -n "${APP}" && -d "${APP}" ]]; then
    (cd dist && tar -czf "release/Leafkit-macos-${ARCH}.tar.gz" "$(basename "$APP")")
    echo "Packed: dist/release/Leafkit-macos-${ARCH}.tar.gz"
  else
    # Fallback: pack onedir folder
    if [[ -d dist/Leafkit ]]; then
      (cd dist && tar -czf "release/Leafkit-macos-${ARCH}.tar.gz" Leafkit)
      echo "Packed onedir: dist/release/Leafkit-macos-${ARCH}.tar.gz"
    fi
  fi
  echo "macOS note: Gatekeeper may warn until the app is notarized (Apple Developer ID)."
elif [[ "$OS" == "linux" ]]; then
  echo "→ Linux onedir…"
  pyinstaller "${COMMON[@]}" --onedir --windowed 2>/dev/null \
    || pyinstaller "${COMMON[@]}" --onedir

  if [[ ! -d dist/Leafkit ]]; then
    echo "ERROR: dist/Leafkit not found after PyInstaller" >&2
    exit 1
  fi

  # Portable launcher
  cat > dist/Leafkit/leafkit-run.sh <<'EOF'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
export TCL_LIBRARY="${TCL_LIBRARY:-}"
export TK_LIBRARY="${TK_LIBRARY:-}"
exec "$DIR/Leafkit" "$@"
EOF
  chmod +x dist/Leafkit/leafkit-run.sh dist/Leafkit/Leafkit 2>/dev/null || true

  (cd dist && tar -czf "release/Leafkit-linux-${ARCH}.tar.gz" Leafkit)
  echo "Packed: dist/release/Leafkit-linux-${ARCH}.tar.gz"

  # Optional AppImage (best-effort; needs appimagetool)
  if command -v appimagetool >/dev/null 2>&1 || [[ -x /tmp/appimagetool ]]; then
    echo "→ Building AppImage…"
    AI_ROOT="dist/Leafkit.AppDir"
    rm -rf "$AI_ROOT"
    mkdir -p "$AI_ROOT/usr/bin" "$AI_ROOT/usr/share/applications" "$AI_ROOT/usr/share/icons/hicolor/256x256/apps"
    cp -a dist/Leafkit/* "$AI_ROOT/usr/bin/"
    if [[ -f assets/leafkit.png ]]; then
      cp assets/leafkit.png "$AI_ROOT/usr/share/icons/hicolor/256x256/apps/leafkit.png"
      cp assets/leafkit.png "$AI_ROOT/leafkit.png"
    fi
    cat > "$AI_ROOT/leafkit.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Leafkit
Comment=Offline PDF page toolkit — free forever
Exec=Leafkit
Icon=leafkit
Categories=Office;Graphics;
Terminal=false
EOF
    cp "$AI_ROOT/leafkit.desktop" "$AI_ROOT/usr/share/applications/"
    cat > "$AI_ROOT/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="${HERE}/usr/bin:${PATH}"
cd "${HERE}/usr/bin"
exec ./Leafkit "$@"
EOF
    chmod +x "$AI_ROOT/AppRun"
    TOOL=appimagetool
    [[ -x /tmp/appimagetool ]] && TOOL=/tmp/appimagetool
    ARCH_APP="$ARCH"
    [[ "$ARCH" == "x86_64" ]] && ARCH_APP="x86_64"
    ARCH="$ARCH_APP" "$TOOL" "$AI_ROOT" "dist/release/Leafkit-${ARCH_APP}.AppImage" || true
    if [[ -f dist/release/Leafkit-${ARCH_APP}.AppImage ]]; then
      chmod +x "dist/release/Leafkit-${ARCH_APP}.AppImage"
      echo "AppImage: dist/release/Leafkit-${ARCH_APP}.AppImage"
    else
      echo "AppImage step skipped or failed (tarball still available)."
    fi
  else
    echo "appimagetool not found — tarball only. CI may download appimagetool."
  fi
else
  echo "Unsupported OS for this script: $OS (use scripts/build_exe.ps1 on Windows)" >&2
  exit 1
fi

echo ""
echo "Done. Artifacts under dist/ and dist/release/"
python -c "from leafkit import __version__; print('Version', __version__)"
