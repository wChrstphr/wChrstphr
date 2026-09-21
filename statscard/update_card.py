from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from statscard.card import render_svg
from statscard.loc import compute_loc_stats
from statscard.stats import fetch_profile_stats
from statscard.uptime import format_uptime

LOGIN = "wChrstphr"
UPTIME_START = date(2025, 2, 1)

FIELDS_STATIC = {
    "os": "Linux / Windows 11 / Android",
    "host": "Presidência da República — DSIC",
    "kernel": "Engenharia de Software @ UnB",
    "ide": "VS Code + Claude Code",
    "hobbies": "Leitura, Viagens, Natação",
    "contact": "linkedin.com/in/christopherparaizo · github.com/wChrstphr",
}


def load_art_cells(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["cells"]


def build_card_data(token: str, today: date) -> tuple[dict, dict]:
    profile = fetch_profile_stats(LOGIN, token, today.year)
    loc = compute_loc_stats(LOGIN, profile.repo_names, token, Path("cache/loc_cache.json"))
    fields = dict(FIELDS_STATIC)
    fields["uptime"] = format_uptime(UPTIME_START, today)
    stats = {
        "repos": profile.repos,
        "stars": profile.stars,
        "commits": profile.commits,
        "followers": profile.followers,
        "additions": loc.additions,
        "deletions": loc.deletions,
    }
    return fields, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate dark_mode.svg / light_mode.svg")
    parser.add_argument("--art", type=Path, default=Path("assets/art_data.json"))
    parser.add_argument("--dark-out", type=Path, default=Path("dark_mode.svg"))
    parser.add_argument("--light-out", type=Path, default=Path("light_mode.svg"))
    args = parser.parse_args()

    token = os.environ["ACCESS_TOKEN"]
    art_cells = load_art_cells(args.art)
    fields, stats = build_card_data(token, date.today())

    args.dark_out.write_text(render_svg("dark", art_cells, fields, stats), encoding="utf-8")
    args.light_out.write_text(render_svg("light", art_cells, fields, stats), encoding="utf-8")


if __name__ == "__main__":
    main()
