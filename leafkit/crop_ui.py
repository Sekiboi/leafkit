"""Visual crop dialog: drag a rectangle on a page preview. Offline only."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageTk

from leafkit import __app_name__
from leafkit import render as pdf_render
from leafkit.i18n import _


def run_crop_dialog(
    parent: Any,
    path: Path,
    *,
    password: str | None = None,
    page_index: int = 0,
) -> dict[str, Any] | None:
    """Show visual crop UI.

    Returns dict with keys rect (x0,y0,x1,y1 PDF bottom-left pts), hard, apply_all,
    page_index — or None if cancelled.
    """
    dlg = _CropDialog(parent, path, password=password, page_index=page_index)
    parent.wait_window(dlg)
    if dlg.result is None:
        return None
    return {
        "rect": dlg.result,
        "hard": bool(getattr(dlg, "hard", False)),
        "apply_all": bool(getattr(dlg, "apply_all", True)),
        "page_index": int(getattr(dlg, "page_index", page_index)),
    }


class _CropDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent: Any,
        path: Path,
        *,
        password: str | None = None,
        page_index: int = 0,
    ) -> None:
        super().__init__(parent)
        self.title(f"{_('Visual crop')} · {path.name}")
        self.geometry("720x640")
        self.minsize(520, 480)
        self.transient(parent)
        self.grab_set()
        self.result: tuple[float, float, float, float] | None = None

        self._path = path
        self._password = password
        self._page_i = max(0, page_index)
        self._page_count = 1
        self._page_w = 1.0
        self._page_h = 1.0
        self._scale = 1.0
        self._photo: ImageTk.PhotoImage | None = None
        self._drag_start: tuple[int, int] | None = None
        self._rect_id: int | None = None
        self._sel: tuple[int, int, int, int] | None = None  # canvas pixels

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            top,
            text=_(
                "Drag a rectangle on the page. Soft crop sets boxes; hard discards outside."
            ),
            text_color=("gray40", "gray70"),
            wraplength=680,
            justify="left",
        ).pack(anchor="w")

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(nav, text="◀", width=36, command=lambda: self._shift_page(-1)).pack(
            side="left"
        )
        self.page_label = ctk.CTkLabel(nav, text="1 / 1", width=80)
        self.page_label.pack(side="left", padx=8)
        ctk.CTkButton(nav, text="▶", width=36, command=lambda: self._shift_page(1)).pack(
            side="left"
        )
        self.coord_label = ctk.CTkLabel(
            nav, text="", text_color=("gray40", "gray70"), font=ctk.CTkFont(size=11)
        )
        self.coord_label.pack(side="right")

        # Canvas for drag-select
        self.canvas = tk.Canvas(self, bg="#2b2b2b", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=12, pady=8)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", self._on_resize)

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(opts, text=_("Apply to:")).pack(side="left")
        self.apply_mode = ctk.CTkSegmentedButton(
            opts, values=["this page", "all pages"]
        )
        self.apply_mode.pack(side="left", padx=8)
        self.apply_mode.set("all pages")
        self.hard_var = ctk.CTkCheckBox(opts, text=_("Hard crop (discard outside)"))
        self.hard_var.pack(side="left", padx=12)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkButton(
            btns, text=_("Cancel"), width=100, fg_color="gray40", command=self._cancel
        ).pack(side="right", padx=4)
        ctk.CTkButton(btns, text=_("Apply crop"), width=120, command=self._apply).pack(
            side="right", padx=4
        )
        ctk.CTkButton(
            btns, text=_("Clear"), width=80, fg_color="gray40", command=self._clear_sel
        ).pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(50, self._load_page)

    def _shift_page(self, delta: int) -> None:
        self._page_i = max(0, min(self._page_count - 1, self._page_i + delta))
        self._clear_sel()
        self._load_page()

    def _load_page(self) -> None:
        try:
            # Page size via render session
            with pdf_render.ThumbnailSession(
                self._path, password=self._password, max_width=64
            ) as sess:
                self._page_count = max(1, sess.page_count)
                self._page_i = min(self._page_i, self._page_count - 1)
            # Render large preview
            cw = max(200, self.canvas.winfo_width() or 640)
            ch = max(200, self.canvas.winfo_height() or 480)
            # Fit page in canvas
            import fitz

            doc = fitz.open(str(self._path))
            try:
                if doc.is_encrypted:
                    doc.authenticate(self._password or "")
                page = doc.load_page(self._page_i)
                pr = page.rect
                self._page_w = float(pr.width)
                self._page_h = float(pr.height)
                scale = min(cw / self._page_w, ch / self._page_h, 2.5)
                self._scale = scale
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            finally:
                doc.close()

            self._photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self._img_w, self._img_h = img.size
            ox = max(0, (cw - self._img_w) // 2)
            oy = max(0, (ch - self._img_h) // 2)
            self._ox, self._oy = ox, oy
            self.canvas.create_image(ox, oy, anchor="nw", image=self._photo, tags="page")
            self.page_label.configure(text=f"{self._page_i + 1} / {self._page_count}")
            if self._sel:
                self._draw_sel(*self._sel)
        except Exception as exc:  # noqa: BLE001
            self.canvas.delete("all")
            self.canvas.create_text(
                20, 20, anchor="nw", fill="white", text=f"Preview failed: {exc}"
            )

    def _on_resize(self, _event=None) -> None:  # noqa: ANN001
        if getattr(self, "_resize_after", None):
            try:
                self.after_cancel(self._resize_after)
            except Exception:  # noqa: BLE001
                pass
        self._resize_after = self.after(200, self._load_page)

    def _on_press(self, event) -> None:  # noqa: ANN001
        self._drag_start = (event.x, event.y)
        self._clear_sel()

    def _on_drag(self, event) -> None:  # noqa: ANN001
        if not self._drag_start:
            return
        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y
        self._sel = (x0, y0, x1, y1)
        self._draw_sel(x0, y0, x1, y1)
        self._update_coord_label()

    def _on_release(self, event) -> None:  # noqa: ANN001
        if not self._drag_start:
            return
        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y
        self._drag_start = None
        if abs(x1 - x0) < 4 or abs(y1 - y0) < 4:
            self._clear_sel()
            return
        self._sel = (x0, y0, x1, y1)
        self._draw_sel(x0, y0, x1, y1)
        self._update_coord_label()

    def _draw_sel(self, x0: int, y0: int, x1: int, y1: int) -> None:
        if self._rect_id is not None:
            try:
                self.canvas.delete(self._rect_id)
            except Exception:  # noqa: BLE001
                pass
        self._rect_id = self.canvas.create_rectangle(
            x0, y0, x1, y1, outline="#3B8ED0", width=2, dash=(4, 2)
        )

    def _clear_sel(self) -> None:
        self._sel = None
        if self._rect_id is not None:
            try:
                self.canvas.delete(self._rect_id)
            except Exception:  # noqa: BLE001
                pass
            self._rect_id = None
        self.coord_label.configure(text="")

    def _canvas_to_pdf(
        self, x0: int, y0: int, x1: int, y1: int
    ) -> tuple[float, float, float, float] | None:
        """Map canvas pixels to PDF bottom-left points relative to page origin."""
        ox = getattr(self, "_ox", 0)
        oy = getattr(self, "_oy", 0)
        scale = self._scale or 1.0
        # Clamp to image area
        def clamp_x(x: int) -> float:
            return max(0.0, min(float(getattr(self, "_img_w", 1) - 1), x - ox))

        def clamp_y(y: int) -> float:
            return max(0.0, min(float(getattr(self, "_img_h", 1) - 1), y - oy))

        cx0, cx1 = sorted((clamp_x(x0), clamp_x(x1)))
        cy0, cy1 = sorted((clamp_y(y0), clamp_y(y1)))
        # Image top-left → PDF bottom-left
        pdf_x0 = cx0 / scale
        pdf_x1 = cx1 / scale
        pdf_y_top = cy0 / scale
        pdf_y_bot = cy1 / scale
        # PDF y from bottom
        py0 = self._page_h - pdf_y_bot
        py1 = self._page_h - pdf_y_top
        if pdf_x1 - pdf_x0 < 2 or py1 - py0 < 2:
            return None
        return (pdf_x0, py0, pdf_x1, py1)

    def _update_coord_label(self) -> None:
        if not self._sel:
            self.coord_label.configure(text="")
            return
        r = self._canvas_to_pdf(*self._sel)
        if not r:
            self.coord_label.configure(text="")
            return
        x0, y0, x1, y1 = r
        self.coord_label.configure(
            text=f"PDF pts: ({x0:.0f}, {y0:.0f})–({x1:.0f}, {y1:.0f})  "
            f"{x1 - x0:.0f}×{y1 - y0:.0f}"
        )

    def _apply(self) -> None:
        if not self._sel:
            from tkinter import messagebox

            messagebox.showinfo(__app_name__, "Drag a rectangle on the page first.", parent=self)
            return
        r = self._canvas_to_pdf(*self._sel)
        if not r:
            from tkinter import messagebox

            messagebox.showinfo(__app_name__, "Selection is too small.", parent=self)
            return
        self.result = r
        # Stash apply options on dialog for caller
        self.apply_all = self.apply_mode.get() == "all pages"
        self.hard = bool(self.hard_var.get())
        self.page_index = self._page_i
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
