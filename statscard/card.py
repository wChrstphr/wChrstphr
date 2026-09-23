from __future__ import annotations

CARD_WIDTH = 620
CARD_HEIGHT = 310

TEXT_LEFT = 24
LINE_H = 20

_THEMES = {
    "dark": {
        "bg": "#161b22",
        "border": "#30363d",
        "label": "#ff9868",
        "value": "#a9fef7",
        "title": "#38bdae",
        "dim": "#57606a",
        "add": "#a6e22e",
        "del": "#f92672",
    },
    "light": {
        "bg": "#fffefe",
        "border": "#d0d7de",
        "label": "#b45309",
        "value": "#24292f",
        "title": "#0969da",
        "dim": "#6e7781",
        "add": "#1a7f37",
        "del": "#cf222e",
    },
}

_FIELD_ORDER = [
    "os",
    "host",
    "kernel",
    "ide",
    "lang_programming",
    "lang_computer",
    "lang_real",
    "uptime",
    "hobbies",
    "contact",
]
_FIELD_LABELS = {
    "os": "OS",
    "host": "Host",
    "kernel": "Kernel",
    "ide": "IDE",
    "lang_programming": "languages.programming",
    "lang_computer": "languages.computer",
    "lang_real": "languages.real",
    "uptime": "uptime.software",
    "hobbies": "Hobbies",
    "contact": "Contato",
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(theme: str, fields: dict, stats: dict) -> str:
    colors = _THEMES[theme]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
        f'viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" '
        f'font-family="Consolas, Monaco, monospace" font-size="13">',
        f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="10" '
        f'fill="{colors["bg"]}" stroke="{colors["border"]}"/>',
    ]

    y = 30
    parts.append(
        f'<text x="{TEXT_LEFT}" y="{y}" fill="{colors["title"]}" font-weight="bold">'
        f"christopher@github</text>"
    )
    y += LINE_H
    parts.append(
        f'<line x1="{TEXT_LEFT}" y1="{y - 14}" x2="{CARD_WIDTH - TEXT_LEFT}" y2="{y - 14}" '
        f'stroke="{colors["dim"]}"/>'
    )

    for key in _FIELD_ORDER:
        label = _FIELD_LABELS[key]
        value = _escape(str(fields[key]))
        parts.append(
            f'<text x="{TEXT_LEFT}" y="{y}">'
            f'<tspan fill="{colors["label"]}">{label}: </tspan>'
            f'<tspan fill="{colors["value"]}">{value}</tspan></text>'
        )
        y += LINE_H

    y += 8
    parts.append(
        f'<line x1="{TEXT_LEFT}" y1="{y - 14}" x2="{CARD_WIDTH - TEXT_LEFT}" y2="{y - 14}" '
        f'stroke="{colors["dim"]}"/>'
    )
    stats_line = (
        f'Repos: {stats["repos"]} | Stars: {stats["stars"]} | '
        f'Commits: {stats["commits"]} | Followers: {stats["followers"]}'
    )
    parts.append(f'<text x="{TEXT_LEFT}" y="{y}" fill="{colors["value"]}">{_escape(stats_line)}</text>')
    y += LINE_H
    parts.append(
        f'<text x="{TEXT_LEFT}" y="{y}">'
        f'<tspan fill="{colors["add"]}">+{stats["additions"]}</tspan>'
        f'<tspan fill="{colors["value"]}"> / </tspan>'
        f'<tspan fill="{colors["del"]}">-{stats["deletions"]}</tspan>'
        f'<tspan fill="{colors["dim"]}"> lines of code</tspan></text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)
