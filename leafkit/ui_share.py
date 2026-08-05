"""Share tab tools (mixin for LeafkitApp)."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from leafkit import __app_name__
from leafkit import batch as batch_ops
from leafkit import pdf_ops
from leafkit.i18n import _
from leafkit.ui_constants import PAGENUM_PRESETS as _PAGENUM_PRESETS


class ShareTabMixin:
    """Mixin: Share tab UI + share ops."""

    def _build_share_tab(self) -> None:
        tab = self.tabs.tab("Share")
        scroll = self._tab_scroll(tab)
        self.share_scroll = scroll

        head = ctk.CTkFrame(scroll, fg_color="transparent")
        head.pack(fill="x", pady=(2, 8), padx=4)
        ctk.CTkLabel(
            head,
            text=_("Share"),
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")
        self.share_batch_all = ctk.CTkCheckBox(head, text=_("All listed files"))
        self.share_batch_all.pack(side="right")
        self._tip(
            self.share_batch_all,
            "Run Compress / Clean / Encrypt / Unlock / Resize / Grayscale on every "
            "listed PDF. · Skips review. Esc cancels between files.",
        )

        inner = self._section(
            scroll,
            "Compress",
            "Shrink for email. email = smallest · balanced = safe · max = stronger · scan = photos.",
            anchor="compress",
        )
        rowc = ctk.CTkFrame(inner, fg_color="transparent")
        rowc.pack(fill="x")
        self.compress_preset = ctk.CTkSegmentedButton(
            rowc, values=["email", "balanced", "max", "scan"]
        )
        self.compress_preset.pack(side="left")
        self.compress_preset.set("balanced")
        self._tip(
            self.compress_preset,
            "email=small · balanced=safe · max=images · scan=re-render. "
            "· scan: text not selectable after.",
        )
        b = ctk.CTkButton(
            rowc, text=_("Compress…"), width=120, height=32, command=self._run_compress
        )
        b.pack(side="left", padx=12)
        self._tip(
            b,
            "Shrink selected PDF → new file. · Optional local Ghostscript if installed.",
        )
        gs = pdf_ops.find_ghostscript()
        gs_txt = (
            f"Ghostscript ready ({gs.name}) — used when it helps."
            if gs
            else "Built-in compressor (install Ghostscript for often-smaller files)."
        )
        ctk.CTkLabel(
            inner,
            text=gs_txt,
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", pady=(6, 0))

        inner = self._section(
            scroll,
            "Clean metadata",
            "Strip author, title, dates, and other document info before sharing.",
            anchor="clean",
        )
        b = ctk.CTkButton(
            inner, text=_("Clean metadata…"), width=150, height=32, command=self._run_clean
        )
        b.pack(side="left")
        self._tip(b, "Strip document info fields. · Content pages unchanged.")

        inner = self._section(
            scroll,
            "Encrypt",
            "Password-protect the PDF (AES-256 when available). Keep the password safe.",
            anchor="encrypt",
        )
        ctk.CTkLabel(inner, text=_("New password:")).pack(side="left")
        self.encrypt_pass = ctk.CTkEntry(inner, width=140, show="•")
        self.encrypt_pass.pack(side="left", padx=8)
        self._tip(self.encrypt_pass, "New open password. · Keep it safe — we cannot recover it.")
        ctk.CTkLabel(inner, text=_("Confirm:")).pack(side="left")
        self.encrypt_pass2 = ctk.CTkEntry(inner, width=140, show="•")
        self.encrypt_pass2.pack(side="left", padx=8)
        self._tip(self.encrypt_pass2, "Type the same password again.")
        b = ctk.CTkButton(
            inner, text=_("Encrypt…"), width=100, height=32, command=self._run_encrypt
        )
        b.pack(side="left", padx=8)
        self._tip(b, "Password-protect → new file. · AES when cryptography is installed.")
        b = ctk.CTkButton(
            inner,
            text=_("Save unlocked…"),
            width=120,
            height=32,
            fg_color="gray40",
            hover_color="gray30",
            command=self._run_decrypt,
        )
        b.pack(side="left", padx=8)
        self._tip(
            b,
            "Write a new PDF without password. · Needs open password if locked. "
            "Session only — keep unlocked files safe.",
        )

        inner = self._section(
            scroll,
            "Crop margins",
            "Inset every side by the same margin (inches). Optional page range.",
            anchor="crop",
        )
        ctk.CTkLabel(inner, text=_("Margin (in):")).pack(side="left")
        self.crop_inches = ctk.CTkEntry(inner, width=60)
        self.crop_inches.pack(side="left", padx=8)
        self.crop_inches.insert(0, "0.5")
        self._tip(self.crop_inches, "Margin in inches on every side.")
        ctk.CTkLabel(inner, text=_("Pages (blank=all):")).pack(side="left", padx=(8, 4))
        self.crop_pages = ctk.CTkEntry(inner, width=120, placeholder_text="e.g. 1-3")
        self.crop_pages.pack(side="left")
        self._tip(self.crop_pages, "Optional page range. Blank = all.")
        self.crop_hard = ctk.CTkCheckBox(inner, text=_("Hard crop (discard outside)"))
        self.crop_hard.pack(side="left", padx=12)
        self._tip(
            self.crop_hard,
            "Hard: permanently discards outside content. · Soft: boxes only; some viewers still show full page.",
        )
        b = ctk.CTkButton(
            inner, text=_("Crop…"), width=90, height=32, command=self._run_crop
        )
        b.pack(side="left", padx=8)
        self._tip(b, "Uniform margin crop → new file.")
        b = ctk.CTkButton(
            inner,
            text=_("Visual crop…"),
            width=110,
            height=32,
            fg_color="gray40",
            hover_color="gray30",
            command=self._run_visual_crop,
        )
        b.pack(side="left", padx=8)
        self._tip(
            b,
            "Drag a rectangle on a page preview. · Soft or hard. "
            "One rect for all/selected pages — not a print-shop trim tool.",
        )

        pn_box = ctk.CTkFrame(scroll, corner_radius=8)
        pn_box.pack(fill="x", pady=(0, 10), padx=4)
        self._register_nav_anchor("page_numbers", scroll, pn_box)
        ctk.CTkLabel(
            pn_box, text=_("Page numbers"), font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            pn_box,
            text=_(
                "Stamp = add numbers. Renumber = cover a header/footer band, then stamp "
                "continuous numbers for the current page order (after merge/reorder). "
                "No OCR — fixed band only."
            ),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
            wraplength=860,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 4))
        pn_mode = ctk.CTkFrame(pn_box, fg_color="transparent")
        pn_mode.pack(fill="x", padx=12, pady=(2, 4))
        ctk.CTkLabel(pn_mode, text=_("Mode:")).pack(side="left")
        self.pagenum_mode = ctk.CTkSegmentedButton(
            pn_mode, values=["stamp", "renumber"]
        )
        self.pagenum_mode.pack(side="left", padx=6)
        self.pagenum_mode.set("stamp")
        self._tip(
            self.pagenum_mode,
            "stamp = add # (avoids margin text when found). renumber = white band then #. "
            "· Checks PDF text/drawings in the band — not OCR; scans may still overlap.",
        )
        pn_inner = ctk.CTkFrame(pn_box, fg_color="transparent")
        pn_inner.pack(fill="x", padx=12, pady=(2, 4))
        ctk.CTkLabel(pn_inner, text=_("Style:")).pack(side="left")
        self.pagenum_preset = ctk.CTkSegmentedButton(
            pn_inner,
            values=list(_PAGENUM_PRESETS.keys()),
            command=self._on_pagenum_preset,
        )
        self.pagenum_preset.pack(side="left", padx=6)
        self.pagenum_preset.set("1 / N")
        self._tip(self.pagenum_preset, "Number style preset. Helvetica only — not a full designer.")
        ctk.CTkLabel(pn_inner, text=_("Where:")).pack(side="left", padx=(10, 0))
        self.pagenum_pos = ctk.CTkSegmentedButton(pn_inner, values=["footer", "header"])
        self.pagenum_pos.pack(side="left", padx=6)
        self.pagenum_pos.set("footer")
        self._tip(self.pagenum_pos, "Header or footer band.")
        ctk.CTkLabel(pn_inner, text=_("Align:")).pack(side="left", padx=(8, 0))
        self.pagenum_align = ctk.CTkSegmentedButton(
            pn_inner, values=["left", "center", "right"]
        )
        self.pagenum_align.pack(side="left", padx=6)
        self.pagenum_align.set("center")
        self._tip(self.pagenum_align, "Horizontal alignment.")
        row_pn = ctk.CTkFrame(pn_box, fg_color="transparent")
        row_pn.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(row_pn, text=_("Custom:")).pack(side="left")
        self.pagenum_format = ctk.CTkEntry(row_pn, width=130, placeholder_text="{n} / {total}")
        self.pagenum_format.pack(side="left", padx=6)
        self.pagenum_format.insert(0, "{n} / {total}")
        self.pagenum_format.configure(state="disabled")
        self._tip(self.pagenum_format, "Custom template. Placeholders: {n} {total} {i}.")
        ctk.CTkLabel(row_pn, text=_("Start:")).pack(side="left", padx=(8, 0))
        self.pagenum_start = ctk.CTkEntry(row_pn, width=48)
        self.pagenum_start.pack(side="left", padx=6)
        self.pagenum_start.insert(0, "1")
        self._tip(self.pagenum_start, "First page number (usually 1).")
        ctk.CTkLabel(row_pn, text=_("Pages:")).pack(side="left", padx=(8, 0))
        self.pagenum_pages = ctk.CTkEntry(row_pn, width=90, placeholder_text="all")
        self.pagenum_pages.pack(side="left", padx=6)
        self._tip(self.pagenum_pages, "Optional range. Blank = all pages.")
        b = ctk.CTkButton(
            row_pn,
            text=_("Apply page numbers…"),
            width=160,
            height=32,
            command=self._run_page_numbers,
        )
        b.pack(side="left", padx=8)
        self._tip(b, "Write stamped/renumbered PDF. · Not a full header/footer editor.")

        self.share_more_btn = ctk.CTkButton(
            scroll,
            text=_("More tools  ▸  resize · stamp · text · images · …"),
            height=32,
            fg_color=("gray85", "gray28"),
            text_color=("gray15", "gray90"),
            hover_color=("gray75", "gray35"),
            command=self._toggle_share_more,
        )
        self.share_more_btn.pack(fill="x", padx=4, pady=(4, 8))
        self._tip(self.share_more_btn, "Show or hide less-used share tools.")

        self.share_more = ctk.CTkFrame(scroll, fg_color="transparent")

        inner = self._section(
            self.share_more,
            "Resize pages",
            "Fit every page onto a standard paper size (same as merge fit — may add margin).",
            anchor="resize",
        )
        self.resize_size = ctk.CTkSegmentedButton(
            inner, values=["a4", "letter", "legal"]
        )
        self.resize_size.pack(side="left")
        self.resize_size.set("letter")
        self._tip(self.resize_size, "Target paper size.")
        b = ctk.CTkButton(
            inner, text=_("Resize…"), width=100, height=32, command=self._run_resize
        )
        b.pack(side="left", padx=12)
        self._tip(b, "Fit pages → new PDF. · Not crop-to-fill.")

        inner = self._section(
            self.share_more,
            "Reverse pages",
            "Write the selected PDF with page order reversed.",
            anchor="reverse",
        )
        b = ctk.CTkButton(
            inner, text=_("Reverse…"), width=100, height=32, command=self._run_reverse
        )
        b.pack(side="left")
        self._tip(b, "Last page becomes first → new file.")

        inner = self._section(
            self.share_more,
            "Stamp image",
            "Overlay a PNG/JPEG on pages (logo stamp). Not a full watermark studio.",
            anchor="stamp",
        )
        self.stamp_pos = ctk.CTkSegmentedButton(
            inner,
            values=["bottom-right", "bottom-left", "top-right", "top-left", "center"],
        )
        self.stamp_pos.pack(side="left")
        self.stamp_pos.set("bottom-right")
        self._tip(self.stamp_pos, "Where to place the image on each page.")
        ctk.CTkLabel(inner, text=_("Scale:")).pack(side="left", padx=(10, 2))
        self.stamp_scale = ctk.CTkEntry(inner, width=48)
        self.stamp_scale.pack(side="left")
        self.stamp_scale.insert(0, "0.2")
        self._tip(self.stamp_scale, "Fraction of page width (0.05–1).")
        b = ctk.CTkButton(
            inner, text=_("Stamp image…"), width=120, height=32, command=self._run_stamp_image
        )
        b.pack(side="left", padx=12)
        self._tip(
            b,
            "Pick an image and stamp onto the selected PDF → new file. "
            "· One image, one position — not tiled watermarks.",
        )

        inner = self._section(
            self.share_more,
            "Extract text",
            "Copy selectable text from the selected PDF. Not OCR — scans often return nothing.",
            anchor="extract_text",
        )
        b = ctk.CTkButton(
            inner, text=_("Copy text…"), width=110, height=32, command=self._run_copy_text
        )
        b.pack(side="left")
        self._tip(
            b,
            "Extract text to clipboard. · Image-only pages need OCR (not supported).",
        )
        b = ctk.CTkButton(
            inner,
            text=_("Save .txt…"),
            width=100,
            height=32,
            command=self._run_save_text,
            fg_color="gray40",
        )
        b.pack(side="left", padx=8)
        self._tip(b, "Write UTF-8 text file next to the PDF.")

        inner = self._section(
            self.share_more,
            "Images → PDF",
            "Build a PDF from PNG/JPEG/WebP images (one page per image, list order).",
            anchor="images",
        )
        b = ctk.CTkButton(
            inner, text=_("Add images…"), width=110, height=32, command=self._add_images
        )
        b.pack(side="left")
        self._tip(b, "Add PNG/JPEG/WebP images.")
        b = ctk.CTkButton(
            inner,
            text=_("Clear"),
            width=70,
            height=32,
            command=self._clear_images,
            fg_color="gray40",
        )
        b.pack(side="left", padx=6)
        self._tip(b, "Clear image list.")
        b = ctk.CTkButton(
            inner, text=_("Make PDF…"), width=100, height=32, command=self._run_images_pdf
        )
        b.pack(side="left", padx=6)
        self._tip(b, "One page per image → PDF. · Not OCR.")
        self.images_label = ctk.CTkLabel(
            self.share_more,
            text=_("(no images selected)"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        )
        self.images_label.pack(anchor="w", padx=16, pady=(0, 8))

        inner = self._section(
            self.share_more,
            "N-up",
            "Place 2, 4, or 9 pages on each sheet (handouts / save paper).",
            anchor="nup",
        )
        self.nup_n = ctk.CTkSegmentedButton(inner, values=["2", "4", "9"])
        self.nup_n.pack(side="left")
        self.nup_n.set("2")
        self._tip(self.nup_n, "Pages per sheet.")
        b = ctk.CTkButton(
            inner, text=_("N-up…"), width=100, height=32, command=self._run_nup
        )
        b.pack(side="left", padx=12)
        self._tip(b, "Layout pages on sheets → new PDF.")

        inner = self._section(
            self.share_more,
            "Grayscale",
            "Convert all pages to grayscale (re-render; good for B&W print/email).",
            anchor="grayscale",
        )
        b = ctk.CTkButton(
            inner, text=_("Grayscale…"), width=120, height=32, command=self._run_grayscale
        )
        b.pack(side="left")
        self._tip(
            b,
            "Re-render as gray images. · Text will not stay selectable/searchable.",
        )

        inner = self._section(
            self.share_more,
            "Flatten forms",
            "Bake filled form fields (and annotations) into static page content.",
            anchor="flatten",
        )
        self.flatten_widgets = ctk.CTkCheckBox(inner, text=_("Form fields"))
        self.flatten_widgets.pack(side="left")
        self.flatten_widgets.select()
        self._tip(self.flatten_widgets, "Bake form field appearances.")
        self.flatten_annots = ctk.CTkCheckBox(inner, text=_("Annotations"))
        self.flatten_annots.pack(side="left", padx=12)
        self.flatten_annots.select()
        self._tip(self.flatten_annots, "Bake free annotations.")
        b = ctk.CTkButton(
            inner, text=_("Flatten…"), width=100, height=32, command=self._run_flatten
        )
        b.pack(side="left", padx=8)
        self._tip(
            b,
            "Bake fields into static content. · Fields no longer editable. Not a form designer.",
        )

        ctk.CTkLabel(scroll, text="").pack(pady=4)
    def _toggle_share_more(self) -> None:
        self._share_more_open = not self._share_more_open
        if self._share_more_open:
            self.share_more.pack(fill="x", after=self.share_more_btn)
            self.share_more_btn.configure(
                text=_("More tools  ▾  resize · stamp · text · images · …")
            )
        else:
            self.share_more.pack_forget()
            self.share_more_btn.configure(
                text=_("More tools  ▸  resize · stamp · text · images · …")
            )
    def _on_pagenum_preset(self, value: str) -> None:
        tmpl = _PAGENUM_PRESETS.get(value, "")
        if value == "Custom" or not tmpl:
            self.pagenum_format.configure(state="normal")
            if not self.pagenum_format.get().strip():
                self.pagenum_format.delete(0, "end")
                self.pagenum_format.insert(0, "{n} / {total}")
        else:
            self.pagenum_format.configure(state="normal")
            self.pagenum_format.delete(0, "end")
            self.pagenum_format.insert(0, tmpl)
            self.pagenum_format.configure(state="disabled")

    def _share_batch_enabled(self) -> bool:
        box = getattr(self, "share_batch_all", None)
        try:
            return bool(box.get()) if box is not None else False
        except Exception:  # noqa: BLE001
            return False

    def _share_targets(self) -> list[Path] | None:
        """Selected file, or all listed when batch is on. None if user cancelled."""
        if self._share_batch_enabled():
            if not self._files:
                messagebox.showinfo(
                    __app_name__,
                    "Add at least one PDF first.\n\nDrop files here or click Add PDFs…",
                )
                return None
            return list(self._files)
        src = self._require_selected()
        if src is None:
            return None
        return [src]

    def _run_share_batch(
        self,
        files: list[Path],
        work_one: Callable[[Path], Path],
        *,
        label: str,
        op: str,
        verb: str,
        validate_password: str | None = None,
    ) -> None:
        """Run work_one on each file; skip review; Esc cancels between files."""
        if self._busy:
            return
        if len(files) == 1:
            src = files[0]

            def work() -> Path:
                return work_one(src)

            self._run_bg(
                work,
                lambda p: self._ok_file(p, verb),
                label,
                op=op,
                inputs=[src],
                validate_password=validate_password,
            )
            return

        self._cancel_job = False
        self._job_warnings = []

        def runner() -> None:
            self.after(0, lambda: self._set_busy(True))

            def on_progress(n: int, total: int, src: Path) -> None:
                self.after(
                    0,
                    lambda: self._set_status(
                        f"{label} {n}/{total}: {src.name}… (Esc to cancel)"
                    ),
                )

            ok, errors = batch_ops.run_batch_files(
                files,
                work_one,
                op=op,
                cancel_check=lambda: self._cancel_job,
                validate_password=validate_password,
                on_progress=on_progress,
            )

            def done() -> None:
                self._set_busy(False)
                cancelled = bool(self._cancel_job) and len(ok) + len(errors) < len(
                    files
                )
                if ok:
                    self._remember(ok)
                    folder = ok[0].parent
                    note_parts: list[str] = []
                    if errors:
                        note_parts.append(f"{len(errors)} failed")
                    if cancelled:
                        note_parts.append("cancelled early")
                    note = " · ".join(note_parts)
                    self._set_status(
                        f"{verb}: {len(ok)} file(s)"
                        + (f" · {note}" if note else "")
                    )
                    self._show_toast(
                        verb,
                        f"{len(ok)} file(s) → {folder.name}",
                        folder=folder,
                        note=note,
                    )
                    if errors:
                        messagebox.showwarning(
                            __app_name__,
                            f"{len(ok)} succeeded, {len(errors)} failed:\n\n"
                            + "\n".join(errors[:10]),
                        )
                elif errors:
                    self._fail("\n".join(errors[:12]))
                else:
                    self._set_status("Cancelled — no files written.")

            self.after(0, done)

        threading.Thread(target=runner, daemon=True).start()

    def _run_compress(self) -> None:
        targets = self._share_targets()
        if targets is None:
            return
        preset = self.compress_preset.get()
        if preset == "scan":
            if not messagebox.askyesno(
                __app_name__,
                "Scan compress re-renders every page as an image.\n\n"
                "• Much smaller for photos/scans\n"
                "• Text will no longer be selectable/searchable\n\n"
                "Continue?",
            ):
                return
        pwd = self._password()

        def work_one(src: Path) -> Path:
            out = pdf_ops.default_output_next_to(src, f"_compressed_{preset}")

            def progress(msg: str) -> None:
                self.after(0, lambda m=msg: self._set_status(m))

            return pdf_ops.compress_pdf(
                src,
                out,
                preset=preset,
                password=pwd,
                prefer_ghostscript=True,
                progress=progress if len(targets) == 1 else None,
                cancel_check=lambda: self._cancel_job,
            )

        if len(targets) == 1:
            src = targets[0]

            def on_ok(p: Path) -> None:
                warns = list(getattr(self, "_job_warnings", []) or []) + pdf_ops.take_warnings()
                try:
                    before = src.stat().st_size
                    after = p.stat().st_size
                    pct = (1 - after / before) * 100 if before else 0
                    note = " · ".join(warns) if warns else ""
                    detail = (
                        f"{before // 1024} KB → {after // 1024} KB "
                        f"({pct:.0f}% smaller) · {p.name}"
                    )
                    self._remember(p)
                    self._set_status(
                        f"Compressed: {before // 1024} KB → {after // 1024} KB "
                        f"({pct:.0f}% smaller)"
                    )
                    self._show_toast(
                        f"Compressed ({preset})", detail, path=p, note=note
                    )
                except Exception:  # noqa: BLE001
                    self._ok_file(p, "Compressed")

            self._run_bg(
                lambda: work_one(src),
                on_ok,
                "Compressing",
                op=f"compress_{preset}",
                inputs=[src],
            )
            return

        self._run_share_batch(
            targets,
            work_one,
            label="Compressing",
            op=f"compress_{preset}",
            verb=f"Compressed ({preset})",
        )

    def _run_clean(self) -> None:
        targets = self._share_targets()
        if targets is None:
            return
        kw = self._pwd_kwargs()

        def work_one(src: Path) -> Path:
            out = pdf_ops.default_output_next_to(src, "_cleaned")
            return pdf_ops.clean_metadata(src, out, **kw)

        self._run_share_batch(
            targets,
            work_one,
            label="Cleaning",
            op="clean",
            verb="Metadata cleaned",
        )

    def _run_encrypt(self) -> None:
        targets = self._share_targets()
        if targets is None:
            return
        p1 = self.encrypt_pass.get()
        p2 = self.encrypt_pass2.get()
        if not p1:
            messagebox.showerror(__app_name__, "Enter a password.")
            return
        if p1 != p2:
            messagebox.showerror(__app_name__, "Passwords do not match.")
            return
        if len(targets) > 1 and not messagebox.askyesno(
            __app_name__,
            f"Encrypt {len(targets)} PDFs with the same password?\n\n"
            "Each file becomes a new *_encrypted.pdf.",
        ):
            return
        kw = self._pwd_kwargs()

        def work_one(src: Path) -> Path:
            out = pdf_ops.default_output_next_to(src, "_encrypted")
            return pdf_ops.encrypt_pdf(src, out, p1, **kw)

        self._run_share_batch(
            targets,
            work_one,
            label="Encrypting",
            op="encrypt",
            verb="Encrypted",
            validate_password=p1,
        )

    def _run_decrypt(self) -> None:
        targets = self._share_targets()
        if targets is None:
            return
        kw = self._pwd_kwargs()

        def work_one(src: Path) -> Path:
            out = pdf_ops.default_output_next_to(src, "_unlocked")
            return pdf_ops.decrypt_pdf(src, out, **kw)

        self._run_share_batch(
            targets,
            work_one,
            label="Saving unlocked",
            op="decrypt",
            verb="Unlocked",
        )

    def _run_resize(self) -> None:
        targets = self._share_targets()
        if targets is None:
            return
        size = self.resize_size.get() or "letter"
        kw = self._pwd_kwargs()

        def work_one(src: Path) -> Path:
            out = pdf_ops.default_output_next_to(src, f"_resize_{size}")
            return pdf_ops.resize_pages(src, out, size, **kw)

        self._run_share_batch(
            targets,
            work_one,
            label="Resizing",
            op="resize",
            verb="Resized",
        )

    def _run_reverse(self) -> None:
        targets = self._share_targets()
        if targets is None:
            return
        kw = self._pwd_kwargs()

        def work_one(src: Path) -> Path:
            out = pdf_ops.default_output_next_to(src, "_reversed")
            return pdf_ops.reverse_pages(src, out, **kw)

        self._run_share_batch(
            targets,
            work_one,
            label="Reversing",
            op="reverse",
            verb="Reversed",
        )

    def _run_stamp_image(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        img = filedialog.askopenfilename(
            title="Image to stamp",
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not img:
            return
        try:
            scale = float(self.stamp_scale.get().strip() or "0.2")
        except ValueError:
            messagebox.showerror(__app_name__, "Scale must be a number (e.g. 0.2).")
            return
        pos = self.stamp_pos.get() or "bottom-right"
        out = pdf_ops.default_output_next_to(src, "_stamped")
        kw = self._pwd_kwargs()
        img_path = Path(img)

        def work():
            return pdf_ops.stamp_image(
                src,
                img_path,
                out,
                position=pos,
                scale=scale,
                **kw,
            )

        self._run_bg(
            work,
            lambda p: self._ok_file(p, "Stamped"),
            "Stamping image",
            op="stamp_image",
            inputs=[src],
        )

    def _run_copy_text(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        kw = self._pwd_kwargs()

        def work() -> str:
            return pdf_ops.extract_text(src, **kw)

        def on_ok(text: object) -> None:
            raw = str(text or "")
            warns = list(getattr(self, "_job_warnings", []) or []) + pdf_ops.take_warnings()
            try:
                self.clipboard_clear()
                self.clipboard_append(raw)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(__app_name__, f"Could not copy to clipboard:\n{exc}")
                return
            n = len(raw)
            note = " · ".join(warns) if warns else ""
            if n < 1:
                self._set_status("No selectable text found.")
                messagebox.showinfo(
                    __app_name__,
                    "No selectable text found.\n\n"
                    "Scanned/image-only PDFs need OCR, which Leafkit does not do.",
                )
            else:
                self._set_status(f"Copied {n} characters of text.")
                self._show_toast(
                    "Text copied",
                    f"{n} characters from {src.name}",
                    note=note,
                )

        self._run_bg(
            work,
            on_ok,
            "Extracting text",
            op="extract_text",
            inputs=[src],
            review=False,
        )

    def _run_save_text(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        out = src.with_name(f"{src.stem}.txt")
        kw = self._pwd_kwargs()

        def work() -> Path:
            return pdf_ops.extract_text_to_file(src, out, **kw)

        self._run_bg(
            work,
            lambda p: self._ok_file(p, "Text saved"),
            "Extracting text",
            op="extract_text",
            inputs=[src],
            review=False,
        )

    def _run_crop(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        try:
            inches = float(self.crop_inches.get().strip())
        except ValueError:
            messagebox.showerror(__app_name__, "Margin must be a number (inches).")
            return
        margin_pts = inches * 72.0
        page_spec = self.crop_pages.get().strip() or None
        hard = bool(self.crop_hard.get())
        if hard and not messagebox.askyesno(
            __app_name__,
            "Hard crop permanently discards content outside the margins.\n\nContinue?",
        ):
            return
        suffix = "_hardcrop" if hard else "_cropped"
        out = pdf_ops.default_output_next_to(src, suffix)
        kw = self._pwd_kwargs()

        def work():
            return pdf_ops.crop_margins(
                src, out, margin_pts, page_spec=page_spec, hard=hard, **kw
            )

        self._run_bg(
            work,
            lambda p: self._ok_file(p, "Hard cropped" if hard else "Cropped"),
            "Cropping",
            op="crop_hard" if hard else "crop",
            inputs=[src],
        )

    def _run_visual_crop(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        from leafkit import crop_ui

        choice = crop_ui.run_crop_dialog(self, src, password=self._password())
        if choice is None:
            self._set_status("Visual crop cancelled.")
            return
        rect = choice["rect"]
        hard = bool(choice["hard"])
        apply_all = bool(choice["apply_all"])
        page_i = int(choice["page_index"])
        if hard and not messagebox.askyesno(
            __app_name__,
            "Hard crop permanently discards content outside the rectangle.\n\nContinue?",
        ):
            return
        page_spec = None if apply_all else str(page_i + 1)
        suffix = "_hardcrop_box" if hard else "_crop_box"
        out = pdf_ops.default_output_next_to(src, suffix)
        kw = self._pwd_kwargs()

        def work():
            return pdf_ops.crop_box(
                src, out, rect, page_spec=page_spec, hard=hard, **kw
            )

        self._run_bg(
            work,
            lambda p: self._ok_file(p, "Hard cropped" if hard else "Cropped"),
            "Cropping",
            op="crop_box_hard" if hard else "crop_box",
            inputs=[src],
        )
    def _add_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff"),
                ("All files", "*.*"),
            ],
        )
        for raw in paths:
            p = Path(raw)
            if p not in self._image_files:
                self._image_files.append(p)
        self._refresh_images_label()
    def _clear_images(self) -> None:
        self._image_files.clear()
        self._refresh_images_label()
    def _refresh_images_label(self) -> None:
        if not self._image_files:
            self.images_label.configure(text=_("(no images)"))
        else:
            names = ", ".join(p.name for p in self._image_files[:6])
            extra = f" +{len(self._image_files) - 6} more" if len(self._image_files) > 6 else ""
            self.images_label.configure(text=f"{len(self._image_files)} file(s): {names}{extra}")
    def _run_images_pdf(self) -> None:
        if not self._image_files:
            messagebox.showinfo(__app_name__, "Add images first.")
            return
        first = self._image_files[0]
        out = first.with_name(f"{first.stem}_from_images.pdf")
        imgs = list(self._image_files)

        def work():
            return pdf_ops.images_to_pdf(imgs, out)

        self._run_bg(work, lambda p: self._ok_file(p, "Images→PDF"), "Building PDF")
    def _run_nup(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        try:
            n = int(self.nup_n.get())
        except (TypeError, ValueError):
            messagebox.showerror(__app_name__, "Pick 2, 4, or 9.")
            return
        out = pdf_ops.default_output_next_to(src, f"_nup{n}")
        pwd = self._password()

        def work():
            return pdf_ops.nup_pdf(src, out, n=n, password=pwd)

        self._run_bg(work, lambda p: self._ok_file(p, f"N-up ({n})"), "N-up")
    def _run_grayscale(self) -> None:
        targets = self._share_targets()
        if targets is None:
            return
        if not messagebox.askyesno(
            __app_name__,
            "Grayscale re-renders pages as images.\n\n"
            "Text will no longer be selectable/searchable.\n\n"
            + (
                f"This will process {len(targets)} file(s).\n\n"
                if len(targets) > 1
                else ""
            )
            + "Continue?",
        ):
            return
        pwd = self._password()

        def work_one(src: Path) -> Path:
            out = pdf_ops.default_output_next_to(src, "_gray")
            return pdf_ops.grayscale_pdf(
                src,
                out,
                password=pwd,
                cancel_check=lambda: self._cancel_job,
            )

        self._run_share_batch(
            targets,
            work_one,
            label="Grayscale",
            op="grayscale",
            verb="Grayscale",
        )
    def _run_page_numbers(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        mode = (self.pagenum_mode.get() or "stamp").strip().lower()
        if mode not in ("stamp", "renumber"):
            mode = "stamp"
        if mode == "renumber" and not messagebox.askyesno(
            __app_name__,
            "Renumber covers a fixed header/footer strip with white, "
            "then stamps continuous numbers for the current page order.\n\n"
            "It does not search the page with OCR. Anything in that band may be hidden.\n\n"
            "Continue?",
        ):
            return
        preset = self.pagenum_preset.get()
        tmpl = _PAGENUM_PRESETS.get(preset, "")
        if preset == "Custom" or not tmpl:
            self.pagenum_format.configure(state="normal")
            fmt = self.pagenum_format.get().strip() or "{n} / {total}"
        else:
            fmt = tmpl
        try:
            start = int(self.pagenum_start.get().strip() or "1")
        except ValueError:
            messagebox.showerror(__app_name__, "Start must be an integer.")
            return
        page_spec = self.pagenum_pages.get().strip() or None
        pos = self.pagenum_pos.get()
        align = self.pagenum_align.get()
        suffix = "_renumbered" if mode == "renumber" else "_numbered"
        out = pdf_ops.default_output_next_to(src, suffix)
        kw = self._pwd_kwargs()

        def work():
            return pdf_ops.add_page_numbers(
                src,
                out,
                position=pos,
                align=align,
                format_str=fmt,
                start=start,
                page_spec=page_spec,
                mode=mode,
                **kw,
            )

        verb = "Renumbered" if mode == "renumber" else "Page numbers"
        self._run_bg(
            work,
            lambda p: self._ok_file(p, verb),
            verb,
            op="renumber" if mode == "renumber" else "page_numbers",
            inputs=[src],
        )
    def _run_flatten(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        widgets = bool(self.flatten_widgets.get())
        annots = bool(self.flatten_annots.get())
        if not widgets and not annots:
            messagebox.showerror(
                __app_name__, "Enable form fields and/or annotations."
            )
            return
        if not messagebox.askyesno(
            __app_name__,
            "Flatten bakes form fields into permanent content.\n"
            "Fields will no longer be editable.\n\nContinue?",
        ):
            return
        out = pdf_ops.default_output_next_to(src, "_flattened")
        kw = self._pwd_kwargs()

        def work():
            return pdf_ops.flatten_forms(
                src, out, annotations=annots, widgets=widgets, **kw
            )

        self._run_bg(
            work,
            lambda p: self._ok_file(p, "Flattened"),
            "Flatten",
            op="flatten",
            inputs=[src],
        )

