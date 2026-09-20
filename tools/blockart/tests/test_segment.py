import numpy as np

from tools.blockart.segment import segment_foreground


def test_segment_foreground_isolates_bright_square():
    # 60x60 dark background with a 30x30 bright square centered in it.
    image = np.full((60, 60, 3), 10, dtype=np.uint8)
    image[15:45, 15:45] = 240
    rect = (10, 10, 40, 40)  # (x, y, w, h), loosely around the square

    mask = segment_foreground(image, rect)

    assert mask.shape == (60, 60)
    assert set(np.unique(mask)).issubset({0, 1})
    inside_ratio = mask[15:45, 15:45].mean()
    outside_ratio = mask[:10, :10].mean()
    assert inside_ratio > 0.7
    assert outside_ratio < 0.3
