# Write SHA256 hashes for dist binaries (for GitHub Releases — no code signing required).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Dist = Join-Path $Root "dist"
$Out = Join-Path $Dist "SHA256SUMS.txt"

$lines = @()
Get-ChildItem $Dist -Recurse -Filter "*.exe" | ForEach-Object {
    $h = Get-FileHash $_.FullName -Algorithm SHA256
    $rel = $_.FullName.Substring($Dist.Length).TrimStart("\", "/")
    $lines += "$($h.Hash.ToLower())  $rel"
    Write-Host $lines[-1]
}
$lines | Set-Content -Path $Out -Encoding utf8
Write-Host "Wrote $Out"
