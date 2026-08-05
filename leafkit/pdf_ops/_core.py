"""Core PDF operations (local only): merge, split, extract, rotate, compress, etc.

Reliability: atomic writes, validation, same-path guards, disk preflight, lock retries.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Callable

from pypdf import PdfReader, PdfWriter

try:
    from leafkit import __version__ as _LK_VERSION
except Exception:  # noqa: BLE001
    _LK_VERSION = "dev"

PasswordProvider = Callable[[Path], str | None]


def _stamp_writer_metadata(writer: PdfWriter) -> None:
    """Identify outputs as Leafkit without overwriting user-cleared fields later."""
    try:
        meta = {
            "/Producer": f"Leafkit {_LK_VERSION}",
            "/Creator": f"Leafkit {_LK_VERSION}",
        }
        writer.add_metadata(meta)
    except Exception:  # noqa: BLE001
        pass


def _stamp_fitz_metadata(doc) -> None:
    try:
        meta = doc.metadata or {}
        meta["producer"] = f"Leafkit {_LK_VERSION}"
        meta["creator"] = f"Leafkit {_LK_VERSION}"
        doc.set_metadata(meta)
    except Exception:  # noqa: BLE001
        pass

_last_warnings: list[str] = []


class PdfOpsError(Exception):
    """User-facing PDF operation error."""


def take_warnings() -> list[str]:
    """Return and clear warnings from the last operation(s)."""
    global _last_warnings
    out = list(_last_warnings)
    _last_warnings.clear()
    return out


def _warn(msg: str) -> None:
    if msg and msg not in _last_warnings:
        _last_warnings.append(msg)


def _resolve(path: Path) -> Path:
    path = Path(path).expanduser()
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _paths_equal(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return _resolve(a) == _resolve(b)


def _assert_not_overwrite_inputs(
    sources: list[Path | str] | Path | str,
    output: Path | str,
) -> None:
    """Refuse to write output on top of any input file."""
    out = Path(output)
    srcs = sources if isinstance(sources, list) else [sources]
    for raw in srcs:
        src = Path(raw)
        try:
            if src.is_file() and _paths_equal(src, out):
                raise PdfOpsError(
                    f"Refusing to overwrite an input file:\n  {src}\n\n"
                    "Choose a different output name or folder."
                )
        except PdfOpsError:
            raise
        except OSError:
            if _resolve(src) == _resolve(out):
                raise PdfOpsError(
                    f"Refusing to overwrite an input file:\n  {src}\n\n"
                    "Choose a different output name or folder."
                ) from None


def _disk_free_bytes(path: Path) -> int | None:
    try:
        p = path if path.is_dir() else path.parent
        return shutil.disk_usage(str(p)).free
    except OSError:
        return None


def _estimate_size(paths: list[Path]) -> int:
    total = 0
    for p in paths:
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def _preflight_disk(dest: Path, need_bytes: int) -> None:
    """Fail early if the target drive likely cannot hold the output."""
    free = _disk_free_bytes(dest if dest.is_dir() else dest.parent)
    if free is None:
        return
    # Output + temp sibling + 15 MB slack
    need = int(need_bytes) + 15 * 1024 * 1024
    if free < need:
        raise PdfOpsError(
            "Not enough free disk space for this operation.\n\n"
            f"Need roughly {need // (1024 * 1024)} MB free "
            f"(have {free // (1024 * 1024)} MB).\n"
            "Free some space or choose another drive."
        )


def _retry(
    fn: Callable[[], object],
    *,
    attempts: int = 4,
    base_delay: float = 0.12,
    what: str = "File operation",
) -> object:
    """Retry on Windows lock / AV / OneDrive races."""
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except (OSError, PermissionError) as exc:
            last = exc
            if i + 1 >= attempts:
                break
            time.sleep(base_delay * (i + 1))
    raise PdfOpsError(
        f"{what} failed — the file may be open in another program, "
        f"or a sync tool (OneDrive) is locking it.\n\n{last}"
    ) from last


def _validate_pdf_file(
    path: Path,
    *,
    min_pages: int = 1,
    expected_pages: int | None = None,
) -> int:
    """Open output and ensure it is a readable PDF. Returns page count."""
    path = Path(path)
    if not path.is_file():
        raise PdfOpsError("Output file was not created.")

    def _size() -> int:
        return path.stat().st_size

    size = int(_retry(_size, what="Check output size"))
    if size < 64:
        raise PdfOpsError("Output file is empty or corrupt (too small).")

    def _count() -> int:
        try:
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:  # noqa: BLE001
                    pass
            return len(reader.pages)
        except Exception:
            try:
                import fitz

                doc = fitz.open(str(path))
                try:
                    return int(doc.page_count)
                finally:
                    doc.close()
            except Exception as exc:  # noqa: BLE001
                raise PdfOpsError(
                    f"Output PDF could not be re-opened (corrupt?):\n{exc}"
                ) from exc

    n = int(_retry(_count, what="Validate output PDF"))
    if n < min_pages:
        raise PdfOpsError(
            f"Output PDF has no usable pages (found {n}). Inputs were left unchanged."
        )
    if expected_pages is not None and n != expected_pages:
        raise PdfOpsError(
            f"Output page count mismatch: expected {expected_pages}, got {n}. "
            "Inputs were left unchanged."
        )
    return n


def _atomic_finalize(
    tmp: Path,
    final: Path,
    *,
    min_pages: int = 1,
    expected_pages: int | None = None,
) -> Path:
    """Validate temp PDF then rename into place (atomic on same volume)."""
    try:
        _validate_pdf_file(tmp, min_pages=min_pages, expected_pages=expected_pages)

        def _replace() -> None:
            os.replace(str(tmp), str(final))

        _retry(_replace, what="Finalize output (rename)")
        return final
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def _temp_pdf_path(near: Path) -> Path:
    parent = near.parent if near.suffix else near
    if not parent.is_dir():
        parent = Path(near).parent
    parent.mkdir(parents=True, exist_ok=True)
    return parent / f".leafkit-{uuid.uuid4().hex}.tmp.pdf"


def _ensure_pdf(path: Path) -> Path:
    path = Path(path)
    if not path.is_file():
        raise PdfOpsError(f"File not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise PdfOpsError(f"Not a PDF file: {path.name}")
    return path


def _open_reader(
    path: Path,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> PdfReader:
    path = _ensure_pdf(path)

    def _open() -> PdfReader:
        return PdfReader(str(path))

    try:
        reader = _retry(_open, what=f"Open {path.name}")
    except PdfOpsError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PdfOpsError(f"Could not open {path.name}: {exc}") from exc

    assert isinstance(reader, PdfReader)

    if not reader.is_encrypted:
        return reader

    candidates: list[str | None] = []
    if password is not None:
        candidates.append(password)
    if password_provider is not None:
        try:
            provided = password_provider(path)
        except Exception:  # noqa: BLE001
            provided = None
        if provided is not None and provided not in candidates:
            candidates.append(provided)
    candidates.append("")  # empty often unlocks "owner" restrictions

    last_err: Exception | None = None
    for pwd in candidates:
        try:
            # pypdf: 0 = fail, non-zero success (API varies slightly by version)
            result = reader.decrypt(pwd or "")
            if result == 0:
                continue
            return reader
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            # re-open after failed decrypt attempts on some versions
            try:
                reader = PdfReader(str(path))
            except Exception:
                pass

    raise PdfOpsError(
        f"{path.name} is password-protected. "
        "Enter the correct password (Password field) and try again."
        + (f" ({last_err})" if last_err else "")
    )


def page_count(
    path: Path | str,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> int:
    """Return number of pages in a PDF."""
    reader = _open_reader(Path(path), password=password, password_provider=password_provider)
    return len(reader.pages)


def parse_page_range(spec: str, total_pages: int) -> list[int]:
    """Parse a page-range string into 0-based page indices.

    Examples (1-based input):
        "1"       -> [0]
        "2-5"     -> [1, 2, 3, 4]
        "1,3,5-7" -> [0, 2, 4, 5, 6]
        "1-"      -> all from 1 to end
    """
    spec = (spec or "").strip()
    if not spec:
        raise PdfOpsError("Page range is empty. Example: 1-3, 5, 8-10")
    if total_pages < 1:
        raise PdfOpsError("PDF has no pages.")

    indices: list[int] = []
    seen: set[int] = set()
    parts = re.split(r"\s*,\s*", spec)

    for part in parts:
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            left = left.strip()
            right = right.strip()
            if not left and not right:
                raise PdfOpsError(f"Invalid range: '{part}'")
            try:
                start = int(left) if left else 1
                end = int(right) if right else total_pages
            except ValueError as exc:
                raise PdfOpsError(f"Invalid range: '{part}'") from exc
            if start < 1 or end < 1:
                raise PdfOpsError("Page numbers start at 1.")
            if start > end:
                raise PdfOpsError(f"Range start > end: '{part}'")
            if end > total_pages:
                raise PdfOpsError(
                    f"Page {end} is past the end of the PDF ({total_pages} pages)."
                )
            for p in range(start, end + 1):
                idx = p - 1
                if idx not in seen:
                    seen.add(idx)
                    indices.append(idx)
        else:
            try:
                p = int(part)
            except ValueError as exc:
                raise PdfOpsError(f"Invalid page number: '{part}'") from exc
            if p < 1:
                raise PdfOpsError("Page numbers start at 1.")
            if p > total_pages:
                raise PdfOpsError(
                    f"Page {p} is past the end of the PDF ({total_pages} pages)."
                )
            idx = p - 1
            if idx not in seen:
                seen.add(idx)
                indices.append(idx)

    if not indices:
        raise PdfOpsError("No pages selected.")
    return indices


def _unique_path(path: Path) -> Path:
    """If path exists, append _1, _2, ... before the suffix."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    n = 1
    while True:
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def _write_writer(
    writer: PdfWriter,
    output: Path,
    *,
    sources: list[Path] | None = None,
    expected_pages: int | None = None,
    space_factor: float = 1.6,
) -> Path:
    """Atomically write a PdfWriter result and validate page count."""
    for page in writer.pages:
        _ensure_full_page_visible(page)
    _stamp_writer_metadata(writer)

    requested = Path(output)
    srcs = list(sources or [])
    # Guard requested path before uniquify (_1, _2, …)
    if srcs:
        _assert_not_overwrite_inputs(srcs, requested)

    out = _unique_path(requested)
    out.parent.mkdir(parents=True, exist_ok=True)

    if srcs:
        _assert_not_overwrite_inputs(srcs, out)
        _preflight_disk(out.parent, int(_estimate_size(srcs) * space_factor))
    else:
        _preflight_disk(out.parent, 5 * 1024 * 1024)

    if expected_pages is None:
        expected_pages = len(writer.pages)

    tmp = _temp_pdf_path(out)

    def _write_tmp() -> None:
        with open(tmp, "wb") as f:
            writer.write(f)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass

    try:
        _retry(_write_tmp, what="Write temporary PDF")
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


