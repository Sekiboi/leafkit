"""Tests for drag-and-drop path parsing helpers."""

from pathlib import Path

from leafkit.app import _expand_to_pdfs, _parse_drop_paths


def test_parse_simple_paths() -> None:
    data = r"C:\a.pdf D:\b\c.pdf"
    paths = _parse_drop_paths(data)
    assert paths == [Path(r"C:\a.pdf"), Path(r"D:\b\c.pdf")]


def test_parse_braced_spaces() -> None:
    data = r"{C:\My Docs\file one.pdf} C:\plain.pdf"
    paths = _parse_drop_paths(data)
    assert paths == [Path(r"C:\My Docs\file one.pdf"), Path(r"C:\plain.pdf")]


def test_expand_filters_non_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "ok.pdf"
    txt = tmp_path / "nope.txt"
    pdf.write_bytes(b"%PDF")
    txt.write_text("x", encoding="utf-8")
    out = _expand_to_pdfs([pdf, txt])
    assert out == [pdf]


def test_expand_folder(tmp_path: Path) -> None:
    (tmp_path / "a.pdf").write_bytes(b"%PDF")
    (tmp_path / "b.PDF").write_bytes(b"%PDF")
    (tmp_path / "c.txt").write_text("x", encoding="utf-8")
    out = _expand_to_pdfs([tmp_path])
    names = sorted(p.name.lower() for p in out)
    assert names == ["a.pdf", "b.pdf"]
