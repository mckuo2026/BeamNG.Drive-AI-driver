"""Perception layer — semantic segmentation, optional depth, HSV fallback.

Class id contract — kept stable so planning can use plain numpy comparisons.
"""
from __future__ import annotations

import numpy as np

CLASS_OTHER    = 0
CLASS_ROAD     = 1
CLASS_OBSTACLE = 2
CLASS_SKY      = 3


def apply_perception_roi(frame: np.ndarray, roi) -> np.ndarray:
    """Zero out everything OUTSIDE the perception ROI rectangle.

    This is what stops the segmenter from classifying the BeamNG HUD
    (speedometer, tachometer, gauges), the engine hood, or distant sky as
    road just because their colour happens to land in the LAB road cluster.
    Pixels turned to black sit at LAB(0, 128, 128) — far outside the
    `lab_radius` of any reasonable road cluster, so they reliably map to
    CLASS_OTHER.

    Returns a fresh ndarray; the caller's `frame` is not modified.

    Args:
        frame: HxWx3 BGR uint8.
        roi:   anything with `left_pct`, `right_pct`, `top_pct`, `bottom_pct`
               attributes in 0..1 (i.e. a `vision_control.config.Roi`).
    """
    h, w = frame.shape[:2]
    x1 = max(0, min(w, int(roi.left_pct   * w)))
    x2 = max(0, min(w, int(roi.right_pct  * w)))
    y1 = max(0, min(h, int(roi.top_pct    * h)))
    y2 = max(0, min(h, int(roi.bottom_pct * h)))
    out = np.zeros_like(frame)
    if x2 > x1 and y2 > y1:
        out[y1:y2, x1:x2] = frame[y1:y2, x1:x2]
    return out


__all__ = [
    "CLASS_OTHER", "CLASS_ROAD", "CLASS_OBSTACLE", "CLASS_SKY",
    "apply_perception_roi",
]
