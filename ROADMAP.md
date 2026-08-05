# Leafkit Roadmap

## Free forever (non-negotiable)

**At no point will Leafkit have paid features, freemium tiers, licenses, trials, watermarks, accounts, or “Pro” unlocks.**

Every feature we ship is free for everyone — personal or commercial use — under the MIT license. No dual free/paid builds. No “basic vs premium.” No donation walls that gate tools. No telemetry sold as product.

We are building the kind of software the open internet was supposed to keep: useful, honest, offline-capable, and actually free.

When this doc says we target “PDFsam Visual–class” tools, it means: **those capabilities, free** — not a paid product of our own.

---

**Goal:** Match (and, where it matters, beat) **PDFsam** on everyday page work — **including the class of tools others put behind a paywall** — while staying a small, offline-only app that one person can keep free and updated forever.

**Not the goal:** Become Adobe / PDFsam Enhanced (full editor, OCR, Office conversion, form designer). That is a different product and a paid-team maintenance load. We refuse that path so we never need a paid side to fund it.

---

## North star

> **Just the pages. Offline only. Free forever. For everyone.**  
> Everything you need to merge, split, rearrange, clean, and share PDFs — without uploading, accounts, freemium, or a 40-module kitchen sink.
### Competitor map (what we’re chasing)

| Product | Role | Our stance |
|---------|------|------------|
| **PDFsam Basic** (free OSS) | Merge, split, extract, rotate, mix, insert | **Must match** — table stakes |
| **PDFsam Visual** (paid) | 25+ tools, thumbnails, organize, compress, crop, clean, encrypt… | **Target** — ship the high-value subset for free |
| **PDFsam Enhanced** (paid) | Full editor, OCR, forms, Office convert, sign | **Out of scope** — never |

### Hard constraints (non-negotiable)

| Constraint | Why |
|------------|-----|
| **Offline only** | No network for document work; no accounts; no telemetry required to use |
| **Page toolkit, not editor** | No in-PDF text editing, OCR, form builders, cert signing |
| **No freemium / no paid side — ever** | Every feature ships free for all; complexity must stay maintainable without charging anyone |
| **Small surface** | Prefer one clear UI + few verbs over 40 separate “modules” |
| **Windows-first** | Ship signed Windows builds; other OS only if cost stays near zero |
| **MIT, honest** | Open source; no dark patterns |

---

## Scope boundaries

### In scope (page & document *structure*)

- Merge, split, extract, rotate, mix, insert  
- Delete / reorder pages  
- Visual page selection (thumbnails) where it removes “type page numbers” pain  
- Compress (for email), crop, resize page boxes  
- Metadata clean, encrypt/decrypt (AES where libraries allow)  
- Images → PDF, simple N-up, grayscale  
- Bookmarks / size-based split when feasible  
- Portable `.exe` + shortcuts; optional signed installer later  

### Out of scope (forever, unless the product identity changes)

| Out | Why |
|-----|-----|
| OCR | Heavy models, language packs, constant quality fights |
| Edit text / images inside PDF | Full editor product; endless edge cases |
| Office ↔ PDF conversion | Dependency hell; quality wars with paid suites |
| Fillable form *creation* / data APIs | Separate product |
| Certificate digital signatures | PKI, smart cards, legal expectations |
| Cloud sync, accounts, collab | Violates offline-only |
| Full PDF *reader* / ePub / comics | Different app |
| Plugin marketplace / SaaS | Paid-side gravity |

### “Paid Visual” → free Leafkit (priority filter)

Only take Visual features that are:

1. **Weekly useful** for normal people, and  
2. **Implementable** with `pypdf` / PyMuPDF (or similar) without a second career, and  
3. **Explainable in one sentence** in the UI.

| PDFsam Visual feature | Leafkit? | Notes |
|----------------------|:----------:|-------|
| Organize (reorder / move / multi-file pages) | **Yes** | Core paid pain-killer |
| Delete pages (visual) | **Yes** | Core |
| Compress | **Yes** | High demand; quality presets only (e.g. email / balanced) |
| Crop | **Yes** | Uniform crop or simple rect; not a DTP crop studio |
| Clean metadata | **Yes** | Natural fit with offline/privacy |
| Encrypt / decrypt | **Yes** | Password protect + open protected files |
| Images → PDF | **Yes** | Common; bounded scope |
| Split by size / bookmarks | **Yes** | Completes Basic split parity |
| Mix (alternate pages) | **Yes** | Basic feature; small code |
| Insert pages | **Yes** | Basic feature |
| Extract / rotate / merge (visual) | **Yes** | Enhance existing |
| N-up | **Later** | Useful; secondary |
| Grayscale | **Later** | One-shot utility |
| Resize pages | **Later** | |
| Split by text/content | **No** | Fragile; high maintenance |
| PDF/A validation | **No** | Niche + standards churn |
| Batch folder wizards with 20 options | **Careful** | Only if defaults stay simple |

