"""M1 integration preview — capture → road mask → drivable area → Pure Pursuit.

This is the closest thing to "auto-driving" Vision_Control has at M1.
It does NOT touch the gamepad by default (so it's safe to run anywhere).
Pass `--drive` to also push the computed ControlTarget to vgamepad.

Usage:
    python -m vision_control.tools.preview "GeForce NOW"
    python -m vision_control.tools.preview "GeForce NOW" --drive
    python -m vision_control.tools.preview "GeForce NOW" --record out.mp4

Key bindings (preview window):
    Q / Esc   quit
    R         recalibrate segmenter
    SPACE     toggle pause (control output set to neutral while paused)
    D         toggle --drive on/off
"""
from __future__ import annotations

import argparse
import sys
import time

import cv2
import numpy as np

from ..capture.dxcam_roi import (
    RoiCapture, _safe_preview_pos, _draw_perception_roi_overlay,
    _hide_cv2_window_from_capture,
)
from ..capture.window_focus import get_monitor_rect_for_hwnd
from ..config import Roi
from ..perception import CLASS_ROAD, apply_perception_roi
from ..perception.fallback_hsv import AdaptiveLabSegmenter, _overlay_mask
from ..planning import ObstacleInfo
from ..planning.drivable_area import draw_overlay, from_road_mask
from ..planning.pure_pursuit import compute as compute_control


def _hud(frame: np.ndarray, lines: list[str]) -> None:
    """Draw multi-line HUD text in the top-left of `frame` (in-place)."""
    y = 16
    for text in lines:
        cv2.putText(frame, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (255, 255, 255), 1, cv2.LINE_AA)
        y += 16