def _writer_size_bytes(writer: PdfWriter) -> int:
    buf = io.BytesIO()
    writer.write(buf)
    return buf.tell()


def _box_tuple(box) -> tuple[float, float, float, float] | None:
    try:
        return (
            float(box.left),
            float(box.bottom),
            float(box.right),
            float(box.top),
        )
    except Exception:  # noqa: BLE001
        return None


def _ensure_full_page_visible(page) -> None:
    """Prevent mid-page clipping after merge/copy.

    Some PDFs (and some export tools) ship a CropBox / TrimBox smaller than
    the real content or MediaBox. Viewers then show text cut off halfway down
    the page. For page-ops we always want the full page canvas.
    """
    try:
        media = page.mediabox
    except Exception:  # noqa: BLE001
        return

    media_t = _box_tuple(media)
    if media_t is None:
        return

    # Expand any box that is missing, degenerate, or smaller than MediaBox
    for attr in ("cropbox", "trimbox", "bleedbox", "artbox"):
        try:
            box = getattr(page, attr, None)
            bt = _box_tuple(box) if box is not None else None
            if bt is None:
                setattr(page, attr, media)
                continue
            mw = media_t[2] - media_t[0]
            mh = media_t[3] - media_t[1]
            bw = bt[2] - bt[0]
            bh = bt[3] - bt[1]
            # Smaller than MediaBox → content can be clipped
            if bw + 0.5 < mw or bh + 0.5 < mh:
                setattr(page, attr, media)
            elif bw <= 1 or bh <= 1:
                setattr(page, attr, media)
        except Exception:  # noqa: BLE001
            try:
                setattr(page, attr, media)
            except Exception:  # noqa: BLE001
                pass


