"""Planning layer — drivable area + Pure Pursuit. See docs/PROPOSAL.md §3."""

from dataclasses import dataclass

import numpy as np


@dataclass
class DrivableArea:
    polygon:         np.ndarray         # Nx2 int32, in capture-frame coords
    lookahead_point: tuple[int, int]
    confidence:      float              # 0.0 ~ 1.0


@dataclass
class ObstacleInfo:
    min_distance_pct: float             # 0.0 = touching, 1.0 = far / none
    has_close_block:  bool              # True → emergency brake

    @classmethod
    def empty(cls) -> "ObstacleInfo":
        return cls(min_distance_pct=1.0, has_close_block=False)


@dataclass
class ControlTarget:
    steer:    float   # -1.0 ~ +1.0
    throttle: float   #  0.0 ~ +1.0
    brake:    float   #  0.0 ~ +1.0


__all__ = ["DrivableArea", "ObstacleInfo", "ControlTarget"]
