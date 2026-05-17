"""Vision_Control engine: capture, perception, planning, and control.

This is the headless brain that `ui.panel.ControlPanel` wraps. It runs the
full pipeline on a background worker thread, exposes thread-safe getters
for the UI to poll (preview frame, telemetry, state, log lines), and
accepts simple lifecycle commands (start / pause / resume / stop) and
runtime toggles (drive on/off).

State machine:

    IDLE ──start()──► STARTING ──ok──► RUNNING ◄──resume()── PAUSED
      ▲                  │ fail            │  └──pause()────►   │
      │                  ▼                 │                    │
      │               ERROR ◄──any failure─┘  ──stop()──► STOPPING
      └──────────────── stop done ◄────────────────────────────┘

Threads:
    * UI / main thread: only the `tkinter` mainloop touches widgets.
    * worker thread:    capture, segmenter, planning, gamepad output.

All cross-thread reads go through `_lock`. Methods are non-blocking;
`stop()` does NOT join the worker — the UI's idle tick noticings the
state change and removes the join responsibility.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from .capture.dxcam_roi import (
    RoiCapture,
    _draw_perception_roi_overlay,
)
from .capture.window_focus import find_window_by_title
from .config import Roi
from .control.gamepad import GamepadBackend
from .perception import CLASS_ROAD, apply_perception_roi
from .perception.fallback_hsv import AdaptiveLabSegmenter, _overlay_mask
from .planning import ObstacleInfo
from .planning.drivable_area import draw_overlay, from_road_mask
from .planning.pure_pursuit import compute as compute_control


class State(str, Enum):
    IDLE     = "idle"
    STARTING = "starting"
    RUNNING  = "running"
    PAUSED   = "paused"
    STOPPING = "stopping"
    ERROR    = "error"


@dataclass
class Telemetry:
    fps:        float = 0.0
    steer:      float = 0.0
    throttle:   float = 0.0
    brake:      float = 0.0
    road_pct:   float = 0.0
    confidence: float = 0.0
    calibrated: bool  = False
    calib_seen: int   = 0
    calib_need: int   = 24
    drive_on:   bool  = False
    has_gamepad: bool = False
    capture_backend: str = ""


class VisionEngine:
    """Headless orchestrator for the full Vision_Control pipeline."""

    PREVIEW_TARGET_SIZE: tuple[int, int] = (640, 360)
    CAPTURE_FPS:         int             = 60

    def __init__(self) -> None:
        self._lock        = threading.Lock()
        self._state       = State.IDLE
        self._error_msg   = ""
        self._stop_evt    = threading.Event()
        self._pause_evt   = threading.Event()    # set == paused
        self._worker:      threading.Thread | None = None

        self._latest_preview:   np.ndarray | None = None
        self._latest_telemetry: Telemetry = Telemetry()

        self._drive       = False
        self._log_q:       queue.Queue[str] = queue.Queue(maxsize=400)

        self._cap:        Any | None        = None
        self._seg:        AdaptiveLabSegmenter | None = None
        self._gamepad:    GamepadBackend | None     = None

    # ── thread-safe getters / setters ─────────────────────────────────────
    def get_state(self) -> tuple[State, str]:
        with self._lock:
            return self._state, self._error_msg

    def get_preview(self) -> np.ndarray | None:
        with self._lock:
            if self._latest_preview is None:
                return None
            return self._latest_preview.copy()

    def get_telemetry(self) -> Telemetry:
        with self._lock:
            t = self._latest_telemetry
        return Telemetry(**t.__dict__)

    def drain_log(self, max_lines: int = 100) -> list[str]:
        out: list[str] = []
        for _ in range(max_lines):
            try:
                out.append(self._log_q.get_nowait())
            except queue.Empty:
                break
        return out

    def set_drive(self, enabled: bool) -> None:
        with self._lock:
            self._drive = bool(enabled)
            self._latest_telemetry.drive_on = self._drive
        # Force neutral if turning off mid-run.
        if not enabled and self._gamepad is not None:
            try:
                self._gamepad.release_all()
            except Exception:  # noqa: BLE001
                pass

    def recalibrate(self) -> None:
        if self._seg is not None:
            self._seg.reset()
            self._log("Segmenter recalibrating")

    # ── lifecycle ─────────────────────────────────────────────────────────
    def start(self, window_title: str, capture_backend: str = "auto") -> None:
        with self._lock:
            if self._state in (State.STARTING, State.RUNNING, State.PAUSED, State.STOPPING):
                return
            self._state = State.STARTING
            self._error_msg = ""
        self._stop_evt.clear()
        self._pause_evt.clear()
        self._worker = threading.Thread(
            target=self._run, args=(window_title, capture_backend),
            name="VisionEngine", daemon=True,
        )
        self._worker.start()

    def pause(self) -> None:
        self._pause_evt.set()
        with self._lock:
            if self._state == State.RUNNING:
                self._state = State.PAUSED
        if self._gamepad is not None:
            try:
                self._gamepad.release_all()
            except Exception:  # noqa: BLE001
                pass
        self._log("Paused")

    def resume(self) -> None:
        self._pause_evt.clear()
        with self._lock:
            if self._state == State.PAUSED:
                self._state = State.RUNNING
        self._log("Resumed")

    def stop(self) -> None:
        with self._lock:
            if self._state in (State.IDLE, State.STOPPING):
                return
            self._state = State.STOPPING
        self._stop_evt.set()
        self._pause_evt.clear()
        self._log("Stop requested")

    # ── internals ─────────────────────────────────────────────────────────
    def _log(self, msg: str) -> None:
        line = f"{time.strftime('%H:%M:%S')}  {msg}"
        try:
            self._log_q.put_nowait(line)
        except queue.Full:
            # Drop oldest, push newest.
            try:
                self._log_q.get_nowait()
                self._log_q.put_nowait(line)
            except (queue.Empty, queue.Full):
                pass

    def _set_state(self, s: State, error: str = "") -> None:
        with self._lock:
            self._state = s
            if error:
                self._error_msg = error

    def _run(self, window_title: str, capture_backend: str) -> None:
        """Worker thread entry point."""
        try:
            # 1. Find window first so we fail fast with a clear error.
            if find_window_by_title([window_title], exact=False) is None:
                raise RuntimeError(
                    f"No visible window matches {window_title!r}. "
                    f"Open GeForce NOW (or BeamNG locally) and try again."
                )

            # 2. Capture. Auto mode tries target-window capture first so
            # overlapping desktop windows are not fed into perception. If that
            # path is unavailable for the cloud client, it falls back to DXGI ROI.
            full_roi = Roi(left_pct=0.0, right_pct=1.0,
                           top_pct=0.0,  bottom_pct=1.0)
            self._cap = self._open_capture(window_title, full_roi, capture_backend)
            self._log(f"Capture started ({self.PREVIEW_TARGET_SIZE[0]}x"
                      f"{self.PREVIEW_TARGET_SIZE[1]} @ {self.CAPTURE_FPS}fps, "
                      f"backend={self._cap.stats.get('backend', 'dxcam')})")

            # 3. Segmenter (LAB fallback for now; ONNX is post-M1).
            self._seg = AdaptiveLabSegmenter(n_calib_frames=24)

            # 4. Gamepad (optional).
            try:
                gp = GamepadBackend()
                if gp.is_available():
                    gp.open()
                    self._gamepad = gp
                    self._log("Gamepad ready (vgamepad / ViGEm)")
                else:
                    self._log("vgamepad not available — drive disabled")
            except Exception as exc:  # noqa: BLE001
                self._log(f"Gamepad init failed: {exc} — drive disabled")
                self._gamepad = None

            with self._lock:
                self._latest_telemetry.has_gamepad = self._gamepad is not None
                self._latest_telemetry.calib_need  = self._seg.n_calib_frames
                self._latest_telemetry.capture_backend = (
                    self._cap.stats.get("backend", "dxcam") if self._cap else ""
                )

            self._set_state(State.RUNNING)
            self._log("Engine running")

            self._main_loop()

        except RuntimeError as exc:
            self._log(f"ERROR: {exc}")
            self._set_state(State.ERROR, str(exc))
        except Exception as exc:  # noqa: BLE001
            self._log(f"Unexpected error: {exc}")
            self._set_state(State.ERROR, str(exc))
        finally:
            self._cleanup()
            # Only move to IDLE if we didn't enter ERROR — keep error visible.
            with self._lock:
                if self._state != State.ERROR:
                    self._state = State.IDLE
            self._log("Engine stopped")

    def _open_capture(self, window_title: str, roi: Roi, mode: str) -> Any:
        mode = (mode or "auto").lower()
        errors: list[str] = []

        if mode in ("auto", "window", "window-only", "printwindow"):
            try:
                from .capture.window_client import WindowClientCapture

                cap = WindowClientCapture(
                    window_title,
                    roi,
                    target_size=self.PREVIEW_TARGET_SIZE,
                    target_fps=self.CAPTURE_FPS,
                )
                cap.start()
                return cap
            except Exception as exc:  # noqa: BLE001
                errors.append(f"window-only: {exc}")
                if mode != "auto":
                    raise RuntimeError(errors[-1]) from exc

        if mode in ("auto", "dxcam", "dxgi"):
            try:
                cap = RoiCapture(
                    window_title,
                    roi,
                    target_size=self.PREVIEW_TARGET_SIZE,
                    target_fps=self.CAPTURE_FPS,
                )
                cap.start()
                return cap
            except Exception as exc:  # noqa: BLE001
                errors.append(f"dxcam: {exc}")
                raise RuntimeError("; ".join(errors)) from exc

        raise RuntimeError(
            f"Unknown capture backend {mode!r}; expected auto, window, or dxcam."
        )

    def _main_loop(self) -> None:
        assert self._cap and self._seg
        perc_roi = Roi()    # config defaults, drawn as yellow overlay

        fps_count    = 0
        fps_timer    = time.perf_counter()
        last_seen_fps = 0.0

        while not self._stop_evt.is_set():
            bgr = self._cap.latest()
            if bgr is None:
                time.sleep(0.005)
                continue

            paused = self._pause_evt.is_set()

            # ── Perception ────────────────────────────────────────────────
            if not self._seg.is_calibrated:
                # Calibration uses the FULL frame; the strip is already
                # vertically constrained (0.40–0.65) so the HUD never
                # contaminates it.
                self._seg.feed_calibration_frame(bgr)
                mask = None
                drivable = None
                steer = throttle = brake = 0.0
                road_pct = 0.0
                confidence = 0.0
            else:
                # Crop perception input to the configured ROI so the
                # BeamNG HUD (speedometer/tachometer), engine hood, and
                # distant sky cannot land in the road LAB cluster.
                perc_input = apply_perception_roi(bgr, perc_roi)
                mask = self._seg.run(perc_input)
                road = (mask == CLASS_ROAD)
                drivable = from_road_mask(road)
                target = compute_control(
                    drivable, ObstacleInfo.empty(), bgr.shape[:2]
                )
                if paused:
                    steer = throttle = brake = 0.0
                    if self._gamepad is not None:
                        try:
                            self._gamepad.set_raw(0.0, 0.0, 0.0)
                        except Exception:  # noqa: BLE001
                            pass
                else:
                    steer, throttle, brake = target.steer, target.throttle, target.brake
                    if self._drive and self._gamepad is not None:
                        try:
                            self._gamepad.set(target)
                        except Exception:  # noqa: BLE001
                            pass
                    elif self._gamepad is not None:
                        try:
                            self._gamepad.set_raw(0.0, 0.0, 0.0)
                        except Exception:  # noqa: BLE001
                            pass
                road_pct = float(road.mean() * 100)
                confidence = drivable.confidence if drivable else 0.0

            # ── Overlay ───────────────────────────────────────────────────
            overlay = self._build_overlay(
                bgr, mask, drivable, perc_roi,
                paused=paused, fps=last_seen_fps,
                steer=steer, throttle=throttle, brake=brake,
                calibrating=not self._seg.is_calibrated,
            )

            # ── Publish ───────────────────────────────────────────────────
            with self._lock:
                self._latest_preview = overlay
                self._latest_telemetry.fps        = last_seen_fps
                self._latest_telemetry.steer      = steer
                self._latest_telemetry.throttle   = throttle
                self._latest_telemetry.brake      = brake
                self._latest_telemetry.road_pct   = road_pct
                self._latest_telemetry.confidence = confidence
                self._latest_telemetry.calibrated = self._seg.is_calibrated
                self._latest_telemetry.calib_seen = len(self._seg._calib_pool)
                self._latest_telemetry.drive_on   = self._drive

            # ── FPS bookkeeping ───────────────────────────────────────────
            fps_count += 1
            now = time.perf_counter()
            if now - fps_timer >= 1.0:
                last_seen_fps = fps_count / (now - fps_timer)
                fps_count = 0
                fps_timer = now

    def _build_overlay(self, bgr: np.ndarray,
                        mask: np.ndarray | None,
                        drivable: Any,
                        perc_roi: Roi,
                        paused: bool,
                        fps: float,
                        steer: float, throttle: float, brake: float,
                        calibrating: bool) -> np.ndarray:
        import cv2

        if calibrating:
            out = bgr.copy()
            h_, w_ = out.shape[:2]
            assert self._seg
            cs_top    = int(h_ * self._seg.calib_strip[0])
            cs_bottom = int(h_ * self._seg.calib_strip[1])
            cv2.rectangle(out, (0, cs_top), (w_ - 1, cs_bottom),
                          (255, 200, 0), 1, cv2.LINE_AA)
            cv2.putText(out, "calib strip", (4, cs_top - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                        (255, 200, 0), 1, cv2.LINE_AA)
            _draw_perception_roi_overlay(out, perc_roi)
            cv2.putText(out,
                        f"Calibrating  {len(self._seg._calib_pool)}/"
                        f"{self._seg.n_calib_frames}",
                        (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50,
                        (0, 220, 255), 1, cv2.LINE_AA)
            return out

        out = _overlay_mask(bgr, mask) if mask is not None else bgr.copy()
        _draw_perception_roi_overlay(out, perc_roi)
        if drivable is not None:
            out = draw_overlay(out, drivable)

        # Top-left status strip
        h_, w_ = out.shape[:2]
        status = "PAUSED" if paused else ("DRIVE" if self._drive else "view")
        cv2.rectangle(out, (0, 0), (w_, 22), (10, 10, 10), -1)
        cv2.putText(out,
                    f"{status:>6}  fps {fps:4.1f}  "
                    f"steer {steer:+0.2f}  thr {throttle:0.2f}  brk {brake:0.2f}",
                    (8, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (255, 255, 255), 1, cv2.LINE_AA)
        return out

    def _cleanup(self) -> None:
        if self._gamepad is not None:
            try:
                self._gamepad.release_all()
                self._gamepad.close()
            except Exception:  # noqa: BLE001
                pass
            self._gamepad = None
        if self._cap is not None:
            try:
                self._cap.stop()
            except Exception:  # noqa: BLE001
                pass
            self._cap = None
        self._seg = None
