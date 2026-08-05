"""Regenerate assets/leafkit.png and assets/leafkit.ico (minimal freedom bird)."""

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

    m = 0.20 if with_plate else 0.10

    def P(u: float, v: float) -> tuple[float, float]:
        return (m * s + u * (1 - 2 * m) * s, m * s + v * (1 - 2 * m) * s)

    ink = WHITE if with_plate else PLATE

    bird = [
        P(0.08, 0.50),
        P(0.22, 0.44),
        P(0.30, 0.40),
        P(0.38, 0.36),
        P(0.42, 0.18),
        P(0.52, 0.08),
        P(0.58, 0.28),
        P(0.62, 0.38),
        P(0.82, 0.32),
        P(0.96, 0.40),
        P(0.78, 0.48),
        P(0.96, 0.58),
        P(0.78, 0.56),
        P(0.58, 0.58),
        P(0.44, 0.68),
        P(0.38, 0.56),
        P(0.26, 0.52),
        P(0.18, 0.54),
    ]
    d.polygon(bird, fill=ink)
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
