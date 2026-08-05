"""Local watch-folder helpers."""
from __future__ import annotations

from pathlib import Path

from sekikit.pdf_ops._core import (
    PasswordProvider,
    PdfOpsError,
    _assert_not_overwrite_inputs,
    _ensure_pdf,
)
from sekikit.pdf_ops.compress import compress_pdf
from sekikit.pdf_ops.pagenum import (
    WATCH_ACTIONS,
    add_page_numbers,
    flatten_forms,
    renumber_pages,
)
from sekikit.pdf_ops.transform import clean_metadata, grayscale_pdf

def watch_process_file(
    src: Path | str,
    out_dir: Path | str,
    action: str,
    *,
    compress_preset: str = "balanced",
    page_number_format: str = "{n} / {total}",
    page_number_position: str = "footer",
    page_number_align: str = "center",
    password: str | None = None,
    password_provider: PasswordProvider | None = None,
    prefer_ghostscript: bool = True,
) -> Path:
    """Process one PDF for watch-folder batch. Writes into out_dir.

    actions: compress | grayscale | page_numbers | renumber | flatten | clean
    """
    src_p = _ensure_pdf(Path(src))
    dest_dir = Path(out_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    act = (action or "").strip().lower()
    if act not in WATCH_ACTIONS:
        raise PdfOpsError(
            f"Unknown watch action {action!r}. "
            f"Choose one of: {', '.join(sorted(WATCH_ACTIONS))}"
        )

    suffix_map = {
        "compress": f"_compressed_{compress_preset}",
        "grayscale": "_gray",
        "page_numbers": "_numbered",
        "renumber": "_renumbered",
        "flatten": "_flattened",
        "clean": "_cleaned",
    }
    out = dest_dir / f"{src_p.stem}{suffix_map[act]}.pdf"
    _assert_not_overwrite_inputs(src_p, out)

    kw: dict = {"password": password}
    if password_provider is not None:
        kw["password_provider"] = password_provider

    if act == "compress":
        return compress_pdf(
            src_p,
            out,
            preset=compress_preset,
            password=password,
            prefer_ghostscript=prefer_ghostscript,
        )
    if act == "grayscale":
        return grayscale_pdf(src_p, out, password=password)
    if act == "page_numbers":
        return add_page_numbers(
            src_p,
            out,
            position=page_number_position,
            align=page_number_align,
            format_str=page_number_format,
            mode="stamp",
            **kw,
        )
    if act == "renumber":
        return renumber_pages(
            src_p,
            out,
            position=page_number_position,
            align=page_number_align,
            format_str=page_number_format,
            **kw,
        )
    if act == "flatten":
        return flatten_forms(src_p, out, **kw)
    return clean_metadata(src_p, out, **kw)


def list_watch_pdfs(folder: Path | str) -> list[Path]:
    """Sorted list of PDF files directly in folder (not recursive)."""
    d = Path(folder)
    if not d.is_dir():
        raise PdfOpsError(f"Watch folder not found: {d}")
    found: list[Path] = []
    try:
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix.lower() == ".pdf":
                if p.name.startswith(".sekikit-"):
                    continue
                found.append(p)
    except OSError as exc:
        raise PdfOpsError(f"Could not list watch folder: {exc}") from exc
    return found
