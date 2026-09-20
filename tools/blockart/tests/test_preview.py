from PIL import Image

from tools.blockart.gridify import ArtCell
from tools.blockart.preview import render_preview


def test_render_preview_writes_png_with_expected_size_and_pixel(tmp_path):
    cells = [ArtCell(row=1, col=2, char="█", color="#ff0000")]
    out_path = tmp_path / "preview.png"

    render_preview(cells, cols=4, rows=3, path=out_path, cell_px=10)

    image = Image.open(out_path)
    assert image.size == (40, 30)
    # Center of cell (row=1, col=2) is at x=25, y=15.
    assert image.convert("RGB").getpixel((25, 15)) == (255, 0, 0)
    # An empty cell, e.g. (0, 0), stays background-black.
    assert image.convert("RGB").getpixel((5, 5)) == (0, 0, 0)
