from PIL import Image

from tools.blockart.gridify import ArtCell
from tools.blockart.preview import render_preview


def test_render_preview_writes_png_with_expected_size_and_pixel(tmp_path):
    cells = [ArtCell(row=1, col=2, char="█", color="#ff0000")]
    out_path = tmp_path / "preview.png"

    render_preview(cells, cols=4, rows=3, path=out_path, cell_w_px=5, cell_h_px=10)

    image = Image.open(out_path)
    assert image.size == (20, 30)
    # Cell (row=1, col=2) spans x=[10, 14], y=[10, 19]; center is x=12, y=15.
    assert image.convert("RGB").getpixel((12, 15)) == (255, 0, 0)
    # An empty cell, e.g. (0, 0) which spans x=[0, 4], y=[0, 9], stays
    # background-black.
    assert image.convert("RGB").getpixel((2, 5)) == (0, 0, 0)
