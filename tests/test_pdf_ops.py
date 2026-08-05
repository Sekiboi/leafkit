"""Unit tests for PDF operations (no GUI)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from leafkit import pdf_ops


def _make_pdf(path: Path, pages: int = 3) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        writer.write(f)
    return path


def _make_encrypted(path: Path, pages: int = 2, password: str = "secret") -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    writer.encrypt(password)
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
    assert pdf_ops.parse_page_range("2,2,3", 5) == [1, 2]


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


def test_merge_with_page_specs(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 4)
    b = _make_pdf(tmp_path / "b.pdf", 3)
    out = pdf_ops.merge_pdfs(
        [a, b],
        tmp_path / "merged.pdf",
        page_specs=["1-2", "2-"],
    )
    assert pdf_ops.page_count(out) == 4  # 2 from a + 2 from b


def test_extract(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 5)
    out = pdf_ops.extract_pages(src, "2-3,5", tmp_path / "ex.pdf")
    assert pdf_ops.page_count(out) == 3


def test_delete_pages(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 5)
    out = pdf_ops.delete_pages(src, "2,4", tmp_path / "del.pdf")
    assert pdf_ops.page_count(out) == 3


def test_delete_all_fails(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 2)
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops.delete_pages(src, "1-", tmp_path / "x.pdf")


def test_insert_pages(tmp_path: Path) -> None:
    base = _make_pdf(tmp_path / "base.pdf", 3)
    ins = _make_pdf(tmp_path / "ins.pdf", 2)
    out = pdf_ops.insert_pages(base, ins, tmp_path / "out.pdf", at_page=2)
    assert pdf_ops.page_count(out) == 5


def test_insert_at_end(tmp_path: Path) -> None:
    base = _make_pdf(tmp_path / "base.pdf", 2)
    ins = _make_pdf(tmp_path / "ins.pdf", 1)
    out = pdf_ops.insert_pages(base, ins, tmp_path / "out.pdf", at_page=99)
    assert pdf_ops.page_count(out) == 3


def test_mix(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 2)
    b = _make_pdf(tmp_path / "b.pdf", 3)
    out = pdf_ops.mix_pdfs([a, b], tmp_path / "mix.pdf")
    assert pdf_ops.page_count(out) == 5


def test_mix_reverse_second(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 2)
    b = _make_pdf(tmp_path / "b.pdf", 2)
    out = pdf_ops.mix_pdfs([a, b], tmp_path / "mix.pdf", reverse_second=True)
    assert pdf_ops.page_count(out) == 4


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


def test_split_at_pages(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 10)
    files = pdf_ops.split_pdf(src, "at_pages", tmp_path / "out", at_pages="3,7")
    assert len(files) == 3
    assert pdf_ops.page_count(files[0]) == 2
    assert pdf_ops.page_count(files[1]) == 4
    assert pdf_ops.page_count(files[2]) == 4


def test_split_even_odd(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 5)
    files = pdf_ops.split_pdf(src, "even_odd", tmp_path / "out")
    assert len(files) == 2
    counts = sorted(pdf_ops.page_count(f) for f in files)
    assert counts == [2, 3]


def test_split_by_size(tmp_path: Path) -> None:
    # Larger pages so size split can trigger with a tiny max_mb
    writer = PdfWriter()
    for _ in range(6):
        writer.add_blank_page(width=2000, height=2000)
    src = tmp_path / "big.pdf"
    with open(src, "wb") as f:
        writer.write(f)
    # Blank pages compress tiny; use a very low cap so we force multiple parts
    files = pdf_ops.split_pdf(src, "size", tmp_path / "out", max_mb=0.00005)
    assert len(files) >= 2
    assert sum(pdf_ops.page_count(f) for f in files) == 6


def test_rotate(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 2)
    out = pdf_ops.rotate_pages(src, 90, tmp_path / "rot.pdf")
    assert out.exists()
    assert pdf_ops.page_count(out) == 2


def test_unique_path(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 1)
    b = _make_pdf(tmp_path / "b.pdf", 1)
    target = tmp_path / "out.pdf"
    _make_pdf(target, 1)
    result = pdf_ops.merge_pdfs([a, b], target)
    assert result.name == "out_1.pdf"


def test_password_open(tmp_path: Path) -> None:
    src = _make_encrypted(tmp_path / "enc.pdf", 2, "secret")
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops.page_count(src)
    assert pdf_ops.page_count(src, password="secret") == 2
    out = pdf_ops.extract_pages(src, "1", tmp_path / "ex.pdf", password="secret")
    assert pdf_ops.page_count(out) == 1


def test_password_provider(tmp_path: Path) -> None:
    src = _make_encrypted(tmp_path / "enc.pdf", 1, "pw")
    out = pdf_ops.extract_pages(
        src,
        "1",
        tmp_path / "ex.pdf",
        password_provider=lambda _p: "pw",
    )
    assert out.exists()


def test_merge_expands_tight_cropbox(tmp_path: Path) -> None:
    """Pages with CropBox smaller than MediaBox must not stay clipped after merge."""
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    for path in (a, b):
        w = PdfWriter()
        w.add_blank_page(width=400, height=600)
        page = w.pages[0]
        page.cropbox.lower_left = (0, 300)
        page.cropbox.upper_right = (400, 600)
        with open(path, "wb") as f:
            w.write(f)

    out = pdf_ops.merge_pdfs([a, b], tmp_path / "merged.pdf")
    r = PdfReader(str(out))
    assert len(r.pages) == 2
    for page in r.pages:
        mb = page.mediabox
        cb = page.cropbox
        assert float(cb.bottom) <= float(mb.bottom) + 0.5
        assert float(cb.top) >= float(mb.top) - 0.5
        assert float(cb.height) + 0.5 >= float(mb.height)
