"""Draw this profile's own stats/streak/langs/year SVGs from the GitHub
GraphQL API. Standard library only -- nothing to break in CI.

Two determinism rules that matter (see the workflow that calls this):
  1. The contribution window is pinned to whole UTC days, not "now minus a
     year" -- otherwise two runs minutes apart bucket days into different
     weeks and the sparkline shifts every night for no real reason.
  2. Repositories are filtered to `privacy: PUBLIC` -- the workflow's
     GITHUB_TOKEN can't see private repos, and a personal token run locally
     would disagree with it if this weren't forced explicitly.

Usage:
  GITHUB_TOKEN=... GH_LOGIN=... python scripts/generate_stats.py
  python scripts/generate_stats.py --offline scripts/fixtures/demo_data.json   (no network, for local testing)
"""
import base64
import datetime
import json
import os
import sys
import urllib.request
from pathlib import Path

import theme

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONT_REGULAR = ROOT / "fonts" / "subset" / "basic-latin-regular.woff2"
FONT_SEMIBOLD = ROOT / "fonts" / "subset" / "basic-latin-semibold.woff2"
FONT_RAMP = ROOT / "fonts" / "subset" / "ramp.woff2"

RAMP = " .`:-=+*cs#%@"  # same 13-level ramp the portrait uses
API_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        name
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


# ---------------------------------------------------------------- fetching --

