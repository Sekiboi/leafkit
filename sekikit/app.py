"""Sekikit GUI — offline PDF page toolkit. Free forever."""

from __future__ import annotations

import os
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from sekikit import __app_name__, __version__
from sekikit import jobs
from sekikit import pdf_ops
from sekikit import prefs as app_prefs
from sekikit import render as pdf_render
from sekikit import review_ui
from sekikit import tooltips
from sekikit.i18n import _, init_i18n
from sekikit.ui_organize import OrganizeTabMixin
from sekikit.ui_share import ShareTabMixin

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _HAS_DND = True
except ImportError:
    DND_FILES = None  # type: ignore[assignment]
    TkinterDnD = None  # type: ignore[assignment]
    _HAS_DND = False


APP_TITLE = f"{__app_name__} v{__version__}"
# Designed size: full chrome + toolbars visible. Min size matches so
# the user cannot shrink past a usable, fully-visible layout.
WINDOW_W = 1000
WINDOW_H = 800
WINDOW_SIZE = f"{WINDOW_W}x{WINDOW_H}"
MIN_SIZE = (WINDOW_W, WINDOW_H)
APP_USER_MODEL_ID = "Sekiboi.Sekikit"

from sekikit.ui_constants import (
    MUTED as _MUTED,
    PAGENUM_PRESETS as _PAGENUM_PRESETS,
    ROW_BG as _ROW_BG,
    ROW_BG_SEL as _ROW_BG_SEL,
    ROW_BORDER_SEL as _ROW_BORDER_SEL,
    SURFACE_EMPTY as _SURFACE_EMPTY,
)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def _resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent.parent
    path = base / relative
    if path.is_file():
        return path
    if getattr(sys, "frozen", False):
        alt = Path(sys.executable).resolve().parent / relative
        if alt.is_file():
            return alt
    return path


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            APP_USER_MODEL_ID
        )
    except Exception:  # noqa: BLE001
        pass


def _parse_drop_paths(data: str) -> list[Path]:
    paths: list[Path] = []
    raw = (data or "").strip()
    if not raw:
        return paths
    i = 0
    n = len(raw)
    while i < n:
        if raw[i].isspace():
            i += 1
            continue
        if raw[i] == "{":
            j = raw.find("}", i + 1)
            if j == -1:
                paths.append(Path(raw[i + 1 :]))
                break
            paths.append(Path(raw[i + 1 : j]))
            i = j + 1
        else:
            j = i
            while j < n and not raw[j].isspace():
                j += 1
            paths.append(Path(raw[i:j]))
            i = j
    return paths


def _expand_to_pdfs(paths: list[Path]) -> list[Path]:
    pdfs: list[Path] = []
    for p in paths:
        try:
            if p.is_dir():
                pdfs.extend(sorted(p.glob("*.pdf")))
                pdfs.extend(sorted(p.glob("*.PDF")))
            elif p.is_file() and p.suffix.lower() == ".pdf":
                pdfs.append(p)
        except OSError:
            continue
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in pdfs:
        key = p.resolve() if p.exists() else p
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


if _HAS_DND:

    class _CTkBase(ctk.CTk, TkinterDnD.DnDWrapper):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)  # type: ignore[union-attr]

else:

    class _CTkBase(ctk.CTk):
        pass


