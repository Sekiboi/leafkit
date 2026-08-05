"""Page structure ops: merge, extract, delete, insert, mix, split, rotate, assemble."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from pypdf import PdfReader, PdfWriter

from sekikit.pdf_ops._core import (
    PAGE_SIZES,
    PasswordProvider,
    PdfOpsError,
    _ensure_full_page_visible,
    _open_reader,
    _transfer_pages,
    _write_writer,
    _writer_size_bytes,
    parse_page_range,
)

def merge_pdfs(
    paths: list[Path | str],
    output: Path | str,
    *,
    page_specs: list[str | None] | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
    preserve_bookmarks: bool = False,
    page_size: str | None = None,
) -> Path:
    """Merge PDFs in order into a single file.

    page_specs: optional per-file 1-based range string, or None/\"\" for all pages.
    preserve_bookmarks: import outlines from each source when possible.
    page_size: None, \"a4\", \"letter\", or \"legal\" — fit each page onto that size.
    """
    if len(paths) < 2:
        raise PdfOpsError("Select at least two PDF files to merge.")
    if page_specs is not None and len(page_specs) != len(paths):
        raise PdfOpsError("Internal error: page_specs length must match files.")

    size_key = (page_size or "").strip().lower() or None
    if size_key and size_key not in PAGE_SIZES:
        raise PdfOpsError("page_size must be a4, letter, legal, or blank.")

    writer = PdfWriter()
    for i, raw in enumerate(paths):
        reader = _open_reader(
            Path(raw), password=password, password_provider=password_provider
        )
        total = len(reader.pages)
        if total < 1:
            continue
        spec = page_specs[i] if page_specs else None
        if spec and str(spec).strip():
            indices = parse_page_range(str(spec), total)
        else:
            indices = list(range(total))
        _transfer_pages(
            writer, reader, indices, import_outline=bool(preserve_bookmarks)
        )

    if len(writer.pages) < 1:
        raise PdfOpsError("Merge produced no pages (check page ranges).")

    if size_key:
        tw, th = PAGE_SIZES[size_key]
        for page in writer.pages:
            _fit_page_to_size(page, tw, th)

    srcs = [Path(x) for x in paths]
    return _write_writer(writer, Path(output), sources=srcs)


def _fit_page_to_size(page, target_w: float, target_h: float) -> None:
    """Scale page content to fit inside target_w x target_h (points)."""
    try:
        mb = page.mediabox
        w = float(mb.width)
        h = float(mb.height)
        if w < 1 or h < 1:
            return
        scale = min(target_w / w, target_h / h)
        if hasattr(page, "scale_by"):
            page.scale_by(scale)
        elif hasattr(page, "scale_to"):
            page.scale_to(w * scale, h * scale)
        try:
            mb2 = page.mediabox
            nw, nh = float(mb2.width), float(mb2.height)
            # scale_by also shrinks mediabox — expand to target without re-scaling
            if abs(nw - target_w) > 1 or abs(nh - target_h) > 1:
                from pypdf.generic import RectangleObject

                page.mediabox = RectangleObject((0, 0, target_w, target_h))
                page.cropbox = page.mediabox
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass


def extract_pages(
    path: Path | str,
    page_spec: str,
    output: Path | str,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Extract pages matching page_spec into a new PDF (full pages only)."""
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    indices = parse_page_range(page_spec, len(reader.pages))

    writer = PdfWriter()
    _transfer_pages(writer, reader, indices)
    return _write_writer(writer, Path(output), sources=[src])


