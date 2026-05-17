"""Smoke unit tests for the pure_pursuit stub.

These cover the only chunk of real logic that exists at M0 — the
geometry-only ControlTarget computation in `planning.pure_pursuit.compute`.
"""
from __future__ import annotations

import numpy as np
import pytest

from vision_control.planning import DrivableArea, ObstacleInfo
from vision_control.planning.pure_pursuit import compute

FRAME = (216, 384)  # (H, W) — matches default config target_size


def _drivable(lookahead: tuple[int, int], conf: float = 1.0) -> DrivableArea:
    return DrivableArea(
        polygon=np.zeros((4, 2), dtype=np.int32),
        lookahead_point=lookahead,
        confidence=conf,
    )


@pytest.mark.smoke
def test_straight_road_no_steer() -> None:
    h, w = FRAME
    target = compute(_drivable((w // 2, int(h * 0.55))), ObstacleInfo.empty(), FRAME)
    assert abs(target.steer) < 0.05
    assert target.throttle > 0.8
    assert target.brake == 0.0


@pytest.mark.smoke
def test_right_offset_lookahead_steers_right() -> None:
    h, w = FRAME
    target = compute(_drivable((int(w * 0.75), int(h * 0.55))),
                     ObstacleInfo.empty(), FRAME)
    assert target.steer > 0.15


@pytest.mark.smoke
def test_left_offset_lookahead_steers_left() -> None:
    h, w = FRAME
    target = compute(_drivable((int(w * 0.25), int(h * 0.55))),
                     ObstacleInfo.empty(), FRAME)
    assert target.steer < -0.15


@pytest.mark.smoke
def test_close_obstacle_emergency_brake() -> None:
    h, w = FRAME
    target = compute(
        _drivable((w // 2, int(h * 0.55))),
        ObstacleInfo(min_distance_pct=0.05, has_close_block=True),
        FRAME,
    )
    assert target.brake == 1.0
    assert target.throttle == 0.0


@pytest.mark.smoke
def test_low_confidence_coasts() -> None:
    h, w = FRAME
    target = compute(_drivable((w // 2, int(h * 0.55)), conf=0.05),
                     ObstacleInfo.empty(), FRAME)
    assert target.throttle == 0.0
    assert target.brake > 0.0
