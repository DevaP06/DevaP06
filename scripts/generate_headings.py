"""Generate section-heading SVGs: lowercase mono label + hairline rule to the
right edge. This is the only way to put a real typeface on a heading, since
GitHub's markdown sanitiser strips <style>/font tags from inline HTML. The
image's alt text carries the word for screen readers and search; GitHub's
README outline won't pick up these headings since they carry no anchor link.

Usage: python scripts/generate_headings.py
"""
import base64
import subprocess
from pathlib import Path

import theme

ROOT = Path(__file__).resolve().parent.parent
FONT_TTF = ROOT / "fonts" / "jbm" / "fonts" / "ttf" / "JetBrainsMono-Medium.ttf"
SUBSET_OUT = ROOT / "fonts" / "subset" / "headings.woff2"
ASSETS = ROOT / "assets"

HEADINGS = [
    ("about", "about"),
    ("skills", "skills & technologies"),
    ("connect", "connect"),
    ("stats", "github stats"),
    ("contrib", "contribution graph"),
]

FONT_SIZE = 15
CHAR_W = FONT_SIZE * 0.6
HEIGHT = 28
WIDTH = 680


def subset_font():
    chars = sorted(set("".join(label for _, label in HEADINGS)))
    text = "".join(chars)
    txt_file = ROOT / "fonts" / "subset" / "_headings_chars.txt"
    txt_file.write_text(text, encoding="utf-8")
    subprocess.run(
        [
            "pyftsubset",
            str(FONT_TTF),
            f"--text-file={txt_file}",
            "--flavor=woff2",
            "--layout-features=",
            "--no-hinting",
            f"--output-file={SUBSET_OUT}",
        ],
        check=True,
    )
    txt_file.unlink()


def build_svg(label):
    font_b64 = base64.b64encode(SUBSET_OUT.read_bytes()).decode("ascii")
    text_w = len(label) * CHAR_W
    rule_x = text_w + 14
    y = HEIGHT / 2 + FONT_SIZE * 0.32
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-label="{label}">
<defs><style>
@font-face{{font-family:'HeadMono';src:url(data:font/woff2;base64,{font_b64}) format('woff2');font-weight:500;font-style:normal;}}
text{{font-family:'HeadMono',monospace;font-size:{FONT_SIZE}px;fill:{theme.LIGHT_MUTED};letter-spacing:0.06em;}}
line{{stroke:{theme.LIGHT_RULE};stroke-width:1;}}
@media (prefers-color-scheme: dark){{
text{{fill:{theme.DARK_MUTED};}}
line{{stroke:{theme.DARK_RULE};}}
}}
</style></defs>
<text x="0" y="{y:.2f}">{label}</text>
<line x1="{rule_x:.2f}" y1="{HEIGHT / 2:.2f}" x2="{WIDTH}" y2="{HEIGHT / 2:.2f}"/>
</svg>'''


def main():
    subset_font()
    ASSETS.mkdir(parents=True, exist_ok=True)
    for key, label in HEADINGS:
        out = ASSETS / f"h-{key}.svg"
        out.write_text(build_svg(label), encoding="utf-8")
        print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
