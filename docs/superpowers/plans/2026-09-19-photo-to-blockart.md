# Photo-to-Blockart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, offline CLI tool that converts a reference photo into Unicode block-art data (character + color per grid cell), producing a committable JSON asset without ever committing the raw photo itself.

**Architecture:** A small `tools/blockart` Python package with pure, unit-testable functions for the color/character mapping (`gridify.py`), an OpenCV GrabCut wrapper for background removal (`segment.py`), JSON export (`export.py`), a PNG preview renderer for visual QA (`preview.py`), and a thin CLI (`generate.py`) that wires them together. The photo never enters the repo; only the derived `assets/art_data.json` and a `assets/art_preview.png` (for review) are committed.

**Tech Stack:** Python 3.11+, OpenCV (`opencv-python-headless`), NumPy, Pillow, pytest.

**Spec:** This plan implements the "arte do personagem" branch of the design agreed in the `resume` repo session on 2026-09-19 (grilling round): character art replaces the Andrew6rant-style ASCII art inside the stats card, rendered as colored Unicode block characters (▀▄█▓▒░ family), derived from the user's reference photo (round wire-frame glasses, dark wavy hair with a side part).

## Global Constraints

- The raw reference photo MUST NOT be committed to the repository at any point — only derived data (`assets/art_data.json`) and a rendered preview (`assets/art_preview.png`) are committed.
- Character set is restricted to exactly five symbols: `" "`, `"░"`, `"▒"`, `"▓"`, `"█"` (space means "no cell" and is never actually stored/emitted).
- Grid resolution is fixed at 60 columns × 40 rows.
- All pure logic (character mapping, color averaging, grid building, JSON export) must have unit tests that run without any real photo or network access.
- Python 3.11+, standard library `dataclasses` and `pathlib` conventions.

---

## Task 1: Project scaffolding + coverage-to-character mapping

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/blockart/__init__.py`
- Create: `tools/blockart/gridify.py`
- Create: `tools/blockart/tests/__init__.py`
- Create: `tools/blockart/tests/test_gridify.py`
- Create: `requirements-blockart.txt`
- Create: `pytest.ini`

**Interfaces:**
- Produces: `tools.blockart.gridify.coverage_to_char(coverage: float) -> str | None`

- [ ] **Step 1: Create package scaffolding and dependency/pytest config**

`tools/__init__.py` (empty file).

`tools/blockart/__init__.py` (empty file).

`tools/blockart/tests/__init__.py` (empty file).

`requirements-blockart.txt`:
```
opencv-python-headless==4.10.0.84
numpy==1.26.4
Pillow==10.4.0
pytest==8.3.2
```

`pytest.ini`:
```ini
[pytest]
testpaths = tools/blockart/tests
```

- [ ] **Step 2: Write the failing test for `coverage_to_char`**

`tools/blockart/tests/test_gridify.py`:
```python
from tools.blockart.gridify import coverage_to_char


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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pip install -r requirements-blockart.txt && pytest tools/blockart/tests/test_gridify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.blockart.gridify'`

- [ ] **Step 4: Implement `coverage_to_char`**

`tools/blockart/gridify.py`:
```python
from __future__ import annotations

_CHAR_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.85, "█"),
    (0.60, "▓"),
    (0.35, "▒"),
    (0.12, "░"),
)


def coverage_to_char(coverage: float) -> str | None:
    """Map a foreground coverage ratio in [0, 1] to a Unicode block character.

    Returns None when coverage is below the lowest threshold, meaning the
    cell should be omitted entirely (treated as background).
    """
    for threshold, char in _CHAR_THRESHOLDS:
        if coverage >= threshold:
            return char
    return None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tools/blockart/tests/test_gridify.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add tools/__init__.py tools/blockart/__init__.py tools/blockart/tests/__init__.py \
        tools/blockart/gridify.py tools/blockart/tests/test_gridify.py \
        requirements-blockart.txt pytest.ini
git commit -m "feat: add coverage-to-char block mapping"
```

---

## Task 2: Color helpers (`rgb_to_hex`, `average_color`)

**Files:**
- Modify: `tools/blockart/gridify.py`
- Modify: `tools/blockart/tests/test_gridify.py`

