"""Smoke unit tests for planning.drivable_area.from_road_mask."""
from __future__ import annotations

import numpy as np
import pytest

from vision_control.planning.drivable_area import from_road_mask


def _trapezoid_mask(h: int, w: int,
                    top_left: float, top_right: float,
                    bot_left: float, bot_right: float) -> np.ndarray:
    """Build a road-like trapezoid mask with the given normalised x positions."""
    mask = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        t = y / max(1, h - 1)
        x_left  = int((top_left  + t * (bot_left  - top_left )) * w)
        x_right = int((top_right + t * (bot_right - top_right)) * w)
        x_left  = max(0, min(w - 1, x_left))
        x_right = max(0, min(w, x_right))
        mask[y, x_left:x_right] = 255
    return mask


@pytest.mark.smoke
def test_straight_road_lookahead_near_center() -> None:
    mask = _trapezoid_mask(216, 384, 0.40, 0.60, 0.20, 0.80)
    out  = from_road_mask(mask, lookahead_pct=0.55)
    assert out is not None
    px, py = out.lookahead_point
    # Lookahead x should be near the center of the frame for a centered road.
    assert abs(px - 192) < 24
    assert out.confidence > 0.05


@pytest.mark.smoke
def test_right_curving_road_lookahead_skews_right() -> None:
    # Road centerline curves right toward the top.
    mask = _trapezoid_mask(216, 384, 0.55, 0.75, 0.20, 0.80)
    out  = from_road_mask(mask, lookahead_pct=0.30)
    assert out is not None
    px, _ = out.lookahead_point
    assert px > 192   # right of center


@pytest.mark.smoke
def test_left_curving_road_lookahead_skews_left() -> None:
    mask = _trapezoid_mask(216, 384, 0.25, 0.45, 0.20, 0.80)
    out  = from_road_mask(mask, lookahead_pct=0.30)
    assert out is not None
    px, _ = out.lookahead_point
    assert px < 192


@pytest.mark.smoke
def test_empty_mask_returns_none() -> None:
    mask = np.zeros((216, 384), dtype=np.uint8)
    assert from_road_mask(mask) is None


@pytest.mark.smoke
def test_tiny_blob_below_min_area_returns_none() -> None:
    mask = np.zeros((216, 384), dtype=np.uint8)
    mask[100:104, 190:194] = 255   # 4×4 dot — well below 3% of frame
    assert from_road_mask(mask, min_area_ratio=0.03) is None


@pytest.mark.smoke
def test_polygon_is_at_least_a_triangle() -> None:
    mask = _trapezoid_mask(216, 384, 0.40, 0.60, 0.20, 0.80)
    out  = from_road_mask(mask)
    assert out is not None
    assert out.polygon is not None
    assert out.polygon.shape[0] >= 3
    assert out.polygon.shape[1] == 2