def utc_date_window():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    to = datetime.datetime.combine(today, datetime.time(23, 59, 59), tzinfo=datetime.timezone.utc)
    frm = datetime.datetime.combine(
        today - datetime.timedelta(days=364), datetime.time(0, 0, 0), tzinfo=datetime.timezone.utc
    )
    return frm.strftime("%Y-%m-%dT%H:%M:%SZ"), to.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_live(login, token):
    frm, to = utc_date_window()
    body = json.dumps({"query": QUERY, "variables": {"login": login, "from": frm, "to": to}}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-profile-stats",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]["user"]


# --------------------------------------------------------------- analysis --

def flatten_days(data):
    days = []
    for week in data["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in week["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort(key=lambda x: x[0])
    return days


def weekly_totals(data):
    return [
        sum(d["contributionCount"] for d in week["contributionDays"])
        for week in data["contributionsCollection"]["contributionCalendar"]["weeks"]
    ]


def compute_streaks(days):
    # current streak: walk backward from the most recent day; if that day has
    # no contributions yet (it may still be in progress), start from the day
    # before it instead so an in-progress day doesn't read as a broken streak.
    i = len(days) - 1
    if i >= 0 and days[i][1] == 0:
        i -= 1
    current_end = days[i][0] if i >= 0 else None
    current = 0
    while i >= 0 and days[i][1] > 0:
        current += 1
        i -= 1
    current_start = days[i + 1][0] if current else None

    longest = 0
    longest_start = longest_end = None
    run = 0
    run_start = None
    for date, count in days:
        if count > 0:
            if run == 0:
                run_start = date
            run += 1
            if run > longest:
                longest = run
                longest_start, longest_end = run_start, date
        else:
            run = 0
    return {
        "current": current,
        "current_start": current_start,
        "current_end": current_end,
        "longest": longest,
        "longest_start": longest_start,
        "longest_end": longest_end,
    }


def compute_languages(data):
    by_bytes = {}
    by_repo_count = {}
    for repo in data["repositories"]["nodes"]:
        edges = repo["languages"]["edges"]
        for edge in edges:
            name = edge["node"]["name"]
            color = edge["node"]["color"] or "#8b949e"
            entry = by_bytes.setdefault(name, {"bytes": 0, "color": color})
            entry["bytes"] += edge["size"]
        if edges:
            top = edges[0]["node"]["name"]
            by_repo_count[top] = by_repo_count.get(top, 0) + 1
    total_bytes = sum(v["bytes"] for v in by_bytes.values()) or 1
    ranked = sorted(by_bytes.items(), key=lambda kv: kv[1]["bytes"], reverse=True)[:6]
    return [
        {"name": name, "pct": v["bytes"] / total_bytes, "color": v["color"], "repos": by_repo_count.get(name, 0)}
        for name, v in ranked
    ]


# ------------------------------------------------------------------- SVG --

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def font_face(name, path, weight):
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"@font-face{{font-family:'{name}';src:url(data:font/woff2;base64,{b64}) format('woff2');font-weight:{weight};font-style:normal;}}"


def base_style():
    return (
        font_face("DataMono", FONT_REGULAR, 400)
        + font_face("DataMonoSB", FONT_SEMIBOLD, 600)
        + f"text{{font-family:'DataMono',monospace;fill:{theme.LIGHT_INK};}}"
        + f".muted{{fill:{theme.LIGHT_MUTED};}}"
        + f".sb{{font-family:'DataMonoSB',monospace;fill:{theme.LIGHT_INK};}}"
        + f".rule{{stroke:{theme.LIGHT_RULE};}}"
        + f".accent{{fill:{theme.LIGHT_ACCENT};stroke:{theme.LIGHT_ACCENT};}}"
        + "@media (prefers-color-scheme: dark){"
        + f"text{{fill:{theme.DARK_INK};}}"
        + f".muted{{fill:{theme.DARK_MUTED};}}"
        + f".sb{{fill:{theme.DARK_INK};}}"
        + f".rule{{stroke:{theme.DARK_RULE};}}"
        + f".accent{{fill:{theme.DARK_ACCENT};stroke:{theme.DARK_ACCENT};}}"
        + "}"
    )


def svg_open(w, h, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{esc(label)}">'
        f"<defs><style>{base_style()}</style></defs>"
    )


def draw_stats(total, weekly):
    W, H = 460, 140
    out = [svg_open(W, H, f"{total} contributions in the last year")]
    out.append(f'<text x="0" y="34" font-size="30" class="sb">{total:,}</text>')
    out.append('<text x="0" y="54" font-size="12" class="muted">contributions, past 12 months</text>')

    # weekly sparkline, columns not a line-through-zero -- weeks are an
    # aggregate, so a line is defensible here (daily counts are not, see year.svg)
    n = len(weekly) or 1
    peak = max(weekly) or 1
    plot_w, plot_h, plot_y = W, 60, 70
    step = plot_w / n
    bar_w = max(step * 0.6, 1)
    for i, v in enumerate(weekly):
        bh = (v / peak) * plot_h
        x = i * step
        y = plot_y + plot_h - bh
        out.append(f'<rect class="accent" x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{max(bh,1):.2f}" opacity="0.85"/>')
    out.append(f'<line class="rule" x1="0" y1="{plot_y+plot_h:.1f}" x2="{W}" y2="{plot_y+plot_h:.1f}"/>')
    out.append(f'<text x="0" y="{plot_y+plot_h+14}" font-size="10" class="muted">52 weeks ago</text>')
    out.append(f'<text x="{W}" y="{plot_y+plot_h+14}" font-size="10" class="muted" text-anchor="end">today</text>')
    out.append("</svg>")
    return "\n".join(out)


def draw_streak(s):
    W, H = 460, 100
    out = [svg_open(W, H, f"current streak {s['current']} days, longest {s['longest']} days")]
    half = W / 2

    out.append(f'<text x="0" y="30" font-size="26" class="sb">{s["current"]}</text>')
    out.append('<text x="0" y="48" font-size="12" class="muted">day current streak</text>')
    if s["current"]:
        out.append(f'<text x="0" y="66" font-size="10" class="muted">{s["current_start"]} → {s["current_end"]}</text>')

    out.append(f'<line class="rule" x1="{half:.1f}" y1="4" x2="{half:.1f}" y2="{H-4}"/>')

    out.append(f'<text x="{half+24:.1f}" y="30" font-size="26" class="sb">{s["longest"]}</text>')
    out.append(f'<text x="{half+24:.1f}" y="48" font-size="12" class="muted">day longest streak</text>')
    if s["longest"]:
        out.append(f'<text x="{half+24:.1f}" y="66" font-size="10" class="muted">{s["longest_start"]} → {s["longest_end"]}</text>')
    out.append("</svg>")
    return "\n".join(out)


def draw_langs(langs):
    W = 460
    row_h = 30
    H = 16 + row_h * max(len(langs), 1)
    out = [svg_open(W, H, "top languages by bytes")]
    bar_x = 130
    bar_max_w = W - bar_x - 46
    for i, lang in enumerate(langs):
        y = 16 + i * row_h
        out.append(f'<text x="0" y="{y+14}" font-size="12">{esc(lang["name"])}</text>')
        bw = max(bar_max_w * lang["pct"], 2)
        out.append(f'<rect x="{bar_x}" y="{y+2}" width="{bar_max_w}" height="10" class="rule" fill="none"/>')
        out.append(f'<rect x="{bar_x}" y="{y+2}" width="{bw:.2f}" height="10" fill="{lang["color"]}"/>')
        pct_label = f'{lang["pct"]*100:.1f}%'
        out.append(f'<text x="{W}" y="{y+14}" font-size="11" class="muted" text-anchor="end">{pct_label} · {lang["repos"]} repo{"s" if lang["repos"] != 1 else ""}</text>')
    out.append("</svg>")
    return "\n".join(out)


def draw_year(days):
    # one ramp character per day, laid out the same way GitHub's own grid
    # does: 7 rows (Sun..Sat) x N week-columns.
    if not days:
        days = []
    first_date = datetime.date.fromisoformat(days[0][0]) if days else datetime.date.today()
    pad = (first_date.weekday() + 1) % 7  # week starts Sunday
    counts = [None] * pad + [c for _, c in days]
    while len(counts) % 7:
        counts.append(None)
    weeks = len(counts) // 7

    nonzero = [c for c in counts if c]
    peak = max(nonzero) if nonzero else 1
    n = len(RAMP) - 1

    def glyph(c):
        if not c:
            return RAMP[0]
        level = 1 + round((c / peak) * (n - 1))
        return RAMP[min(level, n)]

    grid = [[None] * weeks for _ in range(7)]
    for idx, c in enumerate(counts):
        grid[idx % 7][idx // 7] = glyph(c)

    char_w = 8.0
    row_h = char_w / 0.48
    W = weeks * char_w
    H = 7 * row_h
    font_b64 = base64.b64encode(FONT_RAMP.read_bytes()).decode("ascii")
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {H:.1f}" '
        f'width="{W:.0f}" height="{H:.0f}" role="img" aria-label="contribution grid, {len(days)} days">',
        "<defs><style>",
        "@font-face{font-family:'RampMono';src:url(data:font/woff2;base64,"
        f"{font_b64}) format('woff2');font-weight:400;font-style:normal;}}",
        f"text{{font-family:'RampMono',monospace;font-size:{char_w/0.6:.2f}px;"
        f"fill:{theme.LIGHT_INK};white-space:pre;}}"
        f"@media (prefers-color-scheme: dark){{text{{fill:{theme.DARK_INK};}}}}",
        "</style></defs>",
    ]
    for r in range(7):
        row = "".join(g or RAMP[0] for g in grid[r])
        y = (r + 1) * row_h - (row_h - char_w / 0.6) / 2
        out.append(f'<text x="0" y="{y:.2f}" xml:space="preserve">{esc(row)}</text>')
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------------ main --

def main():
    if "--offline" in sys.argv:
        fixture = Path(sys.argv[sys.argv.index("--offline") + 1])
        data = json.loads(fixture.read_text())
    else:
        token = os.environ["GITHUB_TOKEN"]
        login = os.environ["GH_LOGIN"]
        data = fetch_live(login, token)

    days = flatten_days(data)
    total = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    weekly = weekly_totals(data)
    streaks = compute_streaks(days)
    langs = compute_languages(data)

    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "stats.svg").write_text(draw_stats(total, weekly), encoding="utf-8")
    (ASSETS / "streak.svg").write_text(draw_streak(streaks), encoding="utf-8")
    (ASSETS / "langs.svg").write_text(draw_langs(langs), encoding="utf-8")
    (ASSETS / "year.svg").write_text(draw_year(days), encoding="utf-8")
    print(f"total={total} current_streak={streaks['current']} longest_streak={streaks['longest']} langs={[l['name'] for l in langs]}")


if __name__ == "__main__":
    main()
