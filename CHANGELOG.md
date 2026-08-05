# Changelog

All notable changes to Sekikit are documented here.  
**Everything remains free forever — no paid features.**

## 0.15.0-beta.1 — First public beta (Sekikit)

### Status
- **Beta:** feature-complete enough to dogfood; wants real-world feedback
- Primary download: **Windows Setup.exe** on GitHub Releases
- Free forever · MIT · offline-only · no accounts

### Changed (rename)
- Product renamed from **Leafkit** to **Sekikit** (temporary brand; may change later)
- Python package / CLI: `sekikit` (was `leafkit`)
- Windows exe / installer: `Sekikit.exe`, `Sekikit-<ver>-Setup.exe`
- User data: `%LOCALAPPDATA%\Sekikit` (new folder / install id — not an upgrade of Leafkit)
- GitHub: **github.com/Sekiboi/sekikit**

### Highlights
- Full offline PDF toolkit (Organize, Share, Merge, Mix, Extract, Delete, Insert, Split, Rotate, Watch, CLI)
- Opt-in **anonymous** diagnostics (default off)
- Installer: Start Menu, uninstall, local app data
- Min window size locks so chrome is not clipped

### Known gaps (feedback welcome)
- Unsigned installer (SmartScreen may warn until reputation builds)
- Linux/mac packages less polished than Windows Setup
- Final product name still under consideration
- Edge-case PDFs / UI polish still in progress

## 0.14.1 — Min window size (no clipped UI)

### Changed
- Main window cannot shrink below the designed size (1000×800)
- Min size is raised further if layout/DPI needs more room after first paint
- Window can still grow freely; no scroll-strip toolbars

## 0.14.0 — Rebrand to Leafkit

### Changed
- Product renamed from **JustPages** to **Leafkit**
- Python package / CLI: `leafkit` (was `justpages`)
- Windows exe / installer: `Leafkit.exe`, `Leafkit-<ver>-Setup.exe`
- User data: `%LOCALAPPDATA%\Leafkit` (prefs/logs); new install id (not an upgrade of JustPages)

### Notes
- Old JustPages install (if any) is a separate app — uninstall it from Windows Apps if present
- Later renamed again to **Sekikit** (see 0.15.0-beta.1)

## 0.13.3 — Anonymous diagnostics

### Changed
- Diagnostics reports are **anonymous**: no name, account, device ID, or hostname
- Crash/job log tails **redact** home paths, usernames, emails, IPs, and UNC hosts
- Coarse OS summary only (no long build fingerprint); Ghostscript listed as found/not found
- First-run, Settings, and About **notice that enabling diagnostics is anonymous**

### Docs
- REPORTING.md / PRIVACY.md updated for anonymity guarantees

## 0.13.2 — Install-and-play + opt-in diagnostics (defaults off)

### Added
- **Windows Setup.exe:** Inno Setup (`installer/Sekikit.iss`) + `scripts/build_installer.ps1`
- **First-run Welcome:** optional Diagnostics checkbox (**defaults unchecked / Off**)
- **Settings:** enable/disable diagnostics export anytime
- **About:** Copy/Save diagnostics **only if enabled**
- Installed app data: `%LOCALAPPDATA%\Sekikit` (prefs, logs — not Program Files)
- Docs: `INSTALLER.md`, updated REPORTING/PRIVACY

### Notes
- Meet install-and-play expectations (Start Menu, uninstall, silent flags).
- Diagnostics never auto-upload; local export only when user opted in.
- Sign Setup.exe when you have a cert (SmartScreen).

## 0.13.1 — Packaging + UI polish

### Added
- Linux/mac package scripts + CI; UI polish (empty states, About/Settings)

### Added
- **Linux / macOS packaging**: `scripts/build_unix.sh` → tarball (and AppImage when `appimagetool` is present)
- **CI**: `.github/workflows/package-unix.yml` (tag `v*` or manual) uploads Linux + macOS artifacts
- Polished **empty file list**, **Organize empty tray**, **About** / **Settings** windows
- Shortcuts: **Ctrl+,** Settings, **Ctrl+S** Save combined tray

### Changed
- Share tab header denser (batch checkbox on the right)
- `docs/LINUX_MAC.md` first-class package docs
- Windows `build_exe.ps1` hidden-imports for pdf_ops package modules