**Interfaces:**
- Consumes: nothing from Task 1 beyond the module they share.
- Produces: `tools.blockart.gridify.rgb_to_hex(rgb: tuple[float, float, float]) -> str`, `tools.blockart.gridify.average_color(pixels: "numpy.ndarray") -> tuple[float, float, float]`

- [ ] **Step 1: Write the failing tests**

Append to `tools/blockart/tests/test_gridify.py`:
```python
import numpy as np

from tools.blockart.gridify import average_color, rgb_to_hex


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tools/blockart/tests/test_gridify.py -v`
Expected: FAIL with `ImportError: cannot import name 'average_color'` (and `rgb_to_hex`)

- [ ] **Step 3: Implement the color helpers**

Add to `tools/blockart/gridify.py` (below the imports, above `_CHAR_THRESHOLDS`):
```python
import numpy as np
```

Append to the end of `tools/blockart/gridify.py`:
```python
def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    """Format an (r, g, b) tuple as a '#rrggbb' hex color, clamping to [0, 255]."""
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def average_color(pixels: np.ndarray) -> tuple[float, float, float]:
    """Average RGB across an (N, 3) array of pixels. Returns black for empty input."""
    if pixels.size == 0:
        return (0.0, 0.0, 0.0)
    mean = pixels.reshape(-1, 3).mean(axis=0)
    return (float(mean[0]), float(mean[1]), float(mean[2]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tools/blockart/tests/test_gridify.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/blockart/gridify.py tools/blockart/tests/test_gridify.py
git commit -m "feat: add rgb_to_hex and average_color helpers"
```

---

## Task 3: Grid builder (`build_art_cells`)

**Files:**
- Modify: `tools/blockart/gridify.py`
- Modify: `tools/blockart/tests/test_gridify.py`

**Interfaces:**
- Consumes: `coverage_to_char`, `rgb_to_hex`, `average_color` from Task 1/2 (same module, called directly, no import needed).
- Produces: `tools.blockart.gridify.ArtCell` (dataclass with `row: int, col: int, char: str, color: str`), `tools.blockart.gridify.build_art_cells(image_rgb: np.ndarray, mask: np.ndarray, cols: int, rows: int) -> list[ArtCell]`

- [ ] **Step 1: Write the failing test**

Append to `tools/blockart/tests/test_gridify.py`:
```python
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
    mask[0, 0] = 1  # 1 of 4 px in the cell -> coverage 0.25 -> "▒"

    cells = build_art_cells(image, mask, cols=2, rows=2)

    assert len(cells) == 1
    assert cells[0].char == "▒"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tools/blockart/tests/test_gridify.py -v`
Expected: FAIL with `ImportError: cannot import name 'ArtCell'`

- [ ] **Step 3: Implement `ArtCell` and `build_art_cells`**

Add near the top of `tools/blockart/gridify.py` (after the `import numpy as np` line):
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtCell:
    row: int
    col: int
    char: str
    color: str
```

Append to the end of `tools/blockart/gridify.py`:
```python
def build_art_cells(
    image_rgb: np.ndarray,
    mask: np.ndarray,
    cols: int,
    rows: int,
) -> list[ArtCell]:
    """Split image_rgb/mask into a cols x rows grid and emit one ArtCell per
    cell whose foreground coverage clears the lowest threshold.

    image_rgb: (H, W, 3) uint8 array.
    mask: (H, W) array, nonzero where the pixel is foreground.
    """
    height, width = mask.shape
    cell_h = height / rows
    cell_w = width / cols
    cells: list[ArtCell] = []
    for row in range(rows):
        y0 = int(row * cell_h)
        y1 = int((row + 1) * cell_h) if row < rows - 1 else height
        for col in range(cols):
            x0 = int(col * cell_w)
            x1 = int((col + 1) * cell_w) if col < cols - 1 else width
            cell_mask = mask[y0:y1, x0:x1]
            total = cell_mask.size
            if total == 0:
                continue
            fg_pixels_mask = cell_mask != 0
            coverage = float(fg_pixels_mask.sum()) / total
            char = coverage_to_char(coverage)
            if char is None:
                continue
            cell_image = image_rgb[y0:y1, x0:x1][fg_pixels_mask]
            color = rgb_to_hex(average_color(cell_image))
            cells.append(ArtCell(row=row, col=col, char=char, color=color))
    return cells
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tools/blockart/tests/test_gridify.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/blockart/gridify.py tools/blockart/tests/test_gridify.py
git commit -m "feat: add build_art_cells grid aggregation"
```

---

## Task 4: Background segmentation (`segment_foreground`)

**Files:**
- Create: `tools/blockart/segment.py`
- Create: `tools/blockart/tests/test_segment.py`

**Interfaces:**
- Produces: `tools.blockart.segment.segment_foreground(image_bgr: np.ndarray, rect: tuple[int, int, int, int], iterations: int = 5) -> np.ndarray`

- [ ] **Step 1: Write the failing test**

`tools/blockart/tests/test_segment.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tools/blockart/tests/test_segment.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.blockart.segment'`

