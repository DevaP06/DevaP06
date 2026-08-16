"""Generate an animated ASCII-typing portrait SVG from a source photo.

Pipeline: rembg cutout (-> white) -> bilateral filter -> CLAHE -> darkening
curve -> ramp mapping -> animated SVG. Only the 13 ramp glyphs are needed at
render time, so the embedded font subset stays under ~2KB.

Usage: python scripts/generate_portrait.py
"""
import base64
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove

import theme

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "profile.png"
FONT_SUBSET = ROOT / "fonts" / "subset" / "ramp.woff2"
OUT_SVG = ROOT / "assets" / "portrait.svg"

# Manually chosen: chin to just above the hair, tight frame, slight angle,
# side light already present in the source photo. See "the photo decides
# everything" -- no amount of parameter tuning rescues a bad crop.
CROP_BOX = (170, 30, 1010, 1140)

RAMP = " .`:-=+*cs#%@"           # light -> dark, 13 levels
COLS = 90
CHAR_W = 7.74                     # 0.600em advance at FONT_SIZE (JetBrains Mono metric)
FONT_SIZE = 12.9
ROW_H = CHAR_W / 0.48             # matches the rows formula's implied cell aspect
STAGGER = 0.09                    # seconds between each row's typing start
WIPE_DUR = 0.5                    # seconds for a single row's wipe-in


def load_source():
    return Image.open(SOURCE).convert("RGB").crop(CROP_BOX)


def cutout_on_white(im):
    """rembg cutout, composited onto pure white so background clears to the ramp's blank end."""
    rgba = remove(im)
    bg = Image.new("RGB", rgba.size, (255, 255, 255))
    bg.paste(rgba, mask=rgba.split()[3])
    return bg


def process(im):
    gray = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
    smooth = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(smooth)
    curved = (255.0 * (contrasted.astype(np.float64) / 255.0) ** 1.7).astype(np.uint8)
    return curved


def to_ascii(gray_arr, cols):
    h, w = gray_arr.shape
    rows = max(1, round(cols * (h / w) * 0.48))
    small = cv2.resize(gray_arr, (cols, rows), interpolation=cv2.INTER_AREA)
    n = len(RAMP) - 1
    idx = np.clip(np.round((255 - small.astype(np.float64)) / 255 * n), 0, n).astype(int)
    return ["".join(RAMP[i] for i in row) for row in idx]


def esc(c):
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(c, c)


def build_svg(lines):
    cols = max(len(l) for l in lines)
    rows = len(lines)
    vb_w = cols * CHAR_W
    vb_h = rows * ROW_H
    font_b64 = base64.b64encode(FONT_SUBSET.read_bytes()).decode("ascii")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb_w:.2f} {vb_h:.2f}" '
        f'width="{vb_w:.0f}" height="{vb_h:.0f}" role="img" aria-label="ASCII portrait">',
        "<defs><style>",
        "@font-face{font-family:'RampMono';src:url(data:font/woff2;base64,"
        f"{font_b64}) format('woff2');font-weight:400;font-style:normal;}}",
        f"text{{font-family:'RampMono',monospace;font-size:{FONT_SIZE}px;"
        f"fill:{theme.LIGHT_INK};white-space:pre;}}",
        f".cursor{{fill:{theme.LIGHT_INK};}}",
        f"@media (prefers-color-scheme: dark){{text{{fill:{theme.DARK_INK};}}"
        f".cursor{{fill:{theme.DARK_INK};}}}}",
        "</style></defs>",
    ]

    for i, line in enumerate(lines):
        y = (i + 1) * ROW_H - (ROW_H - FONT_SIZE) / 2
        clip_id = f"wipe{i}"
        begin = i * STAGGER
        row_w = len(line) * CHAR_W

        parts.append(f'<clipPath id="{clip_id}">')
        parts.append(f'<rect x="0" y="{i * ROW_H:.2f}" width="0" height="{ROW_H:.2f}">')
        parts.append(
            f'<animate attributeName="width" from="0" to="{row_w:.2f}" '
            f'begin="{begin:.2f}s" dur="{WIPE_DUR}s" fill="freeze"/>'
        )
        parts.append("</rect></clipPath>")

        parts.append(f'<g clip-path="url(#{clip_id})">')
        safe = "".join(esc(c) for c in line)
        parts.append(f'<text x="0" y="{y:.2f}" xml:space="preserve">{safe}</text>')
        parts.append("</g>")

        # cursor block riding the wipe edge, then fading out once the row is done
        parts.append(
            f'<rect class="cursor" x="0" y="{i * ROW_H + 1:.2f}" width="{CHAR_W:.2f}" '
            f'height="{ROW_H - 2:.2f}" opacity="0.85">'
        )
        parts.append(
            f'<animate attributeName="x" from="0" to="{max(row_w - CHAR_W, 0):.2f}" '
            f'begin="{begin:.2f}s" dur="{WIPE_DUR}s" fill="freeze"/>'
        )
        parts.append(
            f'<set attributeName="opacity" to="0" begin="{begin + WIPE_DUR:.2f}s" fill="freeze"/>'
        )
        parts.append("</rect>")

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    im = load_source()
    im = cutout_on_white(im)
    gray = process(im)
    lines = to_ascii(gray, COLS)
    svg = build_svg(lines)
    OUT_SVG.parent.mkdir(parents=True, exist_ok=True)
    OUT_SVG.write_text(svg, encoding="utf-8")
    total_dur = (len(lines) - 1) * STAGGER + WIPE_DUR
    print(f"wrote {OUT_SVG} ({len(lines)} rows x {COLS} cols, ~{total_dur:.1f}s to finish typing)")
    print(f"svg size: {OUT_SVG.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
