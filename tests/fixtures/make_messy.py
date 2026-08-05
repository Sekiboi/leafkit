"""Build synthetic “messy” PDFs for reliability tests (no binary fixtures needed)."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject


def blank(path: Path, pages: int = 3, w: float = 200, h: float = 300) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=w, height=h)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        writer.write(f)
    return path


def rotated_pages(path: Path) -> Path:
    """Pages with mixed rotation flags."""
    w = PdfWriter()
    w.add_blank_page(width=200, height=300)
    w.add_blank_page(width=300, height=200)
    w.pages[1].rotate(90)
    with open(path, "wb") as f:
        w.write(f)
    return path


def tight_cropbox(path: Path) -> Path:
    w = PdfWriter()
    w.add_blank_page(width=400, height=600)
    page = w.pages[0]
    page.cropbox.lower_left = (0, 300)
    page.cropbox.upper_right = (400, 600)
    with open(path, "wb") as f:
        w.write(f)
    return path


def encrypted(path: Path, password: str = "secret", pages: int = 2) -> Path:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=200)
    w.encrypt(password)
    with open(path, "wb") as f:
        w.write(f)
    return path


def mixed_page_sizes(path: Path) -> Path:
    w = PdfWriter()
    w.add_blank_page(width=200, height=300)
    w.add_blank_page(width=612, height=792)  # letter
    w.add_blank_page(width=100, height=100)
    with open(path, "wb") as f:
        w.write(f)
    return path


def with_metadata(path: Path) -> Path:
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.add_metadata({"/Author": "Fixture Author", "/Title": "Fixture Title"})
    with open(path, "wb") as f:
        w.write(f)
    return path


def many_pages(path: Path, n: int = 25) -> Path:
    return blank(path, pages=n)
