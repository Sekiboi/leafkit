"""Pass 4: crop_box soft/hard + CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from leafkit import pdf_ops
from leafkit.cli import main
from tests.fixtures import make_messy


def test_crop_box_soft(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 2, w=400, h=600)
    out = pdf_ops.crop_box(src, tmp_path / "c.pdf", (50, 50, 350, 550), hard=False)
    assert pdf_ops.page_count(out) == 2
    from pypdf import PdfReader

    r = PdfReader(str(out))
    mb = r.pages[0].mediabox
    assert abs(float(mb.width) - 300) < 2
    assert abs(float(mb.height) - 500) < 2


def test_crop_box_hard(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 1, w=400, h=600)
    out = pdf_ops.crop_box(src, tmp_path / "h.pdf", (40, 40, 360, 560), hard=True)
    assert pdf_ops.page_count(out) == 1
    import fitz

    doc = fitz.open(str(out))
    try:
        r = doc[0].rect
        assert abs(r.width - 320) < 3
        assert abs(r.height - 520) < 3
    finally:
        doc.close()


def test_crop_box_page_range(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 3, w=300, h=400)
    out = pdf_ops.crop_box(
        src, tmp_path / "p.pdf", (10, 10, 200, 300), page_spec="2", hard=False
    )
    assert pdf_ops.page_count(out) == 3
    from pypdf import PdfReader

    r = PdfReader(str(out))
    # page 1 (index 0) unchanged ~300 wide
    assert float(r.pages[0].mediabox.width) > 250
    # page 2 cropped
    assert abs(float(r.pages[1].mediabox.width) - 190) < 2


def test_crop_box_too_small(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 1)
    with pytest.raises(pdf_ops.PdfOpsError, match="too small"):
        pdf_ops.crop_box(src, tmp_path / "x.pdf", (0, 0, 5, 5))


def test_cli_crop_box(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 1, w=400, h=400)
    out = tmp_path / "box.pdf"
    rc = main(
        [
            "crop-box",
            str(src),
            "--x0",
            "50",
            "--y0",
            "50",
            "--x1",
            "350",
            "--y1",
            "350",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    assert out.is_file()
    assert pdf_ops.page_count(out) == 1
