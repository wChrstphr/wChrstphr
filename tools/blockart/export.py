from __future__ import annotations

import json
from pathlib import Path

from tools.blockart.gridify import ArtCell


def export_art_data(cells: list[ArtCell], cols: int, rows: int, path: Path) -> None:
    """Write the art grid as JSON: {cols, rows, cells: [{row, col, char, color}]}."""
    data = {
        "cols": cols,
        "rows": rows,
        "cells": [
            {"row": cell.row, "col": cell.col, "char": cell.char, "color": cell.color}
            for cell in cells
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
