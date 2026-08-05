"""Leafkit command-line interface — offline, free forever.

All mutating commands go through jobs.run_job (log + warnings).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable

from leafkit import __app_name__, __version__
from leafkit import jobs
from leafkit import pdf_ops


def _run(
    op: str,
    fn: Callable[[], Any],
    *,
    inputs: list[Path] | None = None,
) -> int:
    try:
        jr = jobs.run_job(op, fn, inputs=list(inputs or []))
    except pdf_ops.PdfOpsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for w in jr.warnings:
        print(f"warning: {w}", file=sys.stderr)
    for p in jr.paths:
        print(p)
    if jr.duration_s >= 0.05:
        print(f"# {jr.duration_s:.2f}s", file=sys.stderr)
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    path = Path(args.input)
    try:
        n = pdf_ops.page_count(path, password=args.password)
    except pdf_ops.PdfOpsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    size = path.stat().st_size if path.is_file() else 0
    print(f"{path}")
    print(f"  pages: {n}")
    print(f"  size:  {size} bytes ({size // 1024} KB)")
    print(f"  leafkit: {__version__}")
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.inputs]
    do_rn = bool(getattr(args, "renumber", False))
    if args.output:
        out = Path(args.output)
    elif do_rn:
        out = pdf_ops.default_output_next_to(paths[0], "_merged_numbered")
    else:
        out = Path(paths[0]).with_name("merged.pdf")

    def work() -> Path:
        def produce(path: Path) -> Path:
            return pdf_ops.merge_pdfs(
                paths,
                path,
                password=args.password,
                preserve_bookmarks=args.bookmarks,
                page_size=args.page_size,
            )

        return pdf_ops.op_then_renumber(
            produce,
            out,
            do_renumber=do_rn,
            password=args.password,
        )

    return _run("merge", work, inputs=paths)


def _cmd_extract(args: argparse.Namespace) -> int:
    src = Path(args.input)
    do_rn = bool(getattr(args, "renumber", False))
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_extract_numbered" if do_rn else "_extract"
    )

    def work() -> Path:
        def produce(path: Path) -> Path:
            return pdf_ops.extract_pages(src, args.pages, path, password=args.password)

        return pdf_ops.op_then_renumber(
            produce,
            out,
            do_renumber=do_rn,
            password=args.password,
        )

    return _run("extract", work, inputs=[src])


def _cmd_split(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out_dir = Path(args.outdir) if args.outdir else src.parent / f"{src.stem}_split"
    do_rn = bool(getattr(args, "renumber", False))

    def work() -> list[Path]:
        paths = pdf_ops.split_pdf(
            src,
            args.mode,
            out_dir,
            every_n=args.n,
            at_pages=args.at_pages,
            max_mb=args.max_mb,
            bookmark_level=args.bookmark_level,
            password=args.password,
        )
        if not do_rn:
            return list(paths)
        out: list[Path] = []
        for p in paths:
            dest = pdf_ops.default_output_next_to(p, "_renumbered")
            out.append(
                pdf_ops.renumber_pages(
                    p, dest, format_str="{n} / {total}", password=args.password
                )
            )
        return out

    return _run("split", work, inputs=[src])


def _cmd_compress(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, f"_compressed_{args.preset}"
    )
    return _run(
        f"compress_{args.preset}",
        lambda: pdf_ops.compress_pdf(
            src,
            out,
            preset=args.preset,
            password=args.password,
            prefer_ghostscript=not args.no_ghostscript,
        ),
        inputs=[src],
    )


def _cmd_rotate(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, f"_rot{args.degrees}"
    )
    return _run(
        "rotate",
        lambda: pdf_ops.rotate_pages(
            src, args.degrees, out, page_spec=args.pages, password=args.password
        ),
        inputs=[src],
    )


def _cmd_delete(args: argparse.Namespace) -> int:
    src = Path(args.input)
    do_rn = bool(getattr(args, "renumber", False))
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_deleted_numbered" if do_rn else "_deleted"
    )

    def work() -> Path:
        def produce(path: Path) -> Path:
            return pdf_ops.delete_pages(src, args.pages, path, password=args.password)

        return pdf_ops.op_then_renumber(
            produce,
            out,
            do_renumber=do_rn,
            password=args.password,
        )

    return _run("delete", work, inputs=[src])


def _cmd_mix(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.inputs]
    do_rn = bool(getattr(args, "renumber", False))
    if args.output:
        out = Path(args.output)
    else:
        out = pdf_ops.default_output_next_to(
            paths[0], "_mixed_numbered" if do_rn else "_mixed"
        )

    def work() -> Path:
        def produce(path: Path) -> Path:
            return pdf_ops.mix_pdfs(
                paths,
                path,
                reverse_second=bool(args.reverse_second),
                password=args.password,
            )

        return pdf_ops.op_then_renumber(
            produce,
            out,
            do_renumber=do_rn,
            password=args.password,
        )

    return _run("mix", work, inputs=paths)


def _cmd_insert(args: argparse.Namespace) -> int:
    base = Path(args.base)
    ins = Path(args.insert)
    do_rn = bool(getattr(args, "renumber", False))
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        base, "_inserted_numbered" if do_rn else "_inserted"
    )

    def work() -> Path:
        def produce(path: Path) -> Path:
            return pdf_ops.insert_pages(
                base,
                ins,
                path,
                at_page=int(args.at_page),
                insert_spec=args.pages,
                password=args.password,
            )

        return pdf_ops.op_then_renumber(
            produce,
            out,
            do_renumber=do_rn,
            password=args.password,
        )

    return _run("insert", work, inputs=[base, ins])


def _cmd_images(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.inputs]
    if args.output:
        out = Path(args.output)
    else:
        out = paths[0].with_name(f"{paths[0].stem}_images.pdf")
        if len(paths) > 1:
            out = paths[0].parent / "images.pdf"
    return _run(
        "images_to_pdf",
        lambda: pdf_ops.images_to_pdf(paths, out),
        inputs=paths,
    )


def _cmd_assemble(args: argparse.Namespace) -> int:
    """Assemble pages: FILE:PAGE (1-based page) repeated, e.g. a.pdf:1 b.pdf:3."""
    specs: list[tuple[Path, int]] = []
    for raw in args.pagespecs:
        if ":" not in raw:
            print(
                f"error: assemble needs FILE:PAGE (1-based), got {raw!r}",
                file=sys.stderr,
            )
            return 1
        file_part, page_part = raw.rsplit(":", 1)
        try:
            page_1based = int(page_part)
        except ValueError:
            print(f"error: bad page number in {raw!r}", file=sys.stderr)
            return 1
        if page_1based < 1:
            print(f"error: page must be >= 1 in {raw!r}", file=sys.stderr)
            return 1
        specs.append((Path(file_part), page_1based - 1))

    if not specs:
        print("error: no pages specified", file=sys.stderr)
        return 1

    do_rn = bool(getattr(args, "renumber", False))
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        specs[0][0], "_assembled_numbered" if do_rn else "_assembled"
    )

    def work() -> Path:
        def produce(path: Path) -> Path:
            return pdf_ops.assemble_pages(specs, path, password=args.password)

        return pdf_ops.op_then_renumber(
            produce,
            out,
            do_renumber=do_rn,
            password=args.password,
        )

    return _run("assemble", work, inputs=[p for p, _ in specs])


def _cmd_crop(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_hardcrop" if args.hard else "_cropped"
    )
    margin_pts = float(args.inches) * 72.0
    return _run(
        "crop_hard" if args.hard else "crop",
        lambda: pdf_ops.crop_margins(
            src,
            out,
            margin_pts,
            page_spec=args.pages,
            hard=bool(args.hard),
            password=args.password,
        ),
        inputs=[src],
    )


def _cmd_crop_box(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_hardcrop_box" if args.hard else "_crop_box"
    )
    rect = (args.x0, args.y0, args.x1, args.y1)
    return _run(
        "crop_box_hard" if args.hard else "crop_box",
        lambda: pdf_ops.crop_box(
            src,
            out,
            rect,
            page_spec=args.pages,
            hard=bool(args.hard),
            password=args.password,
        ),
        inputs=[src],
    )


def _cmd_clean(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(src, "_cleaned")
    return _run(
        "clean",
        lambda: pdf_ops.clean_metadata(src, out, password=args.password),
        inputs=[src],
    )


def _cmd_encrypt(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(src, "_encrypted")
    return _run(
        "encrypt",
        lambda: pdf_ops.encrypt_pdf(
            src, out, args.user_password, password=args.password
        ),
        inputs=[src],
    )


def _cmd_decrypt(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_unlocked"
    )
    return _run(
        "decrypt",
        lambda: pdf_ops.decrypt_pdf(src, out, password=args.password),
        inputs=[src],
    )


def _cmd_resize(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, f"_resize_{args.page_size}"
    )
    return _run(
        "resize",
        lambda: pdf_ops.resize_pages(
            src,
            out,
            args.page_size,
            page_spec=args.pages,
            password=args.password,
        ),
        inputs=[src],
    )


def _cmd_reverse(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_reversed"
    )
    return _run(
        "reverse",
        lambda: pdf_ops.reverse_pages(src, out, password=args.password),
        inputs=[src],
    )


def _cmd_blank(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_blank"
    )
    return _run(
        "blank",
        lambda: pdf_ops.insert_blank_pages(
            src,
            out,
            at_page=int(args.at_page),
            count=int(args.count),
            size=args.size,
            password=args.password,
        ),
        inputs=[src],
    )


def _cmd_stamp_image(args: argparse.Namespace) -> int:
    src = Path(args.input)
    img = Path(args.image)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_stamped"
    )
    return _run(
        "stamp_image",
        lambda: pdf_ops.stamp_image(
            src,
            img,
            out,
            position=args.position,
            margin_pts=float(args.margin),
            scale=float(args.scale),
            opacity=float(args.opacity),
            page_spec=args.pages,
            password=args.password,
        ),
        inputs=[src],
    )


def _cmd_text(args: argparse.Namespace) -> int:
    src = Path(args.input)
    if args.stdout or not args.output:
        try:
            text = pdf_ops.extract_text(
                src, page_spec=args.pages, password=args.password
            )
        except pdf_ops.PdfOpsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        for w in pdf_ops.take_warnings():
            print(f"warning: {w}", file=sys.stderr)
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0
    out = Path(args.output)
    return _run(
        "extract_text",
        lambda: pdf_ops.extract_text_to_file(
            src, out, page_spec=args.pages, password=args.password
        ),
        inputs=[src],
    )


def _cmd_nup(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, f"_nup{args.n}"
    )
    return _run(
        "nup",
        lambda: pdf_ops.nup_pdf(src, out, n=args.n, password=args.password),
        inputs=[src],
    )


def _cmd_grayscale(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(src, "_gray")
    return _run(
        "grayscale",
        lambda: pdf_ops.grayscale_pdf(src, out, password=args.password),
        inputs=[src],
    )


def _cmd_page_numbers(args: argparse.Namespace) -> int:
    src = Path(args.input)
    renumber = bool(getattr(args, "renumber", False))
    mode = "renumber" if renumber else "stamp"
    default_suf = "_renumbered" if renumber else "_numbered"
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, default_suf
    )
    return _run(
        "renumber" if renumber else "page_numbers",
        lambda: pdf_ops.add_page_numbers(
            src,
            out,
            position=args.position,
            align=args.align,
            format_str=args.format,
            start=args.start,
            font_size=args.font_size,
            margin_pts=args.margin,
            page_spec=args.pages,
            mode=mode,
            band_height_pts=args.band_height,
            password=args.password,
        ),
        inputs=[src],
    )


def _cmd_renumber(args: argparse.Namespace) -> int:
    """Alias: renumber always covers band + stamps continuous numbers."""
    args.renumber = True
    return _cmd_page_numbers(args)


def _cmd_flatten(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else pdf_ops.default_output_next_to(
        src, "_flattened"
    )
    return _run(
        "flatten",
        lambda: pdf_ops.flatten_forms(
            src,
            out,
            annotations=not args.no_annots,
            widgets=not args.no_widgets,
            password=args.password,
        ),
        inputs=[src],
    )


def _cmd_watch(args: argparse.Namespace) -> int:
    """Poll a local folder and process new PDFs into an output folder."""
    import time

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    if not in_dir.is_dir():
        print(f"error: input folder not found: {in_dir}", file=sys.stderr)
        return 1
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create output folder: {exc}", file=sys.stderr)
        return 1

    interval = max(0.5, float(args.interval))
    once = bool(args.once)
    processed: set[str] = set()
    print(
        f"Watching {in_dir} → {out_dir}  action={args.action}  "
        f"interval={interval}s  (Ctrl+C to stop)",
        file=sys.stderr,
    )

    def _key(p: Path) -> str:
        try:
            st = p.stat()
            return f"{p.resolve()}|{st.st_size}|{st.st_mtime_ns}"
        except OSError:
            return str(p)

    try:
        while True:
            try:
                files = pdf_ops.list_watch_pdfs(in_dir)
            except pdf_ops.PdfOpsError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1

            for src in files:
                k = _key(src)
                if k in processed:
                    continue
                # Skip files still being written.
                try:
                    size1 = src.stat().st_size
                    time.sleep(0.15)
                    size2 = src.stat().st_size
                    if size1 != size2:
                        continue
                except OSError:
                    continue

                print(f"processing: {src.name}", file=sys.stderr)
                rc = _run(
                    f"watch_{args.action}",
                    lambda s=src: pdf_ops.watch_process_file(
                        s,
                        out_dir,
                        args.action,
                        compress_preset=args.preset,
                        page_number_format=args.format,
                        page_number_position=args.position,
                        page_number_align=args.align,
                        password=args.password,
                        prefer_ghostscript=not args.no_ghostscript,
                    ),
                    inputs=[src],
                )
                if rc == 0:
                    processed.add(k)
                else:
                    # Remember failures to avoid a tight retry loop.
                    processed.add(k)

            if once:
                return 0
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 0


def _cmd_gui(_args: argparse.Namespace) -> int:
    from leafkit.app import main as gui_main

    gui_main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="leafkit",
        description=f"{__app_name__} — offline PDF toolkit (free forever).",
    )
    p.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add_pwd(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--password", default=None, help="Password for encrypted input PDF")

    sp = sub.add_parser("info", help="Show page count and size")
    sp.add_argument("input")
    add_pwd(sp)
    sp.set_defaults(func=_cmd_info)

    sp = sub.add_parser("merge", help="Merge PDFs in order")
    sp.add_argument("inputs", nargs="+")
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument("--bookmarks", action="store_true")
    sp.add_argument("--page-size", choices=["a4", "letter", "legal"], default=None)
    sp.add_argument(
        "--renumber",
        action="store_true",
        help="After merge, cover footer band and stamp continuous page numbers",
    )
    add_pwd(sp)
    sp.set_defaults(func=_cmd_merge)

    sp = sub.add_parser("extract", help="Extract page range")
    sp.add_argument("input")
    sp.add_argument("--pages", required=True)
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument(
        "--renumber",
        action="store_true",
        help="After extract, renumber pages 1…N (fixed band cover)",
    )
    add_pwd(sp)
    sp.set_defaults(func=_cmd_extract)

    sp = sub.add_parser("split", help="Split a PDF")
    sp.add_argument("input")
    sp.add_argument(
        "--mode",
        default="each",
        choices=["each", "every_n", "at_pages", "even_odd", "size", "bookmarks"],
    )
    sp.add_argument("--n", type=int, default=2)
    sp.add_argument("--at-pages", default=None)
    sp.add_argument("--max-mb", type=float, default=2.0)
    sp.add_argument("--bookmark-level", type=int, default=1)
    sp.add_argument("-d", "--outdir", default=None)
    sp.add_argument(
        "--renumber",
        action="store_true",
        help="Renumber each output part (1…N per file)",
    )
    add_pwd(sp)
    sp.set_defaults(func=_cmd_split)

    sp = sub.add_parser("compress", help="Compress a PDF")
    sp.add_argument("input")
    sp.add_argument(
        "--preset",
        choices=["email", "balanced", "max", "scan"],
        default="balanced",
    )
    sp.add_argument("--no-ghostscript", action="store_true")
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_compress)

    sp = sub.add_parser("rotate", help="Rotate pages")
    sp.add_argument("input")
    sp.add_argument("--degrees", type=int, choices=[90, 180, 270], default=90)
    sp.add_argument("--pages", default=None)
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_rotate)

    sp = sub.add_parser("delete", help="Delete pages by range")
    sp.add_argument("input")
    sp.add_argument("--pages", required=True)
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument(
        "--renumber",
        action="store_true",
        help="After delete, renumber remaining pages 1…N",
    )
    add_pwd(sp)
    sp.set_defaults(func=_cmd_delete)

    sp = sub.add_parser(
        "mix",
        help="Alternate pages from PDFs (page1 of each, then page2…)",
    )
    sp.add_argument("inputs", nargs="+")
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument(
        "--reverse-second",
        action="store_true",
        help="Reverse page order of the second PDF (duplex scans)",
    )
    sp.add_argument(
        "--renumber",
        action="store_true",
        help="After mix, renumber continuous 1…N",
    )
    add_pwd(sp)
    sp.set_defaults(func=_cmd_mix)

    sp = sub.add_parser("insert", help="Insert pages from one PDF into another")
    sp.add_argument("base", help="Base PDF (destination)")
    sp.add_argument("insert", help="PDF to insert from")
    sp.add_argument(
        "--at-page",
        type=int,
        default=1,
        help="1-based insert-before page (1 = start)",
    )
    sp.add_argument(
        "--pages",
        default=None,
        help="Pages from insert PDF (1-based range; default = all)",
    )
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument(
        "--renumber",
        action="store_true",
        help="After insert, renumber continuous 1…N",
    )
    add_pwd(sp)
    sp.set_defaults(func=_cmd_insert)

    sp = sub.add_parser("images", help="Build a PDF from image files (PNG/JPEG/…)")
    sp.add_argument("inputs", nargs="+", help="Image paths in page order")
    sp.add_argument("-o", "--output", default=None)
    sp.set_defaults(func=_cmd_images)

    sp = sub.add_parser(
        "assemble",
        help="Build one PDF from FILE:PAGE specs (1-based pages)",
    )
    sp.add_argument(
        "pagespecs",
        nargs="+",
        help="e.g. a.pdf:1 b.pdf:3 a.pdf:2",
    )
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument(
        "--renumber",
        action="store_true",
        help="After assemble, renumber continuous 1…N",
    )
    add_pwd(sp)
    sp.set_defaults(func=_cmd_assemble)

    sp = sub.add_parser("crop", help="Crop margins (soft or hard)")
    sp.add_argument("input")
    sp.add_argument("--inches", type=float, default=0.5)
    sp.add_argument("--pages", default=None)
    sp.add_argument("--hard", action="store_true")
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_crop)

    sp = sub.add_parser(
        "crop-box",
        help="Crop to a PDF-point rectangle (bottom-left origin)",
    )
    sp.add_argument("input")
    sp.add_argument("--x0", type=float, required=True)
    sp.add_argument("--y0", type=float, required=True)
    sp.add_argument("--x1", type=float, required=True)
    sp.add_argument("--y1", type=float, required=True)
    sp.add_argument("--pages", default=None, help="Optional 1-based range")
    sp.add_argument("--hard", action="store_true", help="Discard content outside rect")
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_crop_box)

    sp = sub.add_parser("clean", help="Strip document metadata")
    sp.add_argument("input")
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_clean)

    sp = sub.add_parser("encrypt", help="Password-protect a PDF")
    sp.add_argument("input")
    sp.add_argument("--user-password", required=True)
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_encrypt)

    sp = sub.add_parser(
        "decrypt", help="Save unlocked PDF (strip password; needs open password)"
    )
    sp.add_argument("input")
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_decrypt)

    sp = sub.add_parser(
        "resize", help="Fit pages onto a4 / letter / legal"
    )
    sp.add_argument("input")
    sp.add_argument(
        "--page-size",
        required=True,
        choices=["a4", "letter", "legal"],
    )
    sp.add_argument("--pages", default=None, help="Optional 1-based range")
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_resize)

    sp = sub.add_parser("reverse", help="Reverse page order")
    sp.add_argument("input")
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_reverse)

    sp = sub.add_parser("blank", help="Insert blank page(s)")
    sp.add_argument("input")
    sp.add_argument(
        "--at-page",
        type=int,
        default=1,
        help="1-based insert-before page (1 = start)",
    )
    sp.add_argument("--count", type=int, default=1, help="Number of blank pages")
    sp.add_argument(
        "--size",
        choices=["a4", "letter", "legal"],
        default=None,
        help="Blank size (default = first page of input)",
    )
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_blank)

    sp = sub.add_parser(
        "stamp-image",
        help="Overlay an image on PDF pages (simple stamp)",
    )
    sp.add_argument("input")
    sp.add_argument("image", help="PNG/JPEG path")
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument(
        "--position",
        default="bottom-right",
        choices=[
            "center",
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
            "top",
            "bottom",
        ],
    )
    sp.add_argument(
        "--scale",
        type=float,
        default=0.25,
        help="Fraction of page width (default 0.25)",
    )
    sp.add_argument(
        "--margin",
        type=float,
        default=36.0,
        help="Margin from edges in PDF points",
    )
    sp.add_argument(
        "--opacity",
        type=float,
        default=1.0,
        help="0–1 (best-effort alpha)",
    )
    sp.add_argument("--pages", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_stamp_image)

    sp = sub.add_parser(
        "text",
        help="Extract selectable text (not OCR) to stdout or a .txt file",
    )
    sp.add_argument("input")
    sp.add_argument("-o", "--output", default=None, help="Write .txt file (else stdout)")
    sp.add_argument(
        "--stdout",
        action="store_true",
        help="Force write to stdout even if -o is set",
    )
    sp.add_argument("--pages", default=None, help="Optional 1-based page range")
    add_pwd(sp)
    sp.set_defaults(func=_cmd_text)

    sp = sub.add_parser("nup", help="N-up layout (2, 4, or 9)")
    sp.add_argument("input")
    sp.add_argument("-n", type=int, choices=[2, 4, 9], default=2)
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_nup)

    sp = sub.add_parser("grayscale", help="Convert pages to grayscale")
    sp.add_argument("input")
    sp.add_argument("-o", "--output", default=None)
    add_pwd(sp)
    sp.set_defaults(func=_cmd_grayscale)

    def _add_pagenum_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("input")
        sp.add_argument("-o", "--output", default=None)
        sp.add_argument(
            "--position", choices=["header", "footer"], default="footer"
        )
        sp.add_argument(
            "--align", choices=["left", "center", "right"], default="center"
        )
        sp.add_argument(
            "--format",
            default="{n} / {total}",
            help="Text template: {n} page number, {total} pages, {i} in range",
        )
        sp.add_argument("--start", type=int, default=1)
        sp.add_argument("--font-size", type=float, default=10.0)
        sp.add_argument(
            "--margin", type=float, default=28.0, help="Margin in PDF points"
        )
        sp.add_argument(
            "--band-height",
            type=float,
            default=None,
            help="Renumber only: height of white cover band (points)",
        )
        sp.add_argument("--pages", default=None, help="Optional page range")
        add_pwd(sp)

    sp = sub.add_parser(
        "page-numbers",
        help="Stamp header/footer page numbers (use --renumber to replace band)",
    )
    _add_pagenum_args(sp)
    sp.add_argument(
        "--renumber",
        action="store_true",
        help="Cover header/footer band then stamp continuous numbers (no OCR)",
    )
    sp.set_defaults(func=_cmd_page_numbers)

    sp = sub.add_parser(
        "renumber",
        help="Renumber: cover fixed band + stamp continuous 1…N (after merge/reorder)",
    )
    _add_pagenum_args(sp)
    sp.set_defaults(func=_cmd_renumber, renumber=True)

    sp = sub.add_parser(
        "flatten", help="Bake form fields/annotations into page content"
    )
    sp.add_argument("input")
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument(
        "--no-annots",
        action="store_true",
        help="Do not bake free annotations (only form widgets)",
    )
    sp.add_argument(
        "--no-widgets",
        action="store_true",
        help="Do not bake form fields (only annotations)",
    )
    add_pwd(sp)
    sp.set_defaults(func=_cmd_flatten)

    sp = sub.add_parser(
        "watch",
        help="Watch a local folder and batch-process new PDFs (offline)",
    )
    sp.add_argument("input", help="Input folder to watch")
    sp.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output folder for processed PDFs",
    )
    sp.add_argument(
        "--action",
        choices=sorted(pdf_ops.WATCH_ACTIONS),
        default="compress",
    )
    sp.add_argument(
        "--preset",
        choices=["email", "balanced", "max", "scan"],
        default="balanced",
        help="Compress preset when --action compress",
    )
    sp.add_argument(
        "--format",
        default="{n} / {total}",
        help="Page-number format when --action page_numbers",
    )
    sp.add_argument(
        "--position", choices=["header", "footer"], default="footer"
    )
    sp.add_argument(
        "--align", choices=["left", "center", "right"], default="center"
    )
    sp.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Poll interval seconds (default 2)",
    )
    sp.add_argument(
        "--once",
        action="store_true",
        help="Process current files once and exit (no loop)",
    )
    sp.add_argument("--no-ghostscript", action="store_true")
    add_pwd(sp)
    sp.set_defaults(func=_cmd_watch)

    sp = sub.add_parser("gui", help="Launch the desktop app")
    sp.set_defaults(func=_cmd_gui)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
