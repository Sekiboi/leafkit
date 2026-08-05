"""Phase 2: organize, compress, clean, encrypt, crop, images→PDF."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from PIL import Image

from sekikit import pdf_ops
from sekikit import render as pdf_render


def _make_pdf(path: Path, pages: int = 3) -> Path:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=300, height=400)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        w.write(f)
    return path


def test_reorder(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 4)
    out = pdf_ops.reorder_pages(src, [3, 2, 1, 0], tmp_path / "r.pdf")
    assert pdf_ops.page_count(out) == 4


def test_reorder_bad_perm(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 3)
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops.reorder_pages(src, [0, 1], tmp_path / "x.pdf")


def test_clean_metadata(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 1)
    r = PdfReader(str(src))
    w = PdfWriter()
    w.add_page(r.pages[0])
    w.add_metadata({"/Author": "Secret Person", "/Title": "Secret Doc"})
    stamped = tmp_path / "stamped.pdf"
    with open(stamped, "wb") as f:
        w.write(f)
    out = pdf_ops.clean_metadata(stamped, tmp_path / "clean.pdf")
    meta = PdfReader(str(out)).metadata
    if meta:
        author = str(meta.get("/Author", "") or "")
        assert "Secret" not in author


def test_encrypt_and_open(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 2)
    enc = pdf_ops.encrypt_pdf(src, tmp_path / "enc.pdf", "hunter2")
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops.page_count(enc)
    assert pdf_ops.page_count(enc, password="hunter2") == 2


def test_crop_margins(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 1)
    out = pdf_ops.crop_margins(src, tmp_path / "c.pdf", margin_pts=36)  # 0.5"
    page = PdfReader(str(out)).pages[0]
    assert float(page.mediabox.width) < 300
    assert float(page.mediabox.height) < 400


def test_images_to_pdf(tmp_path: Path) -> None:
    imgs = []
    for i, color in enumerate([(255, 0, 0), (0, 255, 0)]):
        p = tmp_path / f"i{i}.png"
        Image.new("RGB", (80, 60), color).save(p)
        imgs.append(p)
    out = pdf_ops.images_to_pdf(imgs, tmp_path / "from_img.pdf")
    assert pdf_ops.page_count(out) == 2


def test_compress(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 2)
    out = pdf_ops.compress_pdf(
        src, tmp_path / "c.pdf", preset="balanced", prefer_ghostscript=False
    )
    assert out.exists()
    assert pdf_ops.page_count(out) == 2


def test_compress_scan(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 2)
    out = pdf_ops.compress_pdf(
        src, tmp_path / "s.pdf", preset="scan", prefer_ghostscript=False
    )
    assert out.exists()
    assert pdf_ops.page_count(out) == 2


@pytest.mark.skipif(not pdf_render.has_renderer(), reason="pymupdf missing")
def test_render_thumbnail(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 2)
    thumbs = pdf_render.render_thumbnails(src, max_width=64)
    assert len(thumbs) == 2
    assert thumbs[0].width <= 64 + 2


@pytest.mark.skipif(not pdf_render.has_renderer(), reason="pymupdf missing")
def test_thumbnail_session_lazy(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 5)
    with pdf_render.ThumbnailSession(src, max_width=48) as session:
        assert session.page_count == 5
        a = session.get(0)
        b = session.get(4)
        assert a.width <= 48 + 2
        assert b.width <= 48 + 2
