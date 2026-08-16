# Scripts

Everything that draws this profile page. No third-party image services —
every graphic below is generated inside this repo and committed as a plain
SVG. Font details are in [`../fonts/README.md`](../fonts/README.md).

| Script | Run when | Produces |
| --- | --- | --- |
| `generate_portrait.py` | manually, whenever `profile.png` changes | `assets/portrait.svg` — the animated ASCII portrait |
| `generate_headings.py` | manually, whenever a heading label changes | `assets/h-*.svg` — section headings |
| `generate_stats.py` | nightly, by [`refresh-stats.yml`](../.github/workflows/refresh-stats.yml) | `assets/stats.svg`, `streak.svg`, `langs.svg`, `year.svg` |

## One-time setup

```bash
pip install -r scripts/requirements-dev.txt
python scripts/generate_portrait.py
python scripts/generate_headings.py
```

The first run of `generate_portrait.py` downloads rembg's ~176MB background-
removal model to `~/.u2net/` — once, then cached.

## Testing the stats generator without a token

`generate_stats.py` is the one script that runs in CI, so it's worth being
able to exercise it locally without hitting the live API:

```bash
python scripts/generate_stats.py --offline scripts/fixtures/demo_data.json
```

`demo_data.json` is a synthetic fixture shaped like the real GraphQL
response (same nesting, a deliberate gap and a trailing streak in the
contribution days) — useful for checking the streak/language math and the
SVG layout after any edit, before letting the real workflow run against
live data.

## Re-cropping the portrait

`generate_portrait.py` crops `profile.png` with a hardcoded `CROP_BOX`
rather than auto-cropping, because framing is a judgment call the pipeline
can't make well (see the source guide's "the photo decides everything").
If you swap in a new photo, open it, find chin-to-just-above-hair
coordinates, and update `CROP_BOX` before re-running.
