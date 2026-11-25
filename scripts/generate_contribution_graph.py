#!/usr/bin/env python3
"""Generate a dark, 30-day GitHub contribution line chart as an SVG."""

from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError
import json
import math
import os
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "x2ankit"
TOKEN = os.environ["GH_TOKEN"]
END = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0)
START = (END - timedelta(days=29)).replace(hour=0, minute=0, second=0)
query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""
payload = {
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": START.isoformat(),
        "to": END.isoformat(),
    },
}
request = Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "contribution-graph-generator",
    },
)
with urlopen(request, timeout=30) as response:
    result = json.loads(response.read())

if result.get("errors"):
    raise RuntimeError(json.dumps(result["errors"]))

user = result["data"]["user"]
if user is None:
    raise RuntimeError(f"GitHub user {USERNAME} was not found")

days = {}
for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
    for day in week["contributionDays"]:
        days[day["date"]] = day["contributionCount"]

labels = [(START.date() + timedelta(days=i)).isoformat() for i in range(30)]
values = [days.get(day, 0) for day in labels]

W, H = 1100, 400
LEFT, RIGHT, TOP, BOTTOM = 80, 35, 70, 62
plot_w, plot_h = W - LEFT - RIGHT, H - TOP - BOTTOM
peak = max(values, default=0)
y_max = max(5, int(math.ceil(peak / 5.0) * 5))
y_ticks = list(range(0, y_max + 1, max(1, y_max // 5)))
x_step = plot_w / (len(values) - 1)

def x_pos(i):
    return LEFT + i * x_step

def y_pos(value):
    return TOP + plot_h - (value / y_max) * plot_h

coords = [(x_pos(i), y_pos(v)) for i, v in enumerate(values)]
path = f"M {coords[0][0]:.2f},{coords[0][1]:.2f}"
for i in range(1, len(coords)):
    x0, y0 = coords[i - 1]
    x1, y1 = coords[i]
    mid = (x0 + x1) / 2
    path += f" Q {mid:.2f},{y0:.2f} {x1:.2f},{y1:.2f}"

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
    '<title id="title">Ankit\'s GitHub Contribution Graph</title>',
    '<desc id="desc">Daily GitHub contributions over the last 30 days.</desc>',
    '<rect width="100%" height="100%" fill="#0D1117"/>',
    '<text x="550" y="34" text-anchor="middle" fill="#9CA3AF" font-family="Arial,sans-serif" font-size="19">Ankit\'s Contribution Graph</text>',
]
for tick in y_ticks:
    y = y_pos(tick)
    parts.append(f'<line x1="{LEFT}" y1="{y:.2f}" x2="{W-RIGHT}" y2="{y:.2f}" stroke="#30363D" stroke-dasharray="2 3"/>')
    parts.append(f'<text x="{LEFT-14}" y="{y+5:.2f}" text-anchor="end" fill="#8B949E" font-family="Arial,sans-serif" font-size="12">{tick}</text>')

for i, (day, (x, _)) in enumerate(zip(labels, coords)):
    parts.append(f'<line x1="{x:.2f}" y1="{TOP}" x2="{x:.2f}" y2="{H-BOTTOM}" stroke="#30363D" stroke-dasharray="2 3" opacity=".65"/>')
    parts.append(f'<text x="{x:.2f}" y="{H-BOTTOM+21}" text-anchor="middle" fill="#8B949E" font-family="Arial,sans-serif" font-size="11">{int(day[-2:])}</text>')

parts.append(f'<path d="{path}" fill="none" stroke="#2DAA4E" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')
for (x, y), value, day in zip(coords, values, labels):
    parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="#8B949E"><title>{escape(day)}: {value} contributions</title></circle>')

parts.extend([
    f'<text x="{W/2}" y="{H-13}" text-anchor="middle" fill="#8B949E" font-family="Arial,sans-serif" font-size="13">Days</text>',
    f'<text x="23" y="{H/2}" text-anchor="middle" transform="rotate(-90 23 {H/2})" fill="#8B949E" font-family="Arial,sans-serif" font-size="13">Contributions</text>',
    '</svg>',
])
output = Path("assets/contribution-graph.svg")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("\n".join(parts), encoding="utf-8")
print(f"Wrote {output}; total contributions: {sum(values)}")
