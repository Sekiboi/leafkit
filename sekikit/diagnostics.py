"""Local anonymous diagnostics for bug reports — never uploaded automatically.

Users can copy or save a report and paste it into a GitHub Issue.
Reports are anonymous: no name, account, device ID, or full paths.
No PDF content, no passwords.
"""

from __future__ import annotations

import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from sekikit import __version__
from sekikit import jobs
from sekikit import prefs as app_prefs
from sekikit import render as pdf_render


def crash_log_path() -> Path:
    """Crash log lives in user data dir (writable after install)."""
    from sekikit.prefs import user_data_dir

    return user_data_dir() / "sekikit_crash.log"


def app_data_dir() -> Path:
    from sekikit.prefs import user_data_dir

    return user_data_dir()


# --- Anonymization -----------------------------------------------------------

# Windows: C:\Users\Alice\...  (also mixed slashes)
_RE_WIN_USERS = re.compile(
    r"(?i)([A-Z]:[/\\]Users[/\\])([^/\\]+)([/\\]?)",
)
# macOS: /Users/Alice/...
_RE_MAC_USERS = re.compile(r"(/Users/)([^/]+)(/?)")
# Linux: /home/alice/...
_RE_LINUX_HOME = re.compile(r"(/home/)([^/]+)(/?)")
# Windows profile variants under AppData / Documents etc. already covered by Users.
# UNC: \\server\share\...
_RE_UNC = re.compile(r"\\\\[^\\\s]+\\[^\s\"']+")
# file:// URLs with user homes
_RE_FILE_URL = re.compile(r"(?i)file:///[A-Za-z]:/Users/[^/\s]+")
# Email-like (rare in logs; still scrub)
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# IPv4 (local/LAN can identify a network)
_RE_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)


def _safe_username() -> str:
    try:
        name = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        return name.strip()
    except Exception:  # noqa: BLE001
        return ""