- [ ] **Step 3: Implement `segment_foreground`**

`tools/blockart/segment.py`:
```python
from __future__ import annotations

import cv2
import numpy as np


def segment_foreground(
    image_bgr: np.ndarray,
    rect: tuple[int, int, int, int],
    iterations: int = 5,
) -> np.ndarray:
    """Run OpenCV GrabCut on image_bgr using rect (x, y, w, h) as the initial
    foreground bounding box. Returns a (H, W) uint8 mask: 1 = foreground.
    """
    mask = np.zeros(image_bgr.shape[:2], dtype=np.uint8)
    bgd_model = np.zeros((1, 65), dtype=np.float64)
    fgd_model = np.zeros((1, 65), dtype=np.float64)
    cv2.grabCut(image_bgr, mask, rect, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_RECT)
    return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tools/blockart/tests/test_segment.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/blockart/segment.py tools/blockart/tests/test_segment.py
git commit -m "feat: add GrabCut-based foreground segmentation"
```

### Revision (discovered during Task 8's real-photo run)

The rect-init implementation above passed its synthetic test but failed badly
on the actual reference photo: plain `GC_INIT_WITH_RECT` classified dark hair
as background whenever it was color-similar to a dark outdoor backdrop,
regardless of the rect's margin (tried 3%, 12%, 20%, and a tight pre-crop —
none fixed it). The fix is to seed GrabCut with `GC_INIT_WITH_MASK` instead:
an ellipse inscribed in `rect` marks a generous "probable foreground" region,
a smaller concentric ellipse marks "definite foreground" (strong prior that
overrides the color-similarity confusion), and the four image corners mark
"definite background". The public signature is unchanged (`rect` still
defines the outer bound); only the internal algorithm and the `iterations`
default (5 -> 8) change:

```python
from __future__ import annotations

import cv2
import numpy as np


def segment_foreground(
    image_bgr: np.ndarray,
    rect: tuple[int, int, int, int],
    iterations: int = 8,
) -> np.ndarray:
    """Segment the foreground within rect using mask-seeded GrabCut.

    rect (x, y, w, h) bounds a generous foreground candidate region. An
    ellipse inscribed in rect is marked "probable foreground", a smaller
    concentric ellipse (32% of rect's half-extents) is marked "definite
    foreground", and the four image corners are marked "definite
    background". Mask-based seeding (GC_INIT_WITH_MASK) is used instead of
    plain rect-init because rect-init alone misclassifies dark hair as
    background when it's color-similar to a dark outdoor backdrop; seeding
    strong foreground priors inside the head region fixes this.

    Returns a (H, W) uint8 mask: 1 = foreground.
    """
    height, width = image_bgr.shape[:2]
    x, y, w, h = rect
    mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)
    cx, cy = x + w // 2, y + h // 2
    cv2.ellipse(mask, (cx, cy), (w // 2, h // 2), 0, 0, 360, cv2.GC_PR_FGD, -1)
    cv2.ellipse(mask, (cx, cy), (int(w * 0.32), int(h * 0.32)), 0, 0, 360, cv2.GC_FGD, -1)
    corner = int(min(width, height) * 0.10)
    for cx0, cy0 in (
        (0, 0),
        (width - corner, 0),
        (0, height - corner),
        (width - corner, height - corner),
    ):
        mask[cy0 : cy0 + corner, cx0 : cx0 + corner] = cv2.GC_BGD
    bgd_model = np.zeros((1, 65), dtype=np.float64)
    fgd_model = np.zeros((1, 65), dtype=np.float64)
    cv2.grabCut(image_bgr, mask, None, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_MASK)
    return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
```