def _draw_control_bar(frame: np.ndarray, steer: float,
                      throttle: float, brake: float) -> None:
    """Right-side gauges for current ControlTarget."""
    h, w = frame.shape[:2]
    # Steer bar (horizontal, center, top)
    bx0, bx1 = w // 4, 3 * w // 4
    by = h - 18
    cv2.rectangle(frame, (bx0, by - 5), (bx1, by + 5), (40, 40, 60), -1)
    cv2.line(frame, ((bx0 + bx1) // 2, by - 6), ((bx0 + bx1) // 2, by + 6),
             (180, 180, 180), 1)
    cx = int((bx0 + bx1) // 2 + steer * (bx1 - bx0) // 2)
    cv2.circle(frame, (cx, by), 6, (0, 220, 80), -1)

    # Throttle (green) / Brake (red) — right-edge vertical bars
    tx = w - 14
    cv2.rectangle(frame, (tx - 8, 20), (tx, h - 30), (40, 40, 60), -1)
    fill_t = int((h - 50) * float(throttle))
    cv2.rectangle(frame, (tx - 8, h - 30 - fill_t), (tx, h - 30),
                  (80, 220, 80), -1)
    bx = w - 26
    cv2.rectangle(frame, (bx - 8, 20), (bx, h - 30), (40, 40, 60), -1)
    fill_b = int((h - 50) * float(brake))
    cv2.rectangle(frame, (bx - 8, h - 30 - fill_b), (bx, h - 30),
                  (80, 80, 220), -1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vision_control.tools.preview",
        description="M1 integration preview: capture → segmenter → planner.",
    )
    p.add_argument("window", help="window title (substring match)")
    p.add_argument("--drive", action="store_true",
                   help="also push ControlTarget to vgamepad (BeamNG control)")
    p.add_argument("--width",  type=int, default=640, help="capture target width")
    p.add_argument("--height", type=int, default=360, help="capture target height")
    p.add_argument("--fps",    type=int, default=60,  help="capture fps")
    p.add_argument("--record", metavar="PATH",
                   help="record the preview window to an MP4 file")
    p.add_argument("--scale", type=float, default=1.0,
                   help="preview window size multiplier (1.0 = native)")
    args = p.parse_args(argv)

    # ─── capture ────────────────────────────────────────────────────────────
    # Capture the WHOLE client area; perception still uses the configured
    # ROI internally for K-means calibration and as a planning hint, but the
    # preview always shows the entire window so you can see context.
    full_roi = Roi(left_pct=0.0, right_pct=1.0, top_pct=0.0, bottom_pct=1.0)
    perc_roi = Roi()  # config defaults — drawn as a yellow rectangle overlay
    cap = RoiCapture(args.window, full_roi,
                     target_size=(args.width, args.height),
                     target_fps=args.fps)
    try:
        cap.start()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    # ─── segmenter ──────────────────────────────────────────────────────────
    seg = AdaptiveLabSegmenter(n_calib_frames=24)

    # ─── control (optional) ─────────────────────────────────────────────────
    backend = None
    if args.drive:
        from ..control.gamepad import GamepadBackend
        backend = GamepadBackend()
        if not backend.is_available():
            print("WARN: vgamepad not available — running preview-only mode.")
            backend = None
        else:
            try:
                backend.open()
                print("Gamepad opened. ControlTargets WILL be sent to BeamNG.")
            except RuntimeError as exc:
                print(f"WARN: could not open gamepad ({exc}) — preview only.")
                backend = None

    # ─── recording ──────────────────────────────────────────────────────────
    writer = None
    if args.record:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.record, fourcc, 30.0,
                                 (args.width, args.height))
        if not writer.isOpened():
            print(f"WARN: could not open writer for {args.record}")
            writer = None

    win = "Vision_Control: preview (capture → mask → planner)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    pw = int(args.width  * args.scale)
    ph = int(args.height * args.scale)
    cv2.resizeWindow(win, pw, ph)
    # Auto-position outside the capture region to dodge the infinite mirror.
    mon = get_monitor_rect_for_hwnd(cap._hwnd) or (0, 0, 1920, 1080)
    if cap._region:
        x_, y_ = _safe_preview_pos(cap._region, (pw, ph), mon)
        cv2.moveWindow(win, x_, y_)
    # And — belt + braces — make the window invisible to dxcam itself.
    if _hide_cv2_window_from_capture(win):
        print("[preview] window hidden from screen capture (anti-mirror)")

    paused = False
    drive_enabled = (backend is not None)
    t0 = time.perf_counter()
    last_stats = t0
    frames_processed = 0

    print("Controls: Q quit · R recalibrate · SPACE pause · D toggle drive")
    try:
        while True:
            bgr = cap.latest()
            if bgr is None:
                if cv2.waitKey(10) & 0xFF in (ord("q"), 27):
                    break
                continue

            t_start = time.perf_counter()
            overlay = bgr.copy()
            hud_lines: list[str] = []

            # 1. Calibrate segmenter on first ~24 frames.
            if not seg.is_calibrated:
                seg.feed_calibration_frame(bgr)
                hud_lines.append(
                    f"Calibrating  {len(seg._calib_pool)}/{seg.n_calib_frames}"
                )
                steer = throttle = brake = 0.0
            else:
                # 2. Segment — mask out HUD/sky first so the BeamNG gauges
                # don't get classified as road.
                perc_input = apply_perception_roi(bgr, perc_roi)
                mask = seg.run(perc_input)
                road = (mask == CLASS_ROAD)

                # 3. Drivable area + lookahead.
                drivable = from_road_mask(road)

                # 4. Pure Pursuit → ControlTarget.
                target = compute_control(
                    drivable=drivable,
                    obstacles=ObstacleInfo.empty(),
                    frame_size=bgr.shape[:2],
                )
                steer, throttle, brake = target.steer, target.throttle, target.brake

                # 5. Overlay.
                overlay = _overlay_mask(bgr, mask)
                _draw_perception_roi_overlay(overlay, perc_roi)
                if drivable is not None:
                    overlay = draw_overlay(overlay, drivable)
                    hud_lines.append(
                        f"road {(road.mean()*100):5.1f}%  conf {drivable.confidence:0.2f}  "
                        f"look ({drivable.lookahead_point[0]:3d},"
                        f"{drivable.lookahead_point[1]:3d})"
                    )
                else:
                    hud_lines.append(
                        f"road {(road.mean()*100):5.1f}%  drivable=None"
                    )

                # 6. Drive output (optional).
                if drive_enabled and backend is not None and not paused:
                    backend.set(target)
                elif backend is not None and (paused or not drive_enabled):
                    # Always force neutral when paused or drive disabled.
                    backend.set_raw(0.0, 0.0, 0.0)

            elapsed_ms = (time.perf_counter() - t_start) * 1000
            frames_processed += 1
            now = time.perf_counter()
            if now - last_stats >= 1.0:
                fps_proc = frames_processed / (now - t0)
                last_stats = now
            else:
                fps_proc = frames_processed / max(now - t0, 1e-6)

            hud_lines.insert(0,
                f"{('PAUSED' if paused else 'live  '):>6}  "
                f"{('DRIVE' if drive_enabled else 'view '):>5}  "
                f"proc {elapsed_ms:5.1f}ms  "
                f"fps {fps_proc:4.1f}"
            )
            _hud(overlay, hud_lines)
            _draw_control_bar(overlay, steer, throttle, brake)
            cv2.imshow(win, overlay)

            if writer is not None:
                writer.write(overlay)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif key == ord("r"):
                seg.reset()
                print("  → recalibrating segmenter")
            elif key == ord(" "):
                paused = not paused
                print(f"  → {'paused' if paused else 'resumed'}")
            elif key == ord("d"):
                if backend is None:
                    print("  → cannot toggle DRIVE: gamepad not opened")
                else:
                    drive_enabled = not drive_enabled
                    print(f"  → drive {'ON' if drive_enabled else 'OFF'}")
                    if not drive_enabled:
                        backend.set_raw(0.0, 0.0, 0.0)
    except KeyboardInterrupt:
        pass
    finally:
        # BaseException everywhere so a second Ctrl-C during cleanup
        # cannot leave a virtual gamepad active or a stuck preview window.
        if backend is not None:
            try:
                backend.release_all()
                backend.close()
            except BaseException:
                pass
        if writer is not None:
            try:
                writer.release()
            except BaseException:
                pass
        try:
            cap.stop()
        except BaseException:
            pass
        try:
            cv2.destroyAllWindows()
        except BaseException:
            pass

    elapsed = time.perf_counter() - t0
    print(f"\nProcessed {frames_processed} frames in {elapsed:.1f}s "
          f"(avg {frames_processed / max(elapsed, 1e-9):.1f} fps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
