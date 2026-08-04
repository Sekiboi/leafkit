"""JustPages GUI — offline PDF page toolkit."""

from __future__ import annotations

import os
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from justpages import __app_name__, __version__
from justpages import pdf_ops


APP_TITLE = f"{__app_name__} v{__version__}"
WINDOW_SIZE = "780x620"
MIN_SIZE = (640, 520)

# CustomTkinter appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def _resource_path(relative: str) -> Path:
    """Path helper for frozen (PyInstaller) and source runs."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / relative


class JustPagesApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(*MIN_SIZE)

        self._files: list[Path] = []
        self._busy = False

        self._build_ui()
        self._set_status("Ready — add PDF files to begin. Everything stays on your PC.")

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="JustPages",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Merge · Extract · Split · Rotate — offline, no upload",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray70"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        # File list toolbar
        file_bar = ctk.CTkFrame(body, fg_color="transparent")
        file_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        for i in range(6):
            file_bar.grid_columnconfigure(i, weight=0)
        file_bar.grid_columnconfigure(5, weight=1)

        ctk.CTkButton(file_bar, text="Add PDFs…", width=100, command=self._add_files).grid(
            row=0, column=0, padx=(0, 6)
        )
        ctk.CTkButton(
            file_bar, text="Remove", width=80, command=self._remove_selected, fg_color="gray40"
        ).grid(row=0, column=1, padx=6)
        ctk.CTkButton(
            file_bar, text="Clear", width=70, command=self._clear_files, fg_color="gray40"
        ).grid(row=0, column=2, padx=6)
        ctk.CTkButton(file_bar, text="↑", width=36, command=lambda: self._move(-1)).grid(
            row=0, column=3, padx=(12, 4)
        )
        ctk.CTkButton(file_bar, text="↓", width=36, command=lambda: self._move(1)).grid(
            row=0, column=4, padx=4
        )

        self.file_list = ctk.CTkTextbox(body, height=140, activate_scrollbars=True)
        self.file_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self.file_list.configure(state="disabled")
        # Selection line via click is awkward in CTkTextbox; use index field
        self._selected_index = 0

        select_bar = ctk.CTkFrame(body, fg_color="transparent")
        select_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        ctk.CTkLabel(select_bar, text="Selected row (1-based):").pack(side="left")
        self.sel_entry = ctk.CTkEntry(select_bar, width=50)
        self.sel_entry.pack(side="left", padx=8)
        self.sel_entry.insert(0, "1")
        ctk.CTkLabel(
            select_bar,
            text="(used by Remove / Move / Extract / Split / Rotate)",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(side="left")

        # Tabs for actions
        self.tabs = ctk.CTkTabview(body)
        self.tabs.grid(row=3, column=0, sticky="ew", padx=12, pady=(6, 12))
        for name in ("Merge", "Extract", "Split", "Rotate"):
            self.tabs.add(name)

        self._build_merge_tab()
        self._build_extract_tab()
        self._build_split_tab()
        self._build_rotate_tab()

        # Status + footer
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
        ctk.CTkLabel(
            footer,
            text="MIT · 100% offline · github.com/Sekiboi/justpages",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Drag-and-drop is platform-specific; offer open via double-click zone hint
        self.bind("<Control-o>", lambda _e: self._add_files())

    def _build_merge_tab(self) -> None:
        tab = self.tabs.tab("Merge")
        ctk.CTkLabel(
            tab,
            text="Combine all listed PDFs in order (use ↑↓ to reorder).",
            anchor="w",
        ).pack(fill="x", pady=(8, 8))
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkButton(row, text="Choose output…", width=120, command=self._pick_merge_out).pack(
            side="left"
        )
        self.merge_out = ctk.CTkEntry(row, placeholder_text="Output path (optional — defaults next to first file)")
        self.merge_out.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ctk.CTkButton(tab, text="Merge PDFs", height=36, command=self._run_merge).pack(
            fill="x", pady=(12, 8)
        )

    def _build_extract_tab(self) -> None:
        tab = self.tabs.tab("Extract")
        ctk.CTkLabel(
            tab,
            text="Pull pages from the selected PDF into a new file. Pages are 1-based.",
            anchor="w",
        ).pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(
            tab,
            text="Examples:  1-3   ·   2,5,9   ·   1,4-6,10-",
            anchor="w",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text="Pages:").pack(side="left")
        self.extract_range = ctk.CTkEntry(row, width=200, placeholder_text="e.g. 2-5, 9")
        self.extract_range.pack(side="left", padx=8)

        row2 = ctk.CTkFrame(tab, fg_color="transparent")
        row2.pack(fill="x", pady=4)
        ctk.CTkButton(row2, text="Choose output…", width=120, command=self._pick_extract_out).pack(
            side="left"
        )
        self.extract_out = ctk.CTkEntry(row2, placeholder_text="Output path (optional)")
        self.extract_out.pack(side="left", fill="x", expand=True, padx=(8, 0))

        ctk.CTkButton(tab, text="Extract pages", height=36, command=self._run_extract).pack(
            fill="x", pady=(12, 8)
        )

    def _build_split_tab(self) -> None:
        tab = self.tabs.tab("Split")
        ctk.CTkLabel(
            tab,
            text="Split the selected PDF into multiple files.",
            anchor="w",
        ).pack(fill="x", pady=(8, 8))

        self.split_mode = ctk.StringVar(value="each")
        modes = ctk.CTkFrame(tab, fg_color="transparent")
        modes.pack(fill="x")
        ctk.CTkRadioButton(
            modes, text="One file per page", variable=self.split_mode, value="each"
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            modes, text="Every N pages:", variable=self.split_mode, value="every_n"
        ).pack(side="left")
        self.split_n = ctk.CTkEntry(modes, width=50)
        self.split_n.pack(side="left", padx=8)
        self.split_n.insert(0, "2")

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=(10, 4))
        ctk.CTkButton(row, text="Output folder…", width=120, command=self._pick_split_dir).pack(
            side="left"
        )
        self.split_dir = ctk.CTkEntry(row, placeholder_text="Folder (optional — defaults next to source)")
        self.split_dir.pack(side="left", fill="x", expand=True, padx=(8, 0))

        ctk.CTkButton(tab, text="Split PDF", height=36, command=self._run_split).pack(
            fill="x", pady=(12, 8)
        )

    def _build_rotate_tab(self) -> None:
        tab = self.tabs.tab("Rotate")
        ctk.CTkLabel(
            tab,
            text="Rotate pages of the selected PDF (clockwise).",
            anchor="w",
        ).pack(fill="x", pady=(8, 8))

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text="Degrees:").pack(side="left")
        self.rotate_deg = ctk.CTkSegmentedButton(row, values=["90", "180", "270"])
        self.rotate_deg.pack(side="left", padx=8)
        self.rotate_deg.set("90")

        row2 = ctk.CTkFrame(tab, fg_color="transparent")
        row2.pack(fill="x", pady=4)
        ctk.CTkLabel(row2, text="Pages (blank = all):").pack(side="left")
        self.rotate_range = ctk.CTkEntry(row2, width=200, placeholder_text="e.g. 1-2 or leave blank")
        self.rotate_range.pack(side="left", padx=8)

        row3 = ctk.CTkFrame(tab, fg_color="transparent")
        row3.pack(fill="x", pady=4)
        ctk.CTkButton(row3, text="Choose output…", width=120, command=self._pick_rotate_out).pack(
            side="left"
        )
        self.rotate_out = ctk.CTkEntry(row3, placeholder_text="Output path (optional)")
        self.rotate_out.pack(side="left", fill="x", expand=True, padx=(8, 0))

        ctk.CTkButton(tab, text="Rotate pages", height=36, command=self._run_rotate).pack(
            fill="x", pady=(12, 8)
        )

    # -------------------------------------------------------------- file list
    def _refresh_list(self) -> None:
        self.file_list.configure(state="normal")
        self.file_list.delete("1.0", "end")
        if not self._files:
            self.file_list.insert("end", "(no PDFs yet — click Add PDFs…)\n")
        else:
            for i, p in enumerate(self._files, start=1):
                try:
                    pages = pdf_ops.page_count(p)
                    meta = f"  [{pages} page{'s' if pages != 1 else ''}]"
                except pdf_ops.PdfOpsError:
                    meta = "  [unreadable]"
                self.file_list.insert("end", f"{i}.  {p.name}{meta}\n     {p}\n")
        self.file_list.configure(state="disabled")

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not paths:
            return
        added = 0
        for raw in paths:
            p = Path(raw)
            if p not in self._files:
                self._files.append(p)
                added += 1
        self._refresh_list()
        self._set_status(f"Added {added} file(s). {len(self._files)} total.")

    def _selected_row(self) -> int | None:
        raw = self.sel_entry.get().strip()
        if not raw:
            return None
        try:
            n = int(raw)
        except ValueError:
            return None
        if n < 1 or n > len(self._files):
            return None
        return n - 1

    def _require_selected(self) -> Path | None:
        if not self._files:
            messagebox.showinfo(__app_name__, "Add at least one PDF first.")
            return None
        idx = self._selected_row()
        if idx is None:
            messagebox.showinfo(
                __app_name__,
                "Set “Selected row” to the file number you want "
                f"(1–{len(self._files)}).",
            )
            return None
        return self._files[idx]

    def _remove_selected(self) -> None:
        idx = self._selected_row()
        if idx is None or not self._files:
            return
        removed = self._files.pop(idx)
        if self._files:
            self.sel_entry.delete(0, "end")
            self.sel_entry.insert(0, str(min(idx + 1, len(self._files))))
        self._refresh_list()
        self._set_status(f"Removed {removed.name}.")

    def _clear_files(self) -> None:
        self._files.clear()
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
        self.sel_entry.delete(0, "end")
        self.sel_entry.insert(0, str(new + 1))
        self._refresh_list()

    # ----------------------------------------------------------- path pickers
    def _pick_merge_out(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save merged PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="merged.pdf",
        )
        if path:
            self.merge_out.delete(0, "end")
            self.merge_out.insert(0, path)

    def _pick_extract_out(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save extracted PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="extracted.pdf",
        )
        if path:
            self.extract_out.delete(0, "end")
            self.extract_out.insert(0, path)

    def _pick_split_dir(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder for split files")
        if path:
            self.split_dir.delete(0, "end")
            self.split_dir.insert(0, path)

    def _pick_rotate_out(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save rotated PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="rotated.pdf",
        )
        if path:
            self.rotate_out.delete(0, "end")
            self.rotate_out.insert(0, path)

    # --------------------------------------------------------------- actions
    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy

    def _run_bg(self, work, on_ok, label: str) -> None:
        if self._busy:
            return

        def runner() -> None:
            self.after(0, lambda: self._set_busy(True))
            self.after(0, lambda: self._set_status(f"{label}…"))
            try:
                result = work()
            except pdf_ops.PdfOpsError as exc:
                self.after(0, lambda: self._fail(str(exc)))
            except Exception:  # noqa: BLE001
                tb = traceback.format_exc()
                self.after(0, lambda: self._fail(f"Unexpected error:\n{tb}"))
            else:
                self.after(0, lambda: on_ok(result))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=runner, daemon=True).start()

    def _fail(self, msg: str) -> None:
        self._set_status("Error.")
        messagebox.showerror(__app_name__, msg)

    def _ok_file(self, path: Path, verb: str) -> None:
        self._set_status(f"{verb}: {path}")
        if messagebox.askyesno(__app_name__, f"{verb}.\n\n{path}\n\nOpen containing folder?"):
            self._open_folder(path.parent)

    def _ok_files(self, paths: list[Path], verb: str) -> None:
        if not paths:
            self._set_status("Nothing written.")
            return
        folder = paths[0].parent
        self._set_status(f"{verb}: {len(paths)} file(s) in {folder}")
        if messagebox.askyesno(
            __app_name__,
            f"{verb}: {len(paths)} file(s).\n\n{folder}\n\nOpen folder?",
        ):
            self._open_folder(folder)

    @staticmethod
    def _open_folder(folder: Path) -> None:
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def _run_merge(self) -> None:
        if len(self._files) < 2:
            messagebox.showinfo(__app_name__, "Add at least two PDFs to merge.")
            return
        out_raw = self.merge_out.get().strip()
        if out_raw:
            out = Path(out_raw)
        else:
            out = pdf_ops.default_output_next_to(self._files[0], "_merged")

        def work():
            return pdf_ops.merge_pdfs(self._files, out)

        self._run_bg(work, lambda p: self._ok_file(p, "Merged"), "Merging")

    def _run_extract(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        page_spec = self.extract_range.get().strip()
        out_raw = self.extract_out.get().strip()
        if out_raw:
            out = Path(out_raw)
        else:
            safe = page_spec.replace(",", "_").replace("-", "to").replace(" ", "")
            out = pdf_ops.default_output_next_to(src, f"_pages_{safe or 'extract'}")

        def work():
            return pdf_ops.extract_pages(src, page_spec, out)

        self._run_bg(work, lambda p: self._ok_file(p, "Extracted"), "Extracting")

    def _run_split(self) -> None:
        src = self._require_selected()
        if src is None:
            return
        mode = self.split_mode.get()
        every_n = 1
        if mode == "every_n":
            try:
                every_n = int(self.split_n.get().strip())
            except ValueError:
                messagebox.showerror(__app_name__, "N must be a whole number.")
                return
        dir_raw = self.split_dir.get().strip()
        out_dir = Path(dir_raw) if dir_raw else src.parent / f"{src.stem}_split"

        def work():
            return pdf_ops.split_pdf(src, mode, out_dir, every_n=every_n)

        self._run_bg(work, lambda ps: self._ok_files(ps, "Split"), "Splitting")

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
        if out_raw:
            out = Path(out_raw)
        else:
            out = pdf_ops.default_output_next_to(src, f"_rot{degrees}")

        def work():
            return pdf_ops.rotate_pages(src, degrees, out, page_spec=page_spec)

        self._run_bg(work, lambda p: self._ok_file(p, "Rotated"), "Rotating")


def main() -> None:
    app = JustPagesApp()
    app.mainloop()


if __name__ == "__main__":
    main()
