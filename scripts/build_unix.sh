#!/usr/bin/env bash
# Build Sekikit GUI packages for Linux (onedir + optional AppImage) and macOS (.app).
# Run on the target OS (or in CI). Offline runtime after build — free forever, MIT.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
echo "Building Sekikit for ${OS}/${ARCH}…"

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

ICON_PNG="assets/sekikit.png"
ADD_DATA=(
  --add-data "assets/sekikit.png${SEP}assets"
  --add-data "locales${SEP}locales"
)
if [[ -f assets/sekikit.ico ]]; then
  ADD_DATA+=(--add-data "assets/sekikit.ico${SEP}assets")
fi

COMMON=(
  --noconfirm
  --clean
  --name Sekikit
  --collect-all customtkinter
  --collect-all tkinterdnd2
  --hidden-import=pypdf
  --hidden-import=tkinterdnd2
  --hidden-import=fitz
  --hidden-import=sekikit
  --hidden-import=sekikit.app
  --hidden-import=sekikit.pdf_ops
  --hidden-import=sekikit.pdf_ops._core
  --hidden-import=sekikit.pdf_ops.structure
  --hidden-import=sekikit.pdf_ops.compress
  --hidden-import=sekikit.pdf_ops.transform
  --hidden-import=sekikit.pdf_ops.pagenum
  --hidden-import=sekikit.pdf_ops.watch
  --hidden-import=sekikit.render
  --hidden-import=sekikit.cli
  --hidden-import=sekikit.jobs
  --hidden-import=sekikit.batch
  --hidden-import=sekikit.i18n
  --hidden-import=sekikit.prefs
  --hidden-import=sekikit.review_ui
  --hidden-import=sekikit.crop_ui
  --hidden-import=sekikit.ui_organize
  --hidden-import=sekikit.ui_share
  "${ADD_DATA[@]}"
  run.py
)

mkdir -p dist/release

if [[ "$OS" == "darwin" ]]; then
  echo "→ macOS .app (windowed)…"
  pyinstaller "${COMMON[@]}" --windowed --onedir \
    --icon "$ICON_PNG" 2>/dev/null || pyinstaller "${COMMON[@]}" --windowed --onedir
  # PyInstaller places Sekikit.app under dist/
  if [[ -d dist/Sekikit.app ]]; then
    APP="dist/Sekikit.app"
  elif [[ -d dist/Sekikit/Sekikit.app ]]; then
    APP="dist/Sekikit/Sekikit.app"
  else
    # onedir may be dist/Sekikit/Sekikit executable only
    APP=""
    echo "Note: looking for app bundle…"
    find dist -maxdepth 3 -name "Sekikit.app" -type d || true
  fi
  if [[ -n "${APP}" && -d "${APP}" ]]; then
    (cd dist && tar -czf "release/Sekikit-macos-${ARCH}.tar.gz" "$(basename "$APP")")
    echo "Packed: dist/release/Sekikit-macos-${ARCH}.tar.gz"
  else
    # Fallback: pack onedir folder
    if [[ -d dist/Sekikit ]]; then
      (cd dist && tar -czf "release/Sekikit-macos-${ARCH}.tar.gz" Sekikit)
      echo "Packed onedir: dist/release/Sekikit-macos-${ARCH}.tar.gz"
    fi
  fi
  echo "macOS note: Gatekeeper may warn until the app is notarized (Apple Developer ID)."
elif [[ "$OS" == "linux" ]]; then
  echo "→ Linux onedir…"
  pyinstaller "${COMMON[@]}" --onedir --windowed 2>/dev/null \
    || pyinstaller "${COMMON[@]}" --onedir

  if [[ ! -d dist/Sekikit ]]; then
    echo "ERROR: dist/Sekikit not found after PyInstaller" >&2
    exit 1
  fi

  # Portable launcher
  cat > dist/Sekikit/sekikit-run.sh <<'EOF'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
export TCL_LIBRARY="${TCL_LIBRARY:-}"
export TK_LIBRARY="${TK_LIBRARY:-}"
exec "$DIR/Sekikit" "$@"
EOF
  chmod +x dist/Sekikit/sekikit-run.sh dist/Sekikit/Sekikit 2>/dev/null || true

  (cd dist && tar -czf "release/Sekikit-linux-${ARCH}.tar.gz" Sekikit)
  echo "Packed: dist/release/Sekikit-linux-${ARCH}.tar.gz"

  # Optional AppImage (best-effort; needs appimagetool)
  if command -v appimagetool >/dev/null 2>&1 || [[ -x /tmp/appimagetool ]]; then
    echo "→ Building AppImage…"
    AI_ROOT="dist/Sekikit.AppDir"
    rm -rf "$AI_ROOT"
    mkdir -p "$AI_ROOT/usr/bin" "$AI_ROOT/usr/share/applications" "$AI_ROOT/usr/share/icons/hicolor/256x256/apps"
    cp -a dist/Sekikit/* "$AI_ROOT/usr/bin/"
    if [[ -f assets/sekikit.png ]]; then
      cp assets/sekikit.png "$AI_ROOT/usr/share/icons/hicolor/256x256/apps/sekikit.png"
      cp assets/sekikit.png "$AI_ROOT/sekikit.png"
    fi
    cat > "$AI_ROOT/sekikit.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Sekikit
Comment=Offline PDF page toolkit — free forever
Exec=Sekikit
Icon=sekikit
Categories=Office;Graphics;
Terminal=false
EOF
    cp "$AI_ROOT/sekikit.desktop" "$AI_ROOT/usr/share/applications/"
    cat > "$AI_ROOT/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="${HERE}/usr/bin:${PATH}"
cd "${HERE}/usr/bin"
exec ./Sekikit "$@"
EOF
    chmod +x "$AI_ROOT/AppRun"
    TOOL=appimagetool
    [[ -x /tmp/appimagetool ]] && TOOL=/tmp/appimagetool
    ARCH_APP="$ARCH"
    [[ "$ARCH" == "x86_64" ]] && ARCH_APP="x86_64"
    ARCH="$ARCH_APP" "$TOOL" "$AI_ROOT" "dist/release/Sekikit-${ARCH_APP}.AppImage" || true
    if [[ -f dist/release/Sekikit-${ARCH_APP}.AppImage ]]; then
      chmod +x "dist/release/Sekikit-${ARCH_APP}.AppImage"
      echo "AppImage: dist/release/Sekikit-${ARCH_APP}.AppImage"
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
python -c "from sekikit import __version__; print('Version', __version__)"
