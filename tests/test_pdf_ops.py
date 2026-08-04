"""Unit tests for PDF operations (no GUI)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfWriter

from justpages import pdf_ops


def _make_pdf(path: Path, pages: int = 3) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        writer.write(f)
    return path


def test_page_count(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 4)
    assert pdf_ops.page_count(pdf) == 4


def test_parse_page_range() -> None:
    assert pdf_ops.parse_page_range("1", 5) == [0]
    assert pdf_ops.parse_page_range("2-4", 5) == [1, 2, 3]
    assert pdf_ops.parse_page_range("1,3,5", 5) == [0, 2, 4]
    assert pdf_ops.parse_page_range("1-", 3) == [0, 1, 2]
    assert pdf_ops.parse_page_range("2,2,3", 5) == [1, 2]  # dedupe, keep order


def test_parse_page_range_errors() -> None:
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops.parse_page_range("", 3)
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops.parse_page_range("9", 3)
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops.parse_page_range("4-2", 5)


def test_merge(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 2)
    b = _make_pdf(tmp_path / "b.pdf", 3)
    out = pdf_ops.merge_pdfs([a, b], tmp_path / "merged.pdf")
    assert out.exists()
    assert pdf_ops.page_count(out) == 5


def test_extract(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 5)
    out = pdf_ops.extract_pages(src, "2-3,5", tmp_path / "ex.pdf")
    assert pdf_ops.page_count(out) == 3


def test_split_each(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 3)
    files = pdf_ops.split_pdf(src, "each", tmp_path / "out")
    assert len(files) == 3
    assert all(pdf_ops.page_count(f) == 1 for f in files)


def test_split_every_n(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 5)
    files = pdf_ops.split_pdf(src, "every_n", tmp_path / "out", every_n=2)
    assert len(files) == 3
    assert pdf_ops.page_count(files[0]) == 2
    assert pdf_ops.page_count(files[1]) == 2
    assert pdf_ops.page_count(files[2]) == 1


def test_rotate(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 2)
    out = pdf_ops.rotate_pages(src, 90, tmp_path / "rot.pdf")
    assert out.exists()
    assert pdf_ops.page_count(out) == 2


def test_unique_path(tmp_path: Path) -> None:
    first = tmp_path / "x.pdf"
    first.write_bytes(b"%PDF-1.4")
    # merge writes via _unique_path when target exists
    a = _make_pdf(tmp_path / "a.pdf", 1)
    b = _make_pdf(tmp_path / "b.pdf", 1)
    # Create collision target first
    target = tmp_path / "out.pdf"
    _make_pdf(target, 1)
    result = pdf_ops.merge_pdfs([a, b], target)
    assert result.name == "out_1.pdf"
