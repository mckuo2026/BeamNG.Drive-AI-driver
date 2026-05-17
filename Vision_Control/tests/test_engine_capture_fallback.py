from __future__ import annotations

import numpy as np

from vision_control.config import Roi
from vision_control.engine import State, VisionEngine


class _WindowCap:
    def __init__(self) -> None:
        self.stopped = False

    @property
    def stats(self) -> dict[str, str]:
        return {"backend": "window"}

    def stop(self) -> None:
        self.stopped = True


class _DxCap:
    started = 0

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    @property
    def stats(self) -> dict[str, str]:
        return {"backend": "dxcam"}

    def start(self) -> None:
        type(self).started += 1


def test_auto_capture_falls_back_after_repeated_black_frames(monkeypatch) -> None:
    monkeypatch.setattr("vision_control.engine.RoiCapture", _DxCap)
    _DxCap.started = 0

    engine = VisionEngine()
    window_cap = _WindowCap()
    engine._cap = window_cap
    engine._capture_mode = "auto"
    engine._capture_window_title = "Game"
    engine._capture_roi = Roi(left_pct=0.0, right_pct=1.0, top_pct=0.0, bottom_pct=1.0)

    black = np.zeros((8, 8, 3), dtype=np.uint8)

    for _ in range(engine.BLACK_FRAME_FALLBACK_COUNT - 1):
        assert engine._maybe_switch_black_window_capture(black) is False

    assert window_cap.stopped is False
    assert engine._maybe_switch_black_window_capture(black) is True
    assert window_cap.stopped is True
    assert isinstance(engine._cap, _DxCap)
    assert _DxCap.started == 1
    assert engine.get_telemetry().capture_backend == "dxcam"


def test_focus_watchdog_pauses_when_drive_window_loses_focus(monkeypatch) -> None:
    monkeypatch.setattr("vision_control.engine.is_foreground", lambda _hwnd: False)

    engine = VisionEngine()
    engine._target_hwnd = 123
    engine._drive = True
    engine._run_started_at = -999.0
    engine._last_focus_check = -999.0
    engine._set_state(State.RUNNING)

    engine._check_focus_watchdog()

    state, _err = engine.get_state()
    assert state == State.PAUSED
