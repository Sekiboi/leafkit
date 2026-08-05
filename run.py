"""Launch Sekikit from the project root: python run.py"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _crash_log_path() -> Path:
    try:
        from sekikit.diagnostics import crash_log_path

        return crash_log_path()
    except Exception:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent / "sekikit_crash.log"
        return Path(__file__).resolve().parent / "sekikit_crash.log"


def _write_crash(exc: BaseException) -> Path:
    path = _crash_log_path()
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError:
        path = Path.cwd() / "sekikit_crash.log"
        path.write_text(text, encoding="utf-8")
    return path


def _show_error(title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        # Last resort: print for console launches
        print(f"{title}: {message}", file=sys.stderr)


def _check_dependencies() -> None:
    missing: list[str] = []
    for mod, pip_name in (
        ("customtkinter", "customtkinter"),
        ("pypdf", "pypdf"),
        ("PIL", "Pillow"),
        ("tkinterdnd2", "tkinterdnd2"),
    ):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return

    # Common case: system Python instead of the project venv
    venv_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    hint = (
        "Missing packages: " + ", ".join(missing) + "\n\n"
        "Fix (recommended):\n"
        "  1. Double-click  launch.bat  (or launch.vbs for no console)\n"
        "  or\n"
        "  2. In PowerShell from this folder:\n"
        "       .\\.venv\\Scripts\\Activate.ps1\n"
        "       pip install -r requirements.txt\n"
        "       pythonw run.py\n"
    )
    if venv_python.is_file():
        venv_pythonw = venv_python.with_name("pythonw.exe")
        runner = venv_pythonw if venv_pythonw.is_file() else venv_python
        hint += f"\nOr run directly:\n  {runner} run.py\n"

    raise SystemExit(hint)


def main() -> None:
    if not getattr(sys, "frozen", False):
        _check_dependencies()

    from sekikit.app import main as app_main

    app_main()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        # Friendly dependency / intentional exits
        code = exc.code
        if code not in (0, None):
            msg = str(code) if not isinstance(code, int) else f"Exit code {code}"
            if not isinstance(code, int):
                _show_error("Sekikit — setup needed", msg)
            raise
    except Exception as exc:  # noqa: BLE001 — top-level crash barrier
        log_path = _write_crash(exc)
        _show_error(
            "Sekikit crashed",
            f"{exc}\n\nDetails saved to:\n{log_path}",
        )
        raise
