"""PDF compression (Ghostscript optional, MuPDF image re-encode, scan re-render)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from leafkit.pdf_ops._core import (
    PasswordProvider,
    PdfOpsError,
    _assert_not_overwrite_inputs,
    _atomic_finalize,
    _ensure_pdf,
    _open_reader,
    _preflight_disk,
    _retry,
    _stamp_fitz_metadata,
    _temp_pdf_path,
    _unique_path,
    _validate_pdf_file,
    _warn,
)
from leafkit.pdf_ops.transform import _save_fitz_atomic

# balanced=structure, email=images+cleanup, max=strong re-encode, scan=rasterize
COMPRESS_PRESETS = ("email", "balanced", "max", "scan")


def find_ghostscript() -> Path | None:
    """Locate Ghostscript executable if installed (optional strong compressor)."""
    import shutil

    for name in ("gswin64c", "gswin32c", "gs"):
        found = shutil.which(name)
        if found:
            return Path(found)
    for base in (
        Path(r"C:\Program Files\gs"),
        Path(r"C:\Program Files (x86)\gs"),
    ):
        if not base.is_dir():
            continue
        for child in sorted(base.glob("gs*"), reverse=True):
            for exe in ("gswin64c.exe", "gswin32c.exe", "gs.exe"):
                cand = child / "bin" / exe
                if cand.is_file():
                    return cand
    return None


def compress_pdf(
    path: Path | str,
    output: Path | str,
    preset: str = "balanced",
    *,
    password: str | None = None,
    prefer_ghostscript: bool = True,
    progress: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> Path:
    """Compress a PDF.

    Presets: email | balanced | max | scan

    Order of backends:
      1. Ghostscript if installed and prefer_ghostscript (usually best size)
      2. PyMuPDF with proper image re-embed / page re-render for scan
      3. pypdf structure rewrite (fallback)
    """
    src = _ensure_pdf(Path(path))
    preset = (preset or "balanced").lower().strip()
    if preset not in COMPRESS_PRESETS:
        raise PdfOpsError(
            "Compress preset must be email, balanced, max, or scan."
        )

    requested = Path(output)
    _assert_not_overwrite_inputs(src, requested)
    out = _unique_path(requested)
    out.parent.mkdir(parents=True, exist_ok=True)
    _assert_not_overwrite_inputs(src, out)
    factor = 3.0 if preset == "scan" else 2.0
    _preflight_disk(out.parent, int(src.stat().st_size * factor))

    def _prog(msg: str) -> None:
        if progress:
            progress(msg)

    def _cancelled() -> bool:
        return bool(cancel_check and cancel_check())

    if preset == "scan":
        _warn(
            "Scan compress re-renders every page as an image — "
            "text will no longer be selectable."
        )

    gs = find_ghostscript() if prefer_ghostscript and preset != "scan" else None
    if gs is not None:
        try:
            _prog("Compressing with Ghostscript…")
            result = _compress_ghostscript(
                src,
                out,
                preset,
                gs=gs,
                password=password,
                cancel_check=cancel_check,
            )
            _validate_pdf_file(result, min_pages=1)
            return result
        except Exception as exc:  # noqa: BLE001 — fall through to MuPDF
            _prog(f"Ghostscript skipped ({exc}); using built-in compressor…")

    if preset == "scan":
        _prog("Re-rendering pages (scan mode)…")
        if _cancelled():
            raise PdfOpsError("Cancelled.")
        return _compress_rerender(
            src,
            out,
            dpi=120,
            grayscale=True,
            jpeg_quality=45,
            password=password,
            progress=progress,
            cancel_check=cancel_check,
        )

    try:
        import fitz
    except ImportError:
        _prog("PyMuPDF missing — light pypdf rewrite…")
        reader = _open_reader(src, password=password)
        writer = PdfWriter()
        _transfer_pages(writer, reader, list(range(len(reader.pages))))
        try:
            writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        except Exception:  # noqa: BLE001
            pass
        return _write_writer(writer, out, sources=[src], space_factor=1.5)

    try:
        doc = fitz.open(str(src))
    except Exception as exc:  # noqa: BLE001
        raise PdfOpsError(f"Could not open for compress: {exc}") from exc

    try:
        if doc.is_encrypted:
            if not doc.authenticate(password or ""):
                raise PdfOpsError(f"{src.name} is password-protected.")

        if preset in ("email", "max"):
            max_dim = 1000 if preset == "email" else 1500
            quality = 48 if preset == "email" else 68
            _prog("Recompressing images…")
            _recompress_images_fitz(
                doc,
                max_dim=max_dim,
                quality=quality,
                cancel_check=cancel_check,
            )

        if _cancelled():
            raise PdfOpsError("Cancelled.")

        _prog("Writing optimized PDF…")
        tmp_path = _temp_pdf_path(out)
        try:
            def _save() -> None:
                _stamp_fitz_metadata(doc)
                doc.save(
                    str(tmp_path),
                    garbage=4,
                    deflate=True,
                    clean=True,
                    deflate_images=True,
                    deflate_fonts=True,
                    use_objstms=1,
                )

            _retry(_save, what="Write compressed PDF")
            expected = doc.page_count
            _atomic_finalize(tmp_path, out, expected_pages=expected)
        except Exception:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise
    finally:
        doc.close()

    # Optional second pass when GS was not used first
    if prefer_ghostscript and gs is None:
        gs2 = find_ghostscript()
        if gs2 is not None and preset in ("email", "max"):
            try:
                _prog("Second pass: Ghostscript…")
                mid = out.with_name(out.stem + "_mid.pdf")
                out.replace(mid)
                try:
                    _compress_ghostscript(mid, out, preset, gs=gs2, password=None)
                finally:
                    if mid.exists():
                        mid.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:  # noqa: BLE001
                pass

    return out


def _compress_ghostscript(
    src: Path,
    out: Path,
    preset: str,
    *,
    gs: Path,
    password: str | None,
    cancel_check: Callable[[], bool] | None = None,
) -> Path:
    """Run Ghostscript pdfwrite with a size-oriented PDFSETTINGS profile."""
    import subprocess
    import tempfile

    # GS PDFSETTINGS: /screen ~72dpi, /ebook ~150dpi
    settings = {
        "email": "/screen",
        "balanced": "/ebook",
        "max": "/ebook",
        "scan": "/screen",
    }.get(preset, "/ebook")

    # GS often can't open encrypted PDFs — decrypt via MuPDF first.
    work_src = src
    tmp_plain: Path | None = None
    if password:
        try:
            import fitz

            d = fitz.open(str(src))
            try:
                if d.is_encrypted and not d.authenticate(password):
                    raise PdfOpsError(f"{src.name}: wrong password.")
                fd, name = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)
                tmp_plain = Path(name)
                d.save(str(tmp_plain), garbage=4, deflate=True)
                work_src = tmp_plain
            finally:
                d.close()
        except PdfOpsError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PdfOpsError(f"Could not prepare PDF for Ghostscript: {exc}") from exc

    fd, tmp_out_name = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    tmp_out = Path(tmp_out_name)
    proc: subprocess.Popen[str] | None = None
    try:
        cmd = [
            str(gs),
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={settings}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            "-dColorImageDownsampleType=/Bicubic",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dMonoImageDownsampleType=/Bicubic",
            f"-sOutputFile={tmp_out}",
            str(work_src),
        ]
        if preset == "email":
            cmd[4:4] = [
                "-dColorImageResolution=100",
                "-dGrayImageResolution=100",
                "-dMonoImageResolution=150",
            ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Poll so Esc/cancel can kill Ghostscript
        deadline = time.time() + 600
        while True:
            if cancel_check and cancel_check():
                _kill_process_tree(proc)
                raise PdfOpsError("Cancelled.")
            ret = proc.poll()
            if ret is not None:
                break
            if time.time() > deadline:
                _kill_process_tree(proc)
                raise PdfOpsError("Ghostscript timed out (10 minutes).")
            time.sleep(0.15)
        stdout, stderr = proc.communicate(timeout=5)
        if proc.returncode != 0 or not tmp_out.is_file() or tmp_out.stat().st_size < 32:
            err = (stderr or stdout or "unknown error").strip()
            raise PdfOpsError(f"Ghostscript failed: {err[:400]}")
        def _mv() -> None:
            os.replace(str(tmp_out), str(out))

        _retry(_mv, what="Finalize Ghostscript output")
        return out
    finally:
        if proc is not None and proc.poll() is None:
            _kill_process_tree(proc)
        if tmp_out.exists() and tmp_out != out:
            try:
                tmp_out.unlink()
            except OSError:
                pass
        if tmp_plain is not None and tmp_plain.exists():
            try:
                tmp_plain.unlink()
            except OSError:
                pass


def _kill_process_tree(proc) -> None:
    """Best-effort kill Ghostscript and children (Windows + POSIX)."""
    try:
        if proc.poll() is not None:
            return
        if os.name == "nt":
            import subprocess

            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            proc.kill()
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


def _compress_rerender(
    src: Path,
    out: Path,
    *,
    dpi: int,
    grayscale: bool,
    jpeg_quality: int,
    password: str | None,
    progress: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> Path:
    """Rebuild PDF by rasterizing each page — strong for scans/photos."""
    try:
        import fitz
    except ImportError as exc:
        raise PdfOpsError("Scan compress needs PyMuPDF. pip install pymupdf") from exc

    from io import BytesIO

    from PIL import Image as PILImage

    doc = fitz.open(str(src))
    try:
        if doc.is_encrypted and not doc.authenticate(password or ""):
            raise PdfOpsError(f"{src.name} is password-protected.")
        if doc.page_count < 1:
            raise PdfOpsError("PDF has no pages.")

        out_doc = fitz.open()
        try:
            mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
            cs = fitz.csGRAY if grayscale else fitz.csRGB
            total = doc.page_count
            for i in range(total):
                if cancel_check and cancel_check():
                    raise PdfOpsError("Cancelled.")
                if progress and (i % 5 == 0 or i == total - 1):
                    progress(f"Re-rendering page {i + 1}/{total}…")
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=mat, colorspace=cs, alpha=False)
                mode = "L" if grayscale else "RGB"
                im = PILImage.frombytes(mode, (pix.width, pix.height), pix.samples)
                if mode == "L":
                    im = im.convert("RGB")
                buf = BytesIO()
                im.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
                rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(rect, stream=buf.getvalue())
            return _save_fitz_atomic(
                out_doc,
                out,
                sources=[src],
                expected_pages=total,
                space_factor=3.0,
            )
        finally:
            out_doc.close()
    finally:
        doc.close()


def _recompress_images_fitz(
    doc,
    *,
    max_dim: int,
    quality: int,
    cancel_check: Callable[[], bool] | None = None,
) -> None:
    """Re-encode embedded images and replace them properly in the PDF."""
    from io import BytesIO

    from PIL import Image as PILImage

    seen: set[int] = set()
    for page in doc:
        if cancel_check and cancel_check():
            raise PdfOpsError("Cancelled.")
        images = page.get_images(full=True)
        for img in images:
            xref = img[0]
            if xref in seen or xref <= 0:
                continue
            seen.add(xref)
            try:
                info = doc.extract_image(xref)
                raw = info.get("image")
                if not raw:
                    continue
                w0, h0 = info.get("width") or 0, info.get("height") or 0
                if w0 and h0 and w0 * h0 < 80 * 80:
                    continue
                im = PILImage.open(BytesIO(raw))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                elif im.mode == "L":
                    im = im.convert("RGB")
                im.thumbnail((max_dim, max_dim), PILImage.Resampling.LANCZOS)
                buf = BytesIO()
                im.save(buf, format="JPEG", quality=quality, optimize=True)
                jpeg = buf.getvalue()

                replaced = False
                # prefer replace_image (correct XObject rewiring)
                if hasattr(page, "replace_image"):
                    try:
                        page.replace_image(xref, stream=jpeg)
                        replaced = True
                    except Exception:  # noqa: BLE001
                        replaced = False
                if not replaced and hasattr(doc, "update_stream"):
                    try:
                        doc.update_stream(xref, jpeg)
                        try:
                            doc.xref_set_key(xref, "Filter", "/DCTDecode")
                            doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB")
                            doc.xref_set_key(xref, "BitsPerComponent", "8")
                            doc.xref_set_key(xref, "Width", str(im.width))
                            doc.xref_set_key(xref, "Height", str(im.height))
                        except Exception:  # noqa: BLE001
                            pass
                    except Exception:  # noqa: BLE001
                        continue
            except Exception:  # noqa: BLE001 — skip exotic images
                continue