def _safe_hostname() -> str:
    try:
        return (platform.node() or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def anonymize_text(text: str) -> str:
    """Redact usernames, home paths, hosts, emails, and IPs from log snippets."""
    if not text:
        return text

    out = text

    # Prefer concrete home path first (most specific).
    try:
        home = str(Path.home())
        if home and len(home) > 3:
            # Normalize both slash styles for matching on Windows.
            for variant in {home, home.replace("\\", "/"), home.replace("/", "\\")}:
                if variant and variant in out:
                    out = out.replace(variant, "<home>")
    except Exception:  # noqa: BLE001
        pass

    # Pattern-based home redaction (covers paths that differ from Path.home()).
    out = _RE_WIN_USERS.sub(r"\1<user>\3", out)
    out = _RE_MAC_USERS.sub(r"\1<user>\3", out)
    out = _RE_LINUX_HOME.sub(r"\1<user>\3", out)
    out = _RE_UNC.sub(r"\\\\<host>\\<share>", out)
    out = _RE_FILE_URL.sub("file:///<drive>/Users/<user>", out)

    user = _safe_username()
    if user and len(user) >= 2:
        # Whole-word-ish: avoid eating short tokens inside other words.
        out = re.sub(
            re.escape(user),
            "<user>",
            out,
            flags=re.IGNORECASE,
        )

    host = _safe_hostname()
    if host and len(host) >= 2 and host.lower() not in ("localhost", "127.0.0.1"):
        out = re.sub(re.escape(host), "<host>", out, flags=re.IGNORECASE)

    # Common env-expanded data roots that may appear in traces.
    for env_key in ("LOCALAPPDATA", "APPDATA", "TEMP", "TMP", "USERPROFILE"):
        raw = os.environ.get(env_key) or ""
        if raw and len(raw) > 3 and raw in out:
            out = out.replace(raw, f"<{env_key.lower()}>")

    out = _RE_EMAIL.sub("<email>", out)
    out = _RE_IPV4.sub("<ip>", out)
    return out


def _os_summary() -> str:
    """Coarse OS string — enough for bugs, not a device fingerprint."""
    system = platform.system() or "unknown"
    release = platform.release() or ""
    # Skip platform.version() (long build strings / install-specific noise).
    machine = platform.machine() or ""
    parts = [system]
    if release:
        parts.append(release)
    if machine:
        parts.append(f"({machine})")
    return " ".join(parts)


def _tail_text(path: Path, max_lines: int = 40, max_chars: int = 8000) -> str:
    if not path.is_file():
        return "(none)"
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"(unreadable: {type(exc).__name__})"
    lines = raw.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
        body = "\n".join(lines)
        body = f"… (last {max_lines} lines)\n{body}"
    else:
        body = "\n".join(lines)
    if len(body) > max_chars:
        body = "…\n" + body[-max_chars:]
    body = body.strip() or "(empty)"
    return anonymize_text(body)


def build_diagnostics_report(
    *,
    extra_notes: str = "",
    include_crash: bool = True,
    include_job_log: bool = True,
) -> str:
    """Build an anonymous plain-text report safe to paste into GitHub Issues."""
    frozen = bool(getattr(sys, "frozen", False))
    try:
        gs = __import__("sekikit.pdf_ops", fromlist=["find_ghostscript"]).find_ghostscript()
        gs_s = "found" if gs else "not found"
    except Exception:  # noqa: BLE001
        gs_s = "unknown"

    notes = anonymize_text(extra_notes.strip()) if extra_notes.strip() else ""

    lines = [
        "### Sekikit diagnostics (anonymous)",
        "",
        "This report is **anonymous**: no account, name, device ID, hostname,",
        "or full folder paths. Paths in log tails are redacted.",
        "",
        f"- **Version:** {__version__}",
        f"- **Frozen (exe):** {frozen}",
        f"- **Python:** {sys.version.split()[0]} ({platform.python_implementation()})",
        f"- **OS:** {_os_summary()}",
        f"- **Review mode:** {app_prefs.get_review_mode()}",
        f"- **PyMuPDF (thumbnails):** {pdf_render.has_renderer()}",
        f"- **Ghostscript:** {gs_s}",
        f"- **Report generated (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "### Privacy",
        "",
        "- **Anonymous** — no name, email, account, or device identifier.",
        "- No PDF content is included.",
        "- Job log lines use **file basenames only**; remaining paths are redacted.",
        "- Crash traceback paths are redacted (homes, usernames, hosts).",
        "- Passwords are never included.",
        "- Nothing is sent by the app; you choose whether to paste this.",
        "",
    ]
    if notes:
        lines.extend(
            [
                "### User notes",
                "",
                notes,
                "",
            ]
        )

    if include_job_log:
        jpath = jobs.job_log_path()
        lines.extend(
            [
                f"### Recent job log (`{jpath.name}`)",
                "",
                "```",
                _tail_text(jpath, max_lines=30, max_chars=6000),
                "```",
                "",
            ]
        )

    if include_crash:
        cpath = crash_log_path()
        lines.extend(
            [
                f"### Crash log (`{cpath.name}`)",
                "",
                "```",
                _tail_text(cpath, max_lines=80, max_chars=10000),
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "### How to report",
            "",
            "1. Open: https://github.com/Sekiboi/sekikit/issues/new/choose",
            "2. Pick **Bug report** or **Crash report**.",
            "3. Paste this block and describe steps to reproduce.",
            "4. Do **not** attach confidential PDFs unless you choose to.",
            "",
        ]
    )
    return "\n".join(lines)


def save_diagnostics_report(path: Path | None = None) -> Path:
    """Write diagnostics next to the app; return path."""
    if path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = app_data_dir() / f"sekikit_diagnostics_{stamp}.txt"
    path = Path(path)
    path.write_text(build_diagnostics_report(), encoding="utf-8")
    return path
