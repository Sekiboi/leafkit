"""i18n infrastructure tests."""

from __future__ import annotations

from leafkit.i18n import _, available_languages, init_i18n, language, load_language


def test_english_identity() -> None:
    init_i18n("en")
    assert language() == "en"
    assert _("Merge PDFs") == "Merge PDFs"
    assert _("Add PDFs…") == "Add PDFs…"


def test_fallback_unknown_lang() -> None:
    init_i18n("zz_not_a_lang")
    assert language() == "en"
    assert _("About") == "About"


def test_missing_key_returns_original() -> None:
    init_i18n("en")
    assert _("___not_in_catalog___") == "___not_in_catalog___"


def test_en_available() -> None:
    assert "en" in available_languages()
