"""Short hover tooltips for CTk/Tk widgets. Offline only."""

from __future__ import annotations

import tkinter as tk
from typing import Any


class Tooltip:
    """Delayed hover tip. Keep text short (1–2 lines)."""

    def __init__(
        self,
        widget: Any,
        text: str,
        *,
        delay_ms: int = 450,
        wrap: int = 280,
    ) -> None:
        self.widget = widget
        self.text = (text or "").strip()
        self.delay_ms = delay_ms
        self.wrap = wrap
        self._after_id: str | None = None
        self._tip: tk.Toplevel | None = None
        if not self.text:
            return
        try:
            widget.bind("<Enter>", self._schedule, add="+")
            widget.bind("<Leave>", self._hide, add="+")
            widget.bind("<ButtonPress>", self._hide, add="+")
        except Exception:  # noqa: BLE001
            pass

    def _schedule(self, _event=None) -> None:  # noqa: ANN001
        self._cancel()
        try:
            self._after_id = self.widget.after(self.delay_ms, self._show)
        except Exception:  # noqa: BLE001
            self._after_id = None

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:  # noqa: BLE001
                pass
            self._after_id = None

    def _hide(self, _event=None) -> None:  # noqa: ANN001
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._tip = None

    def _show(self) -> None:
        self._after_id = None
        if self._tip is not None:
            return
        try:
            if not self.widget.winfo_exists():
                return
        except Exception:  # noqa: BLE001
            return

        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        try:
            tip.wm_attributes("-topmost", True)
        except Exception:  # noqa: BLE001
            pass

        bg = "#1e1e1e"
        fg = "#f0f0f0"
        frame = tk.Frame(tip, background=bg, borderwidth=1, relief="solid")
        frame.pack(fill="both", expand=True)
        lbl = tk.Label(
            frame,
            text=self.text,
            justify="left",
            background=bg,
            foreground=fg,
            font=("Segoe UI", 9),
            wraplength=self.wrap,
            padx=8,
            pady=6,
        )
        lbl.pack()

        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            tip.geometry(f"+{x}+{y}")
        except Exception:  # noqa: BLE001
            pass

        self._tip = tip


def tip(widget: Any, text: str, **kwargs: Any) -> Tooltip | None:
    """Attach a short tooltip; returns Tooltip or None if empty."""
    if not text or not str(text).strip():
        return None
    return Tooltip(widget, str(text).strip(), **kwargs)
