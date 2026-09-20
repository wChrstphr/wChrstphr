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
