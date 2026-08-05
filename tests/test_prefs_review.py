"""Prefs + review risk classification (no GUI)."""

from __future__ import annotations

from pathlib import Path

from sekikit import prefs


def test_default_review_mode() -> None:
    assert prefs.DEFAULT_REVIEW_MODE == "risk"
    assert "risk" in prefs.REVIEW_MODES


def test_is_risk_op() -> None:
    assert prefs.is_risk_op("delete")
    assert prefs.is_risk_op("delete_renumber")
    assert prefs.is_risk_op("renumber")
    assert prefs.is_risk_op("merge_renumber")
    assert prefs.is_risk_op("crop_hard")
    assert prefs.is_risk_op("grayscale")
    assert prefs.is_risk_op("compress_scan")
    assert prefs.is_risk_op("flatten")
    assert not prefs.is_risk_op("merge")
    assert not prefs.is_risk_op("compress_balanced")
    assert not prefs.is_risk_op("extract")
    assert not prefs.is_risk_op("Opening PDF")


def test_should_review_modes(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "prefs.json"
    monkeypatch.setattr(prefs, "prefs_path", lambda: path)

    prefs.set_review_mode("off")
    assert prefs.should_review("delete") is False
    assert prefs.should_review("merge") is False

    prefs.set_review_mode("risk")
    assert prefs.should_review("delete") is True
    assert prefs.should_review("merge") is False
    assert prefs.should_review("renumber") is True

    prefs.set_review_mode("always")
    assert prefs.should_review("delete") is True
    assert prefs.should_review("merge") is True
    assert prefs.should_review("compress_balanced") is True


def test_invalid_mode_falls_back(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "prefs.json"
    monkeypatch.setattr(prefs, "prefs_path", lambda: path)
    path.write_text('{"review_mode": "nope"}', encoding="utf-8")
    assert prefs.load_prefs()["review_mode"] == "risk"


def test_diagnostics_defaults_off(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "prefs.json"
    monkeypatch.setattr(prefs, "prefs_path", lambda: path)
    data = prefs.load_prefs()
    assert data["diagnostics_enabled"] is False
    assert data["first_run_completed"] is False
    assert prefs.get_diagnostics_enabled() is False


def test_diagnostics_and_first_run_persist(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "prefs.json"
    monkeypatch.setattr(prefs, "prefs_path", lambda: path)
    prefs.set_diagnostics_enabled(True)
    prefs.set_first_run_completed(True)
    assert prefs.get_diagnostics_enabled() is True
    assert prefs.get_first_run_completed() is True
    prefs.set_diagnostics_enabled(False)
    assert prefs.get_diagnostics_enabled() is False


def test_user_data_dir_source(tmp_path: Path, monkeypatch) -> None:
    # Source mode: project root (parent of sekikit package)
    d = prefs.user_data_dir()
    assert d.is_dir()
    assert (d / "sekikit").is_dir() or (d / "pyproject.toml").is_file() or d.exists()
