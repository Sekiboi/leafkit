"""Shared GUI constants (no heavy imports)."""

from __future__ import annotations

PAGENUM_PRESETS: dict[str, str] = {
    "1 / N": "{n} / {total}",
    "Page n": "Page {n}",
    "— n —": "— {n} —",
    "n": "{n}",
    "Custom": "",
}

# File list rows
ROW_BG = ("gray94", "gray18")
ROW_BG_SEL = ("#d4e6f8", "#1a3d5c")
ROW_BORDER_SEL = ("#3B8ED0", "#3B8ED0")

# Soft surfaces for empty states / cards
SURFACE_EMPTY = ("gray96", "gray17")
ACCENT = ("#3B8ED0", "#4A9FE0")
MUTED = ("gray40", "gray70")