## 0.13.0 — Multi-pass feature gameplan complete (Passes 1–5)

### Added (Pass 5)
- **Stamp image** — overlay PNG/JPEG on pages (`stamp-image` CLI; Share More)
- Positions: corners / center / top / bottom; scale, margin, opacity
- Real-world harness covers decrypt/resize/reverse/blank/crop_box/stamp

### Milestone
In-scope page tools from the multi-pass gameplan are shipped free:
decrypt, batch all listed, resize, reverse, blank, extract text, tray split, visual crop, stamp image.

## 0.12.4 — Pass 4: visual / box crop

### Added
- **`crop_box`** — crop to PDF-point rectangle (bottom-left origin); soft or hard
- **CLI** `crop-box --x0 --y0 --x1 --y1 [--hard] [--pages]`
- **Share → Visual crop…** — drag a rectangle on a page preview; apply this page or all; hard optional
- Hard box crop is a risk-mode review op

## 0.12.3 — Pass 3: extract text + tray split

### Added
- **Extract text** — selectable text only, not OCR (`text` CLI; Share More → Copy text / Save .txt)
- **Organize → Split before selected** — write multiple PDFs from tray cuts (multi-source via assemble)
- `split_item_segments` for tray/page-item splits
- `extract_text` / `extract_text_to_file` ops

## 0.12.2 — Pass 2: batch all listed files

### Added
- **Share → All listed files** checkbox: run Compress, Clean, Encrypt, Save unlocked, Resize, Reverse, Grayscale on every PDF in the list
- `sekikit.batch.run_batch_files` helper (progress, cancel between files, per-file errors)
- Batch toast shows success count; partial failures listed in a warning dialog
- Esc cancels remaining files between ops (not mid-compress of one file unless that op supports cancel)

### Notes
- Batch **skips review-before-save** (avoids N modals)
- Encrypt batch uses one password for all files (confirm dialog)

## 0.12.1 — Pass 1: decrypt, resize, reverse, blank

### Added
- **Decrypt / Save unlocked** — strip password to a new PDF (`decrypt` CLI + Share)
- **Resize pages** — fit to a4 / letter / legal (`resize` CLI + Share More)
- **Reverse** — reverse page order (`reverse` CLI + Share More); Organize **Reverse tray**
- **Blank pages** — insert blanks (`blank` CLI); Organize **Insert blank** into tray
- `create_blank_pdf` helper for blank-only files

## 0.12.0 — CLI parity + pdf_ops package

### Added
- **CLI**: `mix`, `insert`, `images`, `assemble` (parity with GUI page tools)
- Password fail in GUI now prompts and caches for the selected file

### Changed
- **`sekikit.pdf_ops`** is a package: `_core`, `structure`, `compress`, `transform`, `pagenum`, `watch` (same public API)
- Removed unused helpers (`run_job_safe`, `page_count_fast`, `ngettext`)
- Docs: product scope and free-forever positioning

## 0.11.4 — Medium hardening (sessions, review, encrypt)

### Changed
- **Organize sessions**: prune unused sources; max 12 open PDF handles (LRU)
- **Review**: stage outputs to `.sekikit-review-*.tmp.pdf`, promote only on Save; Cancel discards draft
- **Encrypt / jobs**: `validate_password` so encrypted outputs get correct page counts in the job log; review can open them

## 0.11.3 — Hardening cleanup (audit items 1–5)

### Changed
- **Split GUI**: `ui_organize.py` + `ui_share.py` mixins (smaller `app.py` shell)
- **Password cache**: resolved path only (no basename sharing)
- **`pdf_ops.op_then_renumber`**: shared by GUI + CLI
- **Job log**: basenames only (privacy — no full folder paths)
- Removed Organize legacy `_thumb_session` / `_preview_page_index` aliases

## 0.11.2 — Renumber strip = font height × full width

### Changed
- Renumber cover is a **full-page-width** band only **≈ number font height** tall
- No tall footer wipe; stamp sits inside that thin line

## 0.11.1 — Renumber no longer wipes body text

### Fixed
- Renumber probe/redaction limited to a **thin outer margin** (~8% height, max 56 pt)
- Only content whose **center** sits in that strip counts as footer/header
- Large drawings/images and body lines are ignored
- Redaction no longer uses deep page wipe that cut off print

## 0.11.0 — Organize multi-PDF tray (combine)