def _transfer_pages(
    writer: PdfWriter,
    reader: PdfReader,
    indices: list[int] | None = None,
    *,
    import_outline: bool = False,
) -> None:
    """Copy full pages from reader → writer without dropping content.

    Uses PdfWriter.append (page-import path) which preserves resources,
    content streams, and annotations better than raw add_page loops.
    Falls back to add_page if append fails for a given subset.
    """
    total = len(reader.pages)
    if total < 1:
        return

    if indices is None:
        indices = list(range(total))
    else:
        indices = list(indices)

    if not indices:
        return

    for idx in indices:
        if idx < 0 or idx >= total:
            raise PdfOpsError(f"Page index out of range: {idx + 1}")

    if indices == list(range(total)):
        try:
            writer.append(reader, import_outline=import_outline)
            return
        except Exception:  # noqa: BLE001 — fall through
            pass

    if len(indices) > 1 and indices == list(range(indices[0], indices[-1] + 1)):
        try:
            # pypdf pages=(start, stop) is half-open
            writer.append(
                reader,
                pages=(indices[0], indices[-1] + 1),
                import_outline=import_outline,
            )
            return
        except Exception:  # noqa: BLE001
            pass

    try:
        writer.append(reader, pages=indices, import_outline=import_outline)
        return
    except Exception:  # noqa: BLE001
        pass

    for idx in indices:
        page = reader.pages[idx]
        _ensure_full_page_visible(page)
        writer.add_page(page)


# Standard page sizes in PDF points (72 pt = 1 inch)
PAGE_SIZES: dict[str, tuple[float, float]] = {
    "a4": (595.28, 841.89),
    "letter": (612.0, 792.0),
    "legal": (612.0, 1008.0),
}

