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
