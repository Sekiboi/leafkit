"""Real-world exercise of every Sekikit operation using Desktop\\PDF Test.

Creates organized result folders and a RESULTS.md report. Offline only.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from sekikit import __version__, pdf_ops
from sekikit.cli import main as cli_main

# Override with SEKIKIT_PDF_TEST if Desktop layout differs on this machine.
SRC = Path(
    os.environ.get("SEKIKIT_PDF_TEST")
    or (Path.home() / "Desktop" / "PDF Test")
)
OUT = SRC / f"sekikit_real_test_v{__version__}"


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""
    ms: float = 0.0
    outputs: list[str] = field(default_factory=list)


RESULTS: list[Result] = []


def _note(name: str, ok: bool, detail: str = "", outputs: list[Path] | None = None, ms: float = 0.0) -> None:
    outs = [str(p) for p in (outputs or [])]
    RESULTS.append(Result(name=name, ok=ok, detail=detail, ms=ms, outputs=outs))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}  ({ms:.0f} ms)  {detail}")


def _run(
    name: str,
    fn,
    *expected_files: Path,
    password: str | None = None,
    expect_pdf: bool = True,
) -> None:
    t0 = time.perf_counter()
    try:
        out = fn()
        ms = (time.perf_counter() - t0) * 1000
        paths: list[Path] = []
        if out is None:
            paths = list(expected_files)
        elif isinstance(out, Path):
            paths = [out]
        elif isinstance(out, (list, tuple)):
            paths = [Path(p) for p in out]
        else:
            paths = list(expected_files)
        for p in paths:
            if not p.is_file():
                _note(name, False, f"missing output: {p}", paths, ms)
                return
            if not expect_pdf or p.suffix.lower() != ".pdf":
                continue
            try:
                n = pdf_ops.page_count(p, password=password)
                if n < 1:
                    _note(name, False, f"0 pages: {p.name}", paths, ms)
                    return
            except Exception as exc:  # noqa: BLE001
                _note(name, False, f"unreadable {p.name}: {exc}", paths, ms)
                return
        parts = []
        for p in paths:
            if expect_pdf and p.suffix.lower() == ".pdf":
                try:
                    parts.append(f"{p.name}({pdf_ops.page_count(p, password=password)}p)")
                except Exception:  # noqa: BLE001
                    parts.append(p.name)
            else:
                parts.append(p.name)
        detail = ", ".join(parts)
        warns = pdf_ops.take_warnings()
        if warns:
            detail += " | " + "; ".join(warns[:2])
        _note(name, True, detail, paths, ms)
    except Exception as exc:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000
        _note(name, False, f"{type(exc).__name__}: {exc}", ms=ms)
        traceback.print_exc()


def main() -> int:
    if not SRC.is_dir():
        print(f"Source folder not found: {SRC}")
        return 1

    pdfs = sorted(SRC.glob("*.pdf"))
    if len(pdfs) < 1:
        print("No PDFs in test folder.")
        return 1

    if OUT.exists():
        shutil.rmtree(OUT, ignore_errors=True)
    folders = {
        "00_info": OUT / "00_info",
        "01_merge": OUT / "01_merge",
        "02_mix": OUT / "02_mix",
        "03_extract": OUT / "03_extract",
        "04_delete": OUT / "04_delete",
        "05_insert": OUT / "05_insert",
        "06_split": OUT / "06_split",
        "07_rotate": OUT / "07_rotate",
        "08_reorder_assemble": OUT / "08_reorder_assemble",
        "09_compress": OUT / "09_compress",
        "10_clean": OUT / "10_clean",
        "11_encrypt": OUT / "11_encrypt",
        "12_crop": OUT / "12_crop",
        "13_nup": OUT / "13_nup",
        "14_grayscale": OUT / "14_grayscale",
        "15_page_numbers": OUT / "15_page_numbers",
        "16_renumber": OUT / "16_renumber",
        "17_flatten": OUT / "17_flatten",
        "18_images": OUT / "18_images",
        "19_stamp": OUT / "19_stamp",
        "20_watch": OUT / "20_watch",
        "21_cli": OUT / "21_cli",
        "22_pass1_5": OUT / "22_pass1_5",
    }
    for d in folders.values():
        d.mkdir(parents=True, exist_ok=True)

    a, b, c = pdfs[0], pdfs[min(1, len(pdfs) - 1)], pdfs[min(2, len(pdfs) - 1)]
    by_name = {p.name: p for p in pdfs}
    a = by_name.get("Prison App.pdf", a)
    b = by_name.get("VoterReg.pdf", b)
    c = by_name.get("Zoroastrianism.pdf", c)

    print(f"Sekikit v{__version__}")
    print(f"Source: {SRC}")
    print(f"Output: {OUT}")
    print(f"Inputs: {[p.name for p in pdfs]}")
    print("---")

    def info_all():
        lines = []
        for p in pdfs:
            n = pdf_ops.page_count(p)
            lines.append(f"{p.name}\tpages={n}\tsize_kb={p.stat().st_size // 1024}")
        report = folders["00_info"] / "page_counts.txt"
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return report

    _run("info (page_count all)", info_all, expect_pdf=False)

    merge_out = folders["01_merge"] / "merged_all.pdf"
    _run(
        "merge_pdfs (all 3)",
        lambda: pdf_ops.merge_pdfs([a, b, c], merge_out),
        merge_out,
    )
    merge_letter = folders["01_merge"] / "merged_letter.pdf"
    _run(
        "merge_pdfs (page_size=letter)",
        lambda: pdf_ops.merge_pdfs([a, b], merge_letter, page_size="letter"),
        merge_letter,
    )
    merge_bm = folders["01_merge"] / "merged_bookmarks.pdf"
    _run(
        "merge_pdfs (bookmarks)",
        lambda: pdf_ops.merge_pdfs([a, c], merge_bm, preserve_bookmarks=True),
        merge_bm,
    )
    merge_rn = folders["01_merge"] / "merged_renumbered.pdf"
    _run(
        "merge + renumber",
        lambda: (
            lambda m: pdf_ops.renumber_pages(m, merge_rn, format_str="{n} / {total}")
        )(pdf_ops.merge_pdfs([a, b], folders["01_merge"] / "merged_tmp.pdf")),
        merge_rn,
    )

    mix_out = folders["02_mix"] / "mixed.pdf"
    _run(
        "mix_pdfs",
        lambda: pdf_ops.mix_pdfs([a, c], mix_out),
        mix_out,
    )

    ex = folders["03_extract"] / "prison_p1-2.pdf"
    _run(
        "extract_pages 1-2",
        lambda: pdf_ops.extract_pages(a, "1-2", ex),
        ex,
    )

    de = folders["04_delete"] / "prison_del_p2.pdf"
    _run(
        "delete_pages page 2",
        lambda: pdf_ops.delete_pages(a, "2", de),
        de,
    )

    ins = folders["05_insert"] / "prison_insert_voter.pdf"
    _run(
        "insert_pages (voter into prison before p2)",
        lambda: pdf_ops.insert_pages(a, b, ins, at_page=2),
        ins,
    )

    split_dir = folders["06_split"] / "each"
    _run(
        "split_pdf mode=each",
        lambda: pdf_ops.split_pdf(a, "each", split_dir),
    )
    split_n = folders["06_split"] / "every_2"
    _run(
        "split_pdf mode=every_n n=2",
        lambda: pdf_ops.split_pdf(c, "every_n", split_n, every_n=2),
    )
    split_eo = folders["06_split"] / "even_odd"
    _run(
        "split_pdf mode=even_odd",
        lambda: pdf_ops.split_pdf(a, "even_odd", split_eo),
    )

    rot = folders["07_rotate"] / "prison_rot90.pdf"
    _run(
        "rotate_pages 90",
        lambda: pdf_ops.rotate_pages(a, 90, rot),
        rot,
    )
    rot2 = folders["07_rotate"] / "prison_rot180_p1.pdf"
    _run(
        "rotate_pages 180 pages=1",
        lambda: pdf_ops.rotate_pages(a, 180, rot2, page_spec="1"),
        rot2,
    )

    reo = folders["08_reorder_assemble"] / "prison_reordered.pdf"
    n_a = pdf_ops.page_count(a)
    order = list(reversed(range(n_a)))
    _run(
        "reorder_pages (reverse)",
        lambda: pdf_ops.reorder_pages(a, order, reo),
        reo,
    )
    asm = folders["08_reorder_assemble"] / "assembled_multi.pdf"
    items = [
        (a, n_a - 1),
        (b, 0),
        (c, 0),
        (a, 0),
    ]
    _run(
        "assemble_pages (multi-PDF tray)",
        lambda: pdf_ops.assemble_pages(items, asm),
        asm,
    )
    asm_rot = folders["08_reorder_assemble"] / "assembled_rot.pdf"
    _run(
        "assemble_pages (with rotation)",
        lambda: pdf_ops.assemble_pages(
            [(b, 0), (a, 0)], asm_rot, rotations={0: 90}
        ),
        asm_rot,
    )

    for preset in ("email", "balanced", "max"):
        outp = folders["09_compress"] / f"prison_{preset}.pdf"
        _run(
            f"compress_pdf preset={preset}",
            lambda o=outp, pr=preset: pdf_ops.compress_pdf(
                a, o, preset=pr, prefer_ghostscript=True
            ),
            outp,
        )
    scan_out = folders["09_compress"] / "voter_scan.pdf"
    _run(
        "compress_pdf preset=scan",
        lambda: pdf_ops.compress_pdf(b, scan_out, preset="scan", prefer_ghostscript=False),
        scan_out,
    )

    cl = folders["10_clean"] / "prison_cleaned.pdf"
    _run("clean_metadata", lambda: pdf_ops.clean_metadata(a, cl), cl)

    enc = folders["11_encrypt"] / "prison_encrypted.pdf"
    _run(
        "encrypt_pdf",
        lambda: pdf_ops.encrypt_pdf(a, enc, "test-pass-123"),
        enc,
        password="test-pass-123",
    )

    def check_enc():
        n = pdf_ops.page_count(enc, password="test-pass-123")
        path = folders["11_encrypt"] / "decrypt_ok.txt"
        path.write_text(f"pages_with_password={n}\n", encoding="utf-8")
        if n < 1:
            raise RuntimeError("encrypted open returned 0 pages")
        return path

    _run("encrypt open with password", check_enc, expect_pdf=False)

    soft = folders["12_crop"] / "prison_softcrop.pdf"
    _run(
        "crop_margins soft 0.25in",
        lambda: pdf_ops.crop_margins(a, soft, 0.25 * 72),
        soft,
    )
    hard = folders["12_crop"] / "prison_hardcrop.pdf"
    _run(
        "crop_margins hard 0.2in",
        lambda: pdf_ops.crop_margins(b, hard, 0.2 * 72, hard=True),
        hard,
    )

    nup2 = folders["13_nup"] / "prison_nup2.pdf"
    _run("nup_pdf n=2", lambda: pdf_ops.nup_pdf(a, nup2, n=2), nup2)
    nup4 = folders["13_nup"] / "prison_nup4.pdf"
    _run("nup_pdf n=4", lambda: pdf_ops.nup_pdf(a, nup4, n=4), nup4)

    gray = folders["14_grayscale"] / "voter_gray.pdf"
    _run("grayscale_pdf", lambda: pdf_ops.grayscale_pdf(b, gray), gray)

    pn = folders["15_page_numbers"] / "prison_numbered.pdf"
    _run(
        "add_page_numbers stamp",
        lambda: pdf_ops.add_page_numbers(
            a, pn, mode="stamp", format_str="{n} / {total}", position="footer"
        ),
        pn,
    )

    rn = folders["16_renumber"] / "merged_renumber.pdf"
    base_m = folders["01_merge"] / "merged_all.pdf"
    if base_m.is_file():
        _run(
            "renumber_pages",
            lambda: pdf_ops.renumber_pages(
                base_m, rn, format_str="{n} / {total}", font_size=10
            ),
            rn,
        )
    else:
        _note("renumber_pages", False, "merge output missing")

    flat = folders["17_flatten"] / "voter_flatten.pdf"
    _run("flatten_forms", lambda: pdf_ops.flatten_forms(b, flat), flat)

    img_dir = folders["18_images"]
    img1 = img_dir / "swatch1.png"
    img2 = img_dir / "swatch2.png"
    Image.new("RGB", (200, 120), (40, 120, 200)).save(img1)
    Image.new("RGB", (200, 120), (200, 80, 40)).save(img2)
    img_pdf = img_dir / "from_images.pdf"
    _run(
        "images_to_pdf",
        lambda: pdf_ops.images_to_pdf([img1, img2], img_pdf),
        img_pdf,
    )

    stamp_out = folders["19_stamp"] / "prison_stamped.pdf"
    _run(
        "stamp_image bottom-right",
        lambda: pdf_ops.stamp_image(
            a, img1, stamp_out, position="bottom-right", scale=0.15
        ),
        stamp_out,
    )

    p15 = folders["22_pass1_5"]
    unlocked = p15 / "unlocked.pdf"
    enc2 = p15 / "enc.pdf"
    _run(
        "encrypt then decrypt",
        lambda: (
            pdf_ops.encrypt_pdf(b, enc2, "test-pass-123"),
            pdf_ops.decrypt_pdf(enc2, unlocked, password="test-pass-123"),
        )[-1],
        unlocked,
    )
    resized = p15 / "resized_letter.pdf"
    _run(
        "resize_pages letter",
        lambda: pdf_ops.resize_pages(b, resized, "letter"),
        resized,
    )
    rev = p15 / "reversed.pdf"
    _run("reverse_pages", lambda: pdf_ops.reverse_pages(b, rev), rev)
    blanked = p15 / "blanked.pdf"
    _run(
        "insert_blank_pages",
        lambda: pdf_ops.insert_blank_pages(b, blanked, at_page=1, count=1),
        blanked,
    )
    box = p15 / "crop_box.pdf"
    _run(
        "crop_box soft",
        lambda: pdf_ops.crop_box(b, box, (36, 36, 400, 500), hard=False),
        box,
    )

    watch_in = folders["20_watch"] / "inbox"
    watch_out = folders["20_watch"] / "outbox"
    watch_in.mkdir(exist_ok=True)
    watch_out.mkdir(exist_ok=True)
    sample = watch_in / "sample.pdf"
    shutil.copy2(b, sample)

    def watch_once():
        rc = cli_main(
            [
                "watch",
                str(watch_in),
                "-o",
                str(watch_out),
                "--action",
                "clean",
                "--once",
            ]
        )
        if rc != 0:
            raise RuntimeError(f"watch exit {rc}")
        outs = list(watch_out.glob("*.pdf"))
        if not outs:
            raise RuntimeError("no watch output")
        return outs[0]

    _run("watch --once clean", watch_once)

    cli_info = folders["21_cli"] / "cli_info.txt"

    def cli_info_cmd():
        rc = cli_main(["info", str(a)])
        if rc != 0:
            raise RuntimeError(f"cli info rc={rc}")
        cli_info.write_text(f"cli info ok for {a.name}\n", encoding="utf-8")
        return cli_info

    _run("CLI info", cli_info_cmd, expect_pdf=False)

    cli_ex = folders["21_cli"] / "cli_extract.pdf"

    def cli_extract():
        rc = cli_main(["extract", str(c), "--pages", "1", "-o", str(cli_ex)])
        if rc != 0:
            raise RuntimeError(f"cli extract rc={rc}")
        return cli_ex

    _run("CLI extract", cli_extract, cli_ex)

    cli_pn = folders["21_cli"] / "cli_pagenum.pdf"

    def cli_pagenum():
        rc = cli_main(
            ["page-numbers", str(b), "-o", str(cli_pn), "--format", "{n}"]
        )
        if rc != 0:
            raise RuntimeError(f"cli page-numbers rc={rc}")
        return cli_pn

    _run("CLI page-numbers", cli_pagenum, cli_pn)

    passed = sum(1 for r in RESULTS if r.ok)
    failed = sum(1 for r in RESULTS if not r.ok)
    lines = [
        f"# Sekikit real-world test report",
        f"",
        f"- **Version:** {__version__}",
        f"- **When (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}",
        f"- **Source folder:** `{SRC}`",
        f"- **Results folder:** `{OUT}`",
        f"- **Inputs:** {', '.join(p.name for p in pdfs)}",
        f"- **Summary:** **{passed} passed**, **{failed} failed**, {len(RESULTS)} total",
        f"",
        f"| # | Operation | Result | Time | Detail |",
        f"|---|-----------|--------|------|--------|",
    ]
    for i, r in enumerate(RESULTS, 1):
        mark = "PASS" if r.ok else "**FAIL**"
        detail = r.detail.replace("|", "\\|")[:120]
        lines.append(f"| {i} | {r.name} | {mark} | {r.ms:.0f} ms | {detail} |")

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- All processing was local (offline).")
    lines.append("- Encrypt test password used: `test-pass-123` (results folder only).")
    lines.append("- Compress `scan` / grayscale re-render text to images (expected).")
    lines.append("- GUI-only surfaces (tooltips, review dialog, Organize DnD UI) use the same ops above.")
    lines.append("")

    report = OUT / "RESULTS.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "version": __version__,
        "passed": passed,
        "failed": failed,
        "total": len(RESULTS),
        "results": [
            {"name": r.name, "ok": r.ok, "ms": r.ms, "detail": r.detail}
            for r in RESULTS
        ],
    }
    (OUT / "RESULTS.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print("---")
    print(f"DONE: {passed}/{len(RESULTS)} passed, {failed} failed")
    print(f"Report: {report}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
