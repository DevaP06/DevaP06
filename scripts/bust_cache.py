"""Stamp a fresh ?v=<token> on each generated-stat image's src in README.md.

GitHub caches the *rendered profile page*, not just the image bytes it
points to. A workflow run that only changes the SVGs never touches
README.md, so the page never re-renders and visitors keep seeing the old
graphics indefinitely (this is the same caching the article's own gotcha
note warns about for a newly-created README). Changing each src's query
string forces both a README.md diff -- which invalidates the page cache --
and a new URL -- which invalidates the asset cache.

Usage: python scripts/bust_cache.py <token>
"""
import re
import sys
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"
PATTERN = re.compile(r'(assets/(?:stats|streak|langs|year)\.svg)(\?v=[0-9a-f]+)?(?=")')


def main():
    token = sys.argv[1][:8]
    text = README.read_text(encoding="utf-8")
    new_text, n = PATTERN.subn(rf"\1?v={token}", text)
    README.write_text(new_text, encoding="utf-8")
    print(f"stamped ?v={token} on {n} image src(s)")


if __name__ == "__main__":
    main()
