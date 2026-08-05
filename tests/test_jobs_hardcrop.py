"""Jobs log, password cache, hard crop, EXIF images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from leafkit import jobs
from leafkit import pdf_ops
from tests.fixtures import make_messy


def test_password_cache(tmp_path: Path) -> None:
    jobs.password_cache_clear()
    src = make_messy.encrypted(tmp_path / "e.pdf", "secret", 2)
    jobs.password_cache_set(src, "secret")
    assert jobs.password_cache_get(src) == "secret"
    # Basename alone must NOT unlock a different path
    other = tmp_path / "other" / "e.pdf"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_bytes(src.read_bytes())
    assert jobs.password_cache_get(other) is None
    n = pdf_ops.page_count(
        src, password_provider=jobs.make_password_provider(None)
    )
    assert n == 2


def test_run_job_logs(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "jobs.log"
    monkeypatch.setattr(jobs, "job_log_path", lambda: log)
    a = make_messy.blank(tmp_path / "a.pdf", 1)
    b = make_messy.blank(tmp_path / "b.pdf", 1)
    jr = jobs.run_job(
        "merge",
        lambda: pdf_ops.merge_pdfs([a, b], tmp_path / "m.pdf"),
        inputs=[a, b],
    )
    assert jr.ok
    assert jr.paths
    assert log.is_file()
    text = log.read_text(encoding="utf-8")
    assert "merge" in text
    assert "a.pdf" in text
    assert str(tmp_path).replace("\\", "\\\\") not in text or "a.pdf" in text
    import json

    entry = json.loads(text.strip().splitlines()[-1])
    assert entry["inputs"] == ["a.pdf", "b.pdf"]
    assert all("/" not in p and "\\" not in p for p in entry["inputs"])


def test_op_then_renumber(tmp_path: Path) -> None:
    a = make_messy.blank(tmp_path / "a.pdf", 2)

    def produce(path: Path) -> Path:
        return pdf_ops.extract_pages(a, "1-2", path)

    out = pdf_ops.op_then_renumber(
        produce,
        tmp_path / "out.pdf",
        do_renumber=True,
        renumber_kwargs={"format_str": "{n}"},
    )
    assert out.is_file()
    assert pdf_ops.page_count(out) == 2


def test_run_job_validate_password_counts_encrypted(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "jobs.log"
    monkeypatch.setattr(jobs, "job_log_path", lambda: log)
    src = make_messy.blank(tmp_path / "a.pdf", 2)
    enc = tmp_path / "e.pdf"
    jr = jobs.run_job(
        "encrypt",
        lambda: pdf_ops.encrypt_pdf(src, enc, "secret"),
        inputs=[src],
        validate_password="secret",
    )
    assert jr.ok
    assert jr.pages == 2


def test_org_session_prune_logic() -> None:
    """Prune keeps only live tray sources and respects max open handles."""
    from leafkit.ui_organize import OrganizeTabMixin

    class Fake(OrganizeTabMixin):
        def __init__(self) -> None:
            self._org_items = []
            self._org_sessions = {}
            self._org_session_order = []

        def _password(self):
            return None

    closed: list[str] = []

    class Sess:
        def __init__(self, k: str):
            self.k = k

        def close(self):
            closed.append(self.k)

    f = Fake()
    f._ORG_SESSION_MAX = 2
    p1, p2, p3 = Path("a.pdf"), Path("b.pdf"), Path("c.pdf")
    f._org_items = [(p1, 0), (p2, 0)]
    f._org_sessions = {
        f._org_session_key(p1): Sess("a"),
        f._org_session_key(p2): Sess("b"),
        f._org_session_key(p3): Sess("c"),
    }
    f._org_session_order = [
        f._org_session_key(p1),
        f._org_session_key(p2),
        f._org_session_key(p3),
    ]
    f._org_prune_sessions()
    assert f._org_session_key(p3) not in f._org_sessions
    assert "c" in closed


def test_run_job_preserves_non_path_value(tmp_path: Path, monkeypatch) -> None:
    """Organize returns ThumbnailSession — must not be coerced to Path(str(...))."""
    log = tmp_path / "jobs.log"
    monkeypatch.setattr(jobs, "job_log_path", lambda: log)

    class _FakeSession:
        page_count = 3

    jr = jobs.run_job("open_org", lambda: _FakeSession())
    assert jr.ok
    assert jr.paths == []
    assert isinstance(jr.value, _FakeSession)
    assert jr.value.page_count == 3


def test_hard_crop(tmp_path: Path) -> None:
    src = make_messy.blank(tmp_path / "s.pdf", 1, w=400, h=600)
    out = pdf_ops.crop_margins(src, tmp_path / "h.pdf", margin_pts=36, hard=True)
    assert pdf_ops.page_count(out) == 1
    out2 = pdf_ops.crop_margins(src, tmp_path / "s2.pdf", margin_pts=36, hard=False)
    assert pdf_ops.page_count(out2) == 1


def test_images_exif_stream(tmp_path: Path) -> None:
    img = tmp_path / "i.jpg"
    Image.new("RGB", (60, 40), (10, 20, 30)).save(img, quality=90)
    out = pdf_ops.images_to_pdf([img], tmp_path / "from.jpg.pdf")
    assert pdf_ops.page_count(out) == 1