### Added
- **Organize page tray** holds pages from **many PDFs** (`path + page index`)
- **Load / replace**, **Add selected**, **Add all**, optional **Range** when adding
- Thumb labels show `filename` + `pN`
- **Save combined PDF** via `pdf_ops.assemble_pages`
- Extract / remove-from-tray / rotate 90° / renumber work on the tray
- Preview + fullscreen navigate the tray order across sources

### Limits
- Not a freeform layout editor; not OCR; sources are never deleted
- Bookmarks/forms across sources remain best-effort

## 0.10.7 — Page-number margin collision check

### Added
- **Footer/header content probe** before stamp/renumber (PDF text, drawings, images in the margin band)
- **Stamp**: tries alternate x/y so the number does not sit on existing print
- **Renumber**: expands white band to cover detected margin content, then stamps
- Warnings when shifted, expanded, or still crowded

### Limits (honest)
- Geometric only — **not OCR**. Scanned image-only footers may not be found.

## 0.10.6 — Hover tooltips (+ launch fix)

### Fixed
- **Wrong version in the window**: `launch.bat` and shortcuts default to **source** (venv) so the title matches `__version__`. Packaged exe only with `SEKIKIT_USE_EXE=1` or `install_shortcuts.ps1 -UsePackagedExe`.

### Added
- Short hover tooltips on interactive controls (buttons, entries, checkboxes, presets)
- Limitation warnings inline where it matters (renumber/OCR, hard crop, scan/gray, flatten, review, watch, bookmarks)

### Added
- Short hover tooltips on interactive controls (buttons, entries, checkboxes, presets)
- Limitation warnings inline where it matters (renumber/OCR, hard crop, scan/gray, flatten, review, watch, bookmarks)

## 0.10.5 — Review before save (risk-based)

### Added
- **Full-screen result review** before keeping an output (Save / Cancel)
- **Settings**: Review mode **Off · Risk only · Always** (default **Risk only**)
- Risk ops: delete, renumber, hard crop, grayscale, scan compress, flatten
- Local prefs file `sekikit_prefs.json` (never uploaded)
- Honest copy: screen preview only — not a print proof; Cancel deletes the new file

### Not promised
- Print-identical proofing, CLI review, or Watch-folder GUI review

## 0.10.4 — Renumber on all relevant ops

### Added
- **Renumber after…** checkbox on: Merge, Mix, Extract, Delete, Insert, Split, Organize (extract / delete / save order)
- Shared helper uses Share page-number style (format / position / align / start) when set
- CLI: `--renumber` on merge, extract, split, delete

Still no OCR or smart footer detection. Rotate intentionally omitted (order unchanged).

## 0.10.3 — Renumber after merge / reorder

### Added
- **Renumber mode** — cover a fixed header/footer band (white), then stamp continuous numbers for the *current* page order (`stamp` still available for blank docs)
- Share: mode **stamp | renumber**; Merge: **Renumber pages after merge**
- CLI: `page-numbers --renumber`, `renumber`, watch action `renumber`
- `pdf_ops.renumber_pages()` helper

### Explicitly not added
- No OCR / no searching for old numbers on the page
- No smart footer detection or full header designer

## 0.10.2 — Organize load fix

### Fixed
- **Organize → Load pages** broken: `ThumbnailSession` was wrongly turned into a `Path` inside `jobs.run_job` / `_run_bg`, so thumbnails never appeared
- Non-path job results are preserved on `JobResult.value`
- Arrow/Delete keys no longer steal input from text fields

### Note
If the window title still says **v0.9.1**, you are running an old packaged `dist\Sekikit\Sekikit.exe`. Rebuild with `.\scripts\build_exe.ps1`, or run source: `pythonw run.py` / set `SEKIKIT_USE_SOURCE=1` before `launch.bat`.

## 0.10.1 — Delight polish (no new product scope)

