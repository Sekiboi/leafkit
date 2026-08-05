"""Full-screen result review before keep (GUI only). Offline only.

Honest: screen preview only — not a print proof. Cancel discards outputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from leafkit import render as pdf_render
from leafkit import tooltips
from leafkit.i18n import _


class ReviewResultDialog(ctk.CTkToplevel):
    """Modal full-screen-ish review: flip pages, Save or Cancel."""

    def __init__(
        self,
        master,
        paths: list[Path],
        *,
        title: str | None = None,
        on_done: Callable[[bool], None] | None = None,
        password: str | None = None,
    ) -> None:
        super().__init__(master)
        self._paths = [Path(p) for p in paths if Path(p).is_file()]
        self._on_done = on_done
        self._password = password
        self._file_i = 0
        self._page_i = 0
        self._page_count = 1
        self._zoom = 1.0
        self._img_ref = None
        self._finished = False
        self._session = None

        self.title(title or _("Review result"))
        self.attributes("-topmost", True)
        try:
            self.state("zoomed")
        except Exception:  # noqa: BLE001
            self.geometry("1000x700")
        self.minsize(720, 520)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.configure(fg_color=("gray95", "gray12"))

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            head,
            text=_("Review result"),
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")
        self.meta_lbl = ctk.CTkLabel(
            head,
            text="",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        )
        self.meta_lbl.pack(side="right")

        ctk.CTkLabel(
            self,
            text=_("Check pages. Save keeps the file. Cancel discards the draft."),
            text_color=("gray35", "gray75"),
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 6))

        self.file_bar = ctk.CTkFrame(self, fg_color="transparent")
        if len(self._paths) > 1:
            self.file_bar.pack(fill="x", padx=16, pady=(0, 4))
            ctk.CTkLabel(self.file_bar, text=_("Files:")).pack(side="left")
            self.file_seg = ctk.CTkSegmentedButton(
                self.file_bar,
                values=[p.name for p in self._paths[:12]],
                command=self._on_file_pick,
            )
            self.file_seg.pack(side="left", padx=8)
            self.file_seg.set(self._paths[0].name)
            if len(self._paths) > 12:
                extra = len(self._paths) - 12
                ctk.CTkLabel(
                    self.file_bar,
                    text=f"+{extra} more (first 12)",
                    text_color=("gray40", "gray70"),
                ).pack(side="left")

        body = ctk.CTkFrame(self, corner_radius=10)
        body.pack(fill="both", expand=True, padx=16, pady=6)
        self.canvas = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.page_lbl = ctk.CTkLabel(self.canvas, text=_("Loading…"))
        self.page_lbl.pack(padx=8, pady=8)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=4)
        b = ctk.CTkButton(nav, text="←", width=44, command=lambda: self._flip(-1))
        b.pack(side="left")
        tooltips.tip(b, "Previous page.")
        self.page_info = ctk.CTkLabel(nav, text="1 / 1", width=100)
        self.page_info.pack(side="left", padx=8)
        b = ctk.CTkButton(nav, text="→", width=44, command=lambda: self._flip(1))
        b.pack(side="left")
        tooltips.tip(b, "Next page.")
        b = ctk.CTkButton(nav, text="−", width=36, command=lambda: self._zoom_by(-0.15))
        b.pack(side="left", padx=(16, 4))
        tooltips.tip(b, "Zoom out.")
        b = ctk.CTkButton(nav, text="+", width=36, command=lambda: self._zoom_by(0.15))
        b.pack(side="left")
        tooltips.tip(b, "Zoom in.")

        ctk.CTkLabel(
            nav,
            text=_("Screen preview only — not a print proof."),
            text_color=("gray45", "gray60"),
            font=ctk.CTkFont(size=11),
        ).pack(side="right")

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=16, pady=(8, 16))
        b = ctk.CTkButton(
            foot,
            text=_("Cancel"),
            width=120,
            height=36,
            fg_color="gray40",
            hover_color="gray30",
            command=self._cancel,
        )
        b.pack(side="left")
        tooltips.tip(b, "Discard this new file. · Does not undo other files.")
        ctk.CTkLabel(
            foot,
            text=_("Esc cancel · Enter save · ← → pages"),
            text_color=("gray45", "gray65"),
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=16)
        b = ctk.CTkButton(
            foot,
            text=_("Save"),
            width=140,
            height=36,
            command=self._save,
        )
        b.pack(side="right")
        tooltips.tip(b, "Keep the new file. · Screen preview ≠ print proof.")

        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Return>", lambda _e: self._save())
        self.bind("<Left>", lambda _e: self._flip(-1))
        self.bind("<Right>", lambda _e: self._flip(1))
        self.bind("<Prior>", lambda _e: self._flip(-1))
        self.bind("<Next>", lambda _e: self._flip(1))

        if not self._paths:
            self.page_lbl.configure(text=_("No file to preview."))
        else:
            self.after(50, self._open_current)

        try:
            self.grab_set()
            self.focus_force()
        except Exception:  # noqa: BLE001
            pass

    def _on_file_pick(self, name: str) -> None:
        for i, p in enumerate(self._paths):
            if p.name == name:
                self._file_i = i
                self._page_i = 0
                self._open_current()
                break

    def _close_session(self) -> None:
        if self._session is not None:
            try:
                self._session.close()
            except Exception:  # noqa: BLE001
                pass
            self._session = None

    def _open_current(self) -> None:
        self._close_session()
        if not self._paths:
            return
        path = self._paths[self._file_i]
        label = path.name
        if label.startswith(".leafkit-review-"):
            label = _("Review draft (not saved yet)")
        self.meta_lbl.configure(text=label)
        if not pdf_render.has_renderer():
            self.page_lbl.configure(
                text=_("Install pymupdf for preview.\nFile is ready — Save or Cancel.")
            )
            self.page_info.configure(text="—")
            return
        try:
            w = int(720 * self._zoom)
            self._session = pdf_render.ThumbnailSession(
                path, password=self._password, max_width=max(200, w)
            )
            self._page_count = max(1, self._session.page_count)
            self._page_i = min(self._page_i, self._page_count - 1)
            self._show_page()
        except Exception as exc:  # noqa: BLE001
            self.page_lbl.configure(
                text=_("Preview failed.\nYou can still Save or Cancel.\n\n") + str(exc)
            )

    def _show_page(self) -> None:
        if self._session is None:
            return
        try:
            path = self._paths[self._file_i]
            w = int(720 * self._zoom)
            if getattr(self._session, "max_width", 0) != max(200, w):
                self._close_session()
                self._session = pdf_render.ThumbnailSession(
                    path, password=self._password, max_width=max(200, w)
                )
                self._page_count = max(1, self._session.page_count)
            img = self._session.get(self._page_i)
            ctk_img = ctk.CTkImage(
                light_image=img, dark_image=img, size=(img.width, img.height)
            )
            self._img_ref = ctk_img
            self.page_lbl.configure(image=ctk_img, text="")
            self.page_info.configure(
                text=f"{self._page_i + 1} / {self._page_count}"
            )
        except Exception as exc:  # noqa: BLE001
            self.page_lbl.configure(image=None, text=str(exc))

    def _flip(self, delta: int) -> None:
        if self._session is None and not self._paths:
            return
        n = self._page_count
        self._page_i = max(0, min(n - 1, self._page_i + delta))
        self._show_page()

    def _zoom_by(self, d: float) -> None:
        self._zoom = max(0.4, min(2.5, self._zoom + d))
        self._open_current()

    def _finish(self, keep: bool) -> None:
        if self._finished:
            return
        self._finished = True
        self._close_session()
        try:
            self.grab_release()
        except Exception:  # noqa: BLE001
            pass
        cb = self._on_done
        try:
            self.destroy()
        except Exception:  # noqa: BLE001
            pass
        if cb:
            cb(keep)

    def _cancel(self) -> None:
        self._finish(False)

    def _save(self) -> None:
        self._finish(True)


def run_review_dialog(
    master,
    paths: list[Path],
    *,
    title: str | None = None,
    password: str | None = None,
) -> bool:
    """Block until user chooses; returns True to keep files."""
    result = {"keep": False}

    def _done(keep: bool) -> None:
        result["keep"] = keep

    dlg = ReviewResultDialog(
        master, paths, title=title, on_done=_done, password=password
    )
    master.wait_window(dlg)
    return bool(result["keep"])
