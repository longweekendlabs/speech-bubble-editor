"""
create_icon.py — Generate the Speech Bubble Editor app icon using Pillow.

Run once before building:
    python create_icon.py

Outputs:
    icons/icon.png   (256 × 256, used by Linux desktop entry)
    icons/icon.ico   (multi-size ICO for Windows exe)
"""

import os
from PIL import Image, ImageDraw

# Brand colour — indigo
BG_COLOUR   = (79,  70, 229)   # #4F46E5
TAIL_COLOUR = (255, 255, 255)

SIZES = [16, 32, 48, 64, 128, 256]


def _draw_bubble(draw: ImageDraw.ImageDraw, size: int):
    """Draw a white speech bubble centred on a (size × size) canvas."""
    cx, cy   = size * 0.50, size * 0.44   # bubble centre
    rx, ry   = size * 0.33, size * 0.22   # ellipse radii

    # ── bubble body (ellipse) ────────────────────────────────────────────────
    draw.ellipse(
        [cx - rx, cy - ry, cx + rx, cy + ry],
        fill=TAIL_COLOUR,
    )

    # ── tail (triangle pointing down-left) ───────────────────────────────────
    tx = cx - rx * 0.25          # tail base left
    ty = cy + ry                 # tail base y (bottom of ellipse)
    tip_x = cx - rx * 0.65      # tip x
    tip_y = cy + ry + size * 0.17  # tip y (below ellipse)
    tr_x  = cx + rx * 0.05      # tail base right
    tr_y  = ty

    # Cover the join between ellipse and tail with the same colour first
    draw.polygon(
        [(tx, ty), (tip_x, tip_y), (tr_x, tr_y)],
        fill=TAIL_COLOUR,
    )


def make_icon(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded-rectangle background
    pad = max(1, int(size * 0.06))
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=max(2, int(size * 0.22)),
        fill=BG_COLOUR,
    )

    _draw_bubble(draw, size)
    return img


def main():
    here      = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(here, "icons")
    os.makedirs(icons_dir, exist_ok=True)

    images = {}
    for s in SIZES:
        images[s] = make_icon(s)
        images[s].save(os.path.join(icons_dir, f"icon_{s}.png"))

    # Main PNG (256 px)
    images[256].save(os.path.join(icons_dir, "icon.png"))

    # Multi-size ICO for Windows
    images[256].save(
        os.path.join(icons_dir, "icon.ico"),
        format="ICO",
        sizes=[(s, s) for s in SIZES],
    )

    print(f"Icons written to: {icons_dir}")
    for name in ("icon.png", "icon.ico"):
        print(f"  {name}")


if __name__ == "__main__":
    main()
