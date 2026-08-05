# Leafkit — limits & honesty

Free forever, offline only. This document states what we **do well** and what we **do not claim**.

## Privacy

- PDF content is processed **only on your machine**.
- No accounts, no upload, no analytics, no required network.
- Optional tools you install yourself (e.g. Ghostscript) also run **locally**.
- Session passwords live in memory only; they are not written to disk.
- `leafkit_jobs.log` is a **local** JSON log of operations (file **basenames** only — not full folder paths — plus duration, success, warnings). It never leaves your PC unless **you** copy it.

## Safe outputs

- Writes go to a temp file, are re-opened to check page count, then renamed into place.
- We refuse to overwrite an input path with an output path.
- Unique names (`_1`, `_2`, …) avoid clobbering existing files.
- Retries on common Windows lock races (viewer open, OneDrive, antivirus).

## Known limits (by design or cost)

| Topic | Limit |
|--------|--------|
| **RAM** | Most ops load the whole PDF. Multi‑GB files may be slow or fail. |
| **Organize thumbs** | Lazy-loaded; huge page counts need time/RAM. |
| **Organize multi-PDF** | Page tray only (order + save). Not freeform layout. Bookmarks/forms across sources best-effort. Sources never deleted. |
| **Bookmarks on merge** | Best-effort; complex outlines may not transfer perfectly. |
| **Soft crop** | Changes page boxes; some viewers still show full media. Use **hard crop** to discard content. |
| **Scan compress / grayscale** | Re-render pages as images — text is no longer selectable. |
| **Password PDFs** | User password supported; exotic DRM is not. |
| **Signed / certified PDFs** | Operations may break digital signatures (expected). |
| **Code signing** | Official builds may be unsigned until a certificate is available; SmartScreen may warn. |
| **Platform** | Windows is primary (packaged `.exe`). Linux/mac: CLI + run-from-source GUI; see `docs/LINUX_MAC.md`. |
| **Page numbers** | Simple Helvetica stamp; not a full header/footer designer. |
| **Page numbers / renumber** | **Renumber** redacts a **full-width strip ≈ number font height** (not a tall footer block), then stamps. **Stamp** may shift to avoid margin text. **Not OCR**. Scanned image-only footers may remain. |
| **Review before save** | Draft is staged as a hidden temp file, then **promoted only on Save**. Cancel discards the draft. Screen preview only — not a print proof. Mode: Off / Risk only / Always. CLI and Watch skip GUI review. |
| **Flatten forms** | Bakes existing fields/annotations; does not create or design forms. |
| **Watch folder** | Local poll only; not recursive; input≠output folder recommended. |
| **CLI** | Full page toolkit including mix / insert / images / assemble / decrypt / resize / reverse / blank. Same engines as GUI. |
| **Decrypt** | User-password unlock only; exotic DRM / owner-only quirks may remain. Unlocked copies are your responsibility. |
| **Resize pages** | Fit-inside standard sizes (may add margin). Not crop-to-fill. |
| **Batch (all listed)** | Share checkbox only. Skips review-before-save. Esc stops **between** files. One shared encrypt password. Not merge/mix. |
| **Extract text** | Selectable PDF text only — **not OCR**. Scans/image pages often empty. Layout not preserved. |
| **Tray split before selected** | Cuts at selected tray positions (not first page). Multi-PDF tray OK. |
| **Interactive / box crop** | One rectangle for chosen pages (this page or all). Soft = boxes; hard = discard outside. Not per-page different rects; not a print-shop trim tool. |
| **Stamp image** | One image, one position, optional opacity. Not tiled/diagonal watermark studio. |

## Scope (what Leafkit is)

Leafkit is an **offline page-structure toolkit**: organize, merge, split, compress, clean, encrypt, and related tools. It is **not** a full PDF editor: no OCR, in-PDF text rewrite, Office conversion, form designer, or certificate-signing product.

## What we will not add (scope)

- Cloud sync, accounts, freemium
- Full PDF editor, OCR, Office conversion
- Form designers, certificate digital-signature workflows as a product

## Reporting issues

Nothing is uploaded automatically. To help improve Leafkit:

1. **About (F1) → Copy diagnostics** (or Save diagnostics…).  
2. Open a [GitHub Issue](https://github.com/Sekiboi/leafkit/issues/new/choose) (Bug or Crash template).  
3. Paste the diagnostics and steps to reproduce.

See [REPORTING.md](REPORTING.md). Prefer not to send confidential PDFs.
