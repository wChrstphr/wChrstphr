import numpy as np

from tools.blockart.gridify import average_color, coverage_to_char, rgb_to_hex


def test_coverage_to_char_thresholds():
    assert coverage_to_char(0.95) == "█"
    assert coverage_to_char(0.85) == "█"
    assert coverage_to_char(0.70) == "▓"
    assert coverage_to_char(0.60) == "▓"
    assert coverage_to_char(0.40) == "▒"
    assert coverage_to_char(0.35) == "▒"
    assert coverage_to_char(0.20) == "░"
    assert coverage_to_char(0.12) == "░"
    assert coverage_to_char(0.05) is None
    assert coverage_to_char(0.0) is None


def test_rgb_to_hex_basic():
    assert rgb_to_hex((255, 0, 0)) == "#ff0000"
    assert rgb_to_hex((0, 0, 0)) == "#000000"
    assert rgb_to_hex((0, 255, 128)) == "#00ff80"


def test_rgb_to_hex_clamps_and_rounds():
    assert rgb_to_hex((300, -10, 127.6)) == "#ff0080"


def test_average_color_empty_returns_black():
    assert average_color(np.empty((0, 3))) == (0.0, 0.0, 0.0)


def test_average_color_computes_mean_per_channel():
    pixels = np.array([[10, 20, 30], [30, 40, 50]])
    assert average_color(pixels) == (20.0, 30.0, 40.0)


from tools.blockart.gridify import ArtCell, build_art_cells


def test_build_art_cells_single_foreground_cell():
    # 4x4 image, 2x2 grid -> each cell is 2x2 px.
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    image[0:2, 0:2] = (255, 0, 0)  # top-left cell: solid red
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[0:2, 0:2] = 1  # only top-left cell is foreground

    cells = build_art_cells(image, mask, cols=2, rows=2)

    assert cells == [ArtCell(row=0, col=0, char="█", color="#ff0000")]


def test_build_art_cells_skips_low_coverage_cells():
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[0, 0] = 1  # 1 of 4 px in the cell -> coverage 0.25 -> "░"

    cells = build_art_cells(image, mask, cols=2, rows=2)

    assert len(cells) == 1
    assert cells[0].char == "░"
