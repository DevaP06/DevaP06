"""Shared colour tokens for generated SVGs. Every graphic switches between
these via an embedded `@media (prefers-color-scheme: dark)` block, since each
SVG is loaded through an <img> tag and rendered by the browser directly --
GitHub's markdown sanitiser never touches it, so real CSS media queries work.
"""

LIGHT_INK = "#1f2328"      # primary text, light theme
DARK_INK = "#c9d1d9"       # primary text, dark theme
LIGHT_MUTED = "#57606a"    # secondary text / headings, light theme
DARK_MUTED = "#8b949e"     # secondary text / headings, dark theme
LIGHT_RULE = "#d0d7de"     # hairlines / gridlines, light theme
DARK_RULE = "#30363d"      # hairlines / gridlines, dark theme
LIGHT_ACCENT = "#0969da"   # bars / sparkline, light theme
DARK_ACCENT = "#58a6ff"    # bars / sparkline, dark theme
