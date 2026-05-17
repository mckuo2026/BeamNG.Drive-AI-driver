"""ONNX-based semantic segmenter (DirectML preferred, CPU fallback).

See docs/PROPOSAL.md §2 and docs/PERFORMANCE.md §3.2.

Status (M1): API skeleton only. The M1 demos use
`vision_control.perception.fallback_hsv.AdaptiveLabSegmenter`, which has
the same `run() -> HxW uint8 class-id mask` contract and works without
any model file. Slot a real ONNX model in here once one is shipped:

    seg = Segmenter("models/ddrnet_slim_4class.onnx",
                    providers=["DmlExecutionProvider", "CPUExecutionProvider"])
    seg.load()
    mask = seg.run(bgr)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


class Segmenter:
    """Run an ONNX segmentation model and return uint8 class-id mask.

    Subclasses / implementations are expected to honour the class IDs in
    `vision_control.perception.__init__`:
        CLASS_OTHER, CLASS_ROAD, CLASS_OBSTACLE, CLASS_SKY.
    """

    def __init__(self, model_path: str | Path, providers: list[str]) -> None:
        self.model_path = Path(model_path)
        self.providers  = providers
        self._session   = None
        self._input_name: str | None = None
        self._input_size: tuple[int, int] = (384, 384)

    def load(self) -> None:
        # TODO (post-M1, requires a shipped ONNX model file):
        #   import onnxruntime as ort
        #   self._session = ort.InferenceSession(
        #       str(self.model_path), providers=self.providers)
        #   self._input_name = self._session.get_inputs()[0].name
        #   self._input_size = self._session.get_inputs()[0].shape[-2:]
        raise NotImplementedError(
            "Segmenter.load — no ONNX model shipped yet. "
            "Use perception.fallback_hsv.AdaptiveLabSegmenter for M1."
        )

    def run(self, bgr: np.ndarray) -> np.ndarray:
        """Return HxW uint8 class-id mask, same H/W as input."""
        # TODO (post-M1):
        #   1. resize bgr -> input_size
        #   2. normalise to float32, NCHW
        #   3. session.run(...) -> NCHW logits
        #   4. argmax -> uint8 mask, resize back with nearest-neighbour
        raise NotImplementedError("Segmenter.run — see fallback_hsv for M1.")


if __name__ == "__main__":
    print("ONNX segmenter is post-M1. For now use:")
    print("    python -m vision_control.perception.fallback_hsv --capture WINDOW")
