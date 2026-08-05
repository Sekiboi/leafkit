# Build Sekikit Windows binaries with the pages+leaf icon.
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

$icon = Join-Path $Root "assets\sekikit.ico"
if (-not (Test-Path $icon)) {
    throw "Icon not found: $icon"
}

$pyiArgs = @(
    "--noconfirm",
    "--windowed",
    "--icon", $icon,
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    "--add-data", "assets\sekikit.ico;assets",
    "--add-data", "assets\sekikit.png;assets",
    "--add-data", "locales;locales",
    "--hidden-import=pypdf",
    "--hidden-import=tkinterdnd2",
    "--hidden-import=fitz",
    "--hidden-import=sekikit",
    "--hidden-import=sekikit.app",
    "--hidden-import=sekikit.pdf_ops",
    "--hidden-import=sekikit.render",
    "--hidden-import=sekikit.cli",
    "--hidden-import=sekikit.jobs",
    "--hidden-import=sekikit.i18n",
    "--hidden-import=sekikit.batch",
    "--hidden-import=sekikit.prefs",
    "--hidden-import=sekikit.review_ui",
    "--hidden-import=sekikit.crop_ui",
    "--hidden-import=sekikit.diagnostics",
    "--hidden-import=sekikit.ui_organize",
    "--hidden-import=sekikit.ui_share",
    "--hidden-import=sekikit.pdf_ops._core",
    "--hidden-import=sekikit.pdf_ops.structure",
    "--hidden-import=sekikit.pdf_ops.compress",
    "--hidden-import=sekikit.pdf_ops.transform",
    "--hidden-import=sekikit.pdf_ops.pagenum",
    "--hidden-import=sekikit.pdf_ops.watch",
    "run.py"
)

Write-Host "Building onedir (preferred)..."
& $venvPython -m PyInstaller @pyiArgs --name Sekikit --onedir

Write-Host "Building onefile..."
& $venvPython -m PyInstaller @pyiArgs --name Sekikit --onefile

$ver = & $venvPython -c "from sekikit import __version__; print(__version__)"
Write-Host ""
Write-Host "Done (source version $ver):"
Write-Host "  $Root\dist\Sekikit\Sekikit.exe   (onedir - preferred)"
Write-Host "  $Root\dist\Sekikit.exe             (onefile)"
Write-Host ""
Write-Host "Re-run this script after every version bump so dist/ matches source."
Write-Host "Install Desktop/Start Menu shortcuts:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\install_shortcuts.ps1"
