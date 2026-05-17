"""Pure Pursuit geometric controller — drivable area + obstacles → ControlTarget.

See docs/PROPOSAL.md §3.3.
"""
from __future__ import annotations

import math

from . import ControlTarget, DrivableArea, ObstacleInfo


def compute(drivable: DrivableArea | None,
            obstacles: ObstacleInfo,
            frame_size: tuple[int, int],
            brake_distance_pct: float = 0.30,
            slow_distance_pct:  float = 0.55) -> ControlTarget:
    """Translate perception output into a steer/throttle/brake triple.

    Coordinate convention: image frame, x→right, y→down.
    "Vehicle position" is assumed to be the bottom-center of the frame.
    """
    h, w = frame_size

    # No drivable info → coast straight with throttle off so we don't run blind.
    if drivable is None or drivable.confidence < 0.1:
        return ControlTarget(steer=0.0, throttle=0.0, brake=0.2)

    # Emergency brake takes priority.
    if obstacles.has_close_block:
        return ControlTarget(steer=0.0, throttle=0.0, brake=1.0)

    # Pure Pursuit geometry — M2 TODO replace with proper formula
    # using the lookahead point. Below is the stub formula sketch:
    px, py = drivable.lookahead_point
    car_x, car_y = w / 2.0, h - 1.0
    dx = px - car_x
    dy = car_y - py            # positive forward
    if dy <= 1.0:
        return ControlTarget(steer=0.0, throttle=0.0, brake=0.4)

    # alpha = angle to lookahead, ell = distance.
    alpha = math.atan2(dx, dy)
    # δ ∝ 2L sin(α) / ell — with L absorbed into a gain.
    # Gain 0.8 (was 2.0) tames the swerve-left-swerve-right oscillation
    # caused by per-frame lookahead jitter from the LAB segmenter; with
    # better perception this can creep back up.
    STEER_GAIN    = 0.8
    STEER_DEADZONE = 0.08      # ignore tiny corrections that cause hunting
    steer = STEER_GAIN * math.sin(alpha)
    if abs(steer) < STEER_DEADZONE:
        steer = 0.0
    steer = max(-1.0, min(1.0, steer))

    # Throttle: ease off when steering hard, ease off when obstacle close-ish.
    throttle = 1.0 - 0.6 * abs(steer)
    if obstacles.min_distance_pct < slow_distance_pct:
        throttle *= 0.5
    if obstacles.min_distance_pct < brake_distance_pct:
        return ControlTarget(steer=steer, throttle=0.0, brake=0.8)

    return ControlTarget(steer=steer, throttle=throttle, brake=0.0)
