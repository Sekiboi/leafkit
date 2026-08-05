"""Page rendering for thumbnails / preview (PyMuPDF). Offline only."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from sekikit.pdf_ops import PdfOpsError, _ensure_pdf


class RenderError(PdfOpsError):
    """Thumbnail/preview failure."""


def has_renderer() -> bool:
    try:
        import fitz  # noqa: F401

        return True
    except ImportError:
        return False


def render_page(
    path: Path | str,
    page_index: int,
    *,
    max_width: int = 120,
    password: str | None = None,
) -> Image.Image:
    """Render one 0-based page to a PIL RGB image (for thumbnails/preview)."""
    path = _ensure_pdf(Path(path))
    try:
        import fitz
    except ImportError as exc:
        raise RenderError(
            "Thumbnails need PyMuPDF. Install: pip install pymupdf"
        ) from exc

    doc = fitz.open(str(path))
    try:
        if doc.is_encrypted:
            ok = doc.authenticate(password or "")
            if not ok:
                raise RenderError(f"{path.name} is password-protected.")
        if page_index < 0 or page_index >= doc.page_count:
            raise RenderError(f"Page {page_index + 1} out of range.")
        page = doc.load_page(page_index)
        rect = page.rect
        if rect.width < 1 or rect.height < 1:
            raise RenderError(f"Page {page_index + 1} has invalid size.")
        scale = max_width / float(rect.width)
        scale = min(scale, 3.0)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return img
    except RenderError:
        raise
    except Exception as exp:  # noqa: BLE001
        raise RenderError(f"Could not render page {page_index + 1}: {exp}") from exp
    finally:
        doc.close()


class ThumbnailSession:
    """Keep one PDF open and render thumbnails on demand (large docs).

    Avoids loading every page into memory at once. Call close() when done.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        password: str | None = None,
        max_width: int = 96,
    ) -> None:
        path = _ensure_pdf(Path(path))
        try:
            import fitz
        except ImportError as exc:
            raise RenderError("PyMuPDF not installed") from exc

        self.path = path
        self.max_width = max_width
        self._fitz = fitz
        self._doc = fitz.open(str(path))
        if self._doc.is_encrypted:
            if not self._doc.authenticate(password or ""):
                self._doc.close()
                raise RenderError(f"{path.name} is password-protected.")
        self.page_count = self._doc.page_count
        self._cache: dict[int, Image.Image] = {}

    def get(self, page_index: int) -> Image.Image:
        if page_index in self._cache:
            return self._cache[page_index]
        if page_index < 0 or page_index >= self.page_count:
            raise RenderError(f"Page {page_index + 1} out of range.")
        page = self._doc.load_page(page_index)
        rect = page.rect
        scale = self.max_width / max(float(rect.width), 1.0)
        scale = min(scale, 3.0)
        pix = page.get_pixmap(matrix=self._fitz.Matrix(scale, scale), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        # Cap thumb cache (~120 pages).
        if len(self._cache) > 120:
            for k in list(self._cache.keys())[:60]:
                del self._cache[k]
        self._cache[page_index] = img
        return img

    def close(self) -> None:
        try:
            self._doc.close()
        except Exception:  # noqa: BLE001
            pass
        self._cache.clear()

    def __enter__(self) -> ThumbnailSession:
        return self

    def __exit__(self, *args) -> None:  # noqa: ANN002
        self.close()


def render_thumbnails(
    path: Path | str,
    *,
    max_width: int = 100,
    password: str | None = None,
    max_pages: int | None = None,
    start: int = 0,
    count: int | None = None,
) -> list[Image.Image]:
    """Render a range of thumbnails (prefer start/count for lazy UI)."""
    with ThumbnailSession(path, password=password, max_width=max_width) as session:
        n = session.page_count
        if max_pages is not None:
            end = min(n, start + max_pages)
        elif count is not None:
            end = min(n, start + count)
        else:
            end = n
        start = max(0, min(start, n))
        return [session.get(i) for i in range(start, end)]
