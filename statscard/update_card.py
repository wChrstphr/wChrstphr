from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from statscard.card import render_svg
from statscard.loc import compute_loc_stats
from statscard.stats import fetch_profile_stats
from statscard.uptime import format_uptime

LOGIN = "wChrstphr"
UPTIME_START = date(2025, 2, 1)

# Repos whose lines-of-code are skewed by large non-code data files rather
# than actual authored code (e.g. a bundled dataset), so they're excluded
# from the LOC stat to keep it meaningful.
LOC_EXCLUDED_REPOS = {"sentiment-analysis"}

FIELDS_STATIC = {
    "os": "Linux / Windows 11 / Android",
    "host": "Presidência da República, DSIC",
    "kernel": "Engenharia de Software @ UnB",
    "ide": "VS Code + Claude Code",
    "lang_programming": "Python, Java, C/C++, TypeScript, JavaScript, SQL",
    "lang_real": "Português, Inglês",
    "hobbies": "Leitura, Viagens, Natação",
    "contact": "linkedin.com/in/christopherparaizo · github.com/wChrstphr",
}


def build_card_data(token: str, today: date) -> tuple[dict, dict]:
    profile = fetch_profile_stats(LOGIN, token, today.year)
    loc_repo_names = [name for name in profile.repo_names if name not in LOC_EXCLUDED_REPOS]
    loc = compute_loc_stats(LOGIN, loc_repo_names, token, Path("cache/loc_cache.json"))
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
    parser.add_argument("--dark-out", type=Path, default=Path("dark_mode.svg"))
    parser.add_argument("--light-out", type=Path, default=Path("light_mode.svg"))
    args = parser.parse_args()

    token = os.environ["ACCESS_TOKEN"]
    fields, stats = build_card_data(token, date.today())

    args.dark_out.write_text(render_svg("dark", fields, stats), encoding="utf-8")
    args.light_out.write_text(render_svg("light", fields, stats), encoding="utf-8")


if __name__ == "__main__":
    main()
