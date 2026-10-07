"""Render the GitHub activity card (assets/activity.svg) in the profile's dark and gold style.

Usage:
    GITHUB_TOKEN=... python render_activity.py --user hummatovic --out assets/activity.svg
    python render_activity.py --input sample.json --out activity.svg   # offline, for previews
"""

import argparse
import datetime as dt
import json
import os
import urllib.request
from xml.sax.saxutils import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

SERIF = "Georgia, 'Times New Roman', 'Liberation Serif', serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
GOLD, IVORY, MUTED = "#C9A24A", "#F2EEE6", "#8A8478"
LEVELS = {
    "NONE": "#1A1812",
    "FIRST_QUARTILE": "#4A3B17",
    "SECOND_QUARTILE": "#7A6124",
    "THIRD_QUARTILE": "#B08D3A",
    "FOURTH_QUARTILE": "#E3C26A",
}

W, H = 1200, 400
PAD = 64
CELL, STEP = 16, 20


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def longest_streak(days):
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    return longest


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def render(cal, today):
    weeks = cal["weeks"][-53:]
    days = [d for w in weeks for d in w["contributionDays"]]
    total = cal["totalContributions"]
    active = sum(1 for d in days if d["contributionCount"])
    longest = longest_streak(days)
    best = max((d["contributionCount"] for d in days), default=0)

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="GitHub activity: {plural(total, "contribution")} in the last year">',
        f"""<defs>
<radialGradient id="glow" cx="0.85" cy="0" r="0.6"><stop offset="0" stop-color="{GOLD}" stop-opacity="0.12"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
<linearGradient id="rule" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/><stop offset="0.5" stop-color="{GOLD}" stop-opacity="0.8"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>
<clipPath id="c"><rect width="{W}" height="{H}" rx="14"/></clipPath>
</defs>""",
        '<g clip-path="url(#c)">',
        f'<rect width="{W}" height="{H}" fill="#0A0A0A"/>',
        f'<rect width="{W}" height="{H}" fill="url(#glow)"/>',
        f'<rect x="0" y="{H - 1.5}" width="{W}" height="1.5" fill="url(#rule)"/>',
        "</g>",
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="13.5" fill="none" stroke="{GOLD}" stroke-opacity="0.35"/>',
        f'<text x="{PAD}" y="62" font-family="{MONO}" font-size="13" letter-spacing="3" fill="{GOLD}">GITHUB ACTIVITY</text>',
        f'<text x="{W - PAD}" y="62" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{MUTED}">'
        f'LAST 12 MONTHS · UPDATED {today:%d %b %Y}</text>'.replace(f"{today:%b}", f"{today:%b}".upper()),
    ]

    stats = [
        (f"{total:,}", "CONTRIBUTIONS"),
        (f"{active:,}", "ACTIVE DAYS"),
        (f"{longest:,}", "LONGEST STREAK (DAYS)"),
        (f"{best:,}", "MOST IN A DAY"),
    ]
    col = (W - 2 * PAD) / len(stats)
    for i, (value, label) in enumerate(stats):
        x = PAD + i * col
        if i:
            s.append(f'<rect x="{x - 24:.0f}" y="96" width="1" height="62" fill="{GOLD}" fill-opacity="0.25"/>')
        s.append(f'<text x="{x:.0f}" y="134" font-family="{SERIF}" font-size="40" fill="{IVORY}">{value}</text>')
        s.append(f'<text x="{x:.0f}" y="158" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{MUTED}">{escape(label)}</text>')

    grid_top = 212
    left = PAD
    last_month = None
    for wi, week in enumerate(weeks):
        x = left + wi * STEP
        first = dt.date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month and wi < len(weeks) - 2:
            if last_month is not None or first.day <= 7:
                s.append(f'<text x="{x:.0f}" y="{grid_top - 12}" font-family="{MONO}" font-size="11" fill="{MUTED}">{first:%b}</text>')
            last_month = first.month
        for d in week["contributionDays"]:
            day = dt.date.fromisoformat(d["date"])
            y = grid_top + ((day.weekday() + 1) % 7) * STEP
            fill = LEVELS.get(d["contributionLevel"], LEVELS["NONE"])
            tip = escape(f'{plural(d["contributionCount"], "contribution")} on {day:%d %b %Y}')
            s.append(f'<rect x="{x:.0f}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{fill}"><title>{tip}</title></rect>')

    legend_y = grid_top + 7 * STEP + 18
    lx = W - PAD - (len(LEVELS) * STEP) - 36
    s.append(f'<text x="{lx - 10}" y="{legend_y + 12}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">Less</text>')
    for i, color in enumerate(LEVELS.values()):
        s.append(f'<rect x="{lx + i * STEP}" y="{legend_y}" width="{CELL - 2}" height="{CELL - 2}" rx="3" fill="{color}"/>')
    s.append(f'<text x="{lx + len(LEVELS) * STEP + 4}" y="{legend_y + 12}" font-family="{MONO}" font-size="11" fill="{MUTED}">More</text>')

    s.append("</svg>")
    return "\n".join(s) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="hummatovic")
    ap.add_argument("--out", default="assets/activity.svg")
    ap.add_argument("--input", help="read the contribution calendar from a JSON file instead of the API")
    args = ap.parse_args()

    if args.input:
        with open(args.input) as f:
            cal = json.load(f)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is not set")
        cal = fetch(args.user, token)

    with open(args.out, "w") as f:
        f.write(render(cal, dt.datetime.now(dt.timezone.utc).date()))


if __name__ == "__main__":
    main()
