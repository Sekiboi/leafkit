"""Organize tab: multi-PDF page tray (mixin for SekikitApp)."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from sekikit import __app_name__
from sekikit import jobs
from sekikit import pdf_ops
from sekikit import render as pdf_render
from sekikit.i18n import _


class OrganizeTabMixin:
    """Mixin: Organize tray UI + multi-source page ops."""

    def _build_organize_tab(self) -> None:
        tab = self.tabs.tab("Organize")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=4, pady=(6, 4))
        ctk.CTkLabel(
            top,
            text=_(
                "Piece PDFs together: load or add pages from the list, reorder, preview, save one PDF. "
                "Sources are never deleted."
            ),
            anchor="w",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(fill="x")

        bar = ctk.CTkFrame(top, fg_color="transparent")
        bar.pack(fill="x", pady=(6, 0))
        b = ctk.CTkButton(bar, text=_("Load / replace"), width=110, command=self._org_load)
        b.pack(side="left", padx=(0, 4))
        self._tip(
            b,
            "Replace tray with pages from the selected list PDF. · Needs pymupdf.",
        )
        b = ctk.CTkButton(bar, text=_("Add selected"), width=100, command=self._org_add_selected)
        b.pack(side="left", padx=4)
        self._tip(
            b,
            "Append pages from the selected list PDF into the tray (piece multiple PDFs).",
        )
        b = ctk.CTkButton(bar, text=_("Add all"), width=80, command=self._org_add_all)
        b.pack(side="left", padx=4)
        self._tip(b, "Append every page from every PDF in the list.")
        ctk.CTkLabel(bar, text=_("Range:")).pack(side="left", padx=(8, 2))
        self.org_add_range = ctk.CTkEntry(bar, width=90, placeholder_text="all")
        self.org_add_range.pack(side="left", padx=2)
        self._tip(
            self.org_add_range,
            "Optional 1-based range when adding (e.g. 1-3). Blank = all pages.",
        )
        b = ctk.CTkButton(
            bar,
            text=_("Reset"),
            width=70,
            command=self._org_reset,
            fg_color="gray40",
        )
        b.pack(side="left", padx=(8, 4))
        self._tip(b, "Clear tray. Does not change files on disk.")
        b = ctk.CTkButton(
            bar, text=_("Select all"), width=80, command=self._org_select_all, fg_color="gray40"
        )
        b.pack(side="left", padx=4)
        self._tip(b, "Select all pages in the tray.")
        b = ctk.CTkButton(
            bar, text=_("Clear sel"), width=70, command=self._org_clear_sel, fg_color="gray40"
        )
        b.pack(side="left", padx=4)
        self._tip(b, "Clear page selection.")
        b = ctk.CTkButton(bar, text=_("← Move"), width=70, command=lambda: self._org_move(-1))
        b.pack(side="left", padx=(8, 4))
        self._tip(b, "Move selected pages earlier.")
        b = ctk.CTkButton(bar, text=_("Move →"), width=70, command=lambda: self._org_move(1))
        b.pack(side="left", padx=4)
        self._tip(b, "Move selected pages later.")

        mid = ctk.CTkFrame(tab, fg_color="transparent")
        mid.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        mid.grid_columnconfigure(0, weight=3)
        mid.grid_columnconfigure(1, weight=2)
        mid.grid_rowconfigure(0, weight=1)

        self.org_scroll = ctk.CTkScrollableFrame(
            mid, label_text=_("Page tray · multi-PDF · click to select")
        )
        self.org_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right = ctk.CTkFrame(mid)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkLabel(hdr, text=_("Preview"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        b = ctk.CTkButton(
            hdr, text="−", width=32, command=lambda: self._preview_set_zoom(-0.25)
        )
        b.pack(side="right", padx=2)
        self._tip(b, "Zoom out.")
        self.preview_zoom_label = ctk.CTkLabel(hdr, text="100%", width=48)
        self.preview_zoom_label.pack(side="right")
        b = ctk.CTkButton(
            hdr, text="+", width=32, command=lambda: self._preview_set_zoom(0.25)
        )
        b.pack(side="right", padx=2)
        self._tip(b, "Zoom in.")
        b = ctk.CTkButton(
            hdr, text=_("Fullscreen"), width=90, command=self._org_fullscreen
        )
        b.pack(side="right", padx=(0, 8))
        self._tip(b, "Fullscreen preview. · Screen view only — not print-proof.")

        self.org_preview_frame = ctk.CTkScrollableFrame(right, label_text="")
        self.org_preview_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.org_preview = ctk.CTkLabel(
            self.org_preview_frame, text=_("(load pages)"), cursor="hand2"
        )
        self.org_preview.pack(padx=4, pady=4)
        self.org_preview.bind("<Double-Button-1>", lambda _e: self._org_fullscreen())
        def _wheel_zoom(event):  # noqa: ANN001
            delta = 0.15 if getattr(event, "delta", 0) > 0 else -0.15
            self._preview_set_zoom(delta)
            return "break"

        self.org_preview_frame.bind("<MouseWheel>", _wheel_zoom)
        self.org_preview.bind("<MouseWheel>", _wheel_zoom)
        self.org_preview_frame.bind("<Control-MouseWheel>", _wheel_zoom)

        self.org_status = ctk.CTkLabel(
            right,
            text=_("Double-click preview or Fullscreen · use + / − to zoom"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=11),
        )
        self.org_status.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))

        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=4, pady=(4, 2))
        b = ctk.CTkButton(
            actions, text=_("Extract selected"), command=self._org_extract
        )
        b.pack(side="left", padx=(0, 6))
        self._tip(b, "Save only selected tray pages as a new PDF.")
        b = ctk.CTkButton(
            actions,
            text=_("Split before selected"),
            command=self._org_split_before_selected,
            fg_color="gray40",
        )
        b.pack(side="left", padx=6)
        self._tip(
            b,
            "Write multiple PDFs: each selected tray page starts a new part "
            "(first page is never a cut). · Multi-PDF trays supported.",
        )
        b = ctk.CTkButton(
            actions, text=_("Remove from tray"), command=self._org_delete, fg_color="#8B3A3A"
        )
        b.pack(side="left", padx=6)
        self._tip(b, "Drop selected from tray (or save without them). · Source files stay on disk.")
        b = ctk.CTkButton(
            actions, text=_("Rotate 90°"), command=lambda: self._org_rotate(90)
        )
        b.pack(side="left", padx=6)
        self._tip(b, "Rotate selected tray pages 90° → new combined PDF.")
        b = ctk.CTkButton(
            actions, text=_("Reverse tray"), command=self._org_reverse_tray, fg_color="gray40"
        )
        b.pack(side="left", padx=6)
        self._tip(b, "Reverse tray order in place (Save to write a file).")
        b = ctk.CTkButton(
            actions,
            text=_("Insert blank"),
            command=self._org_insert_blank,
            fg_color="gray40",
        )
        b.pack(side="left", padx=6)
        self._tip(
            b,
            "Insert one blank page before the first selected tray page "
            "(or at end if none selected). Size matches first source page.",
        )
        b = ctk.CTkButton(
            actions,
            text=_("Save combined PDF"),
            height=34,
            command=self._org_save_order,
        )
        b.pack(side="right")
        self._tip(
            b,
            "Write tray order as one PDF (merge + reorder). · Sources not modified. Ctrl+S",
        )
        org_opts = ctk.CTkFrame(tab, fg_color="transparent")
        org_opts.grid(row=3, column=0, sticky="ew", padx=4, pady=(0, 8))
        self.org_renumber = ctk.CTkCheckBox(
            org_opts,
            text=_("Renumber after extract / save (cover band → continuous 1…N)"),
        )
        self.org_renumber.pack(side="left")
        self._tip(
            self.org_renumber,
            "Then renumber. · Band expands over detected margin text (not OCR).",
        )
    # Max open source PDFs for thumbs (LRU).
    _ORG_SESSION_MAX = 12

    def _org_session_key(self, path: Path) -> str:
        try:
            return str(path.resolve())
        except OSError:
            return str(path)

    def _org_live_session_keys(self) -> set[str]:
        return {self._org_session_key(p) for p, _ in self._org_items}

    def _close_org_sessions(self) -> None:
        for sess in list(self._org_sessions.values()):
            try:
                sess.close()
            except Exception:  # noqa: BLE001
                pass
        self._org_sessions.clear()
        if hasattr(self, "_org_session_order"):
            self._org_session_order.clear()

    def _org_close_session_key(self, key: str) -> None:
        sess = self._org_sessions.pop(key, None)
        if sess is not None:
            try:
                sess.close()
            except Exception:  # noqa: BLE001
                pass
        order = getattr(self, "_org_session_order", None)
        if order is not None and key in order:
            order.remove(key)

    def _org_prune_sessions(self) -> None:
        """Drop sessions for sources no longer in the tray; cap open handle count."""
        if not hasattr(self, "_org_session_order"):
            self._org_session_order: list[str] = []
        live = self._org_live_session_keys()
        for key in list(self._org_sessions.keys()):
            if key not in live:
                self._org_close_session_key(key)
        while len(self._org_sessions) > self._ORG_SESSION_MAX:
            if not self._org_session_order:
                extras = list(self._org_sessions.keys())[
                    : len(self._org_sessions) - self._ORG_SESSION_MAX
                ]
                for key in extras:
                    self._org_close_session_key(key)
                break
            self._org_close_session_key(self._org_session_order[0])

    def _org_get_session(self, path: Path) -> pdf_render.ThumbnailSession:
        if not hasattr(self, "_org_session_order"):
            self._org_session_order = []
        key = self._org_session_key(path)
        if key in self._org_sessions:
            if key in self._org_session_order:
                self._org_session_order.remove(key)
            self._org_session_order.append(key)
            return self._org_sessions[key]
        self._org_prune_sessions()
        while len(self._org_sessions) >= self._ORG_SESSION_MAX:
            if not self._org_session_order:
                break
            self._org_close_session_key(self._org_session_order[0])
        pwd = self._password() or jobs.password_cache_get(path)
        self._org_sessions[key] = pdf_render.ThumbnailSession(
            path, password=pwd, max_width=96
        )
        self._org_session_order.append(key)
        return self._org_sessions[key]

    def _org_item_label(self, pos: int) -> str:
        if pos < 0 or pos >= len(self._org_items):
            return f"#{pos + 1}"
        path, page_idx = self._org_items[pos]
        stem = path.stem
        if len(stem) > 12:
            stem = stem[:11] + "…"
        return f"{stem}\np{page_idx + 1}"
    def _org_parse_add_range(self, total: int) -> list[int]:
        """0-based indices from Range field; all pages if blank."""
        raw = ""
        if hasattr(self, "org_add_range"):
            raw = self.org_add_range.get().strip()
        if not raw:
            return list(range(total))
        return pdf_ops.parse_page_range(raw, total)
    def _org_set_items(self, items: list[tuple[Path, int]], *, primary: Path | None) -> None:
        self._org_items = list(items)
        self._org_path = primary or (items[0][0] if items else None)
        self._org_selected.clear()
        self._preview_strip_pos = None
        self._org_prune_sessions()
        self._rebuild_org_placeholders()
        n = len(self._org_items)
        if n:
            self.org_status.configure(text=f"{n} page(s) in tray. Loading thumbs…")
            self._set_status(f"Organize: {n} page(s)…")
            self._thumb_load_gen += 1
            gen = self._thumb_load_gen
            self._org_load_thumbs_batch(0, batch=24, gen=gen)
            self._org_show_preview_pos(0)
        else:
            self.org_status.configure(text=_("Tray empty — load or add pages."))
            self.org_preview.configure(image=None, text=_("(load pages)"))
    def _org_load(self) -> None:
        """Replace tray with pages from the selected list PDF."""
        src = self._require_selected()
        if src is None:
            return
        if not pdf_render.has_renderer():
            messagebox.showerror(
                __app_name__,
                "Thumbnails need PyMuPDF.\n\npip install pymupdf",
            )
            return
        pwd = self._password()
        self._set_status(f"Opening {src.name}…")
        self.update_idletasks()
        self._close_org_sessions()

        def work():
            session = pdf_render.ThumbnailSession(src, password=pwd, max_width=96)
            return session

        def on_ok(session: pdf_render.ThumbnailSession):
            key = self._org_session_key(src)
            self._org_sessions[key] = session
            n = session.page_count
            try:
                indices = self._org_parse_add_range(n)
            except pdf_ops.PdfOpsError as exc:
                messagebox.showerror(__app_name__, str(exc))
                indices = list(range(n))
            items = [(src, i) for i in indices]
            self._org_set_items(items, primary=src)

        self._run_bg(work, on_ok, "Opening PDF", review=False)
    def _org_add_selected(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        self._org_append_from_files([src])
    def _org_add_all(self) -> None:
        if not self._files:
            messagebox.showinfo(__app_name__, "Add PDFs to the list first.")
            return
        self._org_append_from_files(list(self._files))
    def _org_append_from_files(self, files: list[Path]) -> None:
        if not pdf_render.has_renderer():
            messagebox.showerror(
                __app_name__,
                "Thumbnails need PyMuPDF.\n\npip install pymupdf",
            )
            return
        pwd = self._password()
        self._set_status("Adding pages to tray…")

        def work():
            added: list[tuple[Path, int]] = []
            for src in files:
                try:
                    n = pdf_ops.page_count(
                        src,
                        password=pwd,
                        password_provider=jobs.make_password_provider(pwd),
                    )
                except pdf_ops.PdfOpsError:
                    sess = pdf_render.ThumbnailSession(src, password=pwd, max_width=96)
                    n = sess.page_count
                    self._org_sessions[self._org_session_key(src)] = sess
                try:
                    indices = self._org_parse_add_range(n)
                except pdf_ops.PdfOpsError as exc:
                    raise pdf_ops.PdfOpsError(f"{src.name}: {exc}") from exc
                for i in indices:
                    added.append((src, i))
            return added

        def on_ok(added: list):
            if not added:
                self._set_status("No pages added.")
                return
            for path, _ in added:
                try:
                    self._org_get_session(path)
                except Exception:  # noqa: BLE001
                    pass
            primary = self._org_path or (added[0][0] if added else None)
            new_items = list(self._org_items) + list(added)
            self._org_set_items(new_items, primary=primary)
            self._set_status(f"Added {len(added)} page(s). Tray: {len(self._org_items)}.")

        self._run_bg(work, on_ok, "Adding pages", review=False)
    def _rebuild_org_placeholders(self, n: int | None = None) -> None:
        for w in self.org_scroll.winfo_children():
            w.destroy()
        self._org_buttons = []
        count = len(self._org_items) if n is None else n
        self._org_thumbs = [None] * count  # type: ignore[list-item]
        if count < 1:
            tip = ctk.CTkFrame(self.org_scroll, fg_color="transparent")
            tip.grid(row=0, column=0, columnspan=4, sticky="ew", padx=8, pady=24)
            ctk.CTkLabel(
                tip,
                text=_("Tray is empty"),
                font=ctk.CTkFont(size=15, weight="bold"),
            ).pack(anchor="w")
            ctk.CTkLabel(
                tip,
                text=_(
                    "Load / replace — selected list PDF\n"
                    "Add selected — append pages from list\n"
                    "Ctrl+L load · Ctrl+S save combined"
                ),
                text_color=("gray40", "gray70"),
                font=ctk.CTkFont(size=12),
                justify="left",
            ).pack(anchor="w", pady=(6, 0))
            return
        for pos in range(count):
            label = self._org_item_label(pos) if pos < len(self._org_items) else f"#{pos + 1}"
            btn = ctk.CTkButton(
                self.org_scroll,
                text=f"{label}\n…",
                width=108,
                height=140,
                fg_color=("gray75", "gray30"),
                command=lambda p=pos: self._org_click(p),
            )
            btn.grid(row=pos // 4, column=pos % 4, padx=4, pady=4)
            self._org_buttons.append(btn)
    def _org_load_thumbs_batch(self, start: int, batch: int, gen: int) -> None:
        if gen != self._thumb_load_gen:
            return
        n = len(self._org_items)
        if n < 1:
            return
        end = min(start + batch, n)
        items_snap = list(self._org_items)

        def work():
            results = []
            for pos in range(start, end):
                if self._cancel_job:
                    break
                if pos >= len(items_snap):
                    break
                path, page_idx = items_snap[pos]
                img = None
                try:
                    key = str(path.resolve()) if path.exists() else str(path)
                    sess = self._org_sessions.get(key)
                    if sess is None:
                        pwd = jobs.password_cache_get(path)
                        sess = pdf_render.ThumbnailSession(
                            path, password=pwd, max_width=96
                        )
                        self._org_sessions[key] = sess
                    img = sess.get(page_idx)
                except Exception:  # noqa: BLE001
                    try:
                        img = pdf_render.render_page(
                            path, page_idx, max_width=96, password=jobs.password_cache_get(path)
                        )
                    except Exception:  # noqa: BLE001
                        img = None
                results.append((pos, page_idx, img))
            return results

        def on_ok(results):
            if gen != self._thumb_load_gen:
                return
            for pos, page_idx, img in results:
                if pos >= len(self._org_buttons):
                    continue
                label = self._org_item_label(pos)
                if img is None:
                    self._org_buttons[pos].configure(text=f"{label}\n?")
                    continue
                ctk_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=(img.width, img.height)
                )
                if pos < len(self._org_thumbs):
                    self._org_thumbs[pos] = ctk_img
                self._org_buttons[pos].configure(
                    image=ctk_img, text=label, compound="top"
                )
            self._org_refresh_highlights()
            if end < n and gen == self._thumb_load_gen:
                self._set_status(f"Thumbnails {end}/{n}…")
                self.after(
                    10,
                    lambda: self._org_load_thumbs_batch(end, batch, gen),
                )
            else:
                srcs = {p.name for p, _ in self._org_items}
                self.org_status.configure(
                    text=f"{n} page(s) · {len(srcs)} file(s). Click to select."
                )
                self._set_status(f"Tray ready: {n} page(s) from {len(srcs)} file(s).")

        def runner():
            try:
                res = work()
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._set_status(f"Thumbnail load error: {exc}"))
                return
            self.after(0, lambda: on_ok(res))

        threading.Thread(target=runner, daemon=True).start()
    def _rebuild_org_strip(self, thumbs: list) -> None:
        """Rebuild strip after reorder; thumbs match display order."""
        for w in self.org_scroll.winfo_children():
            w.destroy()
        self._org_buttons = []
        self._org_thumbs = []
        for pos, img in enumerate(thumbs):
            ctk_img = ctk.CTkImage(
                light_image=img, dark_image=img, size=(img.width, img.height)
            )
            self._org_thumbs.append(ctk_img)
            label = self._org_item_label(pos)
            btn = ctk.CTkButton(
                self.org_scroll,
                image=ctk_img,
                text=label,
                compound="top",
                width=108,
                height=140,
                fg_color=("gray75", "gray30"),
                command=lambda p=pos: self._org_click(p),
            )
            btn.grid(row=pos // 4, column=pos % 4, padx=4, pady=4)
            self._org_buttons.append(btn)
        self._org_refresh_highlights()
    def _org_click(self, pos: int) -> None:
        if pos in self._org_selected:
            self._org_selected.discard(pos)
        else:
            self._org_selected.add(pos)
        self._org_refresh_highlights()
        if pos < len(self._org_items):
            self._org_show_preview_pos(pos)
    def _org_refresh_highlights(self) -> None:
        for i, btn in enumerate(self._org_buttons):
            if i in self._org_selected:
                btn.configure(fg_color=("#3B8ED0", "#1F6AA5"), border_width=2)
            else:
                btn.configure(fg_color=("gray75", "gray30"), border_width=0)
        n = len(self._org_selected)
        total = len(self._org_items)
        srcs = len({p for p, _ in self._org_items}) if self._org_items else 0
        self.org_status.configure(
            text=f"{total} page(s) · {srcs} file(s) · {n} selected"
        )
    def _preview_set_zoom(self, delta: float) -> None:
        self._preview_zoom = max(0.5, min(4.0, self._preview_zoom + delta))
        self.preview_zoom_label.configure(text=f"{int(self._preview_zoom * 100)}%")
        if self._preview_strip_pos is not None:
            self._org_show_preview_pos(self._preview_strip_pos)
    def _org_show_preview_pos(self, strip_pos: int) -> None:
        if strip_pos < 0 or strip_pos >= len(self._org_items):
            return
        path, page_index = self._org_items[strip_pos]
        self._preview_strip_pos = strip_pos
        try:
            base_w = int(220 * self._preview_zoom)
            pwd = self._password() or jobs.password_cache_get(path)
            img = pdf_render.render_page(
                path,
                page_index,
                max_width=base_w,
                password=pwd,
            )
            self._preview_pil = img
            self._preview_image = ctk.CTkImage(
                light_image=img, dark_image=img, size=(img.width, img.height)
            )
            self.org_preview.configure(image=self._preview_image, text="")
            self.preview_zoom_label.configure(text=f"{int(self._preview_zoom * 100)}%")
        except Exception as exc:  # noqa: BLE001
            self.org_preview.configure(image=None, text=f"(preview failed)\n{exc}")
    def _org_show_preview(self, page_index: int) -> None:
        """Compat: show by source page index using current strip context."""
        if self._preview_strip_pos is not None and self._preview_strip_pos < len(
            self._org_items
        ):
            self._org_show_preview_pos(self._preview_strip_pos)
            return
        for i, (path, pi) in enumerate(self._org_items):
            if pi == page_index and (
                self._org_path is None or path == self._org_path
            ):
                self._org_show_preview_pos(i)
                return
        if self._org_items:
            self._org_show_preview_pos(0)
    def _org_fullscreen(self) -> None:
        """Open a maximized zoomable page viewer with prev/next navigation."""
        if not self._org_items:
            messagebox.showinfo(__app_name__, "Load or add pages first.")
            return
        if self._preview_strip_pos is None:
            self._preview_strip_pos = 0
        if self._fs_window is not None:
            try:
                self._fs_window.destroy()
            except Exception:  # noqa: BLE001
                pass

        page_list = list(self._org_items)
        pos = self._preview_strip_pos or 0
        pos = max(0, min(len(page_list) - 1, pos))

        top = ctk.CTkToplevel(self)
        self._fs_window = top
        top.geometry("1000x750")
        top.minsize(640, 480)
        try:
            top.state("zoomed")
        except Exception:  # noqa: BLE001
            pass
        top.lift()
        top.focus_force()

        bar = ctk.CTkFrame(top, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=8)
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        self._fs_title = ctk.CTkLabel(
            left, text="", font=ctk.CTkFont(size=14, weight="bold")
        )
        self._fs_title.pack(side="left", padx=(0, 16))
        nav = ctk.CTkFrame(left, fg_color="transparent")
        nav.pack(side="left")
        self._fs_prev_btn = ctk.CTkButton(
            nav, text=_("← Prev"), width=80, command=lambda: self._fs_goto(top, -1)
        )
        self._fs_prev_btn.pack(side="left", padx=2)
        self._fs_page_label = ctk.CTkLabel(nav, text="", width=100)
        self._fs_page_label.pack(side="left", padx=6)
        self._fs_next_btn = ctk.CTkButton(
            nav, text=_("Next →"), width=80, command=lambda: self._fs_goto(top, 1)
        )
        self._fs_next_btn.pack(side="left", padx=2)
        ctk.CTkButton(bar, text=_("Close (Esc)"), width=100, command=top.destroy).pack(
            side="right", padx=4
        )
        ctk.CTkButton(
            bar, text="−", width=36, command=lambda: self._fs_zoom_by(top, -0.25)
        ).pack(side="right", padx=2)
        self._fs_zoom_label = ctk.CTkLabel(bar, text="100%", width=48)
        self._fs_zoom_label.pack(side="right")
        ctk.CTkButton(
            bar, text="+", width=36, command=lambda: self._fs_zoom_by(top, 0.25)
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            bar, text=_("Fit width"), width=80, command=lambda: self._fs_set_zoom(top, 1.0)
        ).pack(side="right", padx=8)
        ctk.CTkLabel(
            top,
            text=_("← → pages · multi-PDF tray · screen preview only"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=11),
        ).pack(fill="x", padx=12)
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self._fs_label = ctk.CTkLabel(scroll, text=_("Loading…"))
        self._fs_label.pack(padx=8, pady=8)

        self._fs_zoom = 1.0
        self._fs_pages = page_list
        self._fs_pos = pos
        self._fs_render(top)

        top.bind("<Escape>", lambda _e: top.destroy())
        top.bind("<Left>", lambda _e: self._fs_goto(top, -1))
        top.bind("<Right>", lambda _e: self._fs_goto(top, 1))
        top.bind("<Prior>", lambda _e: self._fs_goto(top, -1))
        top.bind("<Next>", lambda _e: self._fs_goto(top, 1))
        top.bind("<Home>", lambda _e: self._fs_goto_abs(top, 0))
        top.bind("<End>", lambda _e: self._fs_goto_abs(top, len(self._fs_pages) - 1))
        top.bind("<plus>", lambda _e: self._fs_zoom_by(top, 0.25))
        top.bind("<minus>", lambda _e: self._fs_zoom_by(top, -0.25))
        top.bind("<Control-plus>", lambda _e: self._fs_zoom_by(top, 0.25))
        top.bind("<Control-minus>", lambda _e: self._fs_zoom_by(top, -0.25))
        top.bind(
            "<Control-MouseWheel>",
            lambda e: self._fs_zoom_by(top, 0.15 if e.delta > 0 else -0.15),
        )
        top.protocol("WM_DELETE_WINDOW", top.destroy)
    def _fs_goto(self, top, delta: int) -> None:
        if not getattr(self, "_fs_pages", None):
            return
        new_pos = self._fs_pos + delta
        if new_pos < 0 or new_pos >= len(self._fs_pages):
            return
        self._fs_goto_abs(top, new_pos)
    def _fs_goto_abs(self, top, pos: int) -> None:
        if not getattr(self, "_fs_pages", None):
            return
        pos = max(0, min(len(self._fs_pages) - 1, pos))
        self._fs_pos = pos
        try:
            self._org_show_preview_pos(pos)
        except Exception:  # noqa: BLE001
            pass
        self._fs_render(top)
    def _fs_set_zoom(self, top, zoom: float) -> None:
        self._fs_zoom = max(0.25, min(5.0, zoom))
        self._fs_render(top)
    def _fs_zoom_by(self, top, delta: float) -> None:
        self._fs_set_zoom(top, self._fs_zoom + delta)
    def _fs_render(self, top) -> None:
        try:
            path, page_index = self._fs_pages[self._fs_pos]
            total = len(self._fs_pages)
            max_w = int(900 * self._fs_zoom)
            pwd = self._password() or jobs.password_cache_get(path)
            img = pdf_render.render_page(
                path, page_index, max_width=max_w, password=pwd
            )
            self._fs_image = ctk.CTkImage(
                light_image=img, dark_image=img, size=(img.width, img.height)
            )
            self._fs_label.configure(image=self._fs_image, text="")
            title = f"{path.name}  ·  p{page_index + 1}  ·  tray {self._fs_pos + 1}/{total}"
            top.title(f"Sekikit — {self._fs_pos + 1} of {total}")
            if hasattr(self, "_fs_title"):
                self._fs_title.configure(text=title)
            if hasattr(self, "_fs_page_label"):
                self._fs_page_label.configure(text=f"{self._fs_pos + 1} / {total}")
            if hasattr(self, "_fs_zoom_label"):
                self._fs_zoom_label.configure(text=f"{int(self._fs_zoom * 100)}%")
            if hasattr(self, "_fs_prev_btn"):
                self._fs_prev_btn.configure(
                    state="normal" if self._fs_pos > 0 else "disabled"
                )
            if hasattr(self, "_fs_next_btn"):
                self._fs_next_btn.configure(
                    state="normal" if self._fs_pos < total - 1 else "disabled"
                )
        except Exception as exc:  # noqa: BLE001
            self._fs_label.configure(image=None, text=f"Preview failed:\n{exc}")
    def _org_reset(self) -> None:
        """Unload tray so the user can start a new combination."""
        if not self._org_items and not self._org_buttons:
            self._set_status("Organize tray already empty.")
            return
        if self._fs_window is not None:
            try:
                self._fs_window.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._fs_window = None

        self._thumb_load_gen += 1
        self._close_org_sessions()
        self._org_path = None
        self._org_items = []
        self._org_selected.clear()
        self._org_thumbs = []
        self._org_buttons = []
        self._preview_strip_pos = None
        self._preview_pil = None
        self._preview_image = None
        self._preview_zoom = 1.0

        for w in self.org_scroll.winfo_children():
            w.destroy()
        self.org_preview.configure(image=None, text=_("(load pages)"))
        if hasattr(self, "preview_zoom_label"):
            self.preview_zoom_label.configure(text="100%")
        self.org_status.configure(
            text=_("Tray cleared — load or add pages from the list.")
        )
        self._set_status("Organize tray reset.")
    def _org_select_all(self) -> None:
        self._org_selected = set(range(len(self._org_items)))
        self._org_refresh_highlights()
    def _org_clear_sel(self) -> None:
        self._org_selected.clear()
        self._org_refresh_highlights()

    def _org_reverse_tray(self) -> None:
        """Reverse tray order in place (Save writes the file)."""
        if len(self._org_items) < 2:
            self._set_status("Need at least two tray pages to reverse.")
            return
        n = len(self._org_items)
        self._org_items.reverse()
        self._org_selected = {n - 1 - i for i in self._org_selected}
        if self._preview_strip_pos is not None:
            self._preview_strip_pos = n - 1 - self._preview_strip_pos
        self._org_reload_thumbs_for_order()
        self._set_status("Tray reversed — Save combined PDF to write a file.")

    def _org_insert_blank(self) -> None:
        """Insert one blank page into the tray before first selection (or at end)."""
        ref: Path | None = None
        w, h = 612.0, 792.0
        if self._org_items:
            ref = self._org_items[0][0]
        elif self._org_path is not None:
            ref = self._org_path
        else:
            ref = self._require_selected()
            if ref is None:
                return
        try:
            from pypdf import PdfReader

            pwd = self._password() or jobs.password_cache_get(ref)
            r = PdfReader(str(ref))
            if r.is_encrypted:
                r.decrypt(pwd or "")
            if r.pages:
                mb = r.pages[0].mediabox
                w, h = float(mb.width), float(mb.height)
        except Exception:  # noqa: BLE001
            pass

        dest_dir = ref.parent if ref is not None else Path.cwd()
        blank_out = dest_dir / f".sekikit-blank-{ref.stem if ref else 'page'}.pdf"
        try:
            blank_path = pdf_ops.create_blank_pdf(blank_out, width=w, height=h, count=1)
        except pdf_ops.PdfOpsError as exc:
            messagebox.showerror(__app_name__, str(exc))
            return

        insert_at = (
            min(self._org_selected)
            if self._org_selected
            else len(self._org_items)
        )
        self._org_items.insert(insert_at, (blank_path, 0))
        self._org_selected = {insert_at}
        if self._org_path is None:
            self._org_path = blank_path
        self._org_reload_thumbs_for_order()
        self._set_status(
            f"Blank page inserted at #{insert_at + 1} — Save combined PDF when ready."
        )

    def _org_move(self, delta: int) -> None:
        if not self._org_selected or not self._org_items:
            return
        selected = sorted(self._org_selected)
        if delta < 0:
            for pos in selected:
                new = pos + delta
                if new < 0 or new in self._org_selected:
                    continue
                self._org_items[pos], self._org_items[new] = (
                    self._org_items[new],
                    self._org_items[pos],
                )
                self._org_selected.discard(pos)
                self._org_selected.add(new)
        else:
            for pos in reversed(selected):
                new = pos + delta
                if new >= len(self._org_items) or new in self._org_selected:
                    continue
                self._org_items[pos], self._org_items[new] = (
                    self._org_items[new],
                    self._org_items[pos],
                )
                self._org_selected.discard(pos)
                self._org_selected.add(new)
        self._org_reload_thumbs_for_order()
    def _org_reload_thumbs_for_order(self) -> None:
        if not self._org_items:
            return
        try:
            imgs = []
            for path, idx in self._org_items:
                try:
                    sess = self._org_get_session(path)
                    imgs.append(sess.get(idx))
                except Exception:  # noqa: BLE001
                    imgs.append(
                        pdf_render.render_page(
                            path,
                            idx,
                            max_width=96,
                            password=self._password() or jobs.password_cache_get(path),
                        )
                    )
            self._rebuild_org_strip(imgs)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Reorder UI refresh failed: {exc}")
            self._rebuild_org_placeholders()
            self._thumb_load_gen += 1
            self._org_load_thumbs_batch(0, batch=24, gen=self._thumb_load_gen)
    def _org_selected_items(self) -> list[tuple[Path, int]]:
        return [
            self._org_items[p]
            for p in sorted(self._org_selected)
            if p < len(self._org_items)
        ]
    def _org_default_out(self, suffix: str) -> Path:
        base = self._org_path or (
            self._org_items[0][0] if self._org_items else Path("combined.pdf")
        )
        return pdf_ops.default_output_next_to(base, suffix)
    def _org_extract(self) -> None:
        if not self._org_items:
            messagebox.showinfo(__app_name__, "Load or add pages first.")
            return
        selected = self._org_selected_items()
        if not selected:
            messagebox.showinfo(__app_name__, "Select one or more pages first.")
            return
        do_renumber = bool(self.org_renumber.get())
        suf = "_extracted_numbered" if do_renumber else "_extracted"
        out = self._org_default_out(suf)
        kw = self._pwd_kwargs()
        items = list(selected)

        def work():
            def produce(path: Path) -> Path:
                return pdf_ops.assemble_pages(items, path, **kw)

            return self._op_then_renumber(
                produce, out, do_renumber=do_renumber, pwd_kw=kw
            )

        verb = "Extracted + renumbered" if do_renumber else "Extracted"
        self._run_bg(
            work,
            lambda p: self._ok_file(p, verb),
            "Extracting",
            op="extract_renumber" if do_renumber else "extract",
        )

    def _org_split_before_selected(self) -> None:
        """Split tray into files; each selected page (except first) starts a part."""
        if not self._org_items:
            messagebox.showinfo(__app_name__, "Load or add pages first.")
            return
        if not self._org_selected:
            messagebox.showinfo(
                __app_name__,
                "Select the tray page(s) that should start a new file "
                "(not the first page).",
            )
            return
        cuts = sorted(i for i in self._org_selected if i > 0)
        if not cuts:
            messagebox.showinfo(
                __app_name__,
                "Select at least one page after the first.\n\n"
                "Split happens *before* each selected page.",
            )
            return
        n_parts = len(cuts) + 1
        if not messagebox.askyesno(
            __app_name__,
            f"Split into {n_parts} PDF file(s)?\n\n"
            "Each selected page starts a new part. Source files stay on disk.",
        ):
            return
        base = self._org_path or self._org_items[0][0]
        out_dir = base.parent / f"{base.stem}_tray_split"
        do_renumber = bool(self.org_renumber.get())
        kw = self._pwd_kwargs()
        items = list(self._org_items)
        stem = base.stem

        def work():
            paths = pdf_ops.split_item_segments(
                items, cuts, out_dir, stem, **kw
            )
            if not do_renumber:
                return paths
            style = self._renumber_style_kwargs()
            out: list[Path] = []
            for p in paths:
                dest = pdf_ops.default_output_next_to(p, "_renumbered")
                out.append(pdf_ops.renumber_pages(p, dest, **style, **kw))
            return out

        verb = "Split + renumbered" if do_renumber else "Split"
        self._run_bg(
            work,
            lambda paths: self._ok_files(paths, verb),
            "Splitting tray",
            op="split_renumber" if do_renumber else "split",
            review=False,
        )

    def _org_delete(self) -> None:
        """Remove selected pages from the tray (does not delete source files)."""
        if not self._org_items:
            messagebox.showinfo(__app_name__, "Load or add pages first.")
            return
        if not self._org_selected:
            messagebox.showinfo(__app_name__, "Select pages to remove from the tray.")
            return
        n = len(self._org_selected)
        if not messagebox.askyesno(
            __app_name__,
            f"Remove {n} page(s) from the tray?\n\nSource PDF files stay on disk.",
        ):
            return
        keep = [
            item
            for i, item in enumerate(self._org_items)
            if i not in self._org_selected
        ]
        primary = self._org_path
        if primary and all(p != primary for p, _ in keep):
            primary = keep[0][0] if keep else None
        self._org_set_items(keep, primary=primary)
        self._set_status(f"Removed {n} page(s) from tray.")
    def _org_rotate(self, degrees: int) -> None:
        if not self._org_items:
            messagebox.showinfo(__app_name__, "Load or add pages first.")
            return
        if not self._org_selected:
            messagebox.showinfo(__app_name__, "Select one or more pages to rotate.")
            return
        out = self._org_default_out(f"_rot{degrees}")
        kw = self._pwd_kwargs()
        items = list(self._org_items)
        rots = {i: degrees for i in self._org_selected}

        def work():
            return pdf_ops.assemble_pages(items, out, rotations=rots, **kw)

        self._run_bg(
            work,
            lambda p: self._ok_file(p, "Rotated"),
            "Rotating",
            op="rotate",
        )
    def _org_save_order(self) -> None:
        if not self._org_items:
            messagebox.showinfo(__app_name__, "Load or add pages first.")
            return
        do_renumber = bool(self.org_renumber.get())
        multi = len({p for p, _ in self._org_items}) > 1
        if multi:
            suf = "_combined_numbered" if do_renumber else "_combined"
        else:
            path0 = self._org_items[0][0]
            natural = all(
                p == path0 and idx == i for i, (p, idx) in enumerate(self._org_items)
            )
            if natural and not do_renumber:
                messagebox.showinfo(
                    __app_name__,
                    "Order unchanged. Add more pages or reorder first.",
                )
                return
            suf = "_reordered_numbered" if do_renumber else "_reordered"
        out = self._org_default_out(suf)
        kw = self._pwd_kwargs()
        items = list(self._org_items)

        def work():
            def produce(path: Path) -> Path:
                return pdf_ops.assemble_pages(items, path, **kw)

            return self._op_then_renumber(
                produce, out, do_renumber=do_renumber, pwd_kw=kw
            )

        verb = "Combined + renumbered" if do_renumber else (
            "Combined" if multi else "Reordered"
        )
        if do_renumber and multi:
            op = "merge_renumber"
        elif multi:
            op = "merge"
        elif do_renumber:
            op = "reorder_renumber"
        else:
            op = "reorder"
        self._run_bg(work, lambda p: self._ok_file(p, verb), "Saving combined", op=op)

