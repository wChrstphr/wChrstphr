import json

from tools.blockart.export import export_art_data
from tools.blockart.gridify import ArtCell


def test_export_art_data_writes_expected_json(tmp_path):
    cells = [
        ArtCell(row=0, col=0, char="█", color="#ff0000"),
        ArtCell(row=0, col=1, char="▒", color="#00ff00"),
    ]
    out_path = tmp_path / "art_data.json"

    export_art_data(cells, cols=2, rows=1, path=out_path)

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data == {
        "cols": 2,
        "rows": 1,
        "cells": [
            {"row": 0, "col": 0, "char": "█", "color": "#ff0000"},
            {"row": 0, "col": 1, "char": "▒", "color": "#00ff00"},
        ],
    }
