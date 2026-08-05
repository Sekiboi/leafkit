"""Local user prefs (offline only — never uploaded)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

REVIEW_MODES = ("off", "risk", "always")
DEFAULT_REVIEW_MODE = "risk"

# Risk-mode ops (matched case-insensitively against job op strings).
_RISK_OP_MARKERS = (
    "delete",
    "renumber",
    "crop_hard",
    "hardcrop",
    "crop_box",
    "grayscale",
    "compress_scan",
    "flatten",
    "decrypt",
)


def user_data_dir() -> Path:
    """Writable app data folder (installed apps must not write under Program Files)."""
    if getattr(sys, "frozen", False):
        # Windows: %LOCALAPPDATA%\Sekikit
        # Other OS: ~/.local/share/Sekikit or ~/Library/Application Support/Sekikit
        if sys.platform == "win32":
            root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
            base = root / "Sekikit"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "Sekikit"
        else:
            xdg = os.environ.get("XDG_DATA_HOME")
            base = (
                Path(xdg) / "Sekikit"
                if xdg
                else Path.home() / ".local" / "share" / "Sekikit"
            )
    else:
        # Source checkout: keep next to project for easy dev
        base = Path(__file__).resolve().parent.parent
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return base


def prefs_path() -> Path:
    return user_data_dir() / "sekikit_prefs.json"


def load_prefs() -> dict[str, Any]:
    path = prefs_path()
    data: dict[str, Any] = {
        "review_mode": DEFAULT_REVIEW_MODE,
        "diagnostics_enabled": False,
        "first_run_completed": False,
    }
    if not path.is_file():
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update(raw)
    except (OSError, json.JSONDecodeError):
        pass
    mode = str(data.get("review_mode", DEFAULT_REVIEW_MODE)).lower()
    if mode not in REVIEW_MODES:
        mode = DEFAULT_REVIEW_MODE
    data["review_mode"] = mode
    data["diagnostics_enabled"] = bool(data.get("diagnostics_enabled", False))
    data["first_run_completed"] = bool(data.get("first_run_completed", False))
    return data


def save_prefs(data: dict[str, Any]) -> None:
    path = prefs_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def get_review_mode() -> str:
    return str(load_prefs().get("review_mode", DEFAULT_REVIEW_MODE))


def set_review_mode(mode: str) -> str:
    mode = (mode or DEFAULT_REVIEW_MODE).strip().lower()
    if mode not in REVIEW_MODES:
        mode = DEFAULT_REVIEW_MODE
    data = load_prefs()
    data["review_mode"] = mode
    save_prefs(data)
    return mode


def get_diagnostics_enabled() -> bool:
    return bool(load_prefs().get("diagnostics_enabled", False))


def set_diagnostics_enabled(enabled: bool) -> bool:
    data = load_prefs()
    data["diagnostics_enabled"] = bool(enabled)
    save_prefs(data)
    return bool(data["diagnostics_enabled"])


def get_first_run_completed() -> bool:
    return bool(load_prefs().get("first_run_completed", False))


def set_first_run_completed(done: bool = True) -> None:
    data = load_prefs()
    data["first_run_completed"] = bool(done)
    save_prefs(data)


def is_risk_op(op: str | None) -> bool:
    """True if this job should prompt under review_mode=risk."""
    if not op:
        return False
    key = op.lower().replace(" ", "_").replace("+", "_")
    for marker in _RISK_OP_MARKERS:
        if marker in key:
            return True
    low = op.lower()
    if "renumber" in low:
        return True
    if "hard crop" in low or "hardcrop" in low:
        return True
    return False


def should_review(op: str | None, *, mode: str | None = None) -> bool:
    m = (mode or get_review_mode()).lower()
    if m == "off":
        return False
    if m == "always":
        return True
    return is_risk_op(op)