### Improved
- **Clickable file list** with name, pages, size — no more “Selected row” numbers
- **Async page counts** (cached) so the list stays snappy
- **Empty state** + **Quick** jumps (Organize / Merge / Compress / Split / Page #)
- **Toast success** with Open file / Open folder (no blocking “open folder?” modal)
- **Share**: core tools first; images / N-up / grayscale / flatten under **More tools**
- **Page number presets** (`1 / N`, `Page n`, `— n —`, …) plus Custom
- Keyboard: ↑/↓ select file, Delete remove, double-click list → Organize
- Open last output opens the file; cross-platform folder/file open helpers

Still free forever, offline only — no feature bloat.

## 0.10.0 — Phase 4 (optional extensions)

### Added
- **Page numbers** — header/footer stamp (`{n}`, `{total}`, `{i}`); Share tab + CLI `page-numbers`
- **Flatten forms** — bake form fields/annotations into page content (`doc.bake`); Share tab + CLI `flatten`
- **Watch folder** — local-only batch (compress / grayscale / page_numbers / flatten / clean); Watch tab + CLI `watch --once`
- **CI**: matrix includes **macOS** (with Windows + Ubuntu)
- **docs/LINUX_MAC.md** + `scripts/run_linux_mac.sh` for run-from-source on Linux/mac

Still free forever. No OCR, cloud, or form *design*.

## 0.9.1 — Community i18n pattern

### Added
- `sekikit.i18n` with `_()` and auto locale / `SEKIKIT_LANG`
- `locales/en.json` English catalog; partial locale files for other languages
- `docs/TRANSLATING.md` — how volunteers add translations
- Example fragment `locales/_example_fr.json`
- Build packs `locales/` into the Windows app

English remains the source language; missing keys fall back to English.

## 0.9.0 — Best-practice hardening (no public release required)

### Added / improved
- **Producer/Creator** stamped as `Sekikit <version>` on outputs
- **CLI** fully uses `jobs.run_job` (same log/warnings as GUI)
- **docs/LIMITS.md** + **docs/PRIVACY.md** (honest limits, no bloat)
- **package_local_release.ps1** — local zip + SHA256 only (does not publish)
- Grayscale **cancel** via Esc
- README links to privacy/limits and local packaging

## 0.8.3 — Reliability pass (items 5–8)

### Added
- **Per-file password cache** (session) + provider for multi-PDF jobs
- **Local job log** (`sekikit_jobs.log`) — JSON lines, offline only
- **Unified `jobs.run_job`** wraps ops (warnings + duration + log)
- **Ghostscript cancel** via Esc (process tree kill on Windows)
- **Hard crop** option (discards content outside margins; CLI `--hard`)
- **EXIF orientation** applied when building PDF from images

## 0.8.2 — Reliability pass (items 1–4)

### Added
- **Atomic writes**: temp file → validate → rename (no half-written PDFs)
- **Output validation**: re-open every result; check page count
- **Same-path guard**: refuse to overwrite input files
- **Retries** on locked files (file sync / antivirus / viewer)
- **Disk space preflight** before heavy writes
- **Warnings** for scan compress / grayscale (text becomes image)
- **Messy fixture pack** + round-trip reliability tests

## 0.8.1 — Stronger compress + large-PDF UI

### Added / improved
- **Compress presets:** `email` · `balanced` · `max` · **`scan`** (re-render pages — best for photos/scans)
- **Ghostscript** used automatically when installed (usually smaller output)
- **Proper image re-embed** via `replace_image` when available
- **Lazy thumbnails** — no 200-page hard stop; loads in batches with bounded cache
- **Cancel** long jobs with **Esc**
- Compress progress status messages

## 0.8.0 — Phase 3 (polish & power)

### Added
- **N-up** (2 / 4 / 9 pages per sheet) — Share tab + CLI
- **Grayscale** conversion — Share tab + CLI
- **Merge options:** preserve bookmarks (best-effort), fit to A4 / Letter / Legal
- **CLI** (`sekikit …`): info, merge, extract, split, compress, rotate, delete, clean, encrypt, nup, grayscale, gui
- **About** dialog (F1) with shortcuts list
- Keyboard: Ctrl+O add files, Ctrl+L load organize pages, F1 about
- GitHub Actions CI (pytest on Windows + Ubuntu)

### Notes
- Code signing / Authenticode still optional (requires a certificate you own)
- Verify release builds with hashes when publishing GitHub Releases

## 0.5.0 — Phase 2

- Organize: thumbnails, multi-select, reorder, preview zoom/fullscreen, reset pages
- Share: compress, clean metadata, encrypt, crop, images→PDF
- Scrollable Share/Split tabs

## 0.3.0 — Phase 1

- Mix, insert, delete, richer split modes, password field, full-page merge fix

## 0.1.0 — Initial

- Merge, extract, split, rotate GUI
