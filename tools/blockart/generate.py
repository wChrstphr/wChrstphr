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
