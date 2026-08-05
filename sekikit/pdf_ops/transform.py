"""Clean metadata, encrypt, crop, N-up, grayscale, images→PDF."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from pypdf import PdfWriter

from sekikit.pdf_ops._core import (
    PasswordProvider,
    PdfOpsError,
    _assert_not_overwrite_inputs,
    _atomic_finalize,
    _ensure_pdf,
    _estimate_size,
    _open_reader,
    _preflight_disk,
    _retry,
    _stamp_fitz_metadata,
    _temp_pdf_path,
    _transfer_pages,
    _unique_path,
    _validate_pdf_file,
    _warn,
    _write_writer,
    parse_page_range,
)

def clean_metadata(
    path: Path | str,
    output: Path | str,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Strip document info metadata (author, title, dates, etc.)."""
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    writer = PdfWriter()
    _transfer_pages(writer, reader, list(range(len(reader.pages))))
    try:
        writer.add_metadata({})
    except Exception:  # noqa: BLE001
        pass
    try:
        writer.metadata = None  # type: ignore[assignment]
    except Exception:  # noqa: BLE001
        pass
    # Empty fields for viewers that keep residual info after clear
    empty = {
        "/Author": "",
        "/Title": "",
        "/Subject": "",
        "/Keywords": "",
        "/Creator": "",
        "/Producer": "Sekikit",
    }
    try:
        writer.add_metadata(empty)
    except Exception:  # noqa: BLE001
        pass
    return _write_writer(writer, Path(output), sources=[src])


