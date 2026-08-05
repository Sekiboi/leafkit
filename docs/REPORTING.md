# Reporting bugs and crashes

Leafkit is **offline-only**: nothing is sent automatically. We improve from **reports you choose to send**.

## Diagnostics is optional (default off) and anonymous

On **first launch**, Leafkit asks once whether to enable **anonymous Diagnostics export**.  
The checkbox defaults to **unchecked** (off). You can change it anytime in **Settings**.

| Diagnostics off (default) | Diagnostics on |
|---------------------------|----------------|
| No Copy/Save diagnostics in About | About → Copy / Save diagnostics |
| App still works fully offline | Same; export is still **local only** |
| Crash may still write a local log file | Same log can be included when you export (paths redacted) |

**Anonymous means:** no name, account, email, device ID, or hostname.  
Job logs use **file basenames only**; crash/job tails **redact home paths, usernames, IPs, and emails**.  
Nothing is ever uploaded by the app. Export only builds a text file/clipboard pack **on your PC**.

## Recommended path

1. Reproduce once if you can.
2. Enable **anonymous** Diagnostics in **Settings** (if you left it off at first run).
3. **About (F1) → Copy diagnostics** (or **Save diagnostics…**).
4. Open a GitHub issue:  
   https://github.com/Sekiboi/leafkit/issues/new/choose  
   - **Bug report** — wrong output, UI glitch, error message  
   - **Crash report** — app exit / crash dialog  
5. Paste the diagnostics block and describe steps.

## What diagnostics includes

| Included | Not included |
|----------|----------------|
| Version, coarse OS (system + release + arch), Python, frozen/exe | Name, account, device ID, hostname |
| Review mode, PyMuPDF / Ghostscript present (yes/no) | PDF file **content** |
| Last lines of `leafkit_jobs.log` (**basenames**; paths redacted) | Full folder paths / usernames |
| Last lines of `leafkit_crash.log` if present (**paths redacted**) | Passwords, telemetry |

## Local log files

| File | Where |
|------|--------|
| `leafkit_crash.log` | `%LOCALAPPDATA%\Leafkit` when installed; project root from source |
| `leafkit_jobs.log` | Same location (operation history, basenames) |
| `leafkit_diagnostics_*.txt` | If you used **Save diagnostics…** |

## Privacy rules for reporters

- Prefer **not** attaching real confidential PDFs.
- If a file is needed to debug, strip sensitive pages or use a redacted copy.
- Never paste passwords into issues.

## Maintainers (how we use reports)

1. Confirm version and OS from diagnostics.  
2. Check recent job log ops + crash traceback.  
3. Reproduce with fixtures or a minimal sample when possible.  
4. Fix in source → tests when useful → rebuild `dist\` for Windows.  
5. Close with changelog note when shipped.

## What we will not do

- Auto-upload crash reports  
- Always-on analytics  
- Require an account to report  
- Include identifying device or account data in exports