---

## Design principles (anti-bloat rules)

1. **One window, one file list, tabs or a short tool list** — not a separate app per verb.  
2. **Defaults over dialogs** — advanced options collapsed.  
3. **Never overwrite** — always new file or `_1` suffix (keep current promise).  
4. **Thumbnails are optional UX**, not a second product — lazy-load, cache, skip if library fails.  
5. **Two PDF engines max** — e.g. `pypdf` for structure + PyMuPDF for render/compress when needed; no third.  
6. **If it needs a settings cloud or license server, kill it.**  
7. **Ship vertical slices** — each release is usable alone; no 6-month “big bang.”  
8. **Tests for every op** — unit tests on blank + a small “messy PDF” fixture pack.

---

## Where we are (v0.13.2 — installer + opt-in diagnostics)

| Area | Status |
|------|--------|
| Phase 1 Basic parity (merge/split/extract/rotate/mix/insert) | Done |
| Phase 2 Organize multi-PDF tray + Share tools | Done |
| N-up, grayscale, compress, crop, clean, encrypt | Done |
| Phase 4 page numbers / renumber / flatten / watch | Done |
| Review-before-save + job log + password session cache | Done |
| Reliability rails (atomic write, no overwrite, tests) | Done |
| CLI full page toolkit (`mix`/`insert`/`images`/`assemble` + rest) | Done |
| `pdf_ops` package layout (maintainable modules) | Done |
| CI, checksums, shortcuts, Windows `.exe` | Done |
| Authenticode code signing | Later (user cert) |
| Pass 1: decrypt / resize / reverse / blank | Done (0.12.1) |
| Pass 2: batch all listed files | Done (0.12.2) |
| Pass 3: extract text + Organize split-before-selected | Done (0.12.3) |
| Pass 4: interactive crop rectangle | Done (0.12.4) |
| Pass 5: stamp image + polish | Done → **0.13.0** |
| Linux/mac packaged GUI + CI artifacts | Done (0.13.1) |
| UI polish (empty states, About/Settings, shortcuts) | Done (0.13.1) |
| v1.0 freeze | After real-world soak + optional signing |

---

## Phased roadmap

Versions are **capability milestones**, not calendar promises. Cadence target: **small release every few weeks**, not quarterly megadrops.

---

### Phase 0 — Trust & install (v0.2)

**Theme:** Feel like real freeware, not a side script.

| Item | Why | Effort |
|------|-----|--------|
| GitHub Releases with onedir zip + onefile | Distribution | S |
| `install_shortcuts` documented / one-click | Discoverability | S |
| Crash log + version in About | Support without a team | S |
| Optional: Authenticode signing (once cert budget allows) | SmartScreen | M (cost) |
| Changelog + this roadmap linked from README | Clarity | S |

**Exit criteria:** Stranger downloads Release, runs app, sees bird icon, no console.

---

### Phase 1 — Full PDFsam **Basic** parity (v0.3) ✅

**Theme:** Everything free SAM does by page numbers — we do too.  
**Shipped in v0.3.0** (page-number UI; visual thumbs = Phase 2).

| Feature | Detail | Status |
|---------|--------|--------|
| **Mix** | Alternate pages from 2+ PDFs; optional reverse second | Done |
| **Insert pages** | Insert PDF/pages at a position | Done |
| **Delete pages** | By range (numbers) | Done |
| **Split: at page list** | Split before given page numbers | Done |
| **Split: even/odd** | Two files: odd pages / even pages | Done |
| **Split: by file size** | Target max MB per part | Done |
| **Split: by bookmarks** | Outline level N | Done |
| **Merge: page ranges per file** | One range line per file in list order | Done |
| **Password field** | Open encrypted PDFs (stays on device) | Done |
| **Open last output** | Session memory → open folder | Done |

**Exit criteria:** Side-by-side checklist vs PDFsam Basic tools: **covered** (UI simpler; no thumbnails yet).

---

### Phase 2 — Visual paid value, free (v0.5) ✅

**Theme:** What people pay Visual for — **see pages, organize, share-ready** — without Enhanced.  
**Shipped in v0.5.0** (all free, offline only).

#### 2a — Eyes ✅

| Feature | Status |
|---------|--------|
| Page thumbnails (PyMuPDF) | Done |
| Click multi-select | Done |
| Preview panel | Done |

