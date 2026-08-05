"""CLI parity: mix, insert, images, assemble."""

from __future__ import annotations

from pathlib import Path

from sekikit.cli import main
from sekikit import pdf_ops
from tests.fixtures import make_messy


def test_cli_mix(tmp_path: Path) -> None:
    a = make_messy.blank(tmp_path / "a.pdf", 2)
    b = make_messy.blank(tmp_path / "b.pdf", 2)
    out = tmp_path / "m.pdf"
    rc = main(["mix", str(a), str(b), "-o", str(out)])
    assert rc == 0
    assert out.is_file()
    assert pdf_ops.page_count(out) == 4


def test_cli_insert(tmp_path: Path) -> None:
    base = make_messy.blank(tmp_path / "base.pdf", 3)
    ins = make_messy.blank(tmp_path / "ins.pdf", 1)
    out = tmp_path / "i.pdf"
    rc = main(
        ["insert", str(base), str(ins), "--at-page", "2", "-o", str(out)]
    )
    assert rc == 0
    assert pdf_ops.page_count(out) == 4


def test_cli_images(tmp_path: Path) -> None:
    from PIL import Image

    imgs = []
    for i in range(2):
        p = tmp_path / f"i{i}.png"
        Image.new("RGB", (40, 50), color=(i * 80, 100, 120)).save(p)
        imgs.append(p)
    out = tmp_path / "from_img.pdf"
    rc = main(["images", str(imgs[0]), str(imgs[1]), "-o", str(out)])
    assert rc == 0
    assert pdf_ops.page_count(out) == 2


def test_cli_assemble(tmp_path: Path) -> None:
    a = make_messy.blank(tmp_path / "a.pdf", 2)
    b = make_messy.blank(tmp_path / "b.pdf", 2)
    out = tmp_path / "as.pdf"
    rc = main(
        [
            "assemble",
            f"{a}:2",
            f"{b}:1",
            f"{a}:1",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    assert pdf_ops.page_count(out) == 3
