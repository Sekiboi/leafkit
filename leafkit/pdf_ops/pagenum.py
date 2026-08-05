"""Page numbers (stamp/renumber) and form flatten."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Callable

from leafkit.pdf_ops._core import (
    PasswordProvider,
    PdfOpsError,
    _assert_not_overwrite_inputs,
    _atomic_finalize,
    _ensure_pdf,
    _preflight_disk,
    _retry,
    _stamp_fitz_metadata,
    _temp_pdf_path,
    _unique_path,
    _validate_pdf_file,
    _warn,
    parse_page_range,
)
from leafkit.pdf_ops.structure import default_output_next_to
from leafkit.pdf_ops.transform import _save_fitz_atomic

_PAGE_NUM_POSITIONS = frozenset({"header", "footer"})
_PAGE_NUM_ALIGNS = frozenset({"left", "center", "right"})
WATCH_ACTIONS = frozenset(
    {
        "compress",
        "grayscale",
        "page_numbers",
        "renumber",
        "flatten",
        "clean",
    }
)


# Renumber/stamp: outer margin only (never body text as header/footer).
_PAGE_NUM_MARGIN_FRAC = 0.08
_PAGE_NUM_MARGIN_MAX_PTS = 56.0
_PAGE_NUM_MARGIN_MIN_PTS = 28.0


def _page_num_max_band(page) -> float:
    """Max header/footer strip we will ever probe or redact."""
    h = float(page.rect.height)
    return max(
        _PAGE_NUM_MARGIN_MIN_PTS,
        min(_PAGE_NUM_MARGIN_MAX_PTS, h * _PAGE_NUM_MARGIN_FRAC),
    )


def _page_num_probe_zone(page, position: str, probe_h: float | None = None):
    """Tight header/footer rectangle (outer strip only)."""
    import fitz

    rect = page.rect
    cap = _page_num_max_band(page)
    h = cap if probe_h is None else max(12.0, min(float(probe_h), cap))
    if position == "header":
        return fitz.Rect(0, 0, rect.width, h)
    return fitz.Rect(0, max(0.0, rect.height - h), rect.width, rect.height)


def _box_in_outer_margin(
    bb: tuple[float, float, float, float],
    page,
    position: str,
    max_band: float,
) -> bool:
    """True if content center sits in the outer header/footer strip only."""
    x0, y0, x1, y1 = bb
    cy = (y0 + y1) / 2.0
    ch = max(0.0, y1 - y0)
    rect = page.rect
    if ch > max(22.0, max_band * 0.85):  # tall → body, not page #
        return False
    if position == "header":
        return cy <= max_band
    return cy >= rect.height - max_band


def _collect_margin_content_boxes(
    page, position: str, probe_h: float | None = None
) -> list[tuple[float, float, float, float]]:
    """Bboxes of short text (and tiny marks) in the outer margin strip only.

    Geometric only — not OCR. Ignores body text that merely intersects a deep zone.
    """
    import fitz

    rect = page.rect
    max_band = _page_num_max_band(page)
    zone = _page_num_probe_zone(page, position, probe_h)
    boxes: list[tuple[float, float, float, float]] = []

    def _add(bb, *, allow_wide_line: bool = False) -> None:
        if not bb:
            return
        r = fitz.Rect(bb)
        if r.is_empty or r.is_infinite:
            return
        if not r.intersects(zone):
            return
        if r.width >= rect.width * 0.90 and r.height >= max_band * 1.2:
            return
        if r.height >= rect.height * 0.25:
            return
        if r.width >= rect.width * 0.92 and not allow_wide_line:
            if r.height > 6:
                return
        tup = (float(r.x0), float(r.y0), float(r.x1), float(r.y1))
        if not _box_in_outer_margin(tup, page, position, max_band):
            return
        boxes.append(tup)

    try:
        data = page.get_text("dict")
        for block in data.get("blocks", []) or []:
            btype = block.get("type", 0)
            if btype == 1:
                r = fitz.Rect(block.get("bbox") or (0, 0, 0, 0))
                if r.height <= max_band and r.width <= rect.width * 0.35:
                    _add(block.get("bbox"))
                continue
            if btype != 0:
                continue
            for line in block.get("lines", []) or []:
                for span in line.get("spans", []) or []:
                    txt = (span.get("text") or "").strip()
                    if not txt:
                        continue
                    _add(span.get("bbox"))
    except Exception:  # noqa: BLE001
        pass

    try:
        for path in page.get_drawings() or []:
            r = path.get("rect")
            if not r:
                continue
            rr = fitz.Rect(r)
            if rr.height <= 4.0 and rr.width >= 20:
                _add(r, allow_wide_line=True)
    except Exception:  # noqa: BLE001
        pass

    return boxes


def _renumber_strip_height(font_size: float) -> float:
    """Vertical cover ≈ number font size (tiny pad for glyph ink)."""
    fs = max(4.0, float(font_size))
    return max(fs + 2.0, fs * 1.15)


def _renumber_cover_rect(
    page,
    position: str,
    *,
    font_size: float,
    margin_pts: float,
    content_boxes: list[tuple[float, float, float, float]] | None = None,
):
    """Full-width cover strip, height ~ font size, parked on the number line.

    Spans the page horizontally. Vertically only a thin line-box so body print
    above/below is not redacted.
    """
    import fitz

    rect = page.rect
    strip_h = _renumber_strip_height(font_size)
    # Baseline near margin; nudge only when old # is in the outer strip
    if position == "header":
        baseline = max(font_size + 2.0, min(margin_pts + font_size, strip_h + 2))
        if content_boxes:
            cy = max((b[1] + b[3]) / 2.0 for b in content_boxes)
            if cy <= _page_num_max_band(page):
                baseline = max(font_size + 1.0, min(cy + font_size * 0.25, strip_h + 4))
        y0 = max(0.0, baseline - font_size - 1.0)
        y1 = min(rect.height, y0 + strip_h)
        y0 = max(0.0, y1 - strip_h)
    else:
        baseline = max(font_size + 2.0, rect.height - max(6.0, min(margin_pts, 40.0)))
        if content_boxes:
            cy = max((b[1] + b[3]) / 2.0 for b in content_boxes)
            if cy >= rect.height - _page_num_max_band(page):
                baseline = min(rect.height - 2.0, cy + font_size * 0.3)
        y1 = min(rect.height, baseline + 2.0)
        y0 = max(0.0, y1 - strip_h)
        min_y0 = rect.height - _page_num_max_band(page)
        if y0 < min_y0:
            y0 = min_y0
            y1 = min(rect.height, y0 + strip_h)

    return fitz.Rect(0.0, y0, rect.width, y1), strip_h, (y1 + y0) / 2.0


def _rects_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    pad: float = 1.5,
) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (
        ax1 + pad <= bx0
        or bx1 + pad <= ax0
        or ay1 + pad <= by0
        or by1 + pad <= ay0
    )


def _pick_stamp_xy(
    page,
    *,
    position: str,
    align: str,
    margin_pts: float,
    font_size: float,
    text_width: float,
    band_h: float,
    content_boxes: list[tuple[float, float, float, float]],
    mode: str,
) -> tuple[float, float, bool]:
    """Choose stamp baseline point; return (x, y, still_overlaps)."""
    rect = page.rect
    tw = text_width
    if align == "left":
        pref_xs = [margin_pts, (rect.width - tw) / 2.0, max(margin_pts, rect.width - margin_pts - tw)]
    elif align == "right":
        pref_xs = [
            max(margin_pts, rect.width - margin_pts - tw),
            (rect.width - tw) / 2.0,
            margin_pts,
        ]
    else:
        pref_xs = [
            max(0.0, (rect.width - tw) / 2.0),
            margin_pts,
            max(margin_pts, rect.width - margin_pts - tw),
        ]

    if position == "header":
        if mode == "renumber":
            pref_ys = [
                min(margin_pts + font_size, max(font_size + 2, band_h - 4)),
                font_size + 4,
                band_h * 0.55,
            ]
        else:
            pref_ys = [
                margin_pts + font_size,
                margin_pts + font_size + 12,
                font_size + 6,
                margin_pts + font_size + 24,
            ]
    else:
        if mode == "renumber":
            pref_ys = [
                max(font_size + 2, rect.height - (band_h * 0.35)),
                rect.height - 12,
                rect.height - band_h * 0.5,
            ]
        else:
            pref_ys = [
                max(font_size + 2, rect.height - margin_pts),
                rect.height - margin_pts - font_size - 6,
                rect.height - 14,
                rect.height - margin_pts - font_size - 18,
            ]

    def clamp_xy(x: float, y: float) -> tuple[float, float]:
        x = max(2.0, min(x, rect.width - 2.0))
        y = max(font_size, min(y, rect.height - 2.0))
        return x, y

    for y in pref_ys:
        for x in pref_xs:
            x, y = clamp_xy(x, y)
            stamp = (x - 1, y - font_size - 1, x + tw + 1, y + 3)
            if not any(_rects_overlap(stamp, b) for b in content_boxes):
                return x, y, False

    x, y = clamp_xy(pref_xs[0], pref_ys[0])
    stamp = (x - 1, y - font_size - 1, x + tw + 1, y + 3)
    overlaps = any(_rects_overlap(stamp, b) for b in content_boxes)
    return x, y, overlaps


def add_page_numbers(
    path: Path | str,
    output: Path | str,
    *,
    position: str = "footer",
    align: str = "center",
    format_str: str = "{n} / {total}",
    start: int = 1,
    font_size: float = 10.0,
    margin_pts: float = 28.0,
    page_spec: str | None = None,
    mode: str = "stamp",
    band_height_pts: float | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Stamp page numbers (header or footer) as permanent text.

    mode:
      stamp    — draw numbers only; shifts placement to avoid existing text when found
      renumber — white-out a header/footer band (expanded if margin text/drawings found),
                 then stamp continuous numbers for the *current* page order.

    Margin check is geometric (PDF text + drawings + images in the band), not OCR.
    Pure scanned (image-only) footers may not be detected.

    format_str placeholders:
      {n}     — page number (start + index)
      {total} — total pages in the document
      {i}     — 1-based index within the stamped range (1..count of targets)
    """
    pos = (position or "footer").strip().lower()
    al = (align or "center").strip().lower()
    mode_l = (mode or "stamp").strip().lower()
    if pos not in _PAGE_NUM_POSITIONS:
        raise PdfOpsError("Position must be 'header' or 'footer'.")
    if al not in _PAGE_NUM_ALIGNS:
        raise PdfOpsError("Align must be 'left', 'center', or 'right'.")
    if mode_l not in ("stamp", "renumber"):
        raise PdfOpsError("Mode must be 'stamp' or 'renumber'.")
    if font_size < 4 or font_size > 72:
        raise PdfOpsError("Font size must be between 4 and 72.")
    if margin_pts < 0:
        raise PdfOpsError("Margin cannot be negative.")
    if start < 0:
        raise PdfOpsError("Start number cannot be negative.")

    if band_height_pts is None:
        band_h_base = max(28.0, min(48.0, margin_pts + font_size + 8.0))
    else:
        band_h_base = float(band_height_pts)
    if mode_l == "renumber" and band_h_base < 12:
        raise PdfOpsError("Band height must be at least 12 points when renumbering.")

    src = _ensure_pdf(Path(path))
    pwd = password
    if pwd is None and password_provider is not None:
        try:
            pwd = password_provider(src)
        except Exception:  # noqa: BLE001
            pwd = None

    try:
        import fitz
    except ImportError as exc:
        raise PdfOpsError(
            "Page numbers need PyMuPDF. pip install pymupdf"
        ) from exc

    doc = fitz.open(str(src))
    try:
        if doc.is_encrypted:
            if not pwd or not doc.authenticate(pwd):
                raise PdfOpsError(f"{src.name}: password required or wrong.")
        total = doc.page_count
        if total < 1:
            raise PdfOpsError("PDF has no pages.")

        if page_spec and page_spec.strip():
            targets = parse_page_range(page_spec, total)
        else:
            targets = list(range(total))

        saw_margin_content = False
        expanded_band = False
        still_overlap = False
        shifted = False

        for range_i, page_i in enumerate(targets):
            page = doc.load_page(page_i)
            n = start + page_i
            i_in_range = range_i + 1
            try:
                text = format_str.format(n=n, total=total, i=i_in_range)
            except (KeyError, ValueError, IndexError) as exc:
                raise PdfOpsError(
                    f"Bad page-number format {format_str!r}: {exc}\n"
                    "Use placeholders {{n}}, {{total}}, {{i}} only."
                ) from exc

            try:
                tw = fitz.get_text_length(
                    text, fontname="helv", fontsize=font_size
                )
            except Exception:  # noqa: BLE001
                tw = len(text) * font_size * 0.5

            rect = page.rect
            probe_h = _page_num_max_band(page)
            content = _collect_margin_content_boxes(page, pos, probe_h)
            if content:
                saw_margin_content = True

            band_h = _renumber_strip_height(font_size)
            if mode_l == "renumber":
                # Thin full-width strip (~font height), not a tall footer wipe
                cover, band_h, _mid = _renumber_cover_rect(
                    page,
                    pos,
                    font_size=font_size,
                    margin_pts=margin_pts,
                    content_boxes=content,
                )
                try:
                    page.add_redact_annot(cover, fill=(1, 1, 1))
                    page.apply_redactions(
                        images=fitz.PDF_REDACT_IMAGE_NONE
                        if hasattr(fitz, "PDF_REDACT_IMAGE_NONE")
                        else 0
                    )
                except Exception:  # noqa: BLE001
                    page.draw_rect(
                        cover,
                        color=(1, 1, 1),
                        fill=(1, 1, 1),
                        width=0,
                        overlay=True,
                    )
                content_for_place: list[tuple[float, float, float, float]] = []
                if pos == "header":
                    y_fixed = min(cover.y1 - 2.0, cover.y0 + font_size)
                else:
                    y_fixed = max(cover.y0 + font_size, cover.y1 - 2.0)
            else:
                band_h = max(12.0, min(band_h_base, _page_num_max_band(page)))
                content_for_place = content
                y_fixed = None

            x, y, overlaps = _pick_stamp_xy(
                page,
                position=pos,
                align=al,
                margin_pts=margin_pts,
                font_size=font_size,
                text_width=tw,
                band_h=band_h,
                content_boxes=content_for_place,
                mode=mode_l,
            )
            if mode_l == "renumber" and y_fixed is not None:
                y = y_fixed
                if al == "left":
                    x = margin_pts
                elif al == "right":
                    x = max(margin_pts, rect.width - margin_pts - tw)
                else:
                    x = max(0.0, (rect.width - tw) / 2.0)
                x = max(2.0, min(x, rect.width - 2.0))
                y = max(font_size, min(y, rect.height - 2.0))
                overlaps = False
            if mode_l == "stamp" and content and not overlaps:
                shifted = True
            if overlaps:
                still_overlap = True

            page.insert_text(
                fitz.Point(x, y),
                text,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0),
                overlay=True,
            )

        if mode_l == "renumber":
            _warn(
                "Renumber: full-width strip ≈ number font height only "
                "(not a tall footer wipe). Scanned footers may remain."
            )
        else:
            if still_overlap:
                _warn(
                    "Page numbers may still overlap existing footer/header print "
                    "on some pages (crowded margin or scanned text)."
                )
            elif shifted:
                _warn(
                    "Page numbers shifted to avoid existing margin text where possible."
                )

        return _save_fitz_atomic(
            doc,
            Path(output),
            sources=[src],
            expected_pages=total,
            space_factor=1.3,
        )
    finally:
        doc.close()


