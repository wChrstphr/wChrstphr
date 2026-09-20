import json

import cv2
import numpy as np

from tools.blockart.generate import default_rect, generate


def test_default_rect_applies_five_percent_margin():
    assert default_rect(100, 200) == (5, 10, 90, 180)


def test_generate_writes_art_data_and_preview(tmp_path):
    photo_path = tmp_path / "photo.png"
    image = np.full((60, 60, 3), 10, dtype=np.uint8)
    image[15:45, 15:45] = 240
    cv2.imwrite(str(photo_path), image)

    out_path = tmp_path / "art_data.json"
    preview_path = tmp_path / "preview.png"

    generate(photo_path, out_path, preview_path, cols=6, rows=6)

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["cols"] == 6
    assert data["rows"] == 6
    assert len(data["cells"]) > 0
    assert preview_path.exists()


def test_generate_raises_on_missing_photo(tmp_path):
    missing = tmp_path / "missing.png"
    try:
        generate(missing, tmp_path / "out.json", None, cols=6, rows=6)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass
