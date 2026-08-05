# Build Leafkit Windows binaries with the pages+leaf icon.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    python -m venv .venv
}
& $venvPython -m pip install -q -r requirements.txt pyinstaller

# Ensure icon assets exist
& $venvPython (Join-Path $Root "scripts\make_icon.py")

$icon = Join-Path $Root "assets\leafkit.ico"
if (-not (Test-Path $icon)) {
    throw "Icon not found: $icon"
}

$pyiArgs = @(
    "--noconfirm",
    "--windowed",
    "--icon", $icon,
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    "--add-data", "assets\leafkit.ico;assets",
    "--add-data", "assets\leafkit.png;assets",
    "--add-data", "locales;locales",
    "--hidden-import=pypdf",
    "--hidden-import=tkinterdnd2",
    "--hidden-import=fitz",
    "--hidden-import=leafkit",
    "--hidden-import=leafkit.app",
    "--hidden-import=leafkit.pdf_ops",
    "--hidden-import=leafkit.render",
    "--hidden-import=leafkit.cli",
    "--hidden-import=leafkit.jobs",
    "--hidden-import=leafkit.i18n",
    "--hidden-import=leafkit.batch",
    "--hidden-import=leafkit.prefs",
    "--hidden-import=leafkit.review_ui",
    "--hidden-import=leafkit.crop_ui",
    "--hidden-import=leafkit.diagnostics",
    "--hidden-import=leafkit.ui_organize",
    "--hidden-import=leafkit.ui_share",
    "--hidden-import=leafkit.pdf_ops._core",
    "--hidden-import=leafkit.pdf_ops.structure",
    "--hidden-import=leafkit.pdf_ops.compress",
    "--hidden-import=leafkit.pdf_ops.transform",
    "--hidden-import=leafkit.pdf_ops.pagenum",
    "--hidden-import=leafkit.pdf_ops.watch",
    "run.py"
)

Write-Host "Building onedir (preferred)..."
& $venvPython -m PyInstaller @pyiArgs --name Leafkit --onedir

Write-Host "Building onefile..."
& $venvPython -m PyInstaller @pyiArgs --name Leafkit --onefile

$ver = & $venvPython -c "from leafkit import __version__; print(__version__)"
Write-Host ""
Write-Host "Done (source version $ver):"
Write-Host "  $Root\dist\Leafkit\Leafkit.exe   (onedir - preferred)"
Write-Host "  $Root\dist\Leafkit.exe             (onefile)"
Write-Host ""
Write-Host "Re-run this script after every version bump so dist/ matches source."
Write-Host "Install Desktop/Start Menu shortcuts:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\install_shortcuts.ps1"
