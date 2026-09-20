from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from tools.blockart.gridify import ArtCell


def render_preview(
    cells: list[ArtCell],
    cols: int,
    rows: int,
    path: Path,
    cell_w_px: int = 5,
    cell_h_px: int = 10,
) -> None:
    """Render the art grid as a flat-color PNG mosaic for visual QA.

    Cells default to a 1:2 width:height ratio to match a typical monospace
    character cell, so the preview looks like the eventual text rendering.
    """
    image = Image.new("RGB", (cols * cell_w_px, rows * cell_h_px), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    for cell in cells:
        x0 = cell.col * cell_w_px
        y0 = cell.row * cell_h_px
        draw.rectangle(
            [x0, y0, x0 + cell_w_px - 1, y0 + cell_h_px - 1], fill=cell.color
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
