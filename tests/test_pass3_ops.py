"""Pass 3: extract text + tray split segments."""

from __future__ import annotations

from pathlib import Path

from sekikit import pdf_ops
from sekikit.cli import main
from tests.fixtures import make_messy


def _pdf_with_text(path: Path, lines: list[str]) -> Path:
    import fitz

    doc = fitz.open()
    for line in lines:
        page = doc.new_page(width=300, height=400)
        page.insert_text((40, 80), line, fontsize=14)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


def test_extract_text(tmp_path: Path) -> None:
    src = _pdf_with_text(tmp_path / "t.pdf", ["Hello Sekikit", "Page two"])
    text = pdf_ops.extract_text(src)
    assert "Hello Sekikit" in text
    assert "Page two" in text


def test_extract_text_page_range(tmp_path: Path) -> None:
    src = _pdf_with_text(tmp_path / "t.pdf", ["AAA", "BBB", "CCC"])
    text = pdf_ops.extract_text(src, page_spec="2")
    assert "BBB" in text
    assert "AAA" not in text


def test_extract_text_to_file(tmp_path: Path) -> None:
    src = _pdf_with_text(tmp_path / "t.pdf", ["Save me"])
    out = pdf_ops.extract_text_to_file(src, tmp_path / "out.txt")
    assert out.is_file()
    assert "Save me" in out.read_text(encoding="utf-8")


def test_extract_text_blank_warns(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "b.pdf", 1)
    pdf_ops.take_warnings()
    text = pdf_ops.extract_text(src)
    assert text == ""
    warns = pdf_ops.take_warnings()
    assert any("selectable text" in w.lower() or "ocr" in w.lower() for w in warns)


def test_split_item_segments(tmp_path: Path) -> None:
    a = make_messy.blank(tmp_path / "a.pdf", 3)
    b = make_messy.blank(tmp_path / "b.pdf", 2)
    # tray: a0,a1,a2,b0,b1 — cut before index 2 and 3
    items = [
        (a, 0),
        (a, 1),
        (a, 2),
        (b, 0),
        (b, 1),
    ]
    parts = pdf_ops.split_item_segments(
        items, [2, 3], tmp_path / "parts", "tray"
    )
    assert len(parts) == 3
    assert pdf_ops.page_count(parts[0]) == 2  # a0,a1
    assert pdf_ops.page_count(parts[1]) == 1  # a2
    assert pdf_ops.page_count(parts[2]) == 2  # b0,b1


def test_split_item_segments_single_source(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "s.pdf", 5)
    items = [(src, i) for i in range(5)]
    parts = pdf_ops.split_item_segments(items, [2, 4], tmp_path / "p", "s")
    assert [pdf_ops.page_count(p) for p in parts] == [2, 2, 1]


def test_cli_text(tmp_path: Path) -> None:
    src = _pdf_with_text(tmp_path / "c.pdf", ["CLI Text"])
    out = tmp_path / "c.txt"
    assert main(["text", str(src), "-o", str(out)]) == 0
    assert out.is_file() or out.with_name(out.name).exists()
    # unique path may add _1
    found = list(tmp_path.glob("c*.txt"))
    assert found
    assert any("CLI Text" in p.read_text(encoding="utf-8") for p in found)
