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
