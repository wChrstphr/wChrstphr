from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtCell:
    row: int
    col: int
    char: str
    color: str

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
