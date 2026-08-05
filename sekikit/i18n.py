"""Lightweight gettext-style i18n for community translations.

English is the source language (string keys = English UI text).
Other languages are JSON files in /locales that map English → translation.

Usage:
    from sekikit.i18n import _, init_i18n
    init_i18n()
    label = _("Merge PDFs")
"""

from __future__ import annotations

import json
import locale
import os
import sys
from pathlib import Path

_catalog: dict[str, str] = {}
_lang: str = "en"


def locales_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "locales"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / "locales"


def available_languages() -> list[str]:
    d = locales_dir()
    if not d.is_dir():
        return ["en"]
    langs = sorted({p.stem for p in d.glob("*.json") if not p.stem.startswith("_")})
    return langs or ["en"]


def _load_json(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if isinstance(v, str) and v.strip()}
    except (OSError, json.JSONDecodeError):
        return {}


def load_language(code: str) -> str:
    """Load language code (e.g. 'en', 'fr'). Falls back to English for missing keys."""
    global _catalog, _lang
    code = (code or "en").replace("-", "_").split("_")[0].lower()
    en = _load_json(locales_dir() / "en.json")
    if code == "en":
        _catalog = en
        _lang = "en"
        return _lang
    overlay = _load_json(locales_dir() / f"{code}.json")
    if not overlay:
        _catalog = en
        _lang = "en"
        return _lang
    merged = dict(en)
    merged.update(overlay)
    _catalog = merged
    _lang = code
    return _lang


def detect_language() -> str:
    """SEKIKIT_LANG → LANG/LC_ALL → OS locale → en."""
    for key in ("SEKIKIT_LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(key, "").strip()
        if raw:
            # LANGUAGE may be colon-separated (fr:en).
            part = raw.split(":")[0]
            code = part.replace("-", "_").split(".")[0].split("_")[0].lower()
            if code and code != "c":
                return code
    try:
        loc = locale.getdefaultlocale()[0]  # type: ignore[deprecated]
        if loc:
            return loc.replace("-", "_").split("_")[0].lower()
    except Exception:  # noqa: BLE001
        pass
    try:
        loc = locale.getlocale()[0]
        if loc:
            return loc.replace("-", "_").split("_")[0].lower()
    except Exception:  # noqa: BLE001
        pass
    return "en"


def init_i18n(lang: str | None = None) -> str:
    """Initialize catalogs. Returns active language code."""
    code = (lang or detect_language()).lower()
    available = available_languages()
    if code not in available:
        code = "en"
    return load_language(code)


def _(message: str) -> str:
    """Translate message; return English (or original) if missing."""
    if not message:
        return message
    if not _catalog:
        return message
    return _catalog.get(message, message)


def language() -> str:
    return _lang
