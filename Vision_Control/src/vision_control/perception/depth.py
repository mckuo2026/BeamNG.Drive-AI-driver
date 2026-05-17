"""Optional monocular depth (MiDaS-small). M3 work.

Disabled by default — set config.perception.use_depth = True to enable.
"""
from __future__ import annotations

import numpy as np


class DepthEstimator:
    def __init__(self, model_path: str, providers: list[str]) -> None:
        self.model_path = model_path
        self.providers  = providers

    def load(self) -> None:
        raise NotImplementedError("DepthEstimator.load — M3")

    def run(self, bgr: np.ndarray) -> np.ndarray:
        """Return HxW float32 in [0,1] where 1 = closest."""
        raise NotImplementedError("DepthEstimator.run — M3")
