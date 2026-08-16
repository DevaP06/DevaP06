# Fonts

Every SVG in [`assets/`](../assets) embeds its own font as a base64 `@font-face`
data URI — a linked font URL can't work here, since these SVGs load through
an `<img>` tag and browsers refuse subresource fetches for image documents.
Each SVG is subset down to only the glyphs it actually uses, so the total
embedded-font weight across the whole profile page stays under ~60KB instead
of ~4.5MB for a full copy of the typeface per file.

**Typeface:** [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono),
SIL Open Font License 1.1 (see [`OFL.txt`](OFL.txt), [`AUTHORS.txt`](AUTHORS.txt)).
Chosen because it's OFL (safe to redistribute in a public repo — commercial
fonts are not an option here) and its advance width is exactly 0.600em at
1000 units/em, which is what the ASCII portrait's character grid assumes.

## What's committed

Only the finished subsets, in [`subset/`](subset):

| File | Covers | Used by |
| --- | --- | --- |
| `ramp.woff2` | the 13 ASCII-ramp glyphs (`` .`:-=+*cs#%@`` ) | `assets/portrait.svg`, `assets/year.svg` |
| `headings.woff2` | only the letters used in section-heading labels | `assets/h-*.svg` |
| `basic-latin-regular.woff2` / `basic-latin-semibold.woff2` | printable ASCII, two weights | `assets/stats.svg`, `assets/streak.svg`, `assets/langs.svg` |

## Regenerating

The full JetBrains Mono release (~10MB unzipped) is **not** committed — see
`.gitignore` — since none of it is needed at runtime. To rebuild a subset
locally:

```bash
pip install fonttools brotli
curl -sL -o fonts/JetBrainsMono.zip \
  https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip
unzip -q fonts/JetBrainsMono.zip -d fonts/jbm
python scripts/generate_portrait.py    # rebuilds ramp.woff2 usage + portrait.svg
python scripts/generate_headings.py    # rebuilds headings.woff2 + assets/h-*.svg
```

`basic-latin-*.woff2` were built once with:

```bash
pyftsubset fonts/jbm/fonts/ttf/JetBrainsMono-Regular.ttf  --unicodes=U+0020-007E --flavor=woff2 --layout-features= --no-hinting --output-file=fonts/subset/basic-latin-regular.woff2
pyftsubset fonts/jbm/fonts/ttf/JetBrainsMono-SemiBold.ttf --unicodes=U+0020-007E --flavor=woff2 --layout-features= --no-hinting --output-file=fonts/subset/basic-latin-semibold.woff2
```