#### 2b — Organize ✅

| Feature | Status |
|---------|--------|
| Reorder (← Move / Move →) | Done |
| Delete / extract / rotate selected | Done |
| Save reordered PDF | Done |
| Multi-PDF page tray | Deferred (Phase 3 optional) |

#### 2c — Share-ready ✅

| Feature | Status |
|---------|--------|
| Compress (email / balanced / max) | Done |
| Clean metadata | Done |
| Encrypt (AES-256 when cryptography present) | Done |
| Crop uniform margins | Done |
| Images → PDF | Done |

**Exit criteria:** Met for weekly Visual-class tasks.

---

### Phase 3 — Polish & power (v0.8) ✅

**Theme:** Reliable freeware people recommend.  
**Shipped in v0.8.0** (still free forever).

| Feature | Status |
|---------|--------|
| **N-up** 2/4/9 | Done (GUI + CLI) |
| **Grayscale** | Done (GUI + CLI) |
| **Page size normalize** on merge | Done (a4/letter/legal) |
| **Bookmarks on merge** | Done (best-effort) |
| **CLI** | Done |
| **CI** | Done (GitHub Actions) |
| **About + shortcuts** | Done |
| **Release SHA256 script** | Done |
| **Authenticode signing** | Optional — needs purchased cert |
| **v1.0 freeze** | After real-world soak |

**Exit criteria for 1.0:** Basic + Organize + Share + CLI stable in the wild; then freeze features.

---

### Phase 4 — Optional extensions ✅ (v0.10.0)

Shipped while staying free, offline, and one-person-maintainable:

| Feature | Status |
|---------|--------|
| Header/footer **page numbers** | Done (Share + CLI `page-numbers`) |
| **Flatten form** appearances (not form design) | Done (Share + CLI `flatten`) |
| **Watch folder** batch (local only) | Done (Watch tab + CLI `watch`) |
| Linux/mac **CI** + source run docs | Done (macOS in matrix; `docs/LINUX_MAC.md`) |

Still **never**: OCR, Office convert, cloud, editor.  
Packaged Linux/mac installers remain optional / low priority (Windows onedir is primary).

---

## Architecture guardrails (so one person can maintain this)

```text
leafkit/
  pdf_ops.py      # pure operations (testable, no GUI)
  render.py       # optional thumbnails/compress backend
  app.py          # GUI only
  tests/          # ops + a few integration cases
```

| Rule | |
|------|--|
| GUI never contains PDF logic | All ops callable from tests/CLI |
| Prefer presets over sliders | Compress = 3 buttons, not 12 codecs |
| Feature flags in UI | Hide unfinished tools |
| Dependency budget | Python + pypdf + one render/compress lib + GUI toolkit |
| No auto-update phoning home | Update = user checks GitHub Releases (or later optional manual “check”) |

---

## Success metrics (honest, free-product style)

We don’t need revenue metrics. We need:

| Signal | Healthy |
|--------|---------|
| Time to first successful merge for a new user | &lt; 2 minutes |
| “I needed Visual for X” — X covered free? | Organize, compress, clean, delete, encrypt |
| Issues that stay open &gt; 30 days | Near zero for crashers |
| Dependency count | Flat or down over time |
| Release notes | Every ship explains one user-visible win |

---

## Explicit non-goals (say no by default)

- Matching Enhanced feature lists in marketing  
- Mobile apps  
- Browser extension  
- AI “summarize this PDF” (scope + API cost + privacy story risk)  
- Softpedia-style adware bundlers  
- Dual free/pro builds, trials, licenses, feature paywalls of any kind  

---

## Suggested sequence (summary)

```text
v0.2  Trust: Releases, About, install path
v0.3  Basic ops: mix, insert, delete, richer split
v0.4  Passwords + merge page ranges  →  Basic parity
v0.5  Thumbnails + click select
v0.6  Organize (reorder / multi-select tools)  →  main paid unlock
v0.7  Compress, clean, encrypt, crop, images→PDF
v0.8  N-up, grayscale, normalize, CLI
v1.0  Stabilize, sign, freeze
```

---

## One-line pitch (for README / Release)

**Leafkit** — PDFsam-class page tools (including what others charge for: organize, compress, clean) — offline only, **free forever for everyone**, no editor bloat, no paid tier — ever.

---

*Living document. When tempted to add a feature, ask: (1) “Is this still free for everyone with no upsell?” (2) “Would others charge for this under Visual, and can we maintain it without ever charging?” If not Basic parity / Visual-class value, or if it pressures us toward a paid side, default to **no**.*
