"""Batch runner for multi-file share ops."""

from __future__ import annotations

from pathlib import Path

from leafkit import batch as batch_ops
from leafkit import pdf_ops
from tests.fixtures import make_messy


def test_run_batch_files_success(tmp_path: Path) -> None:
    a = make_messy.blank(tmp_path / "a.pdf", 1)
    b = make_messy.blank(tmp_path / "b.pdf", 2)

    def work_one(src: Path) -> Path:
        out = tmp_path / f"{src.stem}_cleaned.pdf"
        return pdf_ops.clean_metadata(src, out)

    ok, errors = batch_ops.run_batch_files(
        [a, b], work_one, op="clean"
    )
    assert not errors
    assert len(ok) == 2
    assert all(p.is_file() for p in ok)
    assert pdf_ops.page_count(ok[0]) == 1
    assert pdf_ops.page_count(ok[1]) == 2


def test_run_batch_files_partial_error(tmp_path: Path) -> None:
    good = make_messy.blank(tmp_path / "good.pdf", 1)
    missing = tmp_path / "nope.pdf"

    def work_one(src: Path) -> Path:
        out = tmp_path / f"{src.stem}_out.pdf"
        return pdf_ops.clean_metadata(src, out)

    ok, errors = batch_ops.run_batch_files(
        [good, missing], work_one, op="clean"
    )
    assert len(ok) == 1
    assert len(errors) == 1
    assert "nope" in errors[0].lower() or "not found" in errors[0].lower() or "Could not" in errors[0] or "PDF" in errors[0]


def test_run_batch_cancel_between_files(tmp_path: Path) -> None:
    files = [make_messy.blank(tmp_path / f"f{i}.pdf", 1) for i in range(4)]
    calls: list[str] = []
    cancel_after = 2

    def work_one(src: Path) -> Path:
        calls.append(src.name)
        out = tmp_path / f"{src.stem}_c.pdf"
        return pdf_ops.clean_metadata(src, out)

    def cancel_check() -> bool:
        return len(calls) >= cancel_after

    ok, errors = batch_ops.run_batch_files(
        files,
        work_one,
        op="clean",
        cancel_check=cancel_check,
    )
    # cancel checked at start of each file; after 2 completed, 3rd sees cancel
    assert len(calls) == cancel_after
    assert len(ok) == cancel_after
    assert not errors


def test_run_batch_progress_callback(tmp_path: Path) -> None:
    files = [make_messy.blank(tmp_path / f"p{i}.pdf", 1) for i in range(2)]
    seen: list[tuple[int, int, str]] = []

    def work_one(src: Path) -> Path:
        return pdf_ops.clean_metadata(src, tmp_path / f"{src.stem}_x.pdf")

    def on_progress(n: int, total: int, src: Path) -> None:
        seen.append((n, total, src.name))

    ok, errors = batch_ops.run_batch_files(
        files, work_one, op="clean", on_progress=on_progress
    )
    assert len(ok) == 2
    assert not errors
    assert seen == [(1, 2, "p0.pdf"), (2, 2, "p1.pdf")]
