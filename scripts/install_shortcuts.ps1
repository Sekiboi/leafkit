# Create Desktop + Start Menu shortcuts for Leafkit with the freedom-bird icon.
#
# Default: pythonw + run.py when .venv exists (always matches current source version).
# Packaged exe: pass -UsePackagedExe after building with scripts\build_exe.ps1
#
param(
    [switch]$UsePackagedExe
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Icon = Join-Path $Root "assets\leafkit.ico"
if (-not (Test-Path $Icon)) {
    Write-Host "Icon missing - generating..."
    & (Join-Path $Root ".venv\Scripts\python.exe") (Join-Path $Root "scripts\make_icon.py")
}

$OneFile = Join-Path $Root "dist\Leafkit.exe"
$OneDir = Join-Path $Root "dist\Leafkit\Leafkit.exe"
$Pythonw = Join-Path $Root ".venv\Scripts\pythonw.exe"
$RunPy = Join-Path $Root "run.py"

$Target = $null
$Arguments = ""
$WorkDir = $Root
$ModeLabel = ""

$ver = "unknown"
try {
    $ver = & (Join-Path $Root ".venv\Scripts\python.exe") -c "from leafkit import __version__; print(__version__)"
} catch {}

if ($UsePackagedExe -and (Test-Path $OneDir)) {
    $Target = $OneDir
    $WorkDir = Split-Path $OneDir -Parent
    $ModeLabel = "packaged onedir exe (rebuild after code changes!)"
}
elseif ($UsePackagedExe -and (Test-Path $OneFile)) {
    $Target = $OneFile
    $WorkDir = Split-Path $OneFile -Parent
    $ModeLabel = "packaged onefile exe (rebuild after code changes!)"
}
elseif ((Test-Path $Pythonw) -and (Test-Path $RunPy)) {
    $Target = $Pythonw
    $Arguments = "`"$RunPy`""
    $ModeLabel = "source pythonw + run.py (version $ver)"
}
elseif (Test-Path $OneDir) {
    $Target = $OneDir
    $WorkDir = Split-Path $OneDir -Parent
    $ModeLabel = "packaged onedir exe (no venv found)"
}
elseif (Test-Path $OneFile) {
    $Target = $OneFile
    $WorkDir = Split-Path $OneFile -Parent
    $ModeLabel = "packaged onefile exe (no venv found)"
}
else {
    throw "Nothing to launch. Create .venv + pip install, or build the exe."
}

Write-Host "Shortcut target: $ModeLabel"
Write-Host "  $Target $Arguments"

function New-LeafkitShortcut {
    param(
        [string]$LinkPath,
        [string]$TargetPath,
        [string]$Args,
        [string]$WorkingDirectory,
        [string]$IconLocation
    )
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($LinkPath)
    $sc.TargetPath = $TargetPath
    $sc.Arguments = $Args
    $sc.WorkingDirectory = $WorkingDirectory
    $sc.WindowStyle = 1
    $sc.Description = "Leafkit - offline PDF page toolkit (v$ver)"
    $sc.IconLocation = "$IconLocation,0"
    $sc.Save()
    Write-Host "Created $LinkPath"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs"
New-Item -ItemType Directory -Force -Path $StartMenu | Out-Null

New-LeafkitShortcut -LinkPath (Join-Path $Desktop "Leafkit.lnk") `
    -TargetPath $Target -Args $Arguments `
    -WorkingDirectory $WorkDir -IconLocation $Icon

New-LeafkitShortcut -LinkPath (Join-Path $StartMenu "Leafkit.lnk") `
    -TargetPath $Target -Args $Arguments `
    -WorkingDirectory $WorkDir -IconLocation $Icon

New-LeafkitShortcut -LinkPath (Join-Path $Root "Leafkit.lnk") `
    -TargetPath $Target -Args $Arguments `
    -WorkingDirectory $WorkDir -IconLocation $Icon

Write-Host ""
Write-Host "Done. Desktop/Start Menu Leafkit -> $ModeLabel"
Write-Host "Source version now: $ver"
Write-Host "For packaged exe shortcuts after build: .\scripts\install_shortcuts.ps1 -UsePackagedExe"
