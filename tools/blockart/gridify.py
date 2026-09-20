from __future__ import annotations

import numpy as np

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
