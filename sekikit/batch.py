"""Batch helpers: run one op across many local PDF paths (GUI/CLI reuse)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from sekikit import jobs
from sekikit import pdf_ops


def run_batch_files(
    files: list[Path],
    work_one: Callable[[Path], Path],
    *,
    op: str,
    cancel_check: Callable[[], bool] | None = None,
    validate_password: str | None = None,
    on_progress: Callable[[int, int, Path], None] | None = None,
) -> tuple[list[Path], list[str]]:
    """Run work_one(src)->Path for each file.

    Returns (successful_output_paths, error_messages).
    Skips remaining files when cancel_check() is true (between files).
    Does not raise — failures are collected as strings.
    """
    ok: list[Path] = []
    errors: list[str] = []
    total = len(files)
    for i, src in enumerate(files):
        if cancel_check and cancel_check():
            break
        if on_progress:
            try:
                on_progress(i + 1, total, src)
            except Exception:  # noqa: BLE001
                pass
        try:

            def _fn(s: Path = src) -> Path:
                return work_one(s)

            jr = jobs.run_job(
                op,
                _fn,
                inputs=[src],
                validate_password=validate_password,
            )
            if jr.paths:
                ok.extend(jr.paths)
            elif isinstance(jr.value, Path):
                ok.append(jr.value)
            elif jr.ok and not jr.paths:
                # work returned non-path — treat as error for batch file ops
                errors.append(f"{src.name}: no output file")
        except pdf_ops.PdfOpsError as exc:
            errors.append(f"{src.name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{src.name}: {exc}")
    return ok, errors