class SekikitApp(OrganizeTabMixin, ShareTabMixin, _CTkBase):
    def __init__(self) -> None:
        _set_windows_app_id()
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(*MIN_SIZE)
        self.resizable(True, True)
        self._icon_image = None
        self._header_logo = None
        self._apply_app_icon()
        self.after(250, self._apply_app_icon)
        self.after(500, self._apply_app_icon)

        self._files: list[Path] = []
        self._selected_idx: int = 0
        self._file_rows: list[ctk.CTkFrame] = []
        self._meta_cache: dict[str, dict] = {}
        self._meta_gen: int = 0
        self._busy = False
        self._last_outputs: list[Path] = []
        self._toast_frame: ctk.CTkFrame | None = None
        self._toast_after_id: str | None = None
        self._share_more_open = False
        self._org_items: list[tuple[Path, int]] = []
        self._org_path: Path | None = None
        self._org_selected: set[int] = set()
        self._org_thumbs: list = []
        self._org_buttons: list = []
        self._preview_image = None
        self._preview_pil = None
        self._preview_strip_pos: int | None = None
        self._preview_zoom = 1.0
        self._fs_window = None
        self._fs_zoom = 1.0
        self._fs_image = None
        self._image_files: list[Path] = []
        self._cancel_job = False
        self._org_sessions: dict[str, pdf_render.ThumbnailSession] = {}
        self._org_session_order: list[str] = []
        self._thumb_load_gen = 0
        self._watch_running = False
        self._watch_stop = False
        self._watch_processed: set[str] = set()
        self._watch_thread: threading.Thread | None = None

        self._build_ui()
        self._lock_min_window_size()
        # Re-measure after first paint (fonts/DPI/theme can change req sizes).
        self.after_idle(self._lock_min_window_size)
        self.after(200, self._lock_min_window_size)
        self._setup_drag_drop()
        ready = "Ready — drop PDFs here or click Add. Offline only · free forever."
        if not _HAS_DND:
            ready = "Ready — add PDF files (drag-and-drop package not installed)."
        if not pdf_render.has_renderer():
            ready += " (Install pymupdf for thumbnails.)"
        self._set_status(ready)
        # First launch only: optional diagnostics (default off)
        self.after(400, self._maybe_first_run_diagnostics)

    def _lock_min_window_size(self) -> None:
        """Do not allow shrink past full chrome visibility.

        Desktop practice: if the layout is not reflowable, the floor is the
        size where every control remains fully on-screen. Larger is fine.
        """
        try:
            self.update_idletasks()
            # Designed floor (default geometry).
            min_w, min_h = MIN_SIZE
            # Raise floor if the laid-out chrome needs more (locale, DPI, fonts).
            req_w = int(self.winfo_reqwidth() or 0)
            req_h = int(self.winfo_reqheight() or 0)
            if req_w > min_w:
                min_w = req_w
            if req_h > min_h:
                min_h = req_h
            # Guard against absurd values from transient layout states.
            min_w = min(max(min_w, MIN_SIZE[0]), 1600)
            min_h = min(max(min_h, MIN_SIZE[1]), 1200)
            self.minsize(min_w, min_h)
            # If we are currently smaller than the floor (should be rare), grow.
            try:
                cur_w = int(self.winfo_width())
                cur_h = int(self.winfo_height())
                if cur_w > 1 and cur_h > 1 and (cur_w < min_w or cur_h < min_h):
                    self.geometry(f"{max(cur_w, min_w)}x{max(cur_h, min_h)}")
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            try:
                self.minsize(*MIN_SIZE)
            except Exception:  # noqa: BLE001
                pass

    def _apply_app_icon(self) -> None:
        ico = _resource_path("assets/sekikit.ico")
        png = _resource_path("assets/sekikit.png")
        try:
            if ico.is_file():
                self.iconbitmap(default=str(ico))
                self.iconbitmap(str(ico))
            if png.is_file():
                from PIL import Image, ImageTk

                img = Image.open(png).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
                self._icon_image = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._icon_image)
        except Exception:  # noqa: BLE001
            pass

    def _password(self) -> str | None:
        raw = self.password_entry.get().strip()
        return raw if raw else None

    def _pwd_kwargs(self) -> dict:
        """Global field + per-file session cache (jobs.password_cache)."""
        fallback = self._password()
        return {
            "password": fallback,
            "password_provider": jobs.make_password_provider(fallback),
        }

    def _prompt_and_cache_password(self, path: Path) -> str | None:
        """Ask for a password for one file and store it for this session."""
        from tkinter import simpledialog

        cached = jobs.password_cache_get(path)
        if cached:
            return cached
        pwd = simpledialog.askstring(
            __app_name__,
            f"Password for:\n{path.name}",
            show="*",
            parent=self,
        )
        if pwd:
            jobs.password_cache_set(path, pwd)
            if not self.password_entry.get().strip():
                self.password_entry.delete(0, "end")
                self.password_entry.insert(0, pwd)
        return pwd

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)

        logo_col = 0
        png = _resource_path("assets/sekikit.png")
        if png.is_file():
            try:
                from PIL import Image

                self._header_logo = ctk.CTkImage(
                    light_image=Image.open(png),
                    dark_image=Image.open(png),
                    size=(40, 40),
                )
                ctk.CTkLabel(header, image=self._header_logo, text="").grid(
                    row=0, column=0, rowspan=2, sticky="w", padx=(0, 12)
                )
                logo_col = 1
            except Exception:  # noqa: BLE001
                logo_col = 0

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.grid(row=0, column=logo_col, rowspan=2, sticky="w")

        ctk.CTkLabel(
            title_block,
            text=_("Sekikit"),
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_block,
            text=_("Your PDFs stay on this PC · free forever · no accounts"),
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        file_bar = ctk.CTkFrame(body, fg_color="transparent")
        file_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        b_add = ctk.CTkButton(
            file_bar,
            text=_("Add PDFs…"),
            width=110,
            height=32,
            command=self._add_files,
        )
        b_add.pack(side="left", padx=(0, 6))
        self._tip(b_add, "Add PDFs (or drop files). Offline only.")
        b_rm = ctk.CTkButton(
            file_bar,
            text=_("Remove"),
            width=80,
            height=32,
            command=self._remove_selected,
            fg_color="gray40",
            hover_color="gray30",
        )
        b_rm.pack(side="left", padx=4)
        self._tip(b_rm, "Remove selected file from the list (not from disk).")
        b_cl = ctk.CTkButton(
            file_bar,
            text=_("Clear"),
            width=70,
            height=32,
            command=self._clear_files,
            fg_color="gray40",
            hover_color="gray30",
        )
        b_cl.pack(side="left", padx=4)
        self._tip(b_cl, "Clear the list. Files on disk stay.")
        b_up = ctk.CTkButton(
            file_bar, text="↑", width=36, height=32, command=lambda: self._move(-1)
        )
        b_up.pack(side="left", padx=(12, 3))
        self._tip(b_up, "Move selected file up (merge order).")
        b_dn = ctk.CTkButton(
            file_bar, text="↓", width=36, height=32, command=lambda: self._move(1)
        )
        b_dn.pack(side="left", padx=3)
        self._tip(b_dn, "Move selected file down (merge order).")
        b_last = ctk.CTkButton(
            file_bar,
            text=_("Open last output"),
            width=130,
            height=32,
            command=self._open_last_output,
            fg_color="gray40",
            hover_color="gray30",
        )
        b_last.pack(side="right")
        self._tip(b_last, "Open the last saved result file.")

        self.file_panel = ctk.CTkFrame(body, corner_radius=10)
        self.file_panel.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self.file_panel.grid_columnconfigure(0, weight=1)
        self.file_panel.grid_rowconfigure(0, weight=1)
        self.file_scroll = ctk.CTkScrollableFrame(
            self.file_panel, fg_color="transparent", height=110
        )
        self.file_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        select_bar = ctk.CTkFrame(body, fg_color="transparent")
        select_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 2))
        self.sel_label = ctk.CTkLabel(
            select_bar,
            text=_("No file selected"),
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.sel_label.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(select_bar, text=_("Password:")).pack(side="left", padx=(8, 4))
        self.password_entry = ctk.CTkEntry(
            select_bar, width=120, show="•", placeholder_text="if needed"
        )
        self.password_entry.pack(side="left")
        self.password_entry.bind("<FocusOut>", lambda _e: self._retry_meta_after_password())
        self.password_entry.bind("<Return>", lambda _e: self._retry_meta_after_password())
        self._tip(
            self.password_entry,
            "PDF password if needed. · Session only — never uploaded or saved to disk.",
        )
        ctk.CTkLabel(
            select_bar,
            text=_("never uploaded"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=8)

        quick = ctk.CTkFrame(body, fg_color="transparent")
        quick.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 2))
        ctk.CTkLabel(
            quick,
            text=_("Quick:"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 6))
        self._nav_anchors: dict[str, tuple[object, object]] = {}
        quick_tips = {
            "Organize": "Thumbs, reorder, extract/delete. · Needs pymupdf for previews.",
            "Merge": "Combine listed PDFs in list order.",
            "Compress": "Jump to Share → Compress.",
            "Page #": "Jump to Share → Page numbers.",
            "Split": "Split one PDF into several files.",
        }
        for label, tab_name, anchor in (
            (_("Organize"), "Organize", None),
            (_("Merge"), "Merge", None),
            (_("Compress"), "Share", "compress"),
            (_("Split"), "Split", None),
            (_("Page #"), "Share", "page_numbers"),
        ):
            qb = ctk.CTkButton(
                quick,
                text=label,
                width=88,
                height=28,
                fg_color=("gray85", "gray30"),
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray40"),
                command=lambda t=tab_name, a=anchor: self._go_tab(t, anchor=a),
            )
            qb.pack(side="left", padx=3)
            tip_key = (
                "Compress"
                if label in (_("Compress"), "Compress")
                else "Page #"
                if label in (_("Page #"), "Page #")
                else tab_name
            )
            self._tip(qb, quick_tips.get(tip_key, f"Open {tab_name} tab."))

        self.tabs = ctk.CTkTabview(body)
        self.tabs.grid(row=4, column=0, sticky="nsew", padx=12, pady=(6, 12))
        body.grid_rowconfigure(4, weight=1)
        # Tab names stay English (API keys for tabs.tab(...)).
        for name in (
            "Organize",
            "Share",
            "Merge",
            "Mix",
            "Extract",
            "Delete",
            "Insert",
            "Split",
            "Rotate",
            "Watch",
        ):
            self.tabs.add(name)

        self._build_organize_tab()
        self._build_share_tab()
        self._build_merge_tab()
        self._build_mix_tab()
        self._build_extract_tab()
        self._build_delete_tab()
        self._build_insert_tab()
        self._build_split_tab()
        self._build_rotate_tab()
        self._build_watch_tab()
        self._refresh_list()

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 12))
        footer.grid_columnconfigure(0, weight=1)

        self.status = ctk.CTkLabel(
            footer,
            text="",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray80"),
        )
        self.status.grid(row=0, column=0, sticky="ew")
        foot_row = ctk.CTkFrame(footer, fg_color="transparent")
        foot_row.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkLabel(
            foot_row,
            text=_("MIT · free forever · offline only · github.com/Sekiboi/sekikit"),
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        ).pack(side="left")
        b_about = ctk.CTkButton(
            foot_row,
            text=_("About"),
            width=70,
            height=26,
            fg_color="gray40",
            hover_color="gray30",
            command=self._show_about,
        )
        b_about.pack(side="right", padx=(6, 0))
        self._tip(b_about, "Version, shortcuts, privacy. F1.")
        b_set = ctk.CTkButton(
            foot_row,
            text=_("Settings"),
            width=80,
            height=26,
            fg_color="gray40",
            hover_color="gray30",
            command=self._show_settings,
        )
        b_set.pack(side="right")
        self._tip(
            b_set,
            "Review before save: Off / Risk only / Always. · Local prefs only.",
        )

        self.bind("<Control-o>", lambda _e: self._add_files())
        self.bind("<Control-l>", lambda _e: self._org_load())
        self.bind("<Control-A>", lambda _e: self._org_add_selected())
        self.bind("<Control-s>", lambda _e: self._org_save_order())
        self.bind("<F1>", lambda _e: self._show_about())
        self.bind("<Control-comma>", lambda _e: self._show_settings())
        self.bind("<Escape>", self._request_cancel)
        self.bind("<Delete>", self._on_delete_key)
        self.bind("<Up>", self._on_arrow_up)
        self.bind("<Down>", self._on_arrow_down)

    def _setup_drag_drop(self) -> None:
        if not _HAS_DND or DND_FILES is None:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            self.dnd_bind("<<DragLeave>>", self._on_drag_leave)
        except Exception:  # noqa: BLE001
            pass

    def _on_drag_enter(self, event):  # noqa: ANN001
        self._set_status("Drop PDF files (or a folder of PDFs) to add them…")
        return event.action if hasattr(event, "action") else None

    def _on_drag_leave(self, event):  # noqa: ANN001
        self._set_status("Ready — drop PDFs here or click Add.")
        return event.action if hasattr(event, "action") else None

    def _go_tab(self, name: str, *, anchor: str | None = None) -> None:
        """Jump to a tool tab; optional anchor scrolls to a section inside the tab."""
        try:
            self.tabs.set(name)
        except Exception:  # noqa: BLE001
            pass
        if anchor:
            # Defer until tab is laid out
            self.after(30, lambda a=anchor: self._scroll_to_anchor(a))
            self.after(120, lambda a=anchor: self._scroll_to_anchor(a))
            return
        if name == "Share" and hasattr(self, "share_scroll"):
            try:
                self.share_scroll._parent_canvas.yview_moveto(0)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass

    def _register_nav_anchor(
        self, key: str, scroll: object, widget: object
    ) -> None:
        """Remember a widget inside a CTkScrollableFrame for Quick jumps."""
        if not hasattr(self, "_nav_anchors") or self._nav_anchors is None:
            self._nav_anchors = {}
        self._nav_anchors[key] = (scroll, widget)

    def _scroll_to_anchor(self, key: str) -> None:
        """Scroll parent CTkScrollableFrame so anchor widget is near the top."""
        anchors = getattr(self, "_nav_anchors", None) or {}
        pair = anchors.get(key)
        if not pair:
            return
        scroll, widget = pair
        try:
            # Expand "More tools" if anchor lives there
            if key in (
                "resize",
                "reverse",
                "stamp",
                "extract_text",
                "images",
                "nup",
                "grayscale",
                "flatten",
            ):
                if hasattr(self, "share_more") and not getattr(
                    self, "_share_more_open", False
                ):
                    self._toggle_share_more()

            canvas = getattr(scroll, "_parent_canvas", None)
            if canvas is None:
                return
            try:
                widget.update_idletasks()
                scroll.update_idletasks()  # type: ignore[union-attr]
                canvas.update_idletasks()
            except Exception:  # noqa: BLE001
                pass

            # Position of widget relative to the scrollable frame
            y = float(widget.winfo_y())
            # Walk parents until we reach the frame that is the canvas window
            parent = widget.master
            while parent is not None and parent is not scroll:
                try:
                    y += float(parent.winfo_y())
                except Exception:  # noqa: BLE001
                    break
                parent = getattr(parent, "master", None)

            bbox = canvas.bbox("all")
            if not bbox:
                return
            total_h = max(1.0, float(bbox[3] - bbox[1]))
            view_h = max(1.0, float(canvas.winfo_height()))
            # Leave a small pad above the section
            target = max(0.0, y - 8.0)
            max_scroll = max(0.0, total_h - view_h)
            frac = 0.0 if max_scroll < 1 else min(1.0, target / total_h)
            canvas.yview_moveto(frac)

            # Brief highlight so the target is obvious
            try:
                widget.configure(border_width=2, border_color=("#3B8ED0", "#4A9FE0"))
                self.after(
                    900,
                    lambda w=widget: w.configure(border_width=0),
                )
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass

    def _on_drop(self, event) -> None:  # noqa: ANN001
        try:
            pdfs = _expand_to_pdfs(_parse_drop_paths(event.data))
            if not pdfs:
                self._set_status("Drop ignored — no PDF files found.")
                return
            self._ingest_paths(pdfs)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Drop failed: {exc}")

    def _tab_scroll(self, tab) -> ctk.CTkScrollableFrame:
        """Scrollable body for a tab so content is never cut off."""
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        return scroll

    def _section(
        self,
        parent,
        title: str,
        hint: str = "",
        *,
        anchor: str | None = None,
    ):
        """Card-style section for Share/tool tabs.

        anchor: optional key for Quick-menu scroll targets (_go_tab(..., anchor=)).
        """
        box = ctk.CTkFrame(parent, corner_radius=8)
        box.pack(fill="x", pady=(0, 10), padx=4)
        ctk.CTkLabel(box, text=_(title), font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=12, pady=(10, 2)
        )
        if hint:
            ctk.CTkLabel(
                box,
                text=_(hint),
                text_color=("gray40", "gray70"),
                font=ctk.CTkFont(size=12),
                wraplength=860,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 4))
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(2, 12))
        if anchor:
            self._register_nav_anchor(anchor, parent, box)
        return inner

    @staticmethod
    def _tip(widget, text: str) -> None:
        """Short hover help. Prefer one line; use · for a limit warning."""
        tooltips.tip(widget, text)

    def _add_renumber_checkbox(
        self,
        parent,
        attr: str,
        *,
        text: str | None = None,
    ) -> ctk.CTkCheckBox:
        """Consistent 'renumber after…' control for page-structure ops."""
        label = text or _(
            "Renumber after (cover footer band → continuous 1…N)"
        )
        box = ctk.CTkCheckBox(parent, text=label)
        box.pack(anchor="w", pady=(4, 2))
        setattr(self, attr, box)
        self._tip(
            box,
            "After this job: white band + continuous page #. "
            "· Band expands over detected margin text (not OCR). Strip content is hidden.",
        )
        return box

    def _renumber_style_kwargs(self) -> dict:
        """Match Share page-number style when available; else defaults."""
        fmt = "{n} / {total}"
        pos = "footer"
        align = "center"
        start = 1
        try:
            if hasattr(self, "pagenum_preset"):
                preset = self.pagenum_preset.get()
                tmpl = _PAGENUM_PRESETS.get(preset, "")
                if preset == "Custom" or not tmpl:
                    # Enable disabled entry briefly to read value.
                    try:
                        was = str(self.pagenum_format.cget("state"))
                    except Exception:  # noqa: BLE001
                        was = "normal"
                    self.pagenum_format.configure(state="normal")
                    fmt = self.pagenum_format.get().strip() or fmt
                    if was == "disabled":
                        self.pagenum_format.configure(state="disabled")
                else:
                    fmt = tmpl
                pos = self.pagenum_pos.get() or pos
                align = self.pagenum_align.get() or align
                try:
                    start = int(self.pagenum_start.get().strip() or "1")
                except ValueError:
                    start = 1
        except Exception:  # noqa: BLE001
            pass
        return {
            "position": pos,
            "align": align,
            "format_str": fmt,
            "start": start,
        }

    def _op_then_renumber(
        self,
        produce,
        final_out: Path,
        *,
        do_renumber: bool,
        pwd_kw: dict,
    ) -> Path:
        """Run produce(out_path)->Path; optionally renumber into final_out."""
        style = self._renumber_style_kwargs()
        return pdf_ops.op_then_renumber(
            produce,
            final_out,
            do_renumber=do_renumber,
            renumber_kwargs=style,
            password=pwd_kw.get("password"),
            password_provider=pwd_kw.get("password_provider"),
        )

    def _paths_then_renumber(
        self,
        paths: list[Path],
        *,
        do_renumber: bool,
        pwd_kw: dict,
    ) -> list[Path]:
        """Optionally renumber each output file (e.g. after split)."""
        if not do_renumber or not paths:
            return paths
        style = self._renumber_style_kwargs()
        out: list[Path] = []
        for p in paths:
            dest = pdf_ops.default_output_next_to(p, "_renumbered")
            out.append(pdf_ops.renumber_pages(p, dest, **style, **pwd_kw))
        return out

    def _build_merge_tab(self) -> None:
        tab = self.tabs.tab("Merge")
        scroll = self._tab_scroll(tab)
        ctk.CTkLabel(
            scroll,
            text=_("Combine listed PDFs in order (↑↓ to reorder). Optional per-file page ranges."),
            anchor="w",
        ).pack(fill="x", pady=(8, 4), padx=4)
        ctk.CTkLabel(
            scroll,
            text=_("Ranges: one line per file, same order as the list. Blank line = all pages. Example: 1-3"),
            anchor="w",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(fill="x", pady=(0, 6), padx=4)
        self.merge_ranges = ctk.CTkTextbox(scroll, height=70)
        self.merge_ranges.pack(fill="x", pady=4, padx=4)
        self._tip(
            self.merge_ranges,
            "Optional: one page range per file, same order as list. Blank line = all.",
        )

        opts = ctk.CTkFrame(scroll, fg_color="transparent")
        opts.pack(fill="x", pady=6, padx=4)
        self.merge_bookmarks = ctk.CTkCheckBox(opts, text=_("Preserve bookmarks (best-effort)"))
        self.merge_bookmarks.pack(side="left", padx=(0, 16))
        self._tip(
            self.merge_bookmarks,
            "Keep outlines when possible. · Best-effort — complex outlines may not transfer fully.",
        )
        ctk.CTkLabel(opts, text=_("Fit page size:")).pack(side="left")
        self.merge_page_size = ctk.CTkSegmentedButton(
            opts, values=["none", "a4", "letter", "legal"]
        )
        self.merge_page_size.pack(side="left", padx=8)
        self.merge_page_size.set("none")
        self._tip(self.merge_page_size, "Scale pages to a common size (or none).")

        opts2 = ctk.CTkFrame(scroll, fg_color="transparent")
        opts2.pack(fill="x", pady=(0, 6), padx=4)
        self._add_renumber_checkbox(
            opts2,
            "merge_renumber",
            text=_("Renumber after merge (cover band → continuous 1…N)"),
        )

        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=4, padx=4)
        b = ctk.CTkButton(row, text=_("Choose output…"), width=120, command=self._pick_merge_out)
        b.pack(side="left")
        self._tip(b, "Pick output path (optional).")
        self.merge_out = ctk.CTkEntry(row, placeholder_text="Output (optional)")
        self.merge_out.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._tip(self.merge_out, "Blank = auto name next to first file. Never overwrites inputs.")
        b = ctk.CTkButton(scroll, text=_("Merge PDFs"), height=36, command=self._run_merge)
        b.pack(fill="x", pady=(10, 16), padx=4)
        self._tip(b, "Combine listed PDFs in order → new file.")

    def _build_mix_tab(self) -> None:
        tab = self.tabs.tab("Mix")
        ctk.CTkLabel(
            tab,
            text=_(
                "Alternate pages from all listed PDFs (page1 of each, then page2 of each…). "
                "Useful for single-sided scans."
            ),
            anchor="w",
            wraplength=780,
        ).pack(fill="x", pady=(8, 8))
        self.mix_reverse = ctk.CTkCheckBox(
            tab, text=_("Reverse second file (classic duplex mix)")
        )
        self.mix_reverse.pack(anchor="w", pady=4)
        self._tip(self.mix_reverse, "Reverse page order of the second PDF (duplex scans).")
        self._add_renumber_checkbox(
            tab,
            "mix_renumber",
            text=_("Renumber after mix (cover band → continuous 1…N)"),
        )
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        b = ctk.CTkButton(row, text=_("Choose output…"), width=120, command=self._pick_mix_out)
        b.pack(side="left")
        self._tip(b, "Pick output path (optional).")
        self.mix_out = ctk.CTkEntry(row, placeholder_text="Output (optional)")
        self.mix_out.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._tip(self.mix_out, "Blank = auto name. Never overwrites inputs.")
        b = ctk.CTkButton(tab, text=_("Mix PDFs"), height=36, command=self._run_mix)
        b.pack(fill="x", pady=(12, 8))
        self._tip(b, "Alternate pages from listed PDFs → new file.")

    def _build_extract_tab(self) -> None:
        tab = self.tabs.tab("Extract")
        ctk.CTkLabel(
            tab,
            text=_("Keep only these pages from the selected PDF (1-based)."),
            anchor="w",
        ).pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(
            tab,
            text=_("Examples:  1-3   ·   2,5,9   ·   1,4-6,10-"),
            anchor="w",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=_("Pages:")).pack(side="left")
        self.extract_range = ctk.CTkEntry(row, width=220, placeholder_text="e.g. 2-5, 9")
        self.extract_range.pack(side="left", padx=8)
        self._tip(self.extract_range, "1-based ranges, e.g. 1-3, 5, 8-")
        self._add_renumber_checkbox(
            tab,
            "extract_renumber",
            text=_("Renumber after extract (cover band → continuous 1…N)"),
        )
        row2 = ctk.CTkFrame(tab, fg_color="transparent")
        row2.pack(fill="x", pady=4)
        b = ctk.CTkButton(row2, text=_("Choose output…"), width=120, command=self._pick_extract_out)
        b.pack(side="left")
        self._tip(b, "Pick output path (optional).")
        self.extract_out = ctk.CTkEntry(row2, placeholder_text="Output (optional)")
        self.extract_out.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._tip(self.extract_out, "Blank = auto name. Never overwrites input.")
        b = ctk.CTkButton(tab, text=_("Extract pages"), height=36, command=self._run_extract)
        b.pack(fill="x", pady=(12, 8))
        self._tip(b, "Keep only these pages → new PDF.")

    def _build_delete_tab(self) -> None:
        tab = self.tabs.tab("Delete")
        ctk.CTkLabel(
            tab,
            text=_("Remove pages from the selected PDF; remaining pages are saved as a new file."),
            anchor="w",
        ).pack(fill="x", pady=(8, 8))
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=_("Delete pages:")).pack(side="left")
        self.delete_range = ctk.CTkEntry(row, width=220, placeholder_text="e.g. 2, 5-7")
        self.delete_range.pack(side="left", padx=8)
        self._tip(self.delete_range, "Pages to remove (1-based). Original file is kept.")
        self._add_renumber_checkbox(
            tab,
            "delete_renumber",
            text=_("Renumber after delete (cover band → continuous 1…N)"),
        )
        row2 = ctk.CTkFrame(tab, fg_color="transparent")
        row2.pack(fill="x", pady=4)
        b = ctk.CTkButton(row2, text=_("Choose output…"), width=120, command=self._pick_delete_out)
        b.pack(side="left")
        self._tip(b, "Pick output path (optional).")
        self.delete_out = ctk.CTkEntry(row2, placeholder_text="Output (optional)")
        self.delete_out.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._tip(self.delete_out, "Blank = auto name. Never overwrites input.")
        b = ctk.CTkButton(tab, text=_("Delete pages"), height=36, command=self._run_delete)
        b.pack(fill="x", pady=(12, 8))
        self._tip(b, "Save remaining pages → new file. · Original stays on disk.")

    def _build_insert_tab(self) -> None:
        tab = self.tabs.tab("Insert")
        ctk.CTkLabel(
            tab,
            text=_(
                "Insert pages from one PDF into another. "
                "Selected row = base file. Insert file = next row (or pick path)."
            ),
            anchor="w",
            wraplength=780,
        ).pack(fill="x", pady=(8, 8))
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=_("Insert before page:")).pack(side="left")
        self.insert_at = ctk.CTkEntry(row, width=50)
        self.insert_at.pack(side="left", padx=8)
        self.insert_at.insert(0, "1")
        self._tip(self.insert_at, "1-based insert position in the base PDF.")
        ctk.CTkLabel(row, text=_("(1 = start)")).pack(side="left")
        row2 = ctk.CTkFrame(tab, fg_color="transparent")
        row2.pack(fill="x", pady=4)
        ctk.CTkLabel(row2, text=_("Insert file pages (blank=all):")).pack(side="left")
        self.insert_spec = ctk.CTkEntry(row2, width=160, placeholder_text="optional e.g. 1-2")
        self.insert_spec.pack(side="left", padx=8)
        self._tip(self.insert_spec, "Pages from insert PDF. Blank = all.")
        row3 = ctk.CTkFrame(tab, fg_color="transparent")
        row3.pack(fill="x", pady=4)
        b = ctk.CTkButton(row3, text=_("Insert PDF…"), width=120, command=self._pick_insert_src)
        b.pack(side="left")
        self._tip(b, "Choose the PDF to insert from.")
        self.insert_src = ctk.CTkEntry(row3, placeholder_text="Defaults to next file in list")
        self.insert_src.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._tip(self.insert_src, "Insert source path, or next list file.")
        row4 = ctk.CTkFrame(tab, fg_color="transparent")
        row4.pack(fill="x", pady=4)
        b = ctk.CTkButton(row4, text=_("Choose output…"), width=120, command=self._pick_insert_out)
        b.pack(side="left")
        self._tip(b, "Pick output path (optional).")
        self.insert_out = ctk.CTkEntry(row4, placeholder_text="Output (optional)")
        self.insert_out.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._tip(self.insert_out, "Blank = auto name. Never overwrites inputs.")
        self._add_renumber_checkbox(
            tab,
            "insert_renumber",
            text=_("Renumber after insert (cover band → continuous 1…N)"),
        )
        b = ctk.CTkButton(tab, text=_("Insert pages"), height=36, command=self._run_insert)
        b.pack(fill="x", pady=(12, 8))
        self._tip(b, "Insert into base PDF → new file.")

    def _build_split_tab(self) -> None:
        tab = self.tabs.tab("Split")
        scroll = self._tab_scroll(tab)
        ctk.CTkLabel(
            scroll,
            text=_("Split the selected PDF into multiple files. Scroll if needed."),
            anchor="w",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(fill="x", pady=(4, 8), padx=4)

        self.split_mode = ctk.StringVar(value="each")

        def radio(text: str, value: str, tip: str) -> None:
            rb = ctk.CTkRadioButton(
                scroll, text=text, variable=self.split_mode, value=value
            )
            rb.pack(anchor="w", pady=3, padx=8)
            self._tip(rb, tip)

        radio("One file per page", "each", "One output PDF per page.")
        row_n = ctk.CTkFrame(scroll, fg_color="transparent")
        row_n.pack(fill="x", pady=3, padx=8)
        rb = ctk.CTkRadioButton(
            row_n, text=_("Every N pages:"), variable=self.split_mode, value="every_n"
        )
        rb.pack(side="left")
        self._tip(rb, "Chunk into groups of N pages.")
        self.split_n = ctk.CTkEntry(row_n, width=50)
        self.split_n.pack(side="left", padx=8)
        self.split_n.insert(0, "2")
        self._tip(self.split_n, "Pages per output file.")

        row_at = ctk.CTkFrame(scroll, fg_color="transparent")
        row_at.pack(fill="x", pady=3, padx=8)
        rb = ctk.CTkRadioButton(
            row_at, text=_("At page numbers:"), variable=self.split_mode, value="at_pages"
        )
        rb.pack(side="left")
        self._tip(rb, "Split before these 1-based page numbers.")
        self.split_at = ctk.CTkEntry(row_at, width=160, placeholder_text="e.g. 3, 7")
        self.split_at.pack(side="left", padx=8)
        self._tip(self.split_at, "e.g. 3, 7 — splits before those pages.")

        radio("Odd / even pages → two files", "even_odd", "Two files: odd pages and even pages.")

        row_sz = ctk.CTkFrame(scroll, fg_color="transparent")
        row_sz.pack(fill="x", pady=3, padx=8)
        rb = ctk.CTkRadioButton(
            row_sz, text=_("By max size (MB):"), variable=self.split_mode, value="size"
        )
        rb.pack(side="left")
        self._tip(rb, "Split when chunk approaches this size. · Approximate, not exact.")
        self.split_mb = ctk.CTkEntry(row_sz, width=60)
        self.split_mb.pack(side="left", padx=8)
        self.split_mb.insert(0, "2")
        self._tip(self.split_mb, "Max size in MB per part (approx).")

        row_bm = ctk.CTkFrame(scroll, fg_color="transparent")
        row_bm.pack(fill="x", pady=3, padx=8)
        rb = ctk.CTkRadioButton(
            row_bm, text=_("At bookmarks, level:"), variable=self.split_mode, value="bookmarks"
        )
        rb.pack(side="left")
        self._tip(
            rb,
            "Split at outline entries. · Best-effort if bookmarks are missing/odd.",
        )
        self.split_bm_level = ctk.CTkEntry(row_bm, width=40)
        self.split_bm_level.pack(side="left", padx=8)
        self.split_bm_level.insert(0, "1")
        self._tip(self.split_bm_level, "Bookmark outline level (1 = top).")

        self._add_renumber_checkbox(
            scroll,
            "split_renumber",
            text=_("Renumber each part after split (cover band → 1…N per file)"),
        )
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(12, 4), padx=8)
        b = ctk.CTkButton(row, text=_("Output folder…"), width=120, command=self._pick_split_dir)
        b.pack(side="left")
        self._tip(b, "Folder for split parts.")
        self.split_dir = ctk.CTkEntry(row, placeholder_text="Folder (optional)")
        self.split_dir.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._tip(self.split_dir, "Blank = auto folder next to source.")
        b = ctk.CTkButton(scroll, text=_("Split PDF"), height=36, command=self._run_split)
        b.pack(fill="x", pady=(10, 16), padx=8)
        self._tip(b, "Write multiple PDFs. · Source file is not deleted.")

    def _build_rotate_tab(self) -> None:
        tab = self.tabs.tab("Rotate")
        ctk.CTkLabel(
            tab, text=_("Rotate pages of the selected PDF (clockwise)."), anchor="w"
        ).pack(fill="x", pady=(8, 8))
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=_("Degrees:")).pack(side="left")
        self.rotate_deg = ctk.CTkSegmentedButton(row, values=["90", "180", "270"])
        self.rotate_deg.pack(side="left", padx=8)
        self.rotate_deg.set("90")
        self._tip(self.rotate_deg, "Clockwise rotation.")
        row2 = ctk.CTkFrame(tab, fg_color="transparent")
        row2.pack(fill="x", pady=4)
        ctk.CTkLabel(row2, text=_("Pages (blank = all):")).pack(side="left")
        self.rotate_range = ctk.CTkEntry(row2, width=200, placeholder_text="e.g. 1-2")
        self.rotate_range.pack(side="left", padx=8)
        self._tip(self.rotate_range, "Optional range. Blank = all pages.")
        row3 = ctk.CTkFrame(tab, fg_color="transparent")
        row3.pack(fill="x", pady=4)
        b = ctk.CTkButton(row3, text=_("Choose output…"), width=120, command=self._pick_rotate_out)
        b.pack(side="left")
        self._tip(b, "Pick output path (optional).")
        self.rotate_out = ctk.CTkEntry(row3, placeholder_text="Output (optional)")
        self.rotate_out.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._tip(self.rotate_out, "Blank = auto name. Never overwrites input.")
        b = ctk.CTkButton(tab, text=_("Rotate pages"), height=36, command=self._run_rotate)
        b.pack(fill="x", pady=(12, 8))
        self._tip(b, "Rotate → new PDF.")

    def _cache_key(self, path: Path) -> str:
        try:
            return str(path.resolve())
        except OSError:
            return str(path)

    def _format_size(self, n: int) -> str:
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n // 1024} KB"
        return f"{n / (1024 * 1024):.1f} MB"

    def _refresh_list(self) -> None:
        """Rebuild clickable rows. Page counts load async (cached) for snappy UI."""
        for w in self._file_rows:
            try:
                w.destroy()
            except Exception:  # noqa: BLE001
                pass
        self._file_rows.clear()

        for child in self.file_scroll.winfo_children():
            try:
                child.destroy()
            except Exception:  # noqa: BLE001
                pass

        if not self._files:
            self._selected_idx = 0
            empty = ctk.CTkFrame(
                self.file_scroll,
                fg_color=_SURFACE_EMPTY,
                corner_radius=12,
                border_width=1,
                border_color=("gray85", "gray28"),
            )
            empty.pack(fill="both", expand=True, pady=12, padx=8)
            ctk.CTkLabel(
                empty,
                text=_("Drop PDFs here"),
                font=ctk.CTkFont(size=18, weight="bold"),
            ).pack(pady=(28, 6))
            ctk.CTkLabel(
                empty,
                text=_(
                    "or click Add · folders work too\n"
                    "Nothing leaves this PC · free forever"
                ),
                text_color=_MUTED,
                font=ctk.CTkFont(size=13),
                justify="center",
            ).pack(pady=(0, 12))
            ctk.CTkButton(
                empty,
                text=_("Add PDFs…"),
                width=140,
                height=34,
                command=self._add_files,
            ).pack(pady=(0, 8))
            ctk.CTkLabel(
                empty,
                text=_("Quick: Organize · Merge · Compress · Split"),
                text_color=_MUTED,
                font=ctk.CTkFont(size=11),
            ).pack(pady=(0, 24))
            self._update_sel_label()
            return

        if self._selected_idx >= len(self._files):
            self._selected_idx = max(0, len(self._files) - 1)

        self._meta_gen += 1
        gen = self._meta_gen
        need_async: list[tuple[int, Path]] = []

        for i, p in enumerate(self._files):
            row = self._make_file_row(i, p)
            self._file_rows.append(row)
            key = self._cache_key(p)
            meta = self._meta_cache.get(key)
            try:
                mtime = p.stat().st_mtime_ns
            except OSError:
                mtime = None
            if (
                meta
                and mtime is not None
                and meta.get("mtime") == mtime
                and (meta.get("pages") is not None or meta.get("error"))
            ):
                self._apply_meta_to_row(i, meta)
            else:
                if meta and meta.get("size"):
                    self._apply_meta_to_row(
                        i, {"size": meta["size"], "pages": None, "error": None}
                    )
                need_async.append((i, p))

        self._update_sel_label()
        if need_async:
            pwd_snap = self._password()
            threading.Thread(
                target=self._load_meta_async,
                args=(list(need_async), gen, pwd_snap),
                daemon=True,
            ).start()

    def _make_file_row(self, index: int, path: Path) -> ctk.CTkFrame:
        selected = index == self._selected_idx
        row = ctk.CTkFrame(
            self.file_scroll,
            corner_radius=8,
            fg_color=_ROW_BG_SEL if selected else _ROW_BG,
            border_width=2 if selected else 0,
            border_color=_ROW_BORDER_SEL,
            cursor="hand2",
        )
        row.pack(fill="x", pady=3, padx=2)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        name_lbl = ctk.CTkLabel(
            left,
            text=f"{index + 1}.  {path.name}",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        name_lbl.pack(fill="x")
        path_lbl = ctk.CTkLabel(
            left,
            text=str(path),
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        )
        path_lbl.pack(fill="x")

        meta_lbl = ctk.CTkLabel(
            row,
            text=_("…"),
            width=120,
            anchor="e",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray75"),
        )
        meta_lbl.pack(side="right", padx=12)
        row._meta_lbl = meta_lbl  # type: ignore[attr-defined]
        row._path = path  # type: ignore[attr-defined]
        row._index = index  # type: ignore[attr-defined]

        def _bind(widget) -> None:  # noqa: ANN001
            widget.bind("<Button-1>", lambda _e, i=index: self._select_file(i))
            widget.bind(
                "<Double-Button-1>",
                lambda _e, i=index: self._select_file(i, open_org=True),
            )

        for w in (row, left, name_lbl, path_lbl, meta_lbl):
            _bind(w)
        self._tip(
            row,
            "Click to select · double-click → Organize. · File stays on disk until you save an op.",
        )
        return row

    def _apply_meta_to_row(self, index: int, meta: dict) -> None:
        if index < 0 or index >= len(self._file_rows):
            return
        row = self._file_rows[index]
        lbl = getattr(row, "_meta_lbl", None)
        if lbl is None:
            return
        if meta.get("error"):
            lbl.configure(text=str(meta["error"]))
            return
        pages = meta.get("pages")
        size = meta.get("size", 0)
        if pages is None:
            lbl.configure(text=self._format_size(int(size)) if size else "—")
        else:
            unit = "page" if pages == 1 else "pages"
            lbl.configure(text=f"{pages} {unit} · {self._format_size(int(size))}")

    def _load_meta_async(
        self,
        items: list[tuple[int, Path]],
        gen: int,
        password: str | None = None,
    ) -> None:
        """Background page-count; never blocks the UI."""
        for index, path in items:
            if gen != self._meta_gen:
                return
            try:
                st = path.stat()
                mtime = st.st_mtime_ns
                size = st.st_size
            except OSError:
                meta = {"error": "missing", "fresh": True}
                self._meta_cache[self._cache_key(path)] = meta
                self.after(0, lambda i=index, m=meta: self._apply_meta_to_row(i, m))
                continue

            key = self._cache_key(path)
            cached = self._meta_cache.get(key)
            if (
                cached
                and cached.get("mtime") == mtime
                and cached.get("pages") is not None
                and not cached.get("error")
            ):
                cached["fresh"] = True
                self.after(0, lambda i=index, m=cached: self._apply_meta_to_row(i, m))
                continue

            cached_pwd = jobs.password_cache_get(path) or password
            pages: int | None = None
            err: str | None = None
            try:
                pages = pdf_ops.page_count(
                    path,
                    password=cached_pwd,
                    password_provider=jobs.make_password_provider(cached_pwd),
                )
            except pdf_ops.PdfOpsError as exc:
                msg = str(exc).lower()
                if "password" in msg:
                    err = "password?"
                else:
                    err = "unreadable"
            except Exception:  # noqa: BLE001
                err = "unreadable"

            meta = {
                "pages": pages,
                "size": size,
                "mtime": mtime,
                "error": err,
                "fresh": True,
            }
            self._meta_cache[key] = meta
            if gen != self._meta_gen:
                return
            self.after(0, lambda i=index, m=meta: self._apply_meta_to_row(i, m))

    def _select_file(self, index: int, *, open_org: bool = False) -> None:
        if index < 0 or index >= len(self._files):
            return
        self._selected_idx = index
        for i, row in enumerate(self._file_rows):
            sel = i == index
            try:
                row.configure(
                    fg_color=_ROW_BG_SEL if sel else _ROW_BG,
                    border_width=2 if sel else 0,
                    border_color=_ROW_BORDER_SEL,
                )
            except Exception:  # noqa: BLE001
                pass
        self._update_sel_label()
        if open_org:
            self._go_tab("Organize")
            self.after(50, self._org_load)

    def _update_sel_label(self) -> None:
        if not self._files:
            self.sel_label.configure(text=_("No file selected — add PDFs above"))
            return
        idx = self._selected_idx
        if idx < 0 or idx >= len(self._files):
            self.sel_label.configure(text=_("No file selected"))
            return
        p = self._files[idx]
        self.sel_label.configure(text=f"Selected: {p.name}")

    def _focus_is_text_input(self) -> bool:
        """Don't steal ↑/↓/Delete from entry fields and text boxes."""
        try:
            w = self.focus_get()
            if w is None:
                return False
            cls = w.winfo_class()
            if cls in ("Entry", "Text", "TEntry", "TCombobox"):
                return True
            name = type(w).__name__.lower()
            if "entry" in name or "textbox" in name or "text" in name:
                return True
        except Exception:  # noqa: BLE001
            pass
        return False

    def _move_selection(self, delta: int) -> str | None:
        if not self._files:
            return None
        new = max(0, min(len(self._files) - 1, self._selected_idx + delta))
        self._select_file(new)
        return "break"

    def _on_arrow_up(self, _event=None):  # noqa: ANN001
        if self._focus_is_text_input():
            return None
        return self._move_selection(-1)

    def _on_arrow_down(self, _event=None):  # noqa: ANN001
        if self._focus_is_text_input():
            return None
        return self._move_selection(1)

    def _on_delete_key(self, _event=None):  # noqa: ANN001
        if self._focus_is_text_input():
            return None
        self._remove_selected()
        return "break"

    def _retry_meta_after_password(self) -> None:
        """Re-read page counts after password is entered (async, cached)."""
        if not self._files:
            return
        pwd = self._password()
        if not pwd:
            return
        for p in self._files:
            key = self._cache_key(p)
            meta = self._meta_cache.get(key)
            if meta and meta.get("error") == "password?":
                self._meta_cache.pop(key, None)
        self._meta_gen += 1
        gen = self._meta_gen
        items = list(enumerate(self._files))
        threading.Thread(
            target=self._load_meta_async,
            args=(items, gen, pwd),
            daemon=True,
        ).start()

    def _ingest_paths(self, paths: list[Path]) -> None:
        added = 0
        for p in paths:
            try:
                resolved = p.resolve()
            except OSError:
                resolved = p
            existing = {self._safe_resolve(x) for x in self._files}
            if resolved not in existing and p not in self._files:
                self._files.append(p)
                self._meta_cache.pop(self._cache_key(p), None)
                added += 1
        if added and self._files:
            self._selected_idx = len(self._files) - 1
        self._refresh_list()
        if added:
            self._set_status(f"Added {added} file(s). {len(self._files)} total.")
        else:
            self._set_status(f"No new files (already listed). {len(self._files)} total.")

    @staticmethod
    def _safe_resolve(path: Path) -> Path:
        try:
            return path.resolve()
        except OSError:
            return path

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if paths:
            self._ingest_paths([Path(raw) for raw in paths])

    def _selected_row(self) -> int | None:
        if not self._files:
            return None
        if 0 <= self._selected_idx < len(self._files):
            return self._selected_idx
        return None

    def _require_selected(self) -> Path | None:
        if not self._files:
            messagebox.showinfo(
                __app_name__,
                "Add at least one PDF first.\n\nDrop files here or click Add PDFs…",
            )
            return None
        idx = self._selected_row()
        if idx is None:
            messagebox.showinfo(__app_name__, "Click a file in the list to select it.")
            return None
        return self._files[idx]

    def _remove_selected(self) -> None:
        idx = self._selected_row()
        if idx is None or not self._files:
            return
        removed = self._files.pop(idx)
        self._meta_cache.pop(self._cache_key(removed), None)
        if self._files:
            self._selected_idx = min(idx, len(self._files) - 1)
        else:
            self._selected_idx = 0
        self._refresh_list()
        self._set_status(f"Removed {removed.name}.")

    def _clear_files(self) -> None:
        self._files.clear()
        self._meta_cache.clear()
        self._selected_idx = 0
        self._refresh_list()
        self._set_status("File list cleared.")

    def _move(self, delta: int) -> None:
        idx = self._selected_row()
        if idx is None or not self._files:
            return
        new = idx + delta
        if new < 0 or new >= len(self._files):
            return
        self._files[idx], self._files[new] = self._files[new], self._files[idx]
        self._selected_idx = new
        self._refresh_list()

    def _pick_save(self, entry: ctk.CTkEntry, title: str, initial: str) -> None:
        path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=initial,
        )
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _pick_merge_out(self) -> None:
        self._pick_save(self.merge_out, "Save merged PDF as", "merged.pdf")

    def _pick_mix_out(self) -> None:
        self._pick_save(self.mix_out, "Save mixed PDF as", "mixed.pdf")

    def _pick_extract_out(self) -> None:
        self._pick_save(self.extract_out, "Save extracted PDF as", "extracted.pdf")

    def _pick_delete_out(self) -> None:
        self._pick_save(self.delete_out, "Save PDF after delete as", "deleted_pages.pdf")

    def _pick_insert_out(self) -> None:
        self._pick_save(self.insert_out, "Save insert result as", "inserted.pdf")

    def _pick_insert_src(self) -> None:
        path = filedialog.askopenfilename(
            title="PDF to insert from",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.insert_src.delete(0, "end")
            self.insert_src.insert(0, path)

    def _pick_split_dir(self) -> None:
        path = filedialog.askdirectory(title="Output folder for split files")
        if path:
            self.split_dir.delete(0, "end")
            self.split_dir.insert(0, path)

    def _pick_rotate_out(self) -> None:
        self._pick_save(self.rotate_out, "Save rotated PDF as", "rotated.pdf")

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy

    def _result_paths(self, result: object) -> list[Path]:
        """PDF file paths produced by a job (for review). Ignore non-path payloads.

        Organize 'add pages' returns list[tuple[Path, int]] — not output files.
        """
        if isinstance(result, Path):
            return [result] if result.is_file() else []
        if isinstance(result, (list, tuple)):
            out: list[Path] = []
            for p in result:
                if not isinstance(p, (str, Path)):
                    continue
                try:
                    path = Path(p)
                except (TypeError, ValueError):
                    continue
                if path.is_file() and path.suffix.lower() == ".pdf":
                    out.append(path)
            return out
        return []

    def _discard_outputs(self, paths: list[Path]) -> None:
        for p in paths:
            try:
                if p.is_file():
                    p.unlink()
            except OSError:
                pass

    def _stage_for_review(
        self, finals: list[Path]
    ) -> tuple[list[Path], list[tuple[Path, Path]]]:
        """Move finished outputs to hidden review staging paths.

        Returns (staging_paths, pairs of (staging, intended_final)).
        """
        import uuid

        staged: list[Path] = []
        pairs: list[tuple[Path, Path]] = []
        for final in finals:
            if not final.is_file():
                continue
            stage = final.parent / f".sekikit-review-{uuid.uuid4().hex}.tmp.pdf"
            try:
                os.replace(str(final), str(stage))
            except OSError:
                try:
                    import shutil

                    shutil.copy2(final, stage)
                    final.unlink()
                except OSError:
                    continue
            staged.append(stage)
            pairs.append((stage, final))
        return staged, pairs

    def _promote_reviewed(
        self, pairs: list[tuple[Path, Path]]
    ) -> list[Path]:
        """Move staging files to final names (unique if needed)."""
        promoted: list[Path] = []
        for stage, final in pairs:
            if not stage.is_file():
                continue
            dest = final
            try:
                from sekikit.pdf_ops import _unique_path

                if dest.exists():
                    dest = _unique_path(final)
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.replace(str(stage), str(dest))
                promoted.append(dest)
            except OSError:
                if stage.is_file():
                    promoted.append(stage)
        return promoted

    def _run_bg(
        self,
        work,
        on_ok,
        label: str,
        *,
        op: str | None = None,
        inputs: list | None = None,
        review: bool | None = None,
        validate_password: str | None = None,
    ) -> None:
        """Run work off-UI. Optional full-screen review before on_ok.

        review: True/False force; None = use Settings (off / risk / always).
        validate_password: re-open encrypted outputs for page-count logging.
        """
        if self._busy:
            return
        self._cancel_job = False
        self._job_warnings: list[str] = []
        op_key = op or label

        def runner() -> None:
            self.after(0, lambda: self._set_busy(True))
            self.after(0, lambda: self._set_status(f"{label}… (Esc to cancel long jobs)"))
            try:
                jr = jobs.run_job(
                    op_key,
                    work,
                    inputs=inputs or [],
                    validate_password=validate_password,
                )
                # Prefer Path outputs; pass through non-path values (ThumbnailSession).
                result: object
                if len(jr.paths) == 1:
                    result = jr.paths[0]
                elif len(jr.paths) > 1:
                    result = jr.paths
                elif jr.value is not None:
                    result = jr.value
                else:
                    result = None
                self._job_warnings = list(jr.warnings)
            except pdf_ops.PdfOpsError as exc:
                msg = str(exc)
                if "password" in msg.lower():
                    self.after(0, lambda m=msg: self._fail_password(m))
                else:
                    self.after(0, lambda m=msg: self._fail(m))
                return
            except Exception:  # noqa: BLE001
                tb = traceback.format_exc()
                self.after(0, lambda: self._fail(f"Unexpected error:\n{tb}"))
                return
            else:
                self.after(
                    0,
                    lambda: self._after_job_success(
                        result,
                        on_ok,
                        label,
                        op_key,
                        review,
                        validate_password,
                    ),
                )
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=runner, daemon=True).start()

    def _after_job_success(
        self,
        result: object,
        on_ok,
        label: str,
        op_key: str,
        review: bool | None,
        validate_password: str | None = None,
    ) -> None:
        paths = self._result_paths(result)
        need = (
            bool(review)
            if review is not None
            else app_prefs.should_review(op_key)
        )
        if need and paths:
            self._set_status("Review result…")
            # Stage so Cancel never leaves a final-named file.
            staged, pairs = self._stage_for_review(paths)
            if not staged:
                staged = paths
                pairs = []
            try:
                keep = review_ui.run_review_dialog(
                    self,
                    staged,
                    title=f"{_('Review result')} · {label}",
                    password=validate_password,
                )
            except Exception as exc:  # noqa: BLE001
                if not messagebox.askyesno(
                    __app_name__,
                    f"Preview failed ({exc}).\n\nKeep the output file anyway?",
                ):
                    self._discard_outputs(staged if staged else paths)
                    self._set_status("Cancelled — file not kept.")
                    return
                keep = True
            if not keep:
                self._discard_outputs(staged if staged else paths)
                self._set_status("Cancelled — file not kept.")
                return
            if pairs:
                promoted = self._promote_reviewed(pairs)
                if len(promoted) == 1:
                    result = promoted[0]
                elif promoted:
                    result = promoted
        on_ok(result)

    def _fail_password(self, msg: str) -> None:
        self._set_busy(False)
        self._set_status("Password required.")
        path = self._files[self._selected_idx] if self._files else None
        if path is not None:
            pwd = self._prompt_and_cache_password(path)
            if pwd:
                self._set_status(
                    f"Password saved for {path.name} (this session). Try again."
                )
                return
        messagebox.showerror(
            __app_name__,
            f"{msg}\n\n"
            "Enter the password in the Password field (top), then try again.\n"
            "Passwords are remembered for this session only.",
        )

    def _request_cancel(self, _event=None):  # noqa: ANN001
        if self._busy:
            self._cancel_job = True
            self._set_status("Cancelling…")
            return "break"
        return None

    def _fail(self, msg: str) -> None:
        self._set_status("Error.")
        messagebox.showerror(__app_name__, msg)

    def _remember(self, paths: Path | list[Path]) -> None:
        if isinstance(paths, Path):
            self._last_outputs = [paths]
        else:
            self._last_outputs = list(paths)

    def _ok_file(self, path: Path, verb: str) -> None:
        self._remember(path)
        warns = list(getattr(self, "_job_warnings", []) or []) + pdf_ops.take_warnings()
        note = (" · ".join(warns)) if warns else ""
        self._set_status(f"{verb}: {path.name}")
        self._show_toast(verb, path.name, path=path, note=note)

    def _ok_files(self, paths: list[Path], verb: str) -> None:
        if not paths:
            self._set_status("Nothing written.")
            return
        self._remember(paths)
        folder = paths[0].parent
        self._set_status(f"{verb}: {len(paths)} file(s) in {folder}")
        self._show_toast(
            verb,
            f"{len(paths)} file(s) → {folder.name}",
            folder=folder,
        )

    def _dismiss_toast(self) -> None:
        if self._toast_after_id is not None:
            try:
                self.after_cancel(self._toast_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._toast_after_id = None
        if self._toast_frame is not None:
            try:
                self._toast_frame.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._toast_frame = None

    def _show_toast(
        self,
        title: str,
        detail: str,
        *,
        path: Path | None = None,
        folder: Path | None = None,
        note: str = "",
        ms: int = 7000,
    ) -> None:
        """Non-blocking success strip — Open file / folder without a modal."""
        self._dismiss_toast()
        toast = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=("#3B8ED0", "#3B8ED0"))
        toast.place(relx=0.5, rely=0.985, anchor="s", relwidth=0.94)

        top = ctk.CTkFrame(toast, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            top,
            text=f"✓  {title}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1a6bb5", "#7ec8ff"),
        ).pack(side="left")
        ctk.CTkButton(
            top,
            text="✕",
            width=28,
            height=24,
            fg_color="transparent",
            text_color=("gray40", "gray70"),
            hover_color=("gray85", "gray30"),
            command=self._dismiss_toast,
        ).pack(side="right")

        line = detail
        if note:
            line = f"{detail}  ·  {note}"
        ctk.CTkLabel(
            toast,
            text=line,
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray80"),
        ).pack(fill="x", padx=14, pady=(0, 6))

        btns = ctk.CTkFrame(toast, fg_color="transparent")
        btns.pack(fill="x", padx=10, pady=(0, 10))
        open_folder = folder or (path.parent if path is not None else None)
        if path is not None and path.is_file():
            ctk.CTkButton(
                btns,
                text=_("Open file"),
                width=100,
                height=28,
                command=lambda p=path: (self._open_path(p), self._dismiss_toast()),
            ).pack(side="left", padx=4)
        if open_folder is not None:
            ctk.CTkButton(
                btns,
                text=_("Open folder"),
                width=110,
                height=28,
                fg_color="gray40",
                hover_color="gray30",
                command=lambda f=open_folder: (self._open_folder(f), self._dismiss_toast()),
            ).pack(side="left", padx=4)
        ctk.CTkButton(
            btns,
            text=_("Dismiss"),
            width=80,
            height=28,
            fg_color="transparent",
            border_width=1,
            text_color=("gray30", "gray80"),
            command=self._dismiss_toast,
        ).pack(side="right", padx=4)

        self._toast_frame = toast
        self._toast_after_id = self.after(ms, self._dismiss_toast)

    def _open_last_output(self) -> None:
        if not self._last_outputs:
            messagebox.showinfo(__app_name__, "No output yet this session.")
            return
        path = self._last_outputs[0]
        if path.is_file():
            self._open_path(path)
        elif path.is_dir():
            self._open_folder(path)
        else:
            messagebox.showinfo(__app_name__, f"Last output no longer exists:\n{path}")

    @staticmethod
    def _open_folder(folder: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess

                subprocess.run(["open", str(folder)], check=False)
            else:
                import subprocess

                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _open_path(path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess

                subprocess.run(["open", str(path)], check=False)
            else:
                import subprocess

                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception:  # noqa: BLE001
            pass

    def _run_merge(self) -> None:
        if len(self._files) < 2:
            messagebox.showinfo(__app_name__, "Add at least two PDFs to merge.")
            return
        do_renumber = bool(self.merge_renumber.get())
        out_raw = self.merge_out.get().strip()
        if out_raw:
            out = Path(out_raw)
        elif do_renumber:
            out = pdf_ops.default_output_next_to(self._files[0], "_merged_numbered")
        else:
            out = pdf_ops.default_output_next_to(self._files[0], "_merged")
        lines = self.merge_ranges.get("1.0", "end").splitlines()
        specs: list[str | None] = []
        for i in range(len(self._files)):
            if i < len(lines) and lines[i].strip():
                specs.append(lines[i].strip())
            else:
                specs.append(None)
        if all(s is None for s in specs):
            page_specs = None
        else:
            page_specs = specs
        files = list(self._files)
        kw = self._pwd_kwargs()
        preserve_bm = bool(self.merge_bookmarks.get())
        ps = self.merge_page_size.get()
        page_size = None if not ps or ps == "none" else ps

        def work():
            def produce(path: Path) -> Path:
                return pdf_ops.merge_pdfs(
                    files,
                    path,
                    page_specs=page_specs,
                    preserve_bookmarks=preserve_bm,
                    page_size=page_size,
                    **kw,
                )

            return self._op_then_renumber(
                produce, out, do_renumber=do_renumber, pwd_kw=kw
            )

        verb = "Merged + renumbered" if do_renumber else "Merged"
        self._run_bg(
            work,
            lambda p: self._ok_file(p, verb),
            "Merging",
            op="merge_renumber" if do_renumber else "merge",
        )

    def _run_mix(self) -> None:
        if len(self._files) < 2:
            messagebox.showinfo(__app_name__, "Add at least two PDFs to mix.")
            return
        do_renumber = bool(self.mix_renumber.get())
        out_raw = self.mix_out.get().strip()
        if out_raw:
            out = Path(out_raw)
        elif do_renumber:
            out = pdf_ops.default_output_next_to(self._files[0], "_mixed_numbered")
        else:
            out = pdf_ops.default_output_next_to(self._files[0], "_mixed")
        rev = bool(self.mix_reverse.get())
        files = list(self._files)
        kw = self._pwd_kwargs()

        def work():
            def produce(path: Path) -> Path:
                return pdf_ops.mix_pdfs(files, path, reverse_second=rev, **kw)

            return self._op_then_renumber(
                produce, out, do_renumber=do_renumber, pwd_kw=kw
            )

        verb = "Mixed + renumbered" if do_renumber else "Mixed"
        self._run_bg(
            work,
            lambda p: self._ok_file(p, verb),
            "Mixing",
            op="mix_renumber" if do_renumber else "mix",
        )

    def _run_extract(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        page_spec = self.extract_range.get().strip()
        do_renumber = bool(self.extract_renumber.get())
        out_raw = self.extract_out.get().strip()
        if out_raw:
            out = Path(out_raw)
        else:
            safe = page_spec.replace(",", "_").replace("-", "to").replace(" ", "")
            suf = f"_pages_{safe or 'extract'}"
            if do_renumber:
                suf += "_numbered"
            out = pdf_ops.default_output_next_to(src, suf)
        kw = self._pwd_kwargs()

        def work():
            def produce(path: Path) -> Path:
                return pdf_ops.extract_pages(src, page_spec, path, **kw)

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

    def _run_delete(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        page_spec = self.delete_range.get().strip()
        do_renumber = bool(self.delete_renumber.get())
        out_raw = self.delete_out.get().strip()
        if out_raw:
            out = Path(out_raw)
        elif do_renumber:
            out = pdf_ops.default_output_next_to(src, "_deleted_numbered")
        else:
            out = pdf_ops.default_output_next_to(src, "_deleted")
        kw = self._pwd_kwargs()

        def work():
            def produce(path: Path) -> Path:
                return pdf_ops.delete_pages(src, page_spec, path, **kw)

            return self._op_then_renumber(
                produce, out, do_renumber=do_renumber, pwd_kw=kw
            )

        verb = "Deleted + renumbered" if do_renumber else "Deleted pages"
        self._run_bg(
            work,
            lambda p: self._ok_file(p, verb),
            "Deleting",
            op="delete_renumber" if do_renumber else "delete",
        )

    def _run_insert(self) -> None:
        base = self._require_selected()
        if base is None:
            return
        src_raw = self.insert_src.get().strip()
        if src_raw:
            insert_path = Path(src_raw)
        else:
            idx = self._selected_row()
            if idx is None or idx + 1 >= len(self._files):
                messagebox.showinfo(
                    __app_name__,
                    "Set insert PDF path, or put the insert file on the next list row.",
                )
                return
            insert_path = self._files[idx + 1]
        try:
            at_page = int(self.insert_at.get().strip())
        except ValueError:
            messagebox.showerror(__app_name__, "Insert position must be a whole number.")
            return
        insert_spec = self.insert_spec.get().strip() or None
        do_renumber = bool(self.insert_renumber.get())
        out_raw = self.insert_out.get().strip()
        if out_raw:
            out = Path(out_raw)
        elif do_renumber:
            out = pdf_ops.default_output_next_to(base, "_inserted_numbered")
        else:
            out = pdf_ops.default_output_next_to(base, "_inserted")
        kw = self._pwd_kwargs()

        def work():
            def produce(path: Path) -> Path:
                return pdf_ops.insert_pages(
                    base,
                    insert_path,
                    path,
                    at_page=at_page,
                    insert_spec=insert_spec,
                    **kw,
                )

            return self._op_then_renumber(
                produce, out, do_renumber=do_renumber, pwd_kw=kw
            )

        verb = "Inserted + renumbered" if do_renumber else "Inserted"
        self._run_bg(
            work,
            lambda p: self._ok_file(p, verb),
            "Inserting",
            op="insert_renumber" if do_renumber else "insert",
        )

    def _run_split(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        mode = self.split_mode.get()
        every_n = 1
        at_pages = None
        max_mb = 2.0
        bookmark_level = 1
        if mode == "every_n":
            try:
                every_n = int(self.split_n.get().strip())
            except ValueError:
                messagebox.showerror(__app_name__, "N must be a whole number.")
                return
        elif mode == "at_pages":
            at_pages = self.split_at.get().strip()
        elif mode == "size":
            try:
                max_mb = float(self.split_mb.get().strip())
            except ValueError:
                messagebox.showerror(__app_name__, "Max MB must be a number.")
                return
        elif mode == "bookmarks":
            try:
                bookmark_level = int(self.split_bm_level.get().strip())
            except ValueError:
                messagebox.showerror(__app_name__, "Bookmark level must be a whole number.")
                return
        dir_raw = self.split_dir.get().strip()
        out_dir = Path(dir_raw) if dir_raw else src.parent / f"{src.stem}_split"
        do_renumber = bool(self.split_renumber.get())
        kw = self._pwd_kwargs()

        def work():
            paths = pdf_ops.split_pdf(
                src,
                mode,
                out_dir,
                every_n=every_n,
                at_pages=at_pages,
                max_mb=max_mb,
                bookmark_level=bookmark_level,
                **kw,
            )
            return self._paths_then_renumber(
                list(paths), do_renumber=do_renumber, pwd_kw=kw
            )

        verb = "Split + renumbered" if do_renumber else "Split"
        self._run_bg(
            work,
            lambda ps: self._ok_files(ps, verb),
            "Splitting",
            op="split_renumber" if do_renumber else "split",
        )

    def _run_rotate(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        try:
            degrees = int(self.rotate_deg.get())
        except (TypeError, ValueError):
            messagebox.showerror(__app_name__, "Pick a rotation angle.")
            return
        page_spec = self.rotate_range.get().strip() or None
        out_raw = self.rotate_out.get().strip()
        out = Path(out_raw) if out_raw else pdf_ops.default_output_next_to(src, f"_rot{degrees}")
        kw = self._pwd_kwargs()

        def work():
            return pdf_ops.rotate_pages(src, degrees, out, page_spec=page_spec, **kw)

        self._run_bg(work, lambda p: self._ok_file(p, "Rotated"), "Rotating")


    def _build_watch_tab(self) -> None:
        tab = self.tabs.tab("Watch")
        scroll = self._tab_scroll(tab)

        ctk.CTkLabel(
            scroll,
            text=_(
                "Local watch folder: when a PDF appears in the input folder, "
                "process it into the output folder. Fully offline — nothing is uploaded."
            ),
            anchor="w",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
            wraplength=900,
        ).pack(fill="x", pady=(4, 10), padx=4)

        row_in = ctk.CTkFrame(scroll, fg_color="transparent")
        row_in.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(row_in, text=_("Input folder:"), width=100, anchor="w").pack(
            side="left"
        )
        self.watch_in = ctk.CTkEntry(row_in, placeholder_text="Folder to watch")
        self.watch_in.pack(side="left", fill="x", expand=True, padx=6)
        self._tip(
            self.watch_in,
            "Local inbox folder. · Not recursive. Nothing is uploaded.",
        )
        b = ctk.CTkButton(
            row_in, text=_("Browse…"), width=90, command=self._pick_watch_in
        )
        b.pack(side="left")
        self._tip(b, "Choose input folder.")

        row_out = ctk.CTkFrame(scroll, fg_color="transparent")
        row_out.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(row_out, text=_("Output folder:"), width=100, anchor="w").pack(
            side="left"
        )
        self.watch_out = ctk.CTkEntry(row_out, placeholder_text="Where results go")
        self.watch_out.pack(side="left", fill="x", expand=True, padx=6)
        self._tip(
            self.watch_out,
            "Results folder. · Must differ from input so outputs are not re-processed.",
        )
        b = ctk.CTkButton(
            row_out, text=_("Browse…"), width=90, command=self._pick_watch_out
        )
        b.pack(side="left")
        self._tip(b, "Choose output folder.")

        inner = self._section(
            scroll,
            "Action",
            "Applied to each new PDF in the input folder (files already processed are skipped).",
        )
        self.watch_action = ctk.CTkSegmentedButton(
            inner,
            values=[
                "compress",
                "grayscale",
                "page_numbers",
                "renumber",
                "flatten",
                "clean",
            ],
        )
        self.watch_action.pack(side="left")
        self.watch_action.set("compress")
        self._tip(
            self.watch_action,
            "Batch action per new PDF. · No GUI review in Watch (auto batch).",
        )
        ctk.CTkLabel(inner, text=_("Compress preset:")).pack(side="left", padx=(12, 4))
        self.watch_preset = ctk.CTkSegmentedButton(
            inner, values=["email", "balanced", "max", "scan"]
        )
        self.watch_preset.pack(side="left")
        self.watch_preset.set("balanced")
        self._tip(
            self.watch_preset,
            "For compress only. · scan re-renders pages (text not selectable).",
        )

        row_iv = ctk.CTkFrame(scroll, fg_color="transparent")
        row_iv.pack(fill="x", padx=4, pady=6)
        ctk.CTkLabel(row_iv, text=_("Poll every (sec):")).pack(side="left")
        self.watch_interval = ctk.CTkEntry(row_iv, width=60)
        self.watch_interval.pack(side="left", padx=6)
        self.watch_interval.insert(0, "2")
        self._tip(self.watch_interval, "How often to check the folder.")
        self.watch_start_btn = ctk.CTkButton(
            row_iv, text=_("Start watch"), width=120, command=self._watch_start
        )
        self.watch_start_btn.pack(side="left", padx=12)
        self._tip(
            self.watch_start_btn,
            "Start local polling. · Offline only — never uploads.",
        )
        self.watch_stop_btn = ctk.CTkButton(
            row_iv,
            text=_("Stop"),
            width=80,
            command=self._watch_stop_fn,
            fg_color="gray40",
            state="disabled",
        )
        self.watch_stop_btn.pack(side="left")
        self._tip(self.watch_stop_btn, "Stop watching.")
        b = ctk.CTkButton(
            row_iv,
            text=_("Process once now"),
            width=140,
            command=self._watch_once,
        )
        b.pack(side="left", padx=12)
        self._tip(b, "Run once on current files (no loop).")

        self.watch_log = ctk.CTkTextbox(scroll, height=180)
        self.watch_log.pack(fill="both", expand=True, padx=4, pady=(8, 12))
        self.watch_log.insert("1.0", _("Watch log (local only)…\n"))
        self.watch_log.configure(state="disabled")
        self._tip(self.watch_log, "Local log only. Never uploaded.")

    def _pick_watch_in(self) -> None:
        d = filedialog.askdirectory(title="Watch input folder")
        if d:
            self.watch_in.delete(0, "end")
            self.watch_in.insert(0, d)

    def _pick_watch_out(self) -> None:
        d = filedialog.askdirectory(title="Watch output folder")
        if d:
            self.watch_out.delete(0, "end")
            self.watch_out.insert(0, d)

    def _watch_log_line(self, msg: str) -> None:
        def _do() -> None:
            self.watch_log.configure(state="normal")
            self.watch_log.insert("end", msg + "\n")
            self.watch_log.see("end")
            self.watch_log.configure(state="disabled")

        self.after(0, _do)

    def _watch_validate_dirs(self) -> tuple[Path, Path] | None:
        in_raw = self.watch_in.get().strip()
        out_raw = self.watch_out.get().strip()
        if not in_raw or not out_raw:
            messagebox.showerror(
                __app_name__, "Choose both input and output folders."
            )
            return None
        in_dir = Path(in_raw)
        out_dir = Path(out_raw)
        if not in_dir.is_dir():
            messagebox.showerror(__app_name__, f"Input folder not found:\n{in_dir}")
            return None
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(__app_name__, f"Cannot create output folder:\n{exc}")
            return None
        try:
            if in_dir.resolve() == out_dir.resolve():
                messagebox.showerror(
                    __app_name__,
                    "Input and output folders must be different "
                    "(so outputs are not re-processed).",
                )
                return None
        except OSError:
            pass
        return in_dir, out_dir

    def _watch_file_key(self, p: Path) -> str:
        try:
            st = p.stat()
            return f"{p.resolve()}|{st.st_size}|{st.st_mtime_ns}"
        except OSError:
            return str(p)

    def _watch_run_one(self, src: Path, out_dir: Path) -> None:
        action = self.watch_action.get()
        preset = self.watch_preset.get()
        pwd = self._password()
        try:
            result = jobs.run_job(
                f"watch_{action}",
                lambda: pdf_ops.watch_process_file(
                    src,
                    out_dir,
                    action,
                    compress_preset=preset,
                    password=pwd,
                    password_provider=jobs.make_password_provider(pwd),
                ),
                inputs=[src],
            )
            if result.ok and result.paths:
                self._watch_log_line(f"OK  {src.name} → {result.paths[0].name}")
                self.after(0, lambda: self._set_status(f"Watch: {src.name} done"))
            else:
                self._watch_log_line(f"FAIL {src.name}: {result.error or 'unknown'}")
        except Exception as exc:  # noqa: BLE001
            self._watch_log_line(f"FAIL {src.name}: {exc}")

    def _watch_poll_once(self, in_dir: Path, out_dir: Path) -> int:
        """Process new stable PDFs. Returns count processed this pass."""
        import time

        count = 0
        try:
            files = pdf_ops.list_watch_pdfs(in_dir)
        except pdf_ops.PdfOpsError as exc:
            self._watch_log_line(f"error: {exc}")
            return 0
        for src in files:
            if self._watch_stop:
                break
            key = self._watch_file_key(src)
            if key in self._watch_processed:
                continue
            try:
                s1 = src.stat().st_size
                time.sleep(0.15)
                s2 = src.stat().st_size
                if s1 != s2:
                    continue
            except OSError:
                continue
            self._watch_run_one(src, out_dir)
            self._watch_processed.add(key)
            count += 1
        return count

    def _watch_once(self) -> None:
        dirs = self._watch_validate_dirs()
        if dirs is None:
            return
        in_dir, out_dir = dirs
        if self._watch_running:
            messagebox.showinfo(__app_name__, "Stop the continuous watch first.")
            return

        def work() -> None:
            n = self._watch_poll_once(in_dir, out_dir)
            self._watch_log_line(f"— once: {n} file(s) processed —")

        threading.Thread(target=work, daemon=True).start()

    def _watch_start(self) -> None:
        dirs = self._watch_validate_dirs()
        if dirs is None:
            return
        if self._watch_running:
            return
        try:
            interval = float(self.watch_interval.get().strip() or "2")
        except ValueError:
            messagebox.showerror(__app_name__, "Interval must be a number (seconds).")
            return
        interval = max(0.5, interval)
        in_dir, out_dir = dirs
        self._watch_stop = False
        self._watch_running = True
        self.watch_start_btn.configure(state="disabled")
        self.watch_stop_btn.configure(state="normal")
        self._watch_log_line(
            f"Started watching {in_dir} → {out_dir} "
            f"({self.watch_action.get()}, every {interval}s)"
        )
        self._set_status("Watch folder running…")

        def loop() -> None:
            import time

            while not self._watch_stop:
                self._watch_poll_once(in_dir, out_dir)
                # Sleep in steps so Stop is responsive.
                slept = 0.0
                while slept < interval and not self._watch_stop:
                    time.sleep(0.2)
                    slept += 0.2
            self.after(0, self._watch_on_stopped)

        self._watch_thread = threading.Thread(target=loop, daemon=True)
        self._watch_thread.start()

    def _watch_stop_fn(self) -> None:
        if not self._watch_running:
            return
        self._watch_stop = True
        self._watch_log_line("Stopping…")

    def _watch_on_stopped(self) -> None:
        self._watch_running = False
        self._watch_stop = False
        self.watch_start_btn.configure(state="normal")
        self.watch_stop_btn.configure(state="disabled")
        self._watch_log_line("Stopped.")
        self._set_status("Watch folder stopped.")

    def _maybe_first_run_diagnostics(self) -> None:
        """Once on first launch: offer optional diagnostics (default leave Off)."""
        if app_prefs.get_first_run_completed():
            return
        win = ctk.CTkToplevel(self)
        win.title(_("Welcome to Sekikit"))
        win.geometry("500x400")
        win.minsize(460, 380)
        try:
            win.transient(self)
            win.grab_set()
            win.attributes("-topmost", True)
        except Exception:  # noqa: BLE001
            pass

        card = ctk.CTkFrame(win, corner_radius=10)
        card.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            card,
            text=_("Welcome"),
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 6))
        ctk.CTkLabel(
            card,
            text=_(
                "Sekikit works fully offline. Nothing is uploaded.\n\n"
                "Optional: enable Diagnostics so you can export a local "
                "bug-report pack (version, OS, recent op names — never PDF "
                "content or passwords).\n\n"
                "Reports are anonymous — no name, account, or device ID. "
                "Paths in logs are redacted. Nothing is sent unless you "
                "paste the report into a GitHub Issue.\n\n"
                "Diagnostics stay Off unless you turn them on. "
                "You can change this later in Settings."
            ),
            text_color=_MUTED,
            font=ctk.CTkFont(size=13),
            wraplength=450,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        enable_box = ctk.CTkCheckBox(
            card,
            text=_("Enable anonymous Diagnostics (optional, default off)"),
        )
        enable_box.pack(anchor="w", padx=16, pady=(4, 8))
        # Explicitly leave unchecked = default off
        try:
            enable_box.deselect()
        except Exception:  # noqa: BLE001
            pass
        self._tip(
            enable_box,
            "Off = no export tools. On = About can Copy/Save an anonymous "
            "local report (no name, account, or device ID). "
            "Nothing is sent automatically.",
        )

        def finish() -> None:
            app_prefs.set_diagnostics_enabled(bool(enable_box.get()))
            app_prefs.set_first_run_completed(True)
            if enable_box.get():
                self._set_status(
                    "Anonymous diagnostics enabled — use About to export a report."
                )
            else:
                self._set_status(
                    "Ready — diagnostics left off (change in Settings anytime)."
                )
            try:
                win.grab_release()
            except Exception:  # noqa: BLE001
                pass
            win.destroy()

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(
            row, text=_("Continue"), width=120, command=finish
        ).pack(side="right")

        win.protocol("WM_DELETE_WINDOW", finish)

    def _show_settings(self) -> None:
        """Local prefs only — short, honest."""
        win = ctk.CTkToplevel(self)
        win.title(_("Settings"))
        win.geometry("440x430")
        win.minsize(400, 410)
        try:
            win.transient(self)
            win.grab_set()
        except Exception:  # noqa: BLE001
            pass

        card = ctk.CTkFrame(win, corner_radius=10)
        card.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            card,
            text=_("Settings"),
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            card,
            text=_("Stored only on this PC · never uploaded"),
            text_color=_MUTED,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            card,
            text=_("Review before save"),
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16)
        ctk.CTkLabel(
            card,
            text=_(
                "Preview risky results before keeping the file. "
                "Cancel discards the draft (never leaves a final name)."
            ),
            text_color=_MUTED,
            font=ctk.CTkFont(size=12),
            wraplength=390,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(2, 8))

        mode_map = {
            "Off": "off",
            "Risk only": "risk",
            "Always": "always",
        }
        inv = {v: k for k, v in mode_map.items()}
        cur = app_prefs.get_review_mode()
        seg = ctk.CTkSegmentedButton(card, values=list(mode_map.keys()))
        seg.pack(anchor="w", padx=16, pady=4)
        seg.set(inv.get(cur, "Risk only"))
        self._tip(
            seg,
            "Off=never · Risk only=delete/renumber/hard crop/scan/gray/flatten/decrypt · Always=all. "
            "· Screen only — not print-proof.",
        )

        ctk.CTkLabel(
            card,
            text=_(
                "Risk only: delete, renumber, hard crop, scan/gray, flatten, decrypt. "
                "Screen preview only."
            ),
            text_color=("gray45", "gray60"),
            font=ctk.CTkFont(size=11),
            wraplength=390,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            card,
            text=_("Diagnostics (optional, anonymous)"),
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            card,
            text=_(
                "When on, About can export a local bug-report pack. "
                "Reports are anonymous — no name, account, or device ID; "
                "paths are redacted. Nothing is sent unless you paste it "
                "into a GitHub Issue. Default: off."
            ),
            text_color=_MUTED,
            font=ctk.CTkFont(size=12),
            wraplength=390,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 6))
        diag_box = ctk.CTkCheckBox(
            card, text=_("Enable anonymous diagnostics export")
        )
        diag_box.pack(anchor="w", padx=16, pady=(0, 4))
        if app_prefs.get_diagnostics_enabled():
            diag_box.select()
        else:
            try:
                diag_box.deselect()
            except Exception:  # noqa: BLE001
                pass

        def save_close() -> None:
            app_prefs.set_review_mode(mode_map.get(seg.get(), "risk"))
            app_prefs.set_diagnostics_enabled(bool(diag_box.get()))
            self._set_status(
                f"Settings saved · review = {seg.get()} · diagnostics = "
                f"{'on' if diag_box.get() else 'off'}"
            )
            try:
                win.grab_release()
            except Exception:  # noqa: BLE001
                pass
            win.destroy()

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(
            row, text=_("Cancel"), width=90, fg_color="gray40", command=win.destroy
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(row, text=_("Save"), width=100, command=save_close).pack(
            side="right"
        )

    def _show_about(self) -> None:
        from sekikit import diagnostics

        mode = app_prefs.get_review_mode()
        win = ctk.CTkToplevel(self)
        win.title(f"About {__app_name__}")
        win.geometry("480x520")
        win.minsize(440, 480)
        try:
            win.transient(self)
            win.grab_set()
        except Exception:  # noqa: BLE001
            pass

        card = ctk.CTkFrame(win, corner_radius=10)
        card.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            card,
            text=f"{__app_name__}  v{__version__}",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            card,
            text=_("Offline PDF page toolkit · free forever · MIT"),
            text_color=_MUTED,
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=16, pady=(0, 10))
        ctk.CTkLabel(
            card,
            text=_(
                "No accounts, no uploads, no freemium.\n"
                "Just the pages you need — on this PC only."
            ),
            justify="left",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            card,
            text=_("Shortcuts"),
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(4, 4))
        ctk.CTkLabel(
            card,
            text=(
                "Ctrl+O   Add PDFs\n"
                "Ctrl+L   Organize · Load pages\n"
                "Ctrl+S   Organize · Save combined\n"
                "↑ / ↓    Select file in list\n"
                "Esc      Cancel job / review\n"
                "Ctrl+,   Settings\n"
                "F1       About"
            ),
            justify="left",
            font=ctk.CTkFont(size=12, family="Consolas"),
            text_color=_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            card,
            text=(
                f"Review: {mode}  ·  Settings to change\n"
                f"Prefs: {app_prefs.prefs_path().name}\n"
                f"Job log: {jobs.job_log_path().name}\n"
                "github.com/Sekiboi/sekikit"
            ),
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color=_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        diag_on = app_prefs.get_diagnostics_enabled()
        if diag_on:
            ctk.CTkLabel(
                card,
                text=_(
                    "Anonymous diagnostics are on: export a local report for "
                    "GitHub Issues (no name, account, or device ID). "
                    "Nothing is sent automatically."
                ),
                text_color=_MUTED,
                font=ctk.CTkFont(size=11),
                wraplength=420,
                justify="left",
            ).pack(anchor="w", padx=16, pady=(4, 8))
        else:
            ctk.CTkLabel(
                card,
                text=_(
                    "Diagnostics are off (default). Turn on in Settings if you want "
                    "to export an anonymous local bug-report pack."
                ),
                text_color=_MUTED,
                font=ctk.CTkFont(size=11),
                wraplength=420,
                justify="left",
            ).pack(anchor="w", padx=16, pady=(4, 8))

        def copy_diag() -> None:
            if not app_prefs.get_diagnostics_enabled():
                messagebox.showinfo(
                    __app_name__,
                    "Diagnostics are off.\n\nEnable them in Settings first.",
                    parent=win,
                )
                return
            try:
                text = diagnostics.build_diagnostics_report()
                self.clipboard_clear()
                self.clipboard_append(text)
                self._set_status("Diagnostics copied — paste into a GitHub Issue.")
                messagebox.showinfo(
                    __app_name__,
                    "Anonymous diagnostics copied to the clipboard.\n\n"
                    "Open GitHub Issues → Bug or Crash report → paste.\n"
                    "No name, account, device ID, PDF content, or passwords.",
                    parent=win,
                )
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(__app_name__, f"Could not copy:\n{exc}", parent=win)

        def save_diag() -> None:
            if not app_prefs.get_diagnostics_enabled():
                messagebox.showinfo(
                    __app_name__,
                    "Diagnostics are off.\n\nEnable them in Settings first.",
                    parent=win,
                )
                return
            try:
                path = diagnostics.save_diagnostics_report()
                self._set_status(f"Diagnostics saved: {path.name}")
                messagebox.showinfo(
                    __app_name__,
                    f"Saved:\n{path}\n\n"
                    "Attach or paste into a GitHub Issue if you want.",
                    parent=win,
                )
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(__app_name__, f"Could not save:\n{exc}", parent=win)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4, 16))
        if diag_on:
            ctk.CTkButton(
                btn_row,
                text=_("Copy diagnostics"),
                width=140,
                command=copy_diag,
            ).pack(side="left")
            ctk.CTkButton(
                btn_row,
                text=_("Save diagnostics…"),
                width=140,
                fg_color="gray40",
                command=save_diag,
            ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_row, text=_("Close"), width=90, fg_color="gray40", command=win.destroy
        ).pack(side="right")


def _crash_log_path() -> Path:
    try:
        from sekikit.diagnostics import crash_log_path

        return crash_log_path()
    except Exception:  # noqa: BLE001
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent / "sekikit_crash.log"
        return Path(__file__).resolve().parent.parent / "sekikit_crash.log"


def main() -> None:
    try:
        init_i18n()
        app = SekikitApp()
        app.mainloop()
    except Exception as exc:  # noqa: BLE001
        log_path = _crash_log_path()
        text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(text, encoding="utf-8")
        except OSError:
            log_path = Path.cwd() / "sekikit_crash.log"
            log_path.write_text(text, encoding="utf-8")
        try:
            import tkinter as tk
            from tkinter import messagebox as mb

            root = tk.Tk()
            root.withdraw()
            mb.showerror(
                __app_name__,
                f"Sekikit failed to start:\n\n{exc}\n\nLog:\n{log_path}",
            )
            root.destroy()
        except Exception:
            print(text, file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
