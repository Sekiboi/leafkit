"""Regenerate assets/leafkit.png and assets/leafkit.ico.

Glyph: stack of pages + leaf tip (Leafkit). Same blue/white as the original bird mark.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
# Same palette as the original bird mark
PLATE = (47, 111, 168, 255)
WHITE = (255, 255, 255, 255)


def draw_icon(size: int, with_plate: bool = True) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = float(size)

    if with_plate:
        pad = max(1, int(s * 0.06))
        d.rounded_rectangle(
            [pad, pad, size - pad - 1, size - pad - 1],
            radius=max(2, int(s * 0.22)),
            fill=PLATE,
        )

    m = 0.18 if with_plate else 0.10

    def P(u: float, v: float) -> tuple[float, float]:
        return (m * s + u * (1 - 2 * m) * s, m * s + v * (1 - 2 * m) * s)

    ink = WHITE if with_plate else PLATE
    # Detail lines only on the blue plate (carve into white)
    cut = PLATE if with_plate else None
    stroke = max(1, int(round(s * 0.028)))

    def page_poly(
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fold: float = 0.0,
    ) -> list[tuple[float, float]]:
        if fold <= 0:
            return [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)]
        return [
            P(x0, y0),
            P(x1 - fold, y0),
            P(x1, y0 + fold),
            P(x1, y1),
            P(x0, y1),
        ]

    # Stack: back → middle → front (offsets read as depth)
    for poly in (
        page_poly(0.06, 0.30, 0.76, 0.94),
        page_poly(0.14, 0.22, 0.84, 0.86),
        page_poly(0.22, 0.14, 0.92, 0.78, fold=0.11),
    ):
        d.polygon(poly, fill=ink)

    if cut is not None:
        d.line([P(0.14, 0.30), P(0.76, 0.30)], fill=cut, width=stroke)
        d.line([P(0.22, 0.22), P(0.84, 0.22)], fill=cut, width=stroke)
        for t in (0.36, 0.46, 0.56, 0.66):
            d.line(
                [P(0.32, t), P(0.80, t)],
                fill=cut,
                width=max(1, stroke - 1),
            )
        d.line([P(0.81, 0.14), P(0.92, 0.25)], fill=cut, width=stroke)

    # Leaf tip from the top of the stack
    leaf = [
        P(0.50, 0.00),
        P(0.64, 0.06),
        P(0.72, 0.16),
        P(0.62, 0.20),
        P(0.54, 0.16),
        P(0.46, 0.18),
        P(0.38, 0.14),
        P(0.40, 0.06),
    ]
    d.polygon(leaf, fill=ink)

    if cut is not None:
        d.line(
            [P(0.50, 0.02), P(0.54, 0.16)],
            fill=cut,
            width=max(1, int(s * 0.02)),
        )

    return img


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    draw_icon(512, True).save(ASSETS / "leafkit.png")
    draw_icon(512, False).save(ASSETS / "leafkit_mark.png")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    draw_icon(256, True).save(ASSETS / "leafkit.ico", format="ICO", sizes=sizes)
    print(f"Wrote {ASSETS / 'leafkit.png'}")
    print(f"Wrote {ASSETS / 'leafkit_mark.png'}")
    print(f"Wrote {ASSETS / 'leafkit.ico'}")


if __name__ == "__main__":
    main()