The controller validated this exact code against the real reference photo
(recovered visible hair and glasses, approved by the user) before handing it
off for implementation. The existing synthetic test
(`test_segment_foreground_isolates_bright_square`) is expected to still pass
unchanged — the public contract (shape, value set, region-mean assertions)
didn't change, only the internal seeding strategy.

- [ ] **Step 6: Update the implementation and verify**

Replace the contents of `tools/blockart/segment.py` with the revised code
above. Run: `pytest tools/blockart/tests/test_segment.py -v` — Expected:
PASS (1 passed), with genuine captured output (this plan has twice already
caught fabricated TDD evidence — real command output only).

- [ ] **Step 7: Commit**

```bash
git add tools/blockart/segment.py
git commit -m "fix: seed GrabCut with mask instead of rect"
```

---

## Task 5: JSON export (`export_art_data`)

**Files:**
- Create: `tools/blockart/export.py`
- Create: `tools/blockart/tests/test_export.py`

**Interfaces:**
- Consumes: `tools.blockart.gridify.ArtCell` from Task 3.
- Produces: `tools.blockart.export.export_art_data(cells: list[ArtCell], cols: int, rows: int, path: "pathlib.Path") -> None`

- [ ] **Step 1: Write the failing test**

`tools/blockart/tests/test_export.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tools/blockart/tests/test_export.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.blockart.export'`

- [ ] **Step 3: Implement `export_art_data`**

`tools/blockart/export.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tools/blockart/tests/test_export.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/blockart/export.py tools/blockart/tests/test_export.py
git commit -m "feat: add art_data.json export"
```

---

## Task 6: Preview renderer (`render_preview`)

**Files:**
- Create: `tools/blockart/preview.py`
- Create: `tools/blockart/tests/test_preview.py`

**Interfaces:**
- Consumes: `tools.blockart.gridify.ArtCell` from Task 3.
- Produces: `tools.blockart.preview.render_preview(cells: list[ArtCell], cols: int, rows: int, path: "pathlib.Path", cell_px: int = 10) -> None`

- [ ] **Step 1: Write the failing test**

`tools/blockart/tests/test_preview.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tools/blockart/tests/test_preview.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.blockart.preview'`

- [ ] **Step 3: Implement `render_preview`**

`tools/blockart/preview.py`:
```python
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from tools.blockart.gridify import ArtCell


def render_preview(
    cells: list[ArtCell],
    cols: int,
    rows: int,
    path: Path,
    cell_px: int = 10,
) -> None:
    """Render the art grid as a flat-color PNG mosaic for visual QA."""
    image = Image.new("RGB", (cols * cell_px, rows * cell_px), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    for cell in cells:
        x0 = cell.col * cell_px
        y0 = cell.row * cell_px
        draw.rectangle([x0, y0, x0 + cell_px - 1, y0 + cell_px - 1], fill=cell.color)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tools/blockart/tests/test_preview.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/blockart/preview.py tools/blockart/tests/test_preview.py
git commit -m "feat: add PNG preview renderer for art grid"
```

---

## Task 7: CLI wiring (`generate.py`)

**Files:**
- Create: `tools/blockart/generate.py`
- Create: `tools/blockart/tests/test_generate.py`

**Interfaces:**
- Consumes: `segment_foreground` (Task 4), `build_art_cells` (Task 3), `export_art_data` (Task 5), `render_preview` (Task 6).
- Produces: `tools.blockart.generate.default_rect(width: int, height: int, margin_ratio: float = 0.05) -> tuple[int, int, int, int]`, `tools.blockart.generate.generate(photo_path: Path, out_path: Path, preview_path: Path | None, cols: int, rows: int) -> None`, CLI entry point `main()`.

- [ ] **Step 1: Write the failing tests**

`tools/blockart/tests/test_generate.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tools/blockart/tests/test_generate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.blockart.generate'`

- [ ] **Step 3: Implement `generate.py`**

