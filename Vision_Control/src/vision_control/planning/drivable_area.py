"""Extract drivable polygon + lookahead point from a road mask.

See docs/ARCHITECTURE.md §2.3 and docs/PROPOSAL.md §3.2.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import DrivableArea


def from_road_mask(road_mask: np.ndarray,
                   lookahead_pct: float = 0.40,
                   min_area_ratio: float = 0.03) -> DrivableArea | None:
    """Convert a binary/uint8 road mask into a DrivableArea.

    Strategy:
      1. Take the largest connected component of `road_mask` (RETR_EXTERNAL).
      2. Reject if its area < min_area_ratio * H*W.
      3. approxPolyDP with epsilon = 6 px to get a coarse polygon.
      4. At row y = int(H * lookahead_pct), find the longest run of True
         pixels in `road_mask`; lookahead_point = midpoint of that run.
      5. confidence = clamp(area / (H*W) / 0.4, 0, 1).

    Args:
        road_mask: HxW bool or uint8 (0/255 or any non-zero = road).
        lookahead_pct: where to sample the lookahead row (0..1, top→bottom).
        min_area_ratio: minimum fraction of frame area to consider valid.

    Returns:
        DrivableArea, or None if no usable road region was found.
    """
    if road_mask is None or road_mask.size == 0:
        return None

    if road_mask.dtype != np.uint8:
        mask_u8 = (road_mask.astype(bool).astype(np.uint8) * 255)
    else:
        mask_u8 = (road_mask > 0).astype(np.uint8) * 255

    h, w = mask_u8.shape[:2]

    # 1. Largest contour
    contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(contour))
    if area < min_area_ratio * (h * w):
        return None

    # 3. Polygon approximation
    epsilon = 6.0
    polygon = cv2.approxPolyDP(contour, epsilon, closed=True).reshape(-1, 2)
    polygon = polygon.astype(np.int32)

    # 4. Lookahead point — longest run on the chosen row, but inside the
    # contour bbox so we never pick a stray sliver far away from the main road.
    y = int(round(h * lookahead_pct))
    y = max(0, min(h - 1, y))
    row = mask_u8[y, :] > 0
    lookahead = _longest_run_midpoint(row)
    if lookahead is None:
        # Search a small vertical neighbourhood ±5% for a row with road pixels.
        band = max(1, int(0.05 * h))
        for dy in range(1, band + 1):
            for yy in (y - dy, y + dy):
                if 0 <= yy < h:
                    cand = _longest_run_midpoint(mask_u8[yy, :] > 0)
                    if cand is not None:
                        lookahead = cand
                        y = yy
                        break
            if lookahead is not None:
                break
    if lookahead is None:
        return None

    # 5. Confidence
    area_ratio = area / float(h * w)
    confidence = float(min(1.0, area_ratio / 0.40))

    return DrivableArea(
        polygon=polygon,
        lookahead_point=(int(lookahead), int(y)),
        confidence=confidence,
    )


def _longest_run_midpoint(row: np.ndarray) -> int | None:
    """Given a 1-D boolean row, return the midpoint x of its longest True run."""
    if not row.any():
        return None
    # Encode runs by diff'ing the int representation.
    pad = np.concatenate(([False], row, [False]))
    diff = np.diff(pad.astype(np.int8))
    starts = np.flatnonzero(diff ==  1)
    ends   = np.flatnonzero(diff == -1)
    if len(starts) == 0:
        return None
    lengths = ends - starts
    idx = int(np.argmax(lengths))
    return int((starts[idx] + ends[idx] - 1) // 2)


def draw_overlay(bgr: np.ndarray, drivable: DrivableArea) -> np.ndarray:
    """Return a copy of bgr with the polygon outline and lookahead point drawn."""
    out = bgr.copy()
    if drivable is None:
        return out
    if drivable.polygon is not None and len(drivable.polygon) >= 3:
        cv2.polylines(out, [drivable.polygon.astype(np.int32)],
                      isClosed=True, color=(0, 255, 255),
                      thickness=2, lineType=cv2.LINE_AA)
    px, py = drivable.lookahead_point
    cv2.circle(out, (px, py), 6, (0, 80, 255), -1, lineType=cv2.LINE_AA)
    cv2.circle(out, (px, py), 8, (255, 255, 255),  2, lineType=cv2.LINE_AA)
    # Vehicle reference point
    h, w = out.shape[:2]
    cv2.line(out, (w // 2, h - 1), (px, py),
             (255, 200, 80), 1, cv2.LINE_AA)
    return out
