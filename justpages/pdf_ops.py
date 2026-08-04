"""Core PDF operations: merge, split, extract, rotate.

All work is local. Nothing is uploaded.
"""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter


class PdfOpsError(Exception):
    """User-facing PDF operation error."""


def _ensure_pdf(path: Path) -> Path:
    path = Path(path)
    if not path.is_file():
        raise PdfOpsError(f"File not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise PdfOpsError(f"Not a PDF file: {path.name}")
    return path


def _open_reader(path: Path) -> PdfReader:
    path = _ensure_pdf(path)
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 — surface as clean message
        raise PdfOpsError(f"Could not open {path.name}: {exc}") from exc
    if reader.is_encrypted:
        try:
            # Empty password often unlocks "owner" restricted PDFs
            if reader.decrypt("") == 0:
                raise PdfOpsError(
                    f"{path.name} is password-protected. "
                    "Decrypt it first, then try again."
                )
        except PdfOpsError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PdfOpsError(
                f"{path.name} is password-protected and could not be opened."
            ) from exc
    return reader


def page_count(path: Path | str) -> int:
    """Return number of pages in a PDF."""
    reader = _open_reader(Path(path))
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
            start = int(left) if left else 1
            end = int(right) if right else total_pages
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


def merge_pdfs(paths: list[Path | str], output: Path | str) -> Path:
    """Merge PDFs in order into a single file."""
    if len(paths) < 2:
        raise PdfOpsError("Select at least two PDF files to merge.")

    writer = PdfWriter()
    for raw in paths:
        reader = _open_reader(Path(raw))
        for page in reader.pages:
            writer.add_page(page)

    out = _unique_path(Path(output))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def extract_pages(
    path: Path | str,
    page_spec: str,
    output: Path | str,
) -> Path:
    """Extract pages matching page_spec into a new PDF."""
    src = Path(path)
    reader = _open_reader(src)
    indices = parse_page_range(page_spec, len(reader.pages))

    writer = PdfWriter()
    for idx in indices:
        writer.add_page(reader.pages[idx])

    out = _unique_path(Path(output))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def split_pdf(
    path: Path | str,
    mode: str,
    output_dir: Path | str,
    every_n: int = 1,
) -> list[Path]:
    """Split a PDF.

    mode:
      - "each": one file per page
      - "every_n": groups of N pages
    """
    src = Path(path)
    reader = _open_reader(src)
    total = len(reader.pages)
    if total < 1:
        raise PdfOpsError("PDF has no pages.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem
    written: list[Path] = []

    if mode == "each":
        every_n = 1
    elif mode == "every_n":
        if every_n < 1:
            raise PdfOpsError("'Every N pages' must be at least 1.")
    else:
        raise PdfOpsError(f"Unknown split mode: {mode}")

    start = 0
    part = 1
    while start < total:
        end = min(start + every_n, total)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])

        if every_n == 1:
            name = f"{stem}_page_{start + 1:03d}.pdf"
        else:
            name = f"{stem}_part_{part:03d}_p{start + 1}-{end}.pdf"

        out = _unique_path(out_dir / name)
        with open(out, "wb") as f:
            writer.write(f)
        written.append(out)
        start = end
        part += 1

    return written


def rotate_pages(
    path: Path | str,
    degrees: int,
    output: Path | str,
    page_spec: str | None = None,
) -> Path:
    """Rotate pages by 90, 180, or 270 degrees clockwise.

    If page_spec is None or empty, rotate all pages.
    """
    if degrees not in (90, 180, 270):
        raise PdfOpsError("Rotation must be 90, 180, or 270 degrees.")

    src = Path(path)
    reader = _open_reader(src)
    total = len(reader.pages)

    if page_spec and page_spec.strip():
        targets = set(parse_page_range(page_spec, total))
    else:
        targets = set(range(total))

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in targets:
            page.rotate(degrees)
        writer.add_page(page)

    out = _unique_path(Path(output))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def default_output_next_to(source: Path | str, suffix: str) -> Path:
    """Build a default output path beside the source file."""
    src = Path(source)
    return src.with_name(f"{src.stem}{suffix}.pdf")
