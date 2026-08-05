"""Pass 1: decrypt, resize, reverse, blank."""

from __future__ import annotations

from pathlib import Path

import pytest

from sekikit import pdf_ops
from sekikit.cli import main
from tests.fixtures import make_messy


def test_decrypt_pdf(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 2)
    enc = tmp_path / "e.pdf"
    pdf_ops.encrypt_pdf(src, enc, "secret")
    with pytest.raises(pdf_ops.PdfOpsError):
        pdf_ops.page_count(enc)
    out = pdf_ops.decrypt_pdf(enc, tmp_path / "u.pdf", password="secret")
    assert pdf_ops.page_count(out) == 2


def test_decrypt_unencrypted_warns(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 1)
    pdf_ops.take_warnings()
    out = pdf_ops.decrypt_pdf(src, tmp_path / "u.pdf")
    assert pdf_ops.page_count(out) == 1
    warns = pdf_ops.take_warnings()
    assert any("not password-protected" in w for w in warns)


def test_reverse_pages(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 3)
    out = pdf_ops.reverse_pages(src, tmp_path / "r.pdf")
    assert pdf_ops.page_count(out) == 3


def test_resize_pages(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 2, w=400, h=600)
    out = pdf_ops.resize_pages(src, tmp_path / "s.pdf", "letter")
    assert pdf_ops.page_count(out) == 2


def test_insert_blank_pages(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 2)
    out = pdf_ops.insert_blank_pages(src, tmp_path / "b.pdf", at_page=1, count=2)
    assert pdf_ops.page_count(out) == 4


def test_create_blank_pdf(tmp_path: Path) -> None:
    out = pdf_ops.create_blank_pdf(tmp_path / "blank.pdf", count=2)
    assert pdf_ops.page_count(out) == 2


def test_cli_decrypt_reverse_resize_blank(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "a.pdf", 3)
    enc = tmp_path / "e.pdf"
    pdf_ops.encrypt_pdf(src, enc, "pw")
    unlocked = tmp_path / "u.pdf"
    assert main(["decrypt", str(enc), "-o", str(unlocked), "--password", "pw"]) == 0
    assert pdf_ops.page_count(unlocked) == 3

    rev = tmp_path / "r.pdf"
    assert main(["reverse", str(src), "-o", str(rev)]) == 0
    assert pdf_ops.page_count(rev) == 3

    resized = tmp_path / "s.pdf"
    assert main(["resize", str(src), "--page-size", "a4", "-o", str(resized)]) == 0
    assert pdf_ops.page_count(resized) == 3

    blanked = tmp_path / "bl.pdf"
    assert main(["blank", str(src), "--at-page", "2", "--count", "1", "-o", str(blanked)]) == 0
    assert pdf_ops.page_count(blanked) == 4