def encrypt_pdf(
    path: Path | str,
    output: Path | str,
    user_password: str,
    owner_password: str | None = None,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Password-protect a PDF (AES when supported by pypdf)."""
    if not user_password:
        raise PdfOpsError("User password cannot be empty.")
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    writer = PdfWriter()
    _transfer_pages(writer, reader, list(range(len(reader.pages))))
    owner = owner_password if owner_password else user_password
    try:
        writer.encrypt(user_password, owner_password=owner, algorithm="AES-256")
    except Exception:
        try:
            writer.encrypt(user_password, owner_password=owner)
        except Exception as exc:  # noqa: BLE001
            raise PdfOpsError(
                f"Could not encrypt: {exc}. "
                "Tip: pip install cryptography for AES-256."
            ) from exc
    return _write_writer(
        writer,
        Path(output),
        sources=[src],
        expected_pages=len(writer.pages),
        space_factor=1.3,
    )


def extract_text(
    path: Path | str,
    *,
    page_spec: str | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> str:
    """Extract selectable text from a PDF (not OCR).

    Prefers PyMuPDF when available; falls back to pypdf.
    Image-only / scanned pages often return little or no text.
    """
    src = _ensure_pdf(Path(path))
    pwd = password
    if pwd is None and password_provider is not None:
        try:
            pwd = password_provider(src)
        except Exception:  # noqa: BLE001
            pwd = None

    try:
        import fitz

        doc = fitz.open(str(src))
        try:
            if doc.is_encrypted and not doc.authenticate(pwd or ""):
                raise PdfOpsError(f"{src.name}: password required or wrong.")
            total = doc.page_count
            if total < 1:
                return ""
            if page_spec and page_spec.strip():
                indices = parse_page_range(page_spec, total)
            else:
                indices = list(range(total))
            parts: list[str] = []
            for i in indices:
                page = doc.load_page(i)
                parts.append(page.get_text("text") or "")
            text = "\n".join(parts).strip()
            if not text:
                _warn(
                    f"{src.name}: little or no selectable text "
                    "(scanned/image-only pages need OCR — not supported)."
                )
            return text
        finally:
            doc.close()
    except PdfOpsError:
        raise
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        raise PdfOpsError(f"Could not extract text: {exc}") from exc

    # pypdf fallback
    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)
    if total < 1:
        return ""
    if page_spec and page_spec.strip():
        indices = parse_page_range(page_spec, total)
    else:
        indices = list(range(total))
    parts = []
    for i in indices:
        try:
            parts.append(reader.pages[i].extract_text() or "")
        except Exception:  # noqa: BLE001
            parts.append("")
    text = "\n".join(parts).strip()
    if not text:
        _warn(
            f"{src.name}: little or no selectable text "
            "(scanned/image-only pages need OCR — not supported)."
        )
    return text


def extract_text_to_file(
    path: Path | str,
    output: Path | str,
    *,
    page_spec: str | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Write extracted text to a UTF-8 .txt file (not OCR)."""
    text = extract_text(
        path,
        page_spec=page_spec,
        password=password,
        password_provider=password_provider,
    )
    out = Path(output)
    if out.suffix.lower() != ".txt":
        out = out.with_suffix(".txt")
    out = _unique_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        out.write_text(text + ("\n" if text and not text.endswith("\n") else ""), encoding="utf-8")
    except OSError as exc:
        raise PdfOpsError(f"Could not write text file: {exc}") from exc
    return out


def decrypt_pdf(
    path: Path | str,
    output: Path | str,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Write a new PDF without user/owner password (requires open password if locked).

    If the source is not encrypted, still rewrites a clean unencrypted copy and warns.
    """
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    if not getattr(reader, "is_encrypted", False):
        _warn(f"{src.name}: not password-protected; wrote an unlocked copy.")
    writer = PdfWriter()
    _transfer_pages(writer, reader, list(range(len(reader.pages))))
    return _write_writer(
        writer,
        Path(output),
        sources=[src],
        expected_pages=len(writer.pages),
        space_factor=1.3,
    )


def crop_margins(
    path: Path | str,
    output: Path | str,
    margin_pts: float,
    page_spec: str | None = None,
    *,
    hard: bool = False,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Inset margins by margin_pts (PDF points, 72 pt = 1 inch) on all sides.

    soft (hard=False): set CropBox/MediaBox only (content still in file).
    hard (hard=True): bake crop via MuPDF clip — content outside is discarded.
    """
    if margin_pts < 0:
        raise PdfOpsError("Margin cannot be negative.")
    src = Path(path)

    if hard:
        return _hard_crop_margins(
            src,
            Path(output),
            margin_pts,
            page_spec=page_spec,
            password=password,
            password_provider=password_provider,
        )

    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)
    if page_spec and page_spec.strip():
        targets = set(parse_page_range(page_spec, total))
    else:
        targets = set(range(total))

    writer = PdfWriter()
    _transfer_pages(writer, reader, list(range(total)))
    for i, page in enumerate(writer.pages):
        if i not in targets:
            continue
        try:
            mb = page.mediabox
            left = float(mb.left) + margin_pts
            bottom = float(mb.bottom) + margin_pts
            right = float(mb.right) - margin_pts
            top = float(mb.top) - margin_pts
            if right - left < 10 or top - bottom < 10:
                raise PdfOpsError(
                    f"Margin too large for page {i + 1} — almost nothing would remain."
                )
            from pypdf.generic import RectangleObject

            box = RectangleObject((left, bottom, right, top))
            page.cropbox = box
            page.trimbox = box
            page.mediabox = box
        except PdfOpsError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PdfOpsError(f"Crop failed on page {i + 1}: {exc}") from exc

    return _write_writer(writer, Path(output), sources=[src], expected_pages=total)


def crop_box(
    path: Path | str,
    output: Path | str,
    rect: tuple[float, float, float, float],
    *,
    page_spec: str | None = None,
    hard: bool = False,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Crop pages to a rectangle in PDF points (origin bottom-left).

    rect: (x0, y0, x1, y1) relative to each page's mediabox lower-left.
    soft: set CropBox/MediaBox. hard: bake clip via PyMuPDF (discards outside).
    """
    try:
        x0, y0, x1, y1 = (float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
    except (TypeError, ValueError, IndexError) as exc:
        raise PdfOpsError("Crop rectangle must be four numbers (x0 y0 x1 y1).") from exc
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    if x1 - x0 < 10 or y1 - y0 < 10:
        raise PdfOpsError("Crop rectangle is too small (need at least ~10 pt each side).")

    src = Path(path)
    if hard:
        return _hard_crop_box(
            src,
            Path(output),
            (x0, y0, x1, y1),
            page_spec=page_spec,
            password=password,
            password_provider=password_provider,
        )

    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)
    if page_spec and page_spec.strip():
        targets = set(parse_page_range(page_spec, total))
    else:
        targets = set(range(total))

    writer = PdfWriter()
    _transfer_pages(writer, reader, list(range(total)))
    from pypdf.generic import RectangleObject

    for i, page in enumerate(writer.pages):
        if i not in targets:
            continue
        try:
            mb = page.mediabox
            left = float(mb.left) + x0
            bottom = float(mb.bottom) + y0
            right = float(mb.left) + x1
            top = float(mb.bottom) + y1
            # Clamp to media
            left = max(float(mb.left), min(left, float(mb.right) - 10))
            bottom = max(float(mb.bottom), min(bottom, float(mb.top) - 10))
            right = max(left + 10, min(right, float(mb.right)))
            top = max(bottom + 10, min(top, float(mb.top)))
            box = RectangleObject((left, bottom, right, top))
            page.cropbox = box
            page.trimbox = box
            page.mediabox = box
        except PdfOpsError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PdfOpsError(f"Crop box failed on page {i + 1}: {exc}") from exc

    return _write_writer(writer, Path(output), sources=[src], expected_pages=total)


def _hard_crop_box(
    src: Path,
    output: Path,
    rect: tuple[float, float, float, float],
    *,
    page_spec: str | None,
    password: str | None,
    password_provider: PasswordProvider | None,
) -> Path:
    """Hard crop to rect given in PDF points (bottom-left origin)."""
    try:
        import fitz
    except ImportError as imp_exc:
        raise PdfOpsError(
            "Hard crop needs PyMuPDF. pip install pymupdf"
        ) from imp_exc

    x0, y0, x1, y1 = rect
    pwd = password
    if pwd is None and password_provider is not None:
        try:
            pwd = password_provider(src)
        except Exception:  # noqa: BLE001
            pwd = None

    doc = fitz.open(str(src))
    try:
        if doc.is_encrypted and not doc.authenticate(pwd or ""):
            raise PdfOpsError(f"{src.name} is password-protected.")
        total = doc.page_count
        if total < 1:
            raise PdfOpsError("PDF has no pages.")
        if page_spec and page_spec.strip():
            targets = set(parse_page_range(page_spec, total))
        else:
            targets = set(range(total))

        out_doc = fitz.open()
        try:
            for i in range(total):
                page = doc.load_page(i)
                rect_p = page.rect
                if i in targets:
                    # PDF bottom-left → MuPDF top-left
                    fx0 = rect_p.x0 + x0
                    fx1 = rect_p.x0 + x1
                    fy0 = rect_p.y1 - y1
                    fy1 = rect_p.y1 - y0
                    clip = fitz.Rect(fx0, fy0, fx1, fy1) & rect_p
                    if clip.width < 10 or clip.height < 10:
                        raise PdfOpsError(
                            f"Crop rectangle too small/outside page {i + 1}."
                        )
                    new_page = out_doc.new_page(width=clip.width, height=clip.height)
                    new_page.show_pdf_page(
                        new_page.rect, doc, i, clip=clip, keep_proportion=False
                    )
                else:
                    new_page = out_doc.new_page(
                        width=rect_p.width, height=rect_p.height
                    )
                    new_page.show_pdf_page(new_page.rect, doc, i)
            return _save_fitz_atomic(
                out_doc,
                output,
                sources=[src],
                expected_pages=total,
                space_factor=2.0,
            )
        finally:
            out_doc.close()
    finally:
        doc.close()


def _hard_crop_margins(
    src: Path,
    output: Path,
    margin_pts: float,
    page_spec: str | None,
    *,
    password: str | None,
    password_provider: PasswordProvider | None,
) -> Path:
    """Bake margin crop by clipping page content (PyMuPDF)."""
    try:
        import fitz
    except ImportError as imp_exc:
        raise PdfOpsError(
            "Hard crop needs PyMuPDF. pip install pymupdf"
        ) from imp_exc

    pwd = password
    if pwd is None and password_provider is not None:
        try:
            pwd = password_provider(src)
        except Exception:  # noqa: BLE001
            pwd = None

    doc = fitz.open(str(src))
    try:
        if doc.is_encrypted and not doc.authenticate(pwd or ""):
            raise PdfOpsError(f"{src.name} is password-protected.")
        total = doc.page_count
        if total < 1:
            raise PdfOpsError("PDF has no pages.")
        if page_spec and page_spec.strip():
            targets = set(parse_page_range(page_spec, total))
        else:
            targets = set(range(total))

        out_doc = fitz.open()
        try:
            for i in range(total):
                page = doc.load_page(i)
                rect = page.rect
                if i in targets:
                    clip = fitz.Rect(
                        rect.x0 + margin_pts,
                        rect.y0 + margin_pts,
                        rect.x1 - margin_pts,
                        rect.y1 - margin_pts,
                    )
                    if clip.width < 10 or clip.height < 10:
                        raise PdfOpsError(
                            f"Margin too large for page {i + 1} — almost nothing would remain."
                        )
                    new_page = out_doc.new_page(width=clip.width, height=clip.height)
                    new_page.show_pdf_page(
                        new_page.rect, doc, i, clip=clip, keep_proportion=False
                    )
                else:
                    new_page = out_doc.new_page(width=rect.width, height=rect.height)
                    new_page.show_pdf_page(new_page.rect, doc, i)
            return _save_fitz_atomic(
                out_doc,
                output,
                sources=[src],
                expected_pages=total,
                space_factor=2.0,
            )
        finally:
            out_doc.close()
    finally:
        doc.close()


def _save_fitz_atomic(
    out_doc,
    output: Path,
    *,
    sources: list[Path],
    expected_pages: int,
    space_factor: float = 2.2,
) -> Path:
    """Save a PyMuPDF document via temp file + validate + replace."""
    requested = Path(output)
    _assert_not_overwrite_inputs(sources, requested)
    out = _unique_path(requested)
    out.parent.mkdir(parents=True, exist_ok=True)
    _assert_not_overwrite_inputs(sources, out)
    _preflight_disk(out.parent, int(_estimate_size(sources) * space_factor))
    tmp = _temp_pdf_path(out)

    def _save() -> None:
        _stamp_fitz_metadata(out_doc)
        out_doc.save(
            str(tmp),
            garbage=4,
            deflate=True,
            clean=True,
            deflate_images=True,
        )

    try:
        _retry(_save, what="Write temporary PDF")
        return _atomic_finalize(
            tmp, out, min_pages=1, expected_pages=expected_pages
        )
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def nup_pdf(
    path: Path | str,
    output: Path | str,
    n: int = 2,
    *,
    password: str | None = None,
) -> Path:
    """Put n pages per sheet (2, 4, or 9) — N-up layout via PyMuPDF."""
    if n not in (2, 4, 9):
        raise PdfOpsError("N-up supports 2, 4, or 9 pages per sheet.")
    src = _ensure_pdf(Path(path))

    try:
        import fitz
    except ImportError as exc:
        raise PdfOpsError("N-up needs PyMuPDF. pip install pymupdf") from exc

    cols = {2: 2, 4: 2, 9: 3}[n]
    rows = {2: 1, 4: 2, 9: 3}[n]

    doc = fitz.open(str(src))
    try:
        if doc.is_encrypted and password:
            if not doc.authenticate(password):
                raise PdfOpsError(f"{src.name}: wrong password.")
        if doc.page_count < 1:
            raise PdfOpsError("PDF has no pages.")

        first = doc[0].rect
        cell_w, cell_h = first.width, first.height
        sheet_w = cell_w * cols
        sheet_h = cell_h * rows
        expected = (doc.page_count + n - 1) // n

        out_doc = fitz.open()
        try:
            i = 0
            while i < doc.page_count:
                page = out_doc.new_page(width=sheet_w, height=sheet_h)
                for r in range(rows):
                    for c in range(cols):
                        if i >= doc.page_count:
                            break
                        x0 = c * cell_w
                        y0 = r * cell_h
                        rect = fitz.Rect(x0, y0, x0 + cell_w, y0 + cell_h)
                        page.show_pdf_page(rect, doc, i, keep_proportion=True)
                        i += 1
            return _save_fitz_atomic(
                out_doc,
                Path(output),
                sources=[src],
                expected_pages=expected,
                space_factor=1.8,
            )
        finally:
            out_doc.close()
    finally:
        doc.close()


def grayscale_pdf(
    path: Path | str,
    output: Path | str,
    *,
    password: str | None = None,
    dpi: int = 150,
    cancel_check: Callable[[], bool] | None = None,
) -> Path:
    """Convert all pages to grayscale (re-render; good for print/email)."""
    src = _ensure_pdf(Path(path))
    _warn(
        "Grayscale re-renders pages as images — text will no longer be selectable."
    )

    try:
        import fitz
    except ImportError as exc:
        raise PdfOpsError("Grayscale needs PyMuPDF. pip install pymupdf") from exc

    doc = fitz.open(str(src))
    try:
        if doc.is_encrypted and password:
            if not doc.authenticate(password):
                raise PdfOpsError(f"{src.name}: wrong password.")
        if doc.page_count < 1:
            raise PdfOpsError("PDF has no pages.")

        out_doc = fitz.open()
        try:
            mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
            total = doc.page_count
            for i in range(total):
                if cancel_check and cancel_check():
                    raise PdfOpsError("Cancelled.")
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, alpha=False)
                rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(rect, pixmap=pix)
            return _save_fitz_atomic(
                out_doc,
                Path(output),
                sources=[src],
                expected_pages=total,
                space_factor=2.5,
            )
        finally:
            out_doc.close()
    finally:
        doc.close()


def images_to_pdf(
    image_paths: list[Path | str],
    output: Path | str,
) -> Path:
    """Build a PDF from image files (PNG/JPEG/etc.), one page per image."""
    paths = [Path(p) for p in image_paths]
    if not paths:
        raise PdfOpsError("Add at least one image.")
    for p in paths:
        if not p.is_file():
            raise PdfOpsError(f"Image not found: {p}")

    try:
        import fitz
    except ImportError as exc:
        raise PdfOpsError(
            "Images→PDF needs PyMuPDF. Install: pip install pymupdf"
        ) from exc

    from io import BytesIO

    from PIL import Image as PILImage
    from PIL import ImageOps

    doc = fitz.open()
    try:
        for p in paths:
            try:
                with PILImage.open(p) as im:
                    im = ImageOps.exif_transpose(im)
                    if im.mode not in ("RGB", "L", "RGBA"):
                        im = im.convert("RGB")
                    w, h = im.size
                    page = doc.new_page(width=w, height=h)
                    buf = BytesIO()
                    fmt = "PNG" if im.mode in ("RGBA", "L") else "JPEG"
                    if fmt == "JPEG" and im.mode != "RGB":
                        im = im.convert("RGB")
                    im.save(buf, format=fmt, quality=92, optimize=True)
                    page.insert_image(page.rect, stream=buf.getvalue())
            except Exception as exc:  # noqa: BLE001
                raise PdfOpsError(f"Could not add image {p.name}: {exc}") from exc
        if doc.page_count < 1:
            raise PdfOpsError("No pages created from images.")
        return _save_fitz_atomic(
            doc,
            Path(output),
            sources=paths,
            expected_pages=len(paths),
            space_factor=1.5,
        )
    finally:
        doc.close()


_STAMP_POSITIONS = frozenset(
    {
        "center",
        "top-left",
        "top-right",
        "bottom-left",
        "bottom-right",
        "top",
        "bottom",
    }
)


def stamp_image(
    path: Path | str,
    image_path: Path | str,
    output: Path | str,
    *,
    position: str = "bottom-right",
    margin_pts: float = 36.0,
    scale: float = 0.25,
    opacity: float = 1.0,
    page_spec: str | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Overlay an image on PDF pages (simple stamp — not a watermark studio).

    position: center | top-left | top-right | bottom-left | bottom-right | top | bottom
    scale: fraction of page width (0.05–1.0). opacity: 0–1 (best-effort via pixmap).
    """
    src = _ensure_pdf(Path(path))
    img_path = Path(image_path)
    if not img_path.is_file():
        raise PdfOpsError(f"Image not found: {img_path}")
    pos = (position or "bottom-right").strip().lower().replace("_", "-")
    if pos not in _STAMP_POSITIONS:
        raise PdfOpsError(
            "position must be center, top-left, top-right, bottom-left, "
            "bottom-right, top, or bottom."
        )
    sc = float(scale)
    if sc < 0.05 or sc > 1.0:
        raise PdfOpsError("scale must be between 0.05 and 1.0.")
    op = max(0.0, min(1.0, float(opacity)))
    margin = max(0.0, float(margin_pts))

    try:
        import fitz
    except ImportError as exc:
        raise PdfOpsError("Stamp image needs PyMuPDF. pip install pymupdf") from exc

    from io import BytesIO

    from PIL import Image as PILImage
    from PIL import ImageOps

    try:
        with PILImage.open(img_path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "RGBA", "L"):
                im = im.convert("RGBA")
            if op < 0.999:
                if im.mode != "RGBA":
                    im = im.convert("RGBA")
                alpha = im.split()[-1]
                # scale alpha channel
                alpha = alpha.point(lambda a: int(a * op))
                im.putalpha(alpha)
            buf = BytesIO()
            im.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            iw, ih = im.size
    except Exception as exc:  # noqa: BLE001
        raise PdfOpsError(f"Could not read image {img_path.name}: {exc}") from exc

    pwd = password
    if pwd is None and password_provider is not None:
        try:
            pwd = password_provider(src)
        except Exception:  # noqa: BLE001
            pwd = None

    doc = fitz.open(str(src))
    try:
        if doc.is_encrypted and not doc.authenticate(pwd or ""):
            raise PdfOpsError(f"{src.name}: password required or wrong.")
        total = doc.page_count
        if total < 1:
            raise PdfOpsError("PDF has no pages.")
        if page_spec and page_spec.strip():
            targets = set(parse_page_range(page_spec, total))
        else:
            targets = set(range(total))

        for i in targets:
            page = doc.load_page(i)
            pr = page.rect
            target_w = pr.width * sc
            aspect = ih / max(iw, 1)
            target_h = target_w * aspect
            if target_h > pr.height * 0.95:
                target_h = pr.height * sc
                target_w = target_h / max(aspect, 1e-6)

            if pos == "center":
                x0 = pr.x0 + (pr.width - target_w) / 2
                y0 = pr.y0 + (pr.height - target_h) / 2
            elif pos == "top-left":
                x0 = pr.x0 + margin
                y0 = pr.y0 + margin
            elif pos == "top-right":
                x0 = pr.x1 - margin - target_w
                y0 = pr.y0 + margin
            elif pos == "bottom-left":
                x0 = pr.x0 + margin
                y0 = pr.y1 - margin - target_h
            elif pos == "top":
                x0 = pr.x0 + (pr.width - target_w) / 2
                y0 = pr.y0 + margin
            elif pos == "bottom":
                x0 = pr.x0 + (pr.width - target_w) / 2
                y0 = pr.y1 - margin - target_h
            else:  # bottom-right
                x0 = pr.x1 - margin - target_w
                y0 = pr.y1 - margin - target_h

            rect = fitz.Rect(x0, y0, x0 + target_w, y0 + target_h)
            page.insert_image(rect, stream=img_bytes, keep_proportion=True)

        return _save_fitz_atomic(
            doc,
            Path(output),
            sources=[src],
            expected_pages=total,
            space_factor=1.8,
        )
    finally:
        doc.close()

