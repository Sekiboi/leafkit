# Windows installer & install-and-play

Leafkit is designed as a normal desktop app: **install once, launch from Start Menu**, offline forever.

## User expectations we target

| Expectation | How we meet it |
|-------------|----------------|
| Double-click installer | `Leafkit-<ver>-Setup.exe` (Inno Setup) |
| Start Menu entry | Created by installer |
| Optional desktop icon | Task (default **off** — less clutter) |
| Uninstall cleanly | Windows **Apps & features** / Add or remove programs |
| App does not write under Program Files | Prefs/logs/crash/diagnostics → `%LOCALAPPDATA%\Leafkit` |
| Works without admin when possible | `PrivilegesRequired=lowest` + dialog to elevate for Program Files |
| Silent IT install | `Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART` |
| No network at install | Offline Setup; no download of deps |
| Trust | Sign Setup + exe when cert available (SmartScreen) |
| First-run surprise minimal | One short **Welcome** about optional Diagnostics (default Off) |

## Build Setup.exe (developers)

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php) (free).  
2. From repo root:

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_installer.ps1
```

Produces:

- `dist\Leafkit\` — onedir app (also used standalone)
- `dist\installer\Leafkit-<version>-Setup.exe` — **install-and-play**
- `dist\installer\SHA256SUMS.txt`

If Inno is missing, `build_installer.ps1` exits with guidance; zip portable via `package_local_release.ps1` still works.

## Install locations

| Kind | Path |
|------|------|
| Program files (typical) | `C:\Program Files\Leafkit\` |
| Per-user override | User-chosen / non-elevated mode under local Programs |
| **User data** (always) | `%LOCALAPPDATA%\Leafkit\` |
| | `leafkit_prefs.json`, `leafkit_jobs.log`, `leafkit_crash.log`, diagnostics exports |

Uninstall **does not** delete user data (prefs/logs) so reinstall keeps settings. Users can delete the folder manually.

## Diagnostics (optional, default off)

Aligned with privacy-first desktop norms:

| Practice | Leafkit |
|----------|-----------|
| No automatic upload | Yes |
| Opt-in | First launch asks once; checkbox **defaults unchecked** |
| Change later | Settings → Enable diagnostics export |
| Export only when on | About → Copy / Save diagnostics |
| Local crash file | Always written on hard crash (on disk only); export still gated by opt-in UI |
| PII minimization | No PDF content, no passwords, job log basenames only |

See [REPORTING.md](REPORTING.md) and [PRIVACY.md](PRIVACY.md).

## Portable alternative

No install: run `dist\Leafkit\Leafkit.exe` or the zip from `package_local_release.ps1`.  
Data still uses project folder when not frozen; frozen portable in Program Files-like folders still uses `%LOCALAPPDATA%\Leafkit`.

## Signing (later)

When you have a code-signing certificate:

1. Sign `dist\Leafkit\Leafkit.exe` (and binaries if required).  
2. Sign `Leafkit-*-Setup.exe`.  
3. Publish checksums with the release.

Unsigned freeware often triggers SmartScreen until reputation builds — expected; not a code bug.

## Scope note

- **Inno Setup** is the current Windows packaging tool for this project (required to build Setup.exe).  
- Other package formats are optional later if needed.  
- macOS/Linux use `scripts/build_unix.sh` + CI artifacts (see [LINUX_MAC.md](LINUX_MAC.md)).
