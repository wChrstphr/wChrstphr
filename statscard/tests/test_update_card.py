import json
from datetime import date
from unittest.mock import patch

from statscard.loc import LocStats
from statscard.stats import ProfileStats
from statscard.update_card import build_card_data, load_art_cells, main


def test_load_art_cells_reads_cells_list(tmp_path):
    art_path = tmp_path / "art_data.json"
    art_path.write_text(
        json.dumps({"cols": 2, "rows": 1, "cells": [{"row": 0, "col": 0, "char": "█", "color": "#000000"}]}),
        encoding="utf-8",
    )

    cells = load_art_cells(art_path)

    assert cells == [{"row": 0, "col": 0, "char": "█", "color": "#000000"}]


@patch("statscard.update_card.compute_loc_stats")
@patch("statscard.update_card.fetch_profile_stats")
def test_build_card_data_combines_stats_and_uptime(mock_fetch_profile, mock_compute_loc):
    mock_fetch_profile.return_value = ProfileStats(
        repos=5, stars=10, followers=3, commits=99, repo_names=["a", "b"], created_year=2023
    )
    mock_compute_loc.return_value = LocStats(additions=100, deletions=20)

    fields, stats = build_card_data("fake-token", date(2026, 9, 1))

    assert fields["uptime"] == "1 ano, 7 meses"
    assert fields["os"] == "Linux / Windows 11 / Android"
    assert stats == {
        "repos": 5,
        "stars": 10,
        "commits": 99,
        "followers": 3,
        "additions": 100,
        "deletions": 20,
    }
    mock_fetch_profile.assert_called_once_with("wChrstphr", "fake-token", 2026)
    mock_compute_loc.assert_called_once()


@patch("statscard.update_card.compute_loc_stats")
@patch("statscard.update_card.fetch_profile_stats")
def test_main_writes_both_svg_files(mock_fetch_profile, mock_compute_loc, tmp_path, monkeypatch):
    mock_fetch_profile.return_value = ProfileStats(
        repos=1, stars=1, followers=1, commits=1, repo_names=[], created_year=2025
    )
    mock_compute_loc.return_value = LocStats(additions=1, deletions=1)
    monkeypatch.setenv("ACCESS_TOKEN", "fake-token")

    art_path = tmp_path / "art_data.json"
    art_path.write_text(json.dumps({"cols": 1, "rows": 1, "cells": []}), encoding="utf-8")
    dark_out = tmp_path / "dark_mode.svg"
    light_out = tmp_path / "light_mode.svg"

    with patch(
        "sys.argv",
        [
            "update_card.py",
            "--art",
            str(art_path),
            "--dark-out",
            str(dark_out),
            "--light-out",
            str(light_out),
        ],
    ):
        main()

    assert "<svg" in dark_out.read_text(encoding="utf-8")
    assert "<svg" in light_out.read_text(encoding="utf-8")
