# Build a LOCAL release folder (zip + SHA256). Does NOT publish or push.
# Output: release\Leafkit-<version>\
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) { throw "Create .venv first." }

$ver = & $venvPython -c "from leafkit import __version__; print(__version__)"
$ver = $ver.Trim()
Write-Host "Packaging Leafkit $ver (local only — no upload)"

& (Join-Path $Root "scripts\build_exe.ps1")

$relRoot = Join-Path $Root "release"
$dest = Join-Path $relRoot "Leafkit-$ver"
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item -ItemType Directory -Path $dest | Out-Null

# Prefer onedir tree
$onedir = Join-Path $Root "dist\Leafkit"
if (Test-Path $onedir) {
    Copy-Item $onedir (Join-Path $dest "Leafkit") -Recurse
} else {
    Copy-Item (Join-Path $Root "dist\Leafkit.exe") $dest
}

Copy-Item (Join-Path $Root "README.md") $dest
Copy-Item (Join-Path $Root "LICENSE") $dest
Copy-Item (Join-Path $Root "CHANGELOG.md") $dest -ErrorAction SilentlyContinue
Copy-Item (Join-Path $Root "docs") (Join-Path $dest "docs") -Recurse -ErrorAction SilentlyContinue
if (Test-Path (Join-Path $Root "locales")) {
    Copy-Item (Join-Path $Root "locales") (Join-Path $dest "locales") -Recurse
}

# Checksums
$sums = Join-Path $dest "SHA256SUMS.txt"
$lines = @()
Get-ChildItem $dest -Recurse -File | Where-Object { $_.Name -ne "SHA256SUMS.txt" } | ForEach-Object {
    $h = Get-FileHash $_.FullName -Algorithm SHA256
    $rel = $_.FullName.Substring($dest.Length).TrimStart("\", "/")
    $lines += "$($h.Hash.ToLowerInvariant())  $rel"
}
$lines | Set-Content $sums -Encoding utf8

$zip = Join-Path $relRoot "Leafkit-$ver-windows-x64.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $dest "*") -DestinationPath $zip

Write-Host ""
Write-Host "Local release ready (NOT published):"
Write-Host "  $dest"
Write-Host "  $zip"
Write-Host "Review SHA256SUMS.txt inside the folder before any future public release."