def renumber_pages(
    path: Path | str,
    output: Path | str,
    *,
    position: str = "footer",
    align: str = "center",
    format_str: str = "{n} / {total}",
    start: int = 1,
    font_size: float = 10.0,
    margin_pts: float = 28.0,
    band_height_pts: float | None = None,
    page_spec: str | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Replace numbers in a header/footer band, then stamp continuous 1…N.

    Thin full-width strip ≈ font height. Geometric margin check, not OCR.
    """
    return add_page_numbers(
        path,
        output,
        position=position,
        align=align,
        format_str=format_str,
        start=start,
        font_size=font_size,
        margin_pts=margin_pts,
        page_spec=page_spec,
        mode="renumber",
        band_height_pts=band_height_pts,
        password=password,
        password_provider=password_provider,
    )


def op_then_renumber(
    produce: Callable[[Path], Path],
    final_out: Path | str,
    *,
    do_renumber: bool,
    renumber_kwargs: dict | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Run produce(temp_or_final) then optional renumber into final_out.

    Shared by GUI and CLI so renumber-after-op stays consistent.
    When do_renumber is False, produce(final_out) is returned as-is.
    """
    final = Path(final_out)
    if not do_renumber:
        return produce(final)

    final.parent.mkdir(parents=True, exist_ok=True)
    tmp = final.parent / f".leafkit-mid-{uuid.uuid4().hex}.tmp.pdf"
    mid: Path | None = None
    try:
        mid = produce(tmp)
        kw = dict(renumber_kwargs or {})
        if password is not None and "password" not in kw:
            kw["password"] = password
        if password_provider is not None and "password_provider" not in kw:
            kw["password_provider"] = password_provider
        kw.setdefault("position", "footer")
        kw.setdefault("align", "center")
        kw.setdefault("format_str", "{n} / {total}")
        kw.setdefault("start", 1)
        return renumber_pages(mid, final, **kw)
    finally:
        for p in (mid, tmp):
            if p is None:
                continue
            try:
                if not p.is_file():
                    continue
                try:
                    if final.exists() and p.resolve() == final.resolve():
                        continue
                except OSError:
                    pass
                p.unlink()
            except OSError:
                pass


def flatten_forms(
    path: Path | str,
    output: Path | str,
    *,
    annotations: bool = True,
    widgets: bool = True,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Bake form field appearances (and optionally annotations) into page content.

    After this, fields are no longer editable — the filled values become static
    drawing/text. Does not design forms; only flattens existing ones.
    """
    if not annotations and not widgets:
        raise PdfOpsError("Enable at least one of annotations or widgets.")

    src = _ensure_pdf(Path(path))
    pwd = password
    if pwd is None and password_provider is not None:
        try:
            pwd = password_provider(src)
        except Exception:  # noqa: BLE001
            pwd = None

    try:
        import fitz
    except ImportError as exc:
        raise PdfOpsError(
            "Flatten forms needs PyMuPDF. pip install pymupdf"
        ) from exc

    doc = fitz.open(str(src))
    try:
        if doc.is_encrypted:
            if not pwd or not doc.authenticate(pwd):
                raise PdfOpsError(f"{src.name}: password required or wrong.")
        total = doc.page_count
        if total < 1:
            raise PdfOpsError("PDF has no pages.")

        had_forms = bool(getattr(doc, "is_form_pdf", False))
        try:
            doc.bake(annots=bool(annotations), widgets=bool(widgets))
        except Exception as exc:  # noqa: BLE001
            raise PdfOpsError(f"Could not flatten forms: {exc}") from exc

        if not had_forms and not annotations:
            _warn("PDF had no form fields; output is a clean copy.")
        elif not had_forms:
            _warn(
                "PDF had no AcroForm fields — annotations (if any) were baked."
            )

        return _save_fitz_atomic(
            doc,
            Path(output),
            sources=[src],
            expected_pages=total,
            space_factor=1.4,
        )
    finally:
        doc.close()

