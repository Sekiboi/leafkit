# Leafkit Roadmap

## Free forever (non-negotiable)

**At no point will Leafkit have paid features, freemium tiers, licenses, trials, watermarks, accounts, or “Pro” unlocks.**

Every feature we ship is free for everyone — personal or commercial use — under the MIT license. No dual free/paid builds. No donation walls that gate tools. No telemetry sold as product.

---

**Goal:** Everyday offline page work (merge, split, rearrange, clean, share) in a small app one person can keep free and updated forever.

**Not the goal:** A full PDF editor (OCR, Office conversion, form designer, certificate signing). That is a different product identity and a much larger maintenance load.

---

## North star

> **Just the pages. Offline only. Free forever. For everyone.**  
> Everything you need to merge, split, rearrange, clean, and share PDFs — without uploading, accounts, or a kitchen-sink editor.

### Hard constraints (non-negotiable)

| Constraint | Why |
|------------|-----|
| **Offline only** | No network for document work; no accounts; no telemetry required to use |
| **Page toolkit, not editor** | No in-PDF text editing, OCR, form builders, cert signing |
| **No freemium / no paid side — ever** | Every feature ships free for all; complexity must stay maintainable without charging anyone |
| **Small surface** | Prefer one clear UI + few verbs over dozens of modules |
| **Windows-first** | Ship Windows builds first; other OS when cost stays low |
| **MIT, honest** | Open source; no dark patterns |

---

## Scope boundaries

### In scope (page & document *structure*)

- Merge, split, extract, rotate, mix, insert  
- Delete / reorder pages  
- Page selection (thumbnails) where it removes “type page numbers” pain  
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
| Office ↔ PDF conversion | Dependency hell; quality wars |
| Fillable form *creation* / data APIs | Separate product |
| Certificate digital signatures | PKI, smart cards, legal expectations |
| Cloud sync, accounts, collab | Violates offline-only |
| Full PDF *reader* / ePub / comics | Different app |
| Plugin marketplace / SaaS | Paid-side gravity |

### Priority filter for new tools

Only add features that are:

1. **Weekly useful** for normal people, and  
2. **Implementable** with `pypdf` / PyMuPDF (or similar) without a second career, and  
3. **Explainable in one sentence** in the UI.

| Feature area | Status notes |
|--------------|--------------|
| Organize (reorder / multi-file pages) | Shipped |
| Delete / extract / rotate pages | Shipped |
| Compress | Shipped (presets) |
| Crop | Shipped |
| Clean metadata | Shipped |
| Encrypt / decrypt | Shipped |
| Images → PDF | Shipped |
| Split by size / bookmarks | Shipped |
| Mix / insert | Shipped |
| N-up, grayscale, resize | Shipped |
| Split by text/content | No — fragile |
| PDF/A validation | No — niche + standards churn |
| Batch wizards with many options | Only if defaults stay simple |

---

## Design principles (anti-bloat rules)

1. **One window, one file list, tabs or a short tool list** — not a separate app per verb.  
2. **Defaults over dialogs** — advanced options collapsed.  
3. **Never overwrite** — always new file or `_1` suffix.  
4. **Thumbnails are optional UX** — lazy-load, cache, skip if library fails.  
5. **Two PDF engines max** — e.g. `pypdf` for structure + PyMuPDF for render/compress when needed.  
6. **If it needs a settings cloud or license server, kill it.**  
7. **Ship vertical slices** — each release is usable alone.  
8. **Tests for every op** — unit tests on blank + a small “messy PDF” fixture pack.

---

## Where we are (public beta 0.15.x)

| Area | Status |
|------|--------|
| Core page ops (merge/split/extract/rotate/mix/insert) | Done |
| Organize multi-PDF tray + Share tools | Done |
| N-up, grayscale, compress, crop, clean, encrypt | Done |
| Page numbers / renumber / flatten / watch | Done |
| Review-before-save + job log + password session cache | Done |
| Reliability rails (atomic write, no overwrite, tests) | Done |
| CLI full page toolkit | Done |
| `pdf_ops` package layout | Done |
| CI, checksums, shortcuts, Windows `.exe` / Setup | Done |
| Authenticode code signing | Later (cert) |
| Linux/mac packaged GUI + CI artifacts | Done |
| UI polish | Ongoing |
| v1.0 freeze | After real-world soak + optional signing |

---

## Phased roadmap (history & milestones)

Versions are **capability milestones**, not calendar promises.

### Phase 0 — Trust & install

GitHub Releases, shortcuts, About, crash log, changelog.

### Phase 1 — Core page ops ✅

Mix, insert, delete, richer split, merge ranges, password field, open last output.

### Phase 2 — See & organize ✅

Thumbnails, multi-select, preview, organize tray, compress, clean, encrypt, crop, images→PDF.

### Phase 3 — Polish & power ✅

N-up, grayscale, page size normalize, bookmarks on merge, CLI, CI, About.

### Phase 4 — Extensions ✅

Page numbers, flatten forms, watch folder, Linux/mac CI docs.

Still **never**: OCR, Office convert, cloud, full editor.

---

## Architecture guardrails

```text
leafkit/
  pdf_ops/        # pure operations (testable, no GUI)
  render.py       # optional thumbnails/compress backend
  app.py          # GUI only
  tests/          # ops + a few integration cases
```

| Rule | |
|------|--|
| GUI never contains PDF logic | All ops callable from tests/CLI |
| Prefer presets over sliders | Compress = few buttons, not 12 codecs |
| Dependency budget | Python + pypdf + one render/compress lib + GUI toolkit |
| No auto-update phoning home | Update = user checks GitHub Releases |

---

## Success metrics (honest, free-product style)

| Signal | Healthy |
|--------|---------|
| Time to first successful merge for a new user | &lt; 2 minutes |
| Crashers open &gt; 30 days | Near zero |
| Dependency count | Flat or down over time |
| Release notes | Every ship explains one user-visible win |

---

## Explicit non-goals (say no by default)

- Full editor / OCR / Office conversion as a product  
- Mobile apps  
- Browser extension  
- AI “summarize this PDF” (scope + privacy)  
- Adware bundlers  
- Dual free/pro builds, trials, licenses, feature paywalls of any kind  

---

## One-line pitch

**Leafkit** — offline page tools (merge, organize, compress, clean, and more) — **free forever for everyone**, no editor bloat, no paid tier.

---

*Living document. When tempted to add a feature, ask: (1) “Is this still free for everyone with no upsell?” (2) “Can we maintain it offline without becoming a full editor?” If not, default to **no**.*