`tools/blockart/generate.py`:
```python
from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from tools.blockart.export import export_art_data
from tools.blockart.gridify import build_art_cells
from tools.blockart.preview import render_preview
from tools.blockart.segment import segment_foreground


def default_rect(width: int, height: int, margin_ratio: float = 0.05) -> tuple[int, int, int, int]:
    """A rect inset by margin_ratio on every side, as a GrabCut initial guess."""
    mx = int(width * margin_ratio)
    my = int(height * margin_ratio)
    return (mx, my, width - 2 * mx, height - 2 * my)


def generate(
    photo_path: Path,
    out_path: Path,
    preview_path: Path | None,
    cols: int,
    rows: int,
) -> None:
    image_bgr = cv2.imread(str(photo_path))
    if image_bgr is None:
        raise FileNotFoundError(f"could not read image: {photo_path}")
    height, width = image_bgr.shape[:2]
    rect = default_rect(width, height)
    mask = segment_foreground(image_bgr, rect)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    cells = build_art_cells(image_rgb, mask, cols=cols, rows=rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    export_art_data(cells, cols=cols, rows=rows, path=out_path)
    if preview_path is not None:
        render_preview(cells, cols=cols, rows=rows, path=preview_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a photo into Unicode block-art data.")
    parser.add_argument("photo", type=Path, help="Path to the reference photo (kept out of git)")
    parser.add_argument("--out", type=Path, default=Path("assets/art_data.json"))
    parser.add_argument("--preview", type=Path, default=Path("assets/art_preview.png"))
    parser.add_argument("--cols", type=int, default=60)
    parser.add_argument("--rows", type=int, default=40)
    args = parser.parse_args()
    generate(args.photo, args.out, args.preview, args.cols, args.rows)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tools/blockart/tests/test_generate.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: PASS (13 passed)

- [ ] **Step 6: Commit**

```bash
git add tools/blockart/generate.py tools/blockart/tests/test_generate.py
git commit -m "feat: wire up blockart CLI"
```

---

## Task 8: Generate the real art data (manual, not TDD)

This task has no automated test — it is the one-time run against the real photo, plus your own visual sign-off. It produces the artifact Plan 2 (stats-card-generator) depends on.

**Files:**
- Create: `assets/art_data.json` (committed)
- Create: `assets/art_preview.png` (committed, for reviewers — shows what the mosaic looks like without needing the source photo)

- [ ] **Step 1: Run the CLI against your reference photo**

Keep the photo itself outside the repo (e.g. in your Downloads folder or `~/Pictures`), then run from the repo root:
```bash
pip install -r requirements-blockart.txt
python -m tools.blockart.generate /path/to/your/photo.png --out assets/art_data.json --preview assets/art_preview.png
```

- [ ] **Step 2: Visually inspect the preview**

Open `assets/art_preview.png`. Check that the silhouette reads as a head with round glasses and hair parted in the middle. If the segmentation looks off (background leaking in, or part of the head cut off), adjust the crop by passing a tighter/looser `--cols`/`--rows`, or pre-crop the source photo tighter around the head/shoulders and re-run Step 1.

- [ ] **Step 3: Confirm no raw photo made it into the repo**

Run: `git status --short`
Expected: only `assets/art_data.json` and `assets/art_preview.png` show up as new files — no `.jpg`/`.png` of the actual source photo.

- [ ] **Step 4: Commit**

```bash
git add assets/art_data.json assets/art_preview.png
git commit -m "feat: add generated block-art data"
```

---

## Self-Review Notes

- **Spec coverage:** Unicode block character set (Q8) → Task 1. Background removal without committing the photo (privacy constraint) → Task 4 + Task 8. Grid resolution 60×40 → Global Constraints, enforced via CLI defaults in Task 7. Visual QA before commit → Task 8 Step 2.
- **Placeholder scan:** none found — every step has runnable code or an exact command.
- **Type consistency:** `ArtCell` defined once in Task 3, imported by name (never redefined) in `export.py`, `preview.py`, `generate.py`, and their tests. `cols`/`rows` parameter order is `(cols, rows)` consistently across `build_art_cells`, `export_art_data`, `render_preview`, and `generate`.
