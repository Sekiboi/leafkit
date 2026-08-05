"""Phase 3: n-up, grayscale, merge options, CLI."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from sekikit import pdf_ops
from sekikit.cli import main as cli_main


def _make_pdf(path: Path, pages: int = 4) -> Path:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=300)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        w.write(f)
    return path


def test_nup_2(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 4)
    out = pdf_ops.nup_pdf(src, tmp_path / "n.pdf", n=2)
    assert pdf_ops.page_count(out) == 2


def test_nup_4(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 5)
    out = pdf_ops.nup_pdf(src, tmp_path / "n.pdf", n=4)
    assert pdf_ops.page_count(out) == 2


def test_grayscale(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 2)
    out = pdf_ops.grayscale_pdf(src, tmp_path / "g.pdf")
    assert pdf_ops.page_count(out) == 2


def test_merge_page_size(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 1)
    b = _make_pdf(tmp_path / "b.pdf", 1)
    out = pdf_ops.merge_pdfs([a, b], tmp_path / "m.pdf", page_size="letter")
    assert pdf_ops.page_count(out) == 2


def test_cli_info(tmp_path: Path, capsys) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 3)
    rc = cli_main(["info", str(src)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "pages: 3" in out


def test_cli_extract(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 5)
    out = tmp_path / "ex.pdf"
    rc = cli_main(["extract", str(src), "--pages", "1-2", "-o", str(out)])
    assert rc == 0
    assert pdf_ops.page_count(out) == 2
