"""Reliability: atomic writes, same-path guards, validation, fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from leafkit import pdf_ops
from fixtures import make_messy


def test_atomic_merge_validates(tmp_path: Path) -> None:
    a = make_messy.blank(tmp_path / "a.pdf", 2)
    b = make_messy.blank(tmp_path / "b.pdf", 3)
    out = pdf_ops.merge_pdfs([a, b], tmp_path / "m.pdf")
    assert out.exists()
    assert pdf_ops.page_count(out) == 5
    temps = list(tmp_path.glob(".leafkit-*.tmp.pdf"))
    assert temps == []


def test_refuse_overwrite_input(tmp_path: Path) -> None:
    a = make_messy.blank(tmp_path / "a.pdf", 1)
    b = make_messy.blank(tmp_path / "b.pdf", 1)
    with pytest.raises(pdf_ops.PdfOpsError, match="overwrite"):
        pdf_ops.merge_pdfs([a, b], a)


def test_refuse_overwrite_extract(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "s.pdf", 3)
    with pytest.raises(pdf_ops.PdfOpsError, match="overwrite"):
        pdf_ops.extract_pages(src, "1", src)


def test_validate_rejects_non_pdf(tmp_path: Path) -> None:
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"not a pdf")
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops._validate_pdf_file(junk)


def test_roundtrip_rotate_cropbox(tmp_path: Path) -> None:
    src = make_messy.tight_cropbox(tmp_path / "crop.pdf")
    out = pdf_ops.rotate_pages(src, 90, tmp_path / "rot.pdf")
    r = PdfReader(str(out))
    assert len(r.pages) == 1
    page = r.pages[0]
    assert float(page.cropbox.height) + 0.5 >= float(page.mediabox.height) * 0.9


def test_roundtrip_encrypted(tmp_path: Path) -> None:
    src = make_messy.encrypted(tmp_path / "e.pdf", "pw", 3)
    out = pdf_ops.extract_pages(src, "1-2", tmp_path / "x.pdf", password="pw")
    assert pdf_ops.page_count(out) == 2


def test_roundtrip_mixed_sizes_merge(tmp_path: Path) -> None:
    a = make_messy.mixed_page_sizes(tmp_path / "mix.pdf")
    b = make_messy.blank(tmp_path / "b.pdf", 1)
    out = pdf_ops.merge_pdfs([a, b], tmp_path / "m.pdf")
    assert pdf_ops.page_count(out) == 4


def test_roundtrip_delete_reorder(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "s.pdf", 5)
    deleted = pdf_ops.delete_pages(src, "2,4", tmp_path / "d.pdf")
    assert pdf_ops.page_count(deleted) == 3
    reordered = pdf_ops.reorder_pages(deleted, [2, 1, 0], tmp_path / "r.pdf")
    assert pdf_ops.page_count(reordered) == 3


def test_clean_metadata_fixture(tmp_path: Path) -> None:
    src = make_messy.with_metadata(tmp_path / "meta.pdf")
    out = pdf_ops.clean_metadata(src, tmp_path / "c.pdf")
    meta = PdfReader(str(out)).metadata
    if meta:
        assert "Fixture" not in str(meta.get("/Author", "") or "")


def test_split_validates_parts(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "s.pdf", 4)
    parts = pdf_ops.split_pdf(src, "every_n", tmp_path / "out", every_n=2)
    assert len(parts) == 2
    assert all(pdf_ops.page_count(p) == 2 for p in parts)


def test_preflight_disk_ok(tmp_path: Path) -> None:
    pdf_ops._preflight_disk(tmp_path, 1024)


def test_warnings_scan(tmp_path: Path) -> None:
    pdf_ops.take_warnings()
    src = make_messy.blank(tmp_path / "s.pdf", 1)
    pdf_ops.compress_pdf(
        src, tmp_path / "c.pdf", preset="scan", prefer_ghostscript=False
    )
    warns = pdf_ops.take_warnings()
    assert any("image" in w.lower() or "selectable" in w.lower() for w in warns)
