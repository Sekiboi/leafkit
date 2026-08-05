"""Multi-source assemble (Organize combine)."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from leafkit import pdf_ops


def _make(path: Path, pages: int) -> Path:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=300)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        w.write(f)
    return path


def test_assemble_multi_source(tmp_path: Path) -> None:
    a = _make(tmp_path / "a.pdf", 2)
    b = _make(tmp_path / "b.pdf", 3)
    out = pdf_ops.assemble_pages(
        [(a, 1), (b, 0), (b, 2), (a, 0)],
        tmp_path / "c.pdf",
    )
    assert pdf_ops.page_count(out) == 4


def test_assemble_rotation(tmp_path: Path) -> None:
    a = _make(tmp_path / "a.pdf", 2)
    out = pdf_ops.assemble_pages(
        [(a, 0), (a, 1)],
        tmp_path / "r.pdf",
        rotations={1: 180},
    )
    assert pdf_ops.page_count(out) == 2


def test_assemble_empty_raises(tmp_path: Path) -> None:
    try:
        pdf_ops.assemble_pages([], tmp_path / "x.pdf")
        assert False, "expected error"
    except pdf_ops.PdfOpsError:
        pass


def test_assemble_bad_index(tmp_path: Path) -> None:
    a = _make(tmp_path / "a.pdf", 1)
    try:
        pdf_ops.assemble_pages([(a, 5)], tmp_path / "x.pdf")
        assert False, "expected error"
    except pdf_ops.PdfOpsError:
        pass


def test_result_paths_ignores_org_item_tuples(tmp_path: Path) -> None:
    """Add-to-tray returns (path, page) tuples — must not be treated as outputs."""
    from leafkit.app import LeafkitApp

    a = _make(tmp_path / "a.pdf", 2)
    out = _make(tmp_path / "out.pdf", 1)
    fake = object()
    items = [(a, 0), (a, 1)]
    assert LeafkitApp._result_paths(fake, items) == []
    assert LeafkitApp._result_paths(fake, [out]) == [out]
    assert LeafkitApp._result_paths(fake, out) == [out]
