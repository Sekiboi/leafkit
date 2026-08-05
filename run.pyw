"""Windows no-console entry (double-click). Uses the same startup as run.py."""

from __future__ import annotations

import run as _run

if __name__ == "__main__":
    try:
        _run.main()
    except SystemExit as exc:
        code = exc.code
        if code not in (0, None) and not isinstance(code, int):
            _run._show_error("JustPages — setup needed", str(code))
    except Exception as exc:  # noqa: BLE001
        log_path = _run._write_crash(exc)
        _run._show_error(
            "JustPages crashed",
            f"{exc}\n\nDetails saved to:\n{log_path}",
        )
