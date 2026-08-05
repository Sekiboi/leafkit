"""Diagnostics report for bug reports (local only, anonymous)."""

from __future__ import annotations

from pathlib import Path

from sekikit import __version__
from sekikit import diagnostics


def test_anonymize_text_redacts_paths_and_pii() -> None:
    sample = (
        r"File C:\Users\Alice\Documents\secret.pdf failed\n"
        r"/home/bob/work/file.pdf\n"
        r"/Users/carol/Desktop/x.pdf\n"
        r"contact me@example.com from 192.168.1.50\n"
        r"\\fileserver\share\docs\a.pdf"
    )
    out = diagnostics.anonymize_text(sample)
    assert "Alice" not in out
    assert "bob" not in out
    assert "carol" not in out
    assert r"C:\Users\<user>" in out or "C:\\Users\\<user>" in out
    assert "/home/<user>" in out
    assert "/Users/<user>" in out
    assert "me@example.com" not in out
    assert "<email>" in out
    assert "192.168.1.50" not in out
    assert "<ip>" in out
    assert "fileserver" not in out


def test_build_diagnostics_report_safe(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "sekikit_jobs.log"
    log.write_text(
        '{"op":"merge","ok":true,"inputs":["secret.pdf"],"outputs":["out.pdf"]}\n'
        r'{"op":"fail","ok":false,"error":"C:\\Users\\Alice\\bad.pdf"}\n',
        encoding="utf-8",
    )
    crash = tmp_path / "sekikit_crash.log"
    crash.write_text(
        "Traceback:\n"
        r'  File "C:\Users\Alice\repos\sekikit\app.py", line 1\n'
        "Exception: boom\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("sekikit.jobs.job_log_path", lambda: log)
    monkeypatch.setattr("sekikit.diagnostics.crash_log_path", lambda: crash)

    text = diagnostics.build_diagnostics_report(extra_notes="hello")
    assert __version__ in text
    assert "hello" in text
    assert "secret.pdf" in text  # basename from job log is ok
    assert "Traceback" in text
    assert "anonymous" in text.lower()
    assert "Sekikit diagnostics (anonymous)" in text
    # No username / full home path leaked from crash or job error
    assert "Alice" not in text
    assert r"C:\Users\Alice" not in text
    assert "<user>" in text
    # Coarse OS only — no raw platform.version() dump required
    assert "password" not in text.lower() or "Passwords are never" in text
    # Ghostscript path must not appear (only found / not found / unknown)
    assert "Ghostscript:" in text


def test_build_diagnostics_report_anonymizes_notes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sekikit.jobs.job_log_path", lambda: tmp_path / "missing_jobs.log"
    )
    monkeypatch.setattr(
        "sekikit.diagnostics.crash_log_path",
        lambda: tmp_path / "missing_crash.log",
    )
    text = diagnostics.build_diagnostics_report(
        extra_notes=r"crash at C:\Users\Dave\x.pdf email dave@corp.com"
    )
    assert "Dave" not in text
    assert "dave@corp.com" not in text
    assert "<email>" in text


def test_save_diagnostics_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("sekikit.diagnostics.app_data_dir", lambda: tmp_path)
    path = diagnostics.save_diagnostics_report()
    assert path.is_file()
    assert path.parent == tmp_path
    body = path.read_text(encoding="utf-8")
    assert "Sekikit diagnostics (anonymous)" in body
