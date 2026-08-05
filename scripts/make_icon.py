"""Regenerate assets/sekikit.png and assets/sekikit.ico.

Minimal glyph: one abstract leaf that also reads as a folded page.
Same blue/white palette as before.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
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

    m = 0.20 if with_plate else 0.12

    def P(u: float, v: float) -> tuple[float, float]:
        return (m * s + u * (1 - 2 * m) * s, m * s + v * (1 - 2 * m) * s)

    ink = WHITE if with_plate else PLATE
    cut = PLATE if with_plate else None

    # Single shape: leaf / folded page
    # Pointed tip at top (leaf), straight-ish base and corner fold (page).
    glyph = [
        P(0.50, 0.06),  # tip
        P(0.78, 0.28),  # right shoulder
        P(0.88, 0.52),  # right mid (leaf bulge / page edge)
        P(0.78, 0.78),  # lower right
        P(0.50, 0.94),  # base point (stem / page bottom)
        P(0.22, 0.78),  # lower left
        P(0.12, 0.52),  # left mid
        P(0.22, 0.28),  # left shoulder
    ]
    d.polygon(glyph, fill=ink)

    # One crease: leaf vein + page fold (same line)
    if cut is not None:
        stroke = max(1, int(round(s * 0.035)))
        d.line(
            [P(0.50, 0.12), P(0.50, 0.86)],
            fill=cut,
            width=stroke,
        )
        # Small fold tick at upper-right (page dog-ear hint)
        d.line(
            [P(0.50, 0.28), P(0.72, 0.40)],
            fill=cut,
            width=max(1, stroke - 1),
        )
    else:
        # Bare mark: thin center cut via overdraw with transparent-ish gap —
        # use a slightly narrower second color isn't available; skip detail.
        pass

    return img


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    draw_icon(512, True).save(ASSETS / "sekikit.png")
    draw_icon(512, False).save(ASSETS / "sekikit_mark.png")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    draw_icon(256, True).save(ASSETS / "sekikit.ico", format="ICO", sizes=sizes)
    print(f"Wrote {ASSETS / 'sekikit.png'}")
    print(f"Wrote {ASSETS / 'sekikit_mark.png'}")
    print(f"Wrote {ASSETS / 'sekikit.ico'}")


if __name__ == "__main__":
    main()