def delete_pages(
    path: Path | str,
    page_spec: str,
    output: Path | str,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Delete pages matching page_spec; write remaining full pages to output."""
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)
    to_delete = set(parse_page_range(page_spec, total))
    if len(to_delete) >= total:
        raise PdfOpsError("Cannot delete all pages — nothing would remain.")

    keep = [i for i in range(total) if i not in to_delete]
    writer = PdfWriter()
    _transfer_pages(writer, reader, keep)
    return _write_writer(writer, Path(output), sources=[src])


def insert_pages(
    base_path: Path | str,
    insert_path: Path | str,
    output: Path | str,
    *,
    at_page: int = 1,
    insert_spec: str | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Insert pages from insert_path into base_path before 1-based at_page.

    at_page = 1 inserts at the beginning.
    at_page = len(base)+1 (or larger) appends at the end.
    """
    base = Path(base_path)
    ins = Path(insert_path)
    if base.resolve() == ins.resolve():
        raise PdfOpsError("Base and insert PDF must be different files.")

    base_r = _open_reader(base, password=password, password_provider=password_provider)
    ins_r = _open_reader(ins, password=password, password_provider=password_provider)
    base_n = len(base_r.pages)
    ins_n = len(ins_r.pages)
    if ins_n < 1:
        raise PdfOpsError("Insert PDF has no pages.")
    if at_page < 1:
        raise PdfOpsError("Insert position must be >= 1 (1 = before first page).")

    pos = min(at_page, base_n + 1)
    insert_at = pos - 1

    if insert_spec and insert_spec.strip():
        ins_indices = parse_page_range(insert_spec, ins_n)
    else:
        ins_indices = list(range(ins_n))

    writer = PdfWriter()
    if insert_at > 0:
        _transfer_pages(writer, base_r, list(range(0, insert_at)))
    _transfer_pages(writer, ins_r, ins_indices)
    if insert_at < base_n:
        _transfer_pages(writer, base_r, list(range(insert_at, base_n)))
    return _write_writer(
        writer, Path(output), sources=[base, ins], expected_pages=len(writer.pages)
    )


def mix_pdfs(
    paths: list[Path | str],
    output: Path | str,
    *,
    reverse_second: bool = False,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Alternate pages from two or more PDFs (scanner duplex / mix use case).

    Takes page 1 from each file, then page 2 from each, etc.
    If reverse_second is True and there are at least 2 files, the second
    file's pages are taken in reverse order (classic duplex mix).
    """
    if len(paths) < 2:
        raise PdfOpsError("Mix needs at least two PDF files.")

    streams: list[tuple[PdfReader, list[int]]] = []
    for i, raw in enumerate(paths):
        r = _open_reader(Path(raw), password=password, password_provider=password_provider)
        n = len(r.pages)
        order = list(range(n))
        if reverse_second and i == 1:
            order = list(reversed(order))
        streams.append((r, order))

    max_len = max((len(order) for _r, order in streams), default=0)
    if max_len < 1:
        raise PdfOpsError("PDFs have no pages to mix.")

    writer = PdfWriter()
    for page_i in range(max_len):
        for reader, order in streams:
            if page_i < len(order):
                _transfer_pages(writer, reader, [order[page_i]])
    return _write_writer(
        writer,
        Path(output),
        sources=[Path(p) for p in paths],
        expected_pages=len(writer.pages),
    )


def split_pdf(
    path: Path | str,
    mode: str,
    output_dir: Path | str,
    *,
    every_n: int = 1,
    at_pages: str | None = None,
    max_mb: float = 1.0,
    bookmark_level: int = 1,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> list[Path]:
    """Split a PDF.

    mode:
      - "each": one file per page
      - "every_n": groups of N pages
      - "even_odd" / even-odd files: two outputs — all odd pages, all even pages
        - "at_pages": split before given 1-based page numbers
        - "size": parts targeting max_mb megabytes
        - "bookmarks": split at outline destinations of given level
    """
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)
    if total < 1:
        raise PdfOpsError("PDF has no pages.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem

    if mode == "each":
        return _split_ranges(reader, stem, out_dir, [(i, i) for i in range(total)])

    if mode == "every_n":
        if every_n < 1:
            raise PdfOpsError("'Every N pages' must be at least 1.")
        ranges = []
        start = 0
        while start < total:
            end = min(start + every_n - 1, total - 1)
            ranges.append((start, end))
            start = end + 1
        return _split_ranges(reader, stem, out_dir, ranges)

    if mode == "even_odd":
        odds = [i for i in range(total) if (i + 1) % 2 == 1]
        evens = [i for i in range(total) if (i + 1) % 2 == 0]
        written: list[Path] = []
        if odds:
            w = PdfWriter()
            _transfer_pages(w, reader, odds)
            written.append(
                _write_writer(
                    w, out_dir / f"{stem}_odd_pages.pdf", sources=[src]
                )
            )
        if evens:
            w = PdfWriter()
            _transfer_pages(w, reader, evens)
            written.append(
                _write_writer(
                    w, out_dir / f"{stem}_even_pages.pdf", sources=[src]
                )
            )
        if not written:
            raise PdfOpsError("Nothing to split.")
        return written

    if mode == "at_pages":
        # Split before listed 1-based pages (e.g. "3,7" → [1-2],[3-6],[7-end]).
        if not at_pages or not str(at_pages).strip():
            raise PdfOpsError("Enter page numbers to split at (e.g. 3, 7).")
        cuts = sorted(set(parse_page_range(str(at_pages), total)))
        boundaries = [0]
        for c in cuts:
            if c == 0:
                continue
            if c not in boundaries:
                boundaries.append(c)
        boundaries.append(total)
        ranges = []
        for a, b in zip(boundaries, boundaries[1:]):
            if a < b:
                ranges.append((a, b - 1))
        return _split_ranges(reader, stem, out_dir, ranges)

    if mode == "size":
        if max_mb <= 0:
            raise PdfOpsError("Max size must be greater than 0 MB.")
        max_bytes = int(max_mb * 1024 * 1024)
        return _split_by_size(reader, stem, out_dir, max_bytes)

    if mode == "bookmarks":
        if bookmark_level < 1:
            raise PdfOpsError("Bookmark level must be >= 1.")
        cuts = _bookmark_split_indices(reader, bookmark_level)
        if not cuts:
            raise PdfOpsError(
                "No bookmarks found at that level (or PDF has no outline)."
            )
        boundaries = [0]
        for c in cuts:
            if 0 < c < total and c not in boundaries:
                boundaries.append(c)
        boundaries.append(total)
        ranges = []
        for a, b in zip(boundaries, boundaries[1:]):
            if a < b:
                ranges.append((a, b - 1))
        if len(ranges) < 2:
            raise PdfOpsError(
                "Bookmark split produced only one part — try another level."
            )
        return _split_ranges(reader, stem, out_dir, ranges)

    raise PdfOpsError(f"Unknown split mode: {mode}")


def _split_ranges(
    reader: PdfReader,
    stem: str,
    out_dir: Path,
    ranges: list[tuple[int, int]],
) -> list[Path]:
    """Write inclusive 0-based (start, end) page ranges — full pages only."""
    written: list[Path] = []
    for part, (start, end) in enumerate(ranges, start=1):
        writer = PdfWriter()
        _transfer_pages(writer, reader, list(range(start, end + 1)))
        if start == end:
            name = f"{stem}_page_{start + 1:03d}.pdf"
        else:
            name = f"{stem}_part_{part:03d}_p{start + 1}-{end + 1}.pdf"
        written.append(
            _write_writer(
                writer,
                out_dir / name,
                expected_pages=end - start + 1,
            )
        )
    return written


def _split_by_size(
    reader: PdfReader,
    stem: str,
    out_dir: Path,
    max_bytes: int,
) -> list[Path]:
    written: list[Path] = []
    part = 1
    start_page = 0
    batch: list[int] = []

    def flush(end_page: int) -> None:
        nonlocal part, start_page, batch
        if not batch:
            return
        writer = PdfWriter()
        _transfer_pages(writer, reader, batch)
        name = f"{stem}_part_{part:03d}_p{start_page + 1}-{end_page + 1}.pdf"
        written.append(
            _write_writer(
                writer,
                out_dir / name,
                expected_pages=len(batch),
            )
        )
        part += 1
        start_page = end_page + 1
        batch = []

    for i in range(len(reader.pages)):
        probe_idx = batch + [i]
        probe = PdfWriter()
        _transfer_pages(probe, reader, probe_idx)
        if batch and _writer_size_bytes(probe) > max_bytes:
            flush(i - 1)
            batch = [i]
            single = PdfWriter()
            _transfer_pages(single, reader, batch)
            if _writer_size_bytes(single) > max_bytes:
                flush(i)
            continue
        batch.append(i)

    if batch:
        flush(len(reader.pages) - 1)

    if not written:
        raise PdfOpsError("Size split produced no files.")
    return written


def _bookmark_split_indices(reader: PdfReader, level: int) -> list[int]:
    """0-based page indices where outline items at `level` point (1 = top)."""
    outline = getattr(reader, "outline", None) or []
    found: list[int] = []

    # pypdf outline shape: [dest, [children…], dest2, …]
    def walk_mixed(items: list, depth: int) -> None:
        i = 0
        while i < len(items):
            item = items[i]
            if isinstance(item, list):
                walk_mixed(item, depth + 1)
                i += 1
                continue
            if depth == level:
                try:
                    page_num = reader.get_destination_page_number(item)
                    if page_num is not None and page_num >= 0:
                        found.append(int(page_num))
                except Exception:  # noqa: BLE001
                    pass
            if i + 1 < len(items) and isinstance(items[i + 1], list):
                walk_mixed(items[i + 1], depth + 1)
                i += 2
            else:
                i += 1

    walk_mixed(list(outline), 1)
    return sorted(set(found))


def rotate_pages(
    path: Path | str,
    degrees: int,
    output: Path | str,
    page_spec: str | None = None,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Rotate pages by 90, 180, or 270 degrees clockwise."""
    if degrees not in (90, 180, 270):
        raise PdfOpsError("Rotation must be 90, 180, or 270 degrees.")

    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)

    if page_spec and page_spec.strip():
        targets = set(parse_page_range(page_spec, total))
    else:
        targets = set(range(total))

    writer = PdfWriter()
    _transfer_pages(writer, reader, list(range(total)))
    for i, page in enumerate(writer.pages):
        if i in targets:
            page.rotate(degrees)
    return _write_writer(writer, Path(output), sources=[src], expected_pages=total)


def default_output_next_to(source: Path | str, suffix: str) -> Path:
    """Build a default output path beside the source file."""
    src = Path(source)
    return src.with_name(f"{src.stem}{suffix}.pdf")


def reorder_pages(
    path: Path | str,
    order: list[int],
    output: Path | str,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Rewrite PDF with pages in the given 0-based order (permutation)."""
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)
    if total < 1:
        raise PdfOpsError("PDF has no pages.")
    if len(order) != total or sorted(order) != list(range(total)):
        raise PdfOpsError(
            "Reorder list must be a full permutation of all pages "
            f"(expected {total} pages)."
        )
    writer = PdfWriter()
    _transfer_pages(writer, reader, order)
    return _write_writer(writer, Path(output), sources=[src], expected_pages=total)


def reverse_pages(
    path: Path | str,
    output: Path | str,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Write PDF with pages in reverse order."""
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)
    if total < 1:
        raise PdfOpsError("PDF has no pages.")
    order = list(range(total - 1, -1, -1))
    return reorder_pages(
        src,
        order,
        output,
        password=password,
        password_provider=password_provider,
    )


def resize_pages(
    path: Path | str,
    output: Path | str,
    page_size: str,
    *,
    page_spec: str | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Fit each page onto a standard paper size (a4 / letter / legal).

    Scales to fit inside the target (may add empty margin); same as merge fit.
    """
    size_key = (page_size or "").strip().lower()
    if size_key not in PAGE_SIZES:
        raise PdfOpsError("page_size must be a4, letter, or legal.")
    tw, th = PAGE_SIZES[size_key]
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    total = len(reader.pages)
    if total < 1:
        raise PdfOpsError("PDF has no pages.")
    if page_spec and page_spec.strip():
        targets = set(parse_page_range(page_spec, total))
    else:
        targets = set(range(total))
    writer = PdfWriter()
    _transfer_pages(writer, reader, list(range(total)))
    for i, page in enumerate(writer.pages):
        if i in targets:
            _fit_page_to_size(page, tw, th)
    return _write_writer(
        writer, Path(output), sources=[src], expected_pages=total
    )


def create_blank_pdf(
    output: Path | str,
    *,
    width: float = 612.0,
    height: float = 792.0,
    count: int = 1,
) -> Path:
    """Write a PDF of blank pages (default letter size)."""
    if count < 1:
        raise PdfOpsError("Blank page count must be at least 1.")
    if width < 1 or height < 1:
        raise PdfOpsError("Blank page size is invalid.")
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(width=float(width), height=float(height))
    return _write_writer(
        writer, Path(output), sources=[], expected_pages=count
    )


def insert_blank_pages(
    path: Path | str,
    output: Path | str,
    *,
    at_page: int = 1,
    count: int = 1,
    size: str | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Insert blank page(s) before 1-based at_page (1 = start; >n appends).

    Blank size: named PAGE_SIZES key, else first page mediabox of the source.
    """
    if count < 1:
        raise PdfOpsError("Blank page count must be at least 1.")
    if at_page < 1:
        raise PdfOpsError("Insert position must be >= 1 (1 = before first page).")
    src = Path(path)
    reader = _open_reader(src, password=password, password_provider=password_provider)
    base_n = len(reader.pages)
    if base_n < 1 and not size:
        raise PdfOpsError("PDF has no pages; pass size=a4|letter|legal for blanks.")

    if size:
        size_key = size.strip().lower()
        if size_key not in PAGE_SIZES:
            raise PdfOpsError("size must be a4, letter, legal, or blank.")
        bw, bh = PAGE_SIZES[size_key]
    else:
        mb = reader.pages[0].mediabox
        bw, bh = float(mb.width), float(mb.height)

    pos = min(at_page, base_n + 1)
    insert_at = pos - 1
    writer = PdfWriter()
    if insert_at > 0:
        _transfer_pages(writer, reader, list(range(0, insert_at)))
    for _ in range(count):
        writer.add_blank_page(width=bw, height=bh)
    if insert_at < base_n:
        _transfer_pages(writer, reader, list(range(insert_at, base_n)))
    return _write_writer(
        writer,
        Path(output),
        sources=[src],
        expected_pages=base_n + count,
    )


def split_item_segments(
    items: list[tuple[Path | str, int]],
    cut_before: list[int],
    out_dir: Path | str,
    stem: str,
    *,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> list[Path]:
    """Split a tray of (path, page_index) into multiple PDFs.

    cut_before: 0-based tray indices that start a new part (split *before*
    those positions). Index 0 is ignored. Writes stem_part_001.pdf, …
    Works for multi-source trays via assemble_pages.
    """
    if not items:
        raise PdfOpsError("No pages to split.")
    n = len(items)
    cuts = sorted({int(i) for i in cut_before if 0 < int(i) < n})
    bounds = [0, *cuts, n]
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    part = 1
    for a, b in zip(bounds, bounds[1:]):
        if a >= b:
            continue
        segment = [(Path(p), int(idx)) for p, idx in items[a:b]]
        out = dest / f"{stem}_part_{part:03d}.pdf"
        written.append(
            assemble_pages(
                segment,
                out,
                password=password,
                password_provider=password_provider,
            )
        )
        part += 1
    if not written:
        raise PdfOpsError("Split produced no files.")
    if len(written) == 1:
        _warn("Only one part — select pages that start new segments (not the first).")
    return written


def assemble_pages(
    pages: list[tuple[Path | str, int]],
    output: Path | str,
    *,
    rotations: dict[int, int] | None = None,
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
) -> Path:
    """Build one PDF from pages across one or more sources.

    pages: list of (source_path, 0-based page index) in desired output order.
    rotations: optional map strip_position -> clockwise degrees (90/180/270).
    """
    if not pages:
        raise PdfOpsError("No pages to assemble.")

    items: list[tuple[Path, int]] = []
    for raw_path, idx in pages:
        p = Path(raw_path)
        if not p.is_file():
            raise PdfOpsError(f"File not found: {p}")
        if int(idx) < 0:
            raise PdfOpsError(f"Invalid page index for {p.name}.")
        items.append((p, int(idx)))

    rot_map = rotations or {}
    for pos, deg in rot_map.items():
        if int(deg) % 90 != 0:
            raise PdfOpsError("Rotation must be a multiple of 90°.")

    readers: dict[str, PdfReader] = {}
    sources: list[Path] = []
    seen_src: set[str] = set()

    def _reader_for(path: Path) -> PdfReader:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key not in readers:
            readers[key] = _open_reader(
                path, password=password, password_provider=password_provider
            )
            if key not in seen_src:
                seen_src.add(key)
                sources.append(path)
        return readers[key]

    writer = PdfWriter()
    try:
        for pos, (path, idx) in enumerate(items):
            reader = _reader_for(path)
            total = len(reader.pages)
            if idx >= total:
                raise PdfOpsError(
                    f"{path.name}: page {idx + 1} out of range ({total} pages)."
                )
            before = len(writer.pages)
            _transfer_pages(writer, reader, [idx])
            if len(writer.pages) <= before:
                raise PdfOpsError(f"Could not copy page {idx + 1} from {path.name}.")
            deg = int(rot_map.get(pos, 0) or 0) % 360
            if deg:
                try:
                    writer.pages[-1].rotate(deg)
                except Exception as exc:  # noqa: BLE001
                    raise PdfOpsError(
                        f"Rotate failed on output page {pos + 1}: {exc}"
                    ) from exc

        return _write_writer(
            writer,
            Path(output),
            sources=sources or [items[0][0]],
            expected_pages=len(items),
        )
    finally:
        readers.clear()

