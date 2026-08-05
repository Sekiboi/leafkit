"""Pass 5: stamp_image."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from sekikit import pdf_ops
from sekikit.cli import main
from tests.fixtures import make_messy


def _logo(path: Path) -> Path:
    Image.new("RGBA", (80, 40), (20, 100, 200, 200)).save(path)
    return path


def test_stamp_image(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 2, w=400, h=600)
    logo = _logo(tmp_path / "logo.png")
    out = pdf_ops.stamp_image(
        src, logo, tmp_path / "s.pdf", position="bottom-right", scale=0.2
    )
    assert pdf_ops.page_count(out) == 2
    assert out.stat().st_size > src.stat().st_size * 0.5


def test_stamp_image_center_opacity(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 1, w=300, h=300)
    logo = _logo(tmp_path / "l.png")
    out = pdf_ops.stamp_image(
        src,
        logo,
        tmp_path / "c.pdf",
        position="center",
        scale=0.3,
        opacity=0.5,
    )
    assert pdf_ops.page_count(out) == 1


def test_stamp_image_page_range(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 3)
    logo = _logo(tmp_path / "l.png")
    out = pdf_ops.stamp_image(
        src, logo, tmp_path / "p.pdf", page_spec="1,3", scale=0.15
    )
    assert pdf_ops.page_count(out) == 3


def test_stamp_image_bad_scale(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 1)
    logo = _logo(tmp_path / "l.png")
    with pytest.raises(pdf_ops.PdfOpsError, match="scale"):
        pdf_ops.stamp_image(src, logo, tmp_path / "x.pdf", scale=2.0)


def test_cli_stamp_image(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 1)
    logo = _logo(tmp_path / "logo.png")
    out = tmp_path / "st.pdf"
    rc = main(
        [
            "stamp-image",
            str(src),
            str(logo),
            "-o",
            str(out),
            "--position",
            "top-left",
            "--scale",
            "0.2",
        ]
    )
    assert rc == 0
    assert out.is_file()
