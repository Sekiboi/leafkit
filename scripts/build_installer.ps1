# Build Windows install-and-play Setup.exe (Inno Setup 6+).
# 1) PyInstaller onedir  2) compile Sekikit.iss
# Requires: Inno Setup 6 (https://jrsoftware.org/isinfo.php)
#   Default: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Create .venv and install requirements first."
}

$ver = (& $venvPython -c "from sekikit import __version__; print(__version__)").Trim()
Write-Host "=== Sekikit $ver - Windows installer ==="

# Always rebuild packaged app so Setup matches source
& (Join-Path $Root "scripts\build_exe.ps1")

$onedir = Join-Path $Root "dist\Sekikit\Sekikit.exe"
if (-not (Test-Path $onedir)) {
    throw "Missing $onedir after build_exe.ps1"
}
# Sanity: onedir must include bundled assets (catches incomplete builds)
$need = @(
    (Join-Path $Root "dist\Sekikit\_internal"),
    (Join-Path $Root "assets\sekikit.ico"),
    (Join-Path $Root "docs\PRIVACY.md"),
    (Join-Path $Root "LICENSE")
)
foreach ($p in $need) {
    if (-not (Test-Path $p)) { throw "Missing required path for installer: $p" }
}
$internalAssets = Join-Path $Root "dist\Sekikit\_internal\assets\sekikit.ico"
if (-not (Test-Path $internalAssets)) {
    Write-Host "WARNING: $internalAssets missing - icon may be absent in installed app"
}

$localInno = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
# Outer @() keeps a single match as a 1-element array (else [0] is first char of path)
$isccCandidates = @(
    @(
        ${env:INNOSETUP_ISCC},
        $localInno,
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }
)

if ($isccCandidates.Count -eq 0) {
    Write-Host ""
    Write-Host "Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php"
    Write-Host "Or set INNOSETUP_ISCC to ISCC.exe path."
    Write-Host ""
    Write-Host "Portable fallback (no Setup.exe):"
    Write-Host "  .\scripts\package_local_release.ps1"
    exit 2
}

$iscc = $isccCandidates[0]
$iss = Join-Path $Root "installer\Sekikit.iss"
$outDir = Join-Path $Root "dist\installer"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# Windows VERSIONINFO needs a.b.c.d; strip beta labels for that field only.
$verInfo = if ($ver -match '^(\d+)\.(\d+)\.(\d+)') {
    "$($Matches[1]).$($Matches[2]).$($Matches[3]).0"
} else {
    "0.0.0.1"
}
# Prefer .1 for prereleases so they sort after a future .0 release build
if ($ver -match 'beta|rc|a|b') {
    if ($ver -match '^(\d+)\.(\d+)\.(\d+)') {
        $verInfo = "$($Matches[1]).$($Matches[2]).$($Matches[3]).1"
    }
}

Write-Host "Compiling installer with $iscc AppVersion=$ver VersionInfo=$verInfo ..."
& $iscc "/DMyAppVersion=$ver" "/DMyAppVersionInfo=$verInfo" $iss
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with $LASTEXITCODE" }

$setup = Get-ChildItem $outDir -Filter "Sekikit-*-Setup.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $setup) { throw "Setup.exe not produced in $outDir" }

$hash = (Get-FileHash $setup.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$sumFile = Join-Path $outDir "SHA256SUMS.txt"
"$hash  $($setup.Name)" | Set-Content $sumFile -Encoding utf8

Write-Host ""
Write-Host "Installer ready (install-and-play):"
Write-Host "  $($setup.FullName)"
Write-Host "  $sumFile"
Write-Host "  SHA256: $hash"
Write-Host ""
Write-Host "User expectations met:"
Write-Host "  - Double-click Setup -> wizard -> Start Menu launch"
Write-Host "  - Uninstall via Windows Settings -> Apps"
Write-Host "  - Data in %LOCALAPPDATA%\Sekikit (survives reinstall)"
Write-Host "  - Sign Setup.exe when you have a code-signing certificate"
