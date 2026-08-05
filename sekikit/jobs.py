"""Unified job runner, local job log, session password cache."""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sekikit import __version__
from sekikit import pdf_ops


@dataclass
class JobResult:
    """Result of a single PDF operation."""

    op: str
    paths: list[Path]
    ok: bool
    duration_s: float
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    pages: int | None = None
    # Non-path return (e.g. ThumbnailSession). Never coerce to Path.
    value: Any = None


# Password cache key = resolved path only (never basename).
_password_cache: dict[str, str] = {}


def _cache_key(path: Path | str) -> str:
    p = Path(path).expanduser()
    try:
        return str(p.resolve())
    except OSError:
        return str(p.absolute()) if not p.is_absolute() else str(p)


def password_cache_set(path: Path | str, password: str) -> None:
    _password_cache[_cache_key(path)] = password


def password_cache_get(path: Path | str) -> str | None:
    return _password_cache.get(_cache_key(path))


def password_cache_clear() -> None:
    _password_cache.clear()


def make_password_provider(
    fallback: str | None = None,
) -> Callable[[Path], str | None]:
    """Provider for pdf_ops: cache first, then fallback (global field)."""

    def _provider(path: Path) -> str | None:
        cached = password_cache_get(path)
        if cached:
            return cached
        return fallback

    return _provider


def job_log_path() -> Path:
    """Local job log (user data dir when installed — never uploaded)."""
    from sekikit.prefs import user_data_dir

    return user_data_dir() / "sekikit_jobs.log"


def _basename_only(paths: list[str]) -> list[str]:
    """Privacy: log file names only, not full paths."""
    out: list[str] = []
    for raw in paths:
        try:
            out.append(Path(raw).name or raw)
        except Exception:  # noqa: BLE001
            out.append(str(raw))
    return out


def log_job(
    op: str,
    *,
    inputs: list[str],
    outputs: list[str],
    ok: bool,
    duration_s: float,
    error: str | None = None,
    warnings: list[str] | None = None,
) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": __version__,
        "op": op,
        "ok": ok,
        "duration_s": round(duration_s, 3),
        # Basenames only (privacy).
        "inputs": _basename_only(inputs),
        "outputs": _basename_only(outputs),
        "warnings": warnings or [],
        "error": error,
    }
    line = json.dumps(entry, ensure_ascii=False)
    path = job_log_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def run_job(
    op: str,
    fn: Callable[..., Any],
    *args: Any,
    inputs: list[Path | str] | None = None,
    validate_password: str | None = None,
    **kwargs: Any,
) -> JobResult:
    """Run a pdf_ops function, collect warnings, validate timing, log result.

    validate_password: optional password for re-opening outputs (e.g. encrypt).
    """
    pdf_ops.take_warnings()
    t0 = time.perf_counter()
    in_list = [str(p) for p in (inputs or [])]
    try:
        raw = fn(*args, **kwargs)
        duration = time.perf_counter() - t0
        warns = pdf_ops.take_warnings()
        paths: list[Path]
        value: Any = None
        if raw is None:
            paths = []
        elif isinstance(raw, Path):
            paths = [raw]
            value = raw
        elif isinstance(raw, (list, tuple)):
            if raw and all(isinstance(x, (Path, str)) for x in raw):
                paths = [Path(p) for p in raw]
                value = paths
            else:
                paths = []
                value = raw
        else:
            # Non-path result — do not Path(str(...)).
            paths = []
            value = raw

        pages = None
        if paths and paths[0].is_file() and paths[0].suffix.lower() == ".pdf":
            try:
                pages = pdf_ops.page_count(
                    paths[0], password=validate_password
                )
            except Exception:  # noqa: BLE001
                pages = None

        log_job(
            op,
            inputs=in_list,
            outputs=[str(p) for p in paths],
            ok=True,
            duration_s=duration,
            warnings=warns,
        )
        return JobResult(
            op=op,
            paths=paths,
            ok=True,
            duration_s=duration,
            warnings=warns,
            pages=pages,
            value=value,
        )
    except Exception as exc:  # noqa: BLE001
        duration = time.perf_counter() - t0
        warns = pdf_ops.take_warnings()
        err = str(exc)
        log_job(
            op,
            inputs=in_list,
            outputs=[],
            ok=False,
            duration_s=duration,
            error=err,
            warnings=warns,
        )
        raise
