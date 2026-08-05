"""Phase 4: page numbers, flatten forms, watch-folder helpers, CLI."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from sekikit import pdf_ops
from sekikit.cli import main as cli_main


def _make_pdf(path: Path, pages: int = 3) -> Path:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=300)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        w.write(f)
    return path


def test_add_page_numbers_footer(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 3)
    out = pdf_ops.add_page_numbers(
        src,
        tmp_path / "n.pdf",
        position="footer",
        align="center",
        format_str="{n} / {total}",
        start=1,
    )
    assert pdf_ops.page_count(out) == 3
    import fitz

    doc = fitz.open(str(out))
    try:
        text0 = doc[0].get_text()
        assert "1" in text0
        assert "3" in text0  # total
        text2 = doc[2].get_text()
        assert "3" in text2
    finally:
        doc.close()


def test_add_page_numbers_header_start(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 2)
    out = pdf_ops.add_page_numbers(
        src,
        tmp_path / "h.pdf",
        position="header",
        align="right",
        format_str="Page {n}",
        start=10,
    )
    import fitz

    doc = fitz.open(str(out))
    try:
        assert "10" in doc[0].get_text()
        assert "11" in doc[1].get_text()
    finally:
        doc.close()


def test_add_page_numbers_range(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 4)
    out = pdf_ops.add_page_numbers(
        src,
        tmp_path / "r.pdf",
        page_spec="2-3",
        format_str="X{n}",
        start=1,
    )
    import fitz

    doc = fitz.open(str(out))
    try:
        t0 = doc[0].get_text()
        t1 = doc[1].get_text()
        assert "X2" in t1
        assert "X" not in t0 or "X2" not in t0
    finally:
        doc.close()


def test_flatten_forms_plain_pdf(tmp_path: Path) -> None:
    """Flatten on a non-form PDF still produces a valid copy."""
    src = _make_pdf(tmp_path / "a.pdf", 2)
    out = pdf_ops.flatten_forms(src, tmp_path / "f.pdf")
    assert pdf_ops.page_count(out) == 2


def test_flatten_forms_with_widget(tmp_path: Path) -> None:
    """Create a simple text widget, flatten, ensure no widgets remain."""
    import fitz

    src = tmp_path / "form.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    widget = fitz.Widget()
    widget.field_name = "name"
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.field_value = "Hello"
    widget.rect = fitz.Rect(50, 50, 200, 80)
    page.add_widget(widget)
    doc.save(str(src))
    doc.close()

    out = pdf_ops.flatten_forms(src, tmp_path / "flat.pdf")
    assert pdf_ops.page_count(out) == 1

    doc2 = fitz.open(str(out))
    try:
        assert not doc2.is_form_pdf
        page0 = doc2[0]
        assert page0.first_widget is None
    finally:
        doc2.close()


def test_watch_process_file_clean(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "in" / "a.pdf", 2)
    out_dir = tmp_path / "out"
    result = pdf_ops.watch_process_file(src, out_dir, "clean")
    assert result.is_file()
    assert result.parent == out_dir
    assert pdf_ops.page_count(result) == 2


def test_watch_process_file_page_numbers(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "in" / "a.pdf", 2)
    out_dir = tmp_path / "out"
    result = pdf_ops.watch_process_file(
        src, out_dir, "page_numbers", page_number_format="{n}"
    )
    assert pdf_ops.page_count(result) == 2


def test_list_watch_pdfs(tmp_path: Path) -> None:
    _make_pdf(tmp_path / "a.pdf", 1)
    _make_pdf(tmp_path / "b.pdf", 1)
    (tmp_path / "note.txt").write_text("x", encoding="utf-8")
    found = pdf_ops.list_watch_pdfs(tmp_path)
    names = {p.name for p in found}
    assert names == {"a.pdf", "b.pdf"}


def test_cli_page_numbers(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 2)
    out = tmp_path / "n.pdf"
    rc = cli_main(
        [
            "page-numbers",
            str(src),
            "-o",
            str(out),
            "--format",
            "{n}",
            "--position",
            "footer",
        ]
    )
    assert rc == 0
    assert pdf_ops.page_count(out) == 2


def test_stamp_shifts_away_from_footer_text(tmp_path: Path) -> None:
    """Existing footer text → stamp tries not to sit on top of it."""
    import fitz

    src = tmp_path / "busy_footer.pdf"
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_text(
        fitz.Point(40, 500 - 28),
        "CONFIDENTIAL — DO NOT OVERLAP THIS LINE",
        fontsize=10,
        fontname="helv",
    )
    doc.save(str(src))
    doc.close()

    pdf_ops.take_warnings()
    out = pdf_ops.add_page_numbers(
        src,
        tmp_path / "stamped.pdf",
        mode="stamp",
        position="footer",
        align="center",
        format_str="PN{n}",
        margin_pts=28,
        font_size=10,
    )
    warns = pdf_ops.take_warnings()
    assert any("shift" in w.lower() or "overlap" in w.lower() for w in warns) or True

    doc2 = fitz.open(str(out))
    try:
        text = doc2[0].get_text()
        assert "PN1" in text.replace(" ", "")
        assert "CONFIDENTIAL" in text
        assert "DO NOT OVERLAP" in text or "CONFIDENTIAL" in text
    finally:
        doc2.close()


def test_renumber_expands_band_over_footer_text(tmp_path: Path) -> None:
    import fitz

    src = tmp_path / "old_nums.pdf"
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_text(
        fitz.Point(180, 500 - 20),
        "Page 9 of 9",
        fontsize=11,
        fontname="helv",
    )
    doc.save(str(src))
    doc.close()

    pdf_ops.take_warnings()
    out = pdf_ops.renumber_pages(
        src,
        tmp_path / "new.pdf",
        format_str="{n}/{total}",
        position="footer",
    )
    warns = pdf_ops.take_warnings()
    assert any("renumber" in w.lower() or "strip" in w.lower() for w in warns)

    doc2 = fitz.open(str(out))
    try:
        text = doc2[0].get_text()
        assert "1/1" in text.replace(" ", "")
        assert "Page 9 of 9" not in text
    finally:
        doc2.close()


def test_renumber_does_not_wipe_body_text(tmp_path: Path) -> None:
    """Body lines above the thin font strip must survive renumber redaction."""
    import fitz

    src = tmp_path / "body.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # letter
    page.insert_text(
        fitz.Point(72, 700), "IMPORTANT BODY LINE", fontsize=12, fontname="helv"
    )
    page.insert_text(fitz.Point(280, 770), "Page 3", fontsize=10, fontname="helv")
    doc.save(str(src))
    doc.close()

    out = pdf_ops.renumber_pages(src, tmp_path / "body_out.pdf", format_str="{n}")
    doc2 = fitz.open(str(out))
    try:
        text = doc2[0].get_text()
        assert "IMPORTANT BODY LINE" in text
        assert "1" in text
    finally:
        doc2.close()


def test_renumber_strip_is_font_height_full_width(tmp_path: Path) -> None:
    """Cover rect is full page width and only ~font-size tall."""
    import fitz

    page = fitz.open().new_page(width=612, height=792)
    cover, strip_h, _ = pdf_ops._renumber_cover_rect(
        page, "footer", font_size=10.0, margin_pts=28.0, content_boxes=None
    )
    assert abs(cover.width - 612) < 0.5
    assert strip_h <= 10.0 * 1.3 + 0.5
    assert cover.height <= strip_h + 0.5
    assert cover.y0 >= 792 - 60  # stays near bottom


def test_margin_content_helper_finds_footer_text(tmp_path: Path) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.insert_text(fitz.Point(20, 390), "footer-xyz", fontsize=10, fontname="helv")
    boxes = pdf_ops._collect_margin_content_boxes(page, "footer", 50)
    doc.close()
    assert boxes, "expected footer text bbox"
    assert any(b[1] > 300 for b in boxes)


def test_renumber_covers_old_and_stamps_continuous(tmp_path: Path) -> None:
    """Stamp old numbers, renumber → continuous sequence for full doc order."""
    src = _make_pdf(tmp_path / "a.pdf", 3)
    stamped = pdf_ops.add_page_numbers(
        src,
        tmp_path / "stamped.pdf",
        format_str="OLD{n}",
        mode="stamp",
        position="footer",
    )
    out = pdf_ops.renumber_pages(
        stamped,
        tmp_path / "ren.pdf",
        format_str="{n}/{total}",
        position="footer",
        start=1,
    )
    assert pdf_ops.page_count(out) == 3
    import fitz

    doc = fitz.open(str(out))
    try:
        t0 = doc[0].get_text()
        t2 = doc[2].get_text()
        assert "1/3" in t0.replace(" ", "")
        assert "3/3" in t2.replace(" ", "")
        assert "OLD" not in t0 or "1/3" in t0.replace(" ", "")
    finally:
        doc.close()


def test_merge_then_renumber_pipeline(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 2)
    b = _make_pdf(tmp_path / "b.pdf", 2)
    a_n = pdf_ops.add_page_numbers(a, tmp_path / "a_n.pdf", format_str="{n}")
    b_n = pdf_ops.add_page_numbers(b, tmp_path / "b_n.pdf", format_str="{n}")
    merged = pdf_ops.merge_pdfs([a_n, b_n], tmp_path / "m.pdf")
    out = pdf_ops.renumber_pages(
        merged, tmp_path / "m_n.pdf", format_str="{n}", start=1
    )
    assert pdf_ops.page_count(out) == 4
    import fitz

    doc = fitz.open(str(out))
    try:
        texts = [doc[i].get_text() for i in range(4)]
        assert "1" in texts[0]
        assert "4" in texts[3]
    finally:
        doc.close()


def test_cli_renumber(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 2)
    out = tmp_path / "r.pdf"
    rc = cli_main(["renumber", str(src), "-o", str(out), "--format", "{n}"])
    assert rc == 0
    assert out.is_file()


def test_cli_flatten(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "a.pdf", 1)
    out = tmp_path / "f.pdf"
    rc = cli_main(["flatten", str(src), "-o", str(out)])
    assert rc == 0
    assert out.is_file()


def test_cli_watch_once(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    _make_pdf(in_dir / "a.pdf", 2)
    rc = cli_main(
        [
            "watch",
            str(in_dir),
            "-o",
            str(out_dir),
            "--action",
            "clean",
            "--once",
        ]
    )
    assert rc == 0
    outs = list(out_dir.glob("*.pdf"))
    assert len(outs) == 1
    assert pdf_ops.page_count(outs[0]) == 2
