"""ROI capture via dxcam (DXGI Desktop Duplication).

Captures only the configured rectangle of a target window's client area,
not the whole screen, and bins the result down to `target_size` for
downstream perception. Runs a background thread so the consumer never
blocks on grab().

See docs/ARCHITECTURE.md §2.1 and docs/PERFORMANCE.md §3.1.

CLI:
    python -m vision_control.capture.dxcam_roi --list-windows
    python -m vision_control.capture.dxcam_roi --probe   "GeForce NOW"
    python -m vision_control.capture.dxcam_roi --show    "GeForce NOW"
"""
from __future__ import annotations

import argparse
import gc
import sys
import threading
import time
from typing import Any

import numpy as np

from ..config import Roi
from .window_focus import (
    exclude_from_capture,
    find_hwnd_by_exact_title,
    find_window_by_title,
    get_client_rect_screen,
    get_monitor_rect_for_hwnd,
    list_visible_windows,
)


def _hide_cv2_window_from_capture(win_name: str) -> bool:
    """Best-effort: tell Windows to exclude the named cv2 window from dxcam.

    cv2 doesn't expose the underlying HWND, so we have to find it by title.
    Call this AFTER `cv2.namedWindow(win_name, ...)` (and ideally after
    one `cv2.imshow`+`waitKey(1)` so Windows has actually realized the
    HWND). Returns True if the affinity was applied successfully.
    """
    hwnd = find_hwnd_by_exact_title(win_name)
    if not hwnd:
        return False
    return exclude_from_capture(hwnd)

# ─── Suppress harmless dxcam/comtypes shutdown noise ────────────────────────
# dxcam 0.x + comtypes 1.4.x triggers "access violation in
# _compointer_base.__del__" when COM objects are reclaimed by the GC.
# It happens AFTER all frames are captured successfully; functionality is
# unaffected. Install an unraisablehook that filters out only THAT specific
# message and leaves every other unraisable exception visible.
def _install_comtypes_filter() -> None:
    original = sys.unraisablehook

    def _hook(args: Any) -> None:
        try:
            obj_repr = repr(args.object) if args.object is not None else ""
        except Exception:
            obj_repr = ""
        if (args.exc_type is OSError
                and "_compointer_base" in obj_repr
                and "access violation" in str(args.exc_value or "")):
            return  # swallow
        original(args)

    sys.unraisablehook = _hook


_install_comtypes_filter()


# ─── dxcam multi-monitor selection ──────────────────────────────────────────
#
# `dxcam.create()` with no args binds to the PRIMARY monitor. If the GFN
# window is on a secondary monitor, `cam.grab(region=...)` quietly returns
# None for every frame — hence "fps=0, all grey".
#
# We solve this by:
#   1. asking Win32 which monitor the GFN window is on, and
#   2. parsing `dxcam.output_info()` to find the matching dxcam (device, output)
#      pair plus its virtual-screen offset, then
#   3. translating the absolute screen rect into output-local coordinates
#      before calling cam.grab().

import re as _re

_DXCAM_OUTPUT_RE = _re.compile(
    r"Device\[(\d+)\][^\n]*?Output\[(\d+)\]"
    r"[^\n]*?Res:\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)"
    r"(?:[^\n]*?(?:Offset|Position)\s*:\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\))?",
    _re.IGNORECASE,
)


def _enumerate_dxcam_outputs() -> list[tuple[int, int, int, int, int, int]]:
    """Return [(device_idx, output_idx, ox, oy, w, h), ...] parsed from dxcam.

    Empty list if dxcam isn't importable or output_info parsing fails.
    """
    try:
        import dxcam  # type: ignore
    except ImportError:
        return []
    try:
        info_str = dxcam.output_info()
    except Exception:
        return []
    out: list[tuple[int, int, int, int, int, int]] = []
    for line in info_str.splitlines():
        m = _DXCAM_OUTPUT_RE.search(line)
        if not m:
            continue
        d  = int(m.group(1))
        o  = int(m.group(2))
        w  = int(m.group(3))
        h  = int(m.group(4))
        ox = int(m.group(5)) if m.group(5) is not None else 0
        oy = int(m.group(6)) if m.group(6) is not None else 0
        out.append((d, o, ox, oy, w, h))
    return out


def _select_output_for_window(hwnd: int,
                              rect_abs: tuple[int, int, int, int]
                              ) -> tuple[int, int, tuple[int, int]]:
    """Pick the best (device_idx, output_idx, (offset_x, offset_y)) for a window.

    Heuristic order:
      1. If Win32 gives the monitor rect and any dxcam output matches it
         exactly, use that.
      2. Otherwise the dxcam output whose virtual rect contains the window
         center.
      3. Otherwise primary (0, 0) at offset (0, 0).
    """
    outputs = _enumerate_dxcam_outputs()
    if not outputs:
        return 0, 0, (0, 0)

    mon = get_monitor_rect_for_hwnd(hwnd)
    if mon is not None:
        ml, mt, mr, mb = mon
        for d, o, ox, oy, w, h in outputs:
            if ox == ml and oy == mt and ox + w == mr and oy + h == mb:
                return d, o, (ox, oy)

    cx = (rect_abs[0] + rect_abs[2]) // 2
    cy = (rect_abs[1] + rect_abs[3]) // 2
    for d, o, ox, oy, w, h in outputs:
        if ox <= cx < ox + w and oy <= cy < oy + h:
            return d, o, (ox, oy)

    return 0, 0, (0, 0)


class RoiCapture:
    """Captures a sub-rectangle of a target window at up to target_fps.

    Lifecycle::

        cap = RoiCapture("GeForce NOW", Roi(), (384, 216), target_fps=60)
        cap.start()
        try:
            while ...:
                frame = cap.latest()       # BGR HxW or None
                ...
        finally:
            cap.stop()

    Frames returned from latest() are always at exactly `target_size`
    (width, height). The grab loop refreshes the source window rect every
    ~2 seconds, so if the user moves the GFN window the ROI follows.
    """

    def __init__(self,
                 window_title: str,
                 roi: Roi,
                 target_size: tuple[int, int] = (384, 216),
                 target_fps: int = 60) -> None:
        self.window_title = window_title
        self.roi          = roi
        self.target_size  = target_size           # (width, height)
        self.target_fps   = target_fps

        self._hwnd: int = 0
        self._region: tuple[int, int, int, int] | None = None  # (l,t,r,b) abs
        self._output_offset: tuple[int, int] = (0, 0)          # for output-local
        self._device_idx: int = 0
        self._output_idx: int = 0
        self._cam: Any | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
        self._frames_grabbed: int = 0
        self._frames_returned: int = 0
        self._last_region_check: float = 0.0

    # ─── lifecycle ──────────────────────────────────────────────────────────
    def start(self) -> None:
        """Find the window, open dxcam, spawn the grab thread."""
        if self._thread is not None:
            return  # already started

        match = find_window_by_title([self.window_title], exact=False)
        if match is None:
            raise RuntimeError(
                f"No visible window matching {self.window_title!r}. "
                f"Try `python -m vision_control.capture.dxcam_roi --list-windows`."
            )
        self._hwnd, found_title = match
        self._region = self._compute_region(self._hwnd)
        if self._region is None:
            raise RuntimeError(f"Could not query client rect of {found_title!r}")

        try:
            import dxcam  # type: ignore
        except ImportError as exc:
            raise RuntimeError("dxcam not installed — run install.bat") from exc

        # Pick the right (device, output) for this window — supports multi-monitor.
        d, o, off = _select_output_for_window(self._hwnd, self._region)
        self._device_idx, self._output_idx = d, o
        self._output_offset = off

        # output_color="BGR" → matches OpenCV expectation; saves a cvtColor.
        try:
            self._cam = dxcam.create(device_idx=d, output_idx=o, output_color="BGR")
        except Exception:
            # Some dxcam combos reject explicit indices; fall back to default
            # camera (primary monitor) and keep offset = (0, 0).
            try:
                self._cam = dxcam.create(output_color="BGR")
                self._output_offset = (0, 0)
                self._device_idx = 0
                self._output_idx = 0
            except Exception as exc:
                raise RuntimeError(f"dxcam.create() failed: {exc}") from exc

        # Diagnostic — surface the chosen output so multi-monitor surprises
        # are obvious from the log.
        print(f"[dxcam] device={self._device_idx} output={self._output_idx} "
              f"offset={self._output_offset}  region(abs)={self._region}")

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._grab_loop, name="RoiCapture", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        if self._cam is not None:
            try:
                # dxcam: call stop() to halt the capture loop.
                # Do NOT call release() — combined with comtypes 1.4.x it
                # triggers an access violation in DXCamera.__del__.
                # Letting the reference drop is sufficient.
                if hasattr(self._cam, "stop"):
                    self._cam.stop()
            except Exception:
                pass
            self._cam = None
            # Force COM teardown to happen here in controlled order,
            # not during interpreter shutdown (where the unraisable hook
            # is the only protection).
            gc.collect()

    def latest(self) -> np.ndarray | None:
        """Most recent BGR frame at target_size, or None if no frame yet."""
        with self._lock:
            if self._latest is None:
                return None
            self._frames_returned += 1
            return self._latest.copy()

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "frames_grabbed":  self._frames_grabbed,
            "frames_returned": self._frames_returned,
            "region":          self._region,
            "target_size":     self.target_size,
        }

    # ─── internals ──────────────────────────────────────────────────────────
    def _compute_region(self, hwnd: int) -> tuple[int, int, int, int] | None:
        """Return absolute screen rect (left, top, right, bottom) of the
        configured ROI inside the window's client area.

        The result is clipped to the monitor that contains the window — if
        the user has dragged GFN partially off-screen, we capture only the
        visible part rather than failing silently.
        """
        client = get_client_rect_screen(hwnd)
        if client is None:
            return None
        cl, ct, cr, cb = client
        w = cr - cl
        h = cb - ct
        x1 = cl + int(self.roi.left_pct   * w)
        x2 = cl + int(self.roi.right_pct  * w)
        y1 = ct + int(self.roi.top_pct    * h)
        y2 = ct + int(self.roi.bottom_pct * h)

        # ── Clip to monitor bounds ──────────────────────────────────────
        # On a single-monitor system with the window dragged past the right
        # edge, x2 ends up > monitor_right and dxcam returns None for every
        # frame. Clip so we capture the visible portion at least.
        mon = get_monitor_rect_for_hwnd(hwnd)
        if mon is not None:
            ml, mt, mr, mb = mon
            cx1, cy1, cx2, cy2 = x1, y1, x2, y2
            x1 = max(x1, ml); y1 = max(y1, mt)
            x2 = min(x2, mr); y2 = min(y2, mb)
            if (cx1, cy1, cx2, cy2) != (x1, y1, x2, y2) \
                    and not getattr(self, "_warned_clip", False):
                print(
                    f"[capture] WARN: GFN window extends past monitor edge.\n"
                    f"          Wanted ROI: ({cx1},{cy1},{cx2},{cy2})\n"
                    f"          Monitor:    ({ml},{mt},{mr},{mb})\n"
                    f"          Clipped to: ({x1},{y1},{x2},{y2})\n"
                    f"          → Drag the GFN window fully into view for the\n"
                    f"            best capture; we'll proceed with the visible\n"
                    f"            portion only."
                )
                self._warned_clip = True

        # dxcam requires even-aligned width/height on some GPUs.
        if (x2 - x1) % 2: x2 -= 1
        if (y2 - y1) % 2: y2 -= 1
        if x2 <= x1 or y2 <= y1:
            return None
        return (x1, y1, x2, y2)

    def _grab_loop(self) -> None:
        import cv2  # local import: keep startup fast on systems without cv2
        cam = self._cam
        assert cam is not None
        tw, th = self.target_size
        tick_dt = 1.0 / max(1, self.target_fps)
        next_tick = time.perf_counter()

        while not self._stop.is_set():
            # Periodically re-resolve the window rect so dragging the GFN
            # window doesn't leave the ROI on the desktop.
            now = time.perf_counter()
            if now - self._last_region_check > 2.0:
                new_region = self._compute_region(self._hwnd)
                if new_region is not None and new_region != self._region:
                    self._region = new_region
                self._last_region_check = now

            region = self._region
            if region is None:
                time.sleep(0.05)
                continue

            # dxcam.grab(region=...) expects coordinates relative to the
            # bound output's top-left, NOT virtual-screen coords. Translate.
            ox, oy = self._output_offset
            local_region = (region[0] - ox, region[1] - oy,
                            region[2] - ox, region[3] - oy)

            try:
                frame = cam.grab(region=local_region)
            except Exception:
                frame = None

            if frame is not None:
                self._frames_grabbed += 1
                if frame.shape[1] != tw or frame.shape[0] != th:
                    frame = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
                with self._lock:
                    self._latest = frame

            next_tick += tick_dt
            sleep_for = next_tick - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_tick = time.perf_counter()


# ════════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════════

def _cli_list() -> int:
    print(f"{'HWND':>10}   TITLE")
    print("-" * 70)
    for hwnd, title in list_visible_windows():
        print(f"{hwnd:>10}   {title}")
    return 0


def _cli_probe(window_title: str) -> int:
    match = find_window_by_title([window_title], exact=False)
    if match is None:
        print(f"No window matching {window_title!r}.")
        return 1
    hwnd, title = match
    print(f"Matched: {title!r}  (hwnd={hwnd})")
    rect = get_client_rect_screen(hwnd)
    print(f"Client rect (screen coords): {rect}")
    mon = get_monitor_rect_for_hwnd(hwnd)
    print(f"Monitor rect (Win32):        {mon}")
    roi = Roi()
    if rect is not None:
        cl, ct, cr, cb = rect
        w, h = cr - cl, cb - ct
        x1 = cl + int(roi.left_pct   * w)
        x2 = cl + int(roi.right_pct  * w)
        y1 = ct + int(roi.top_pct    * h)
        y2 = ct + int(roi.bottom_pct * h)
        print(f"Default ROI (Roi defaults):  ({x1}, {y1}, {x2}, {y2})  "
              f"= {x2-x1}×{y2-y1} px")
        d, o, off = _select_output_for_window(hwnd, (x1, y1, x2, y2))
        print(f"Selected dxcam output:       device={d} output={o} offset={off}")
        print(f"Output-local ROI for grab(): "
              f"({x1-off[0]}, {y1-off[1]}, {x2-off[0]}, {y2-off[1]})")
    return 0


def _safe_preview_pos(cap_region: tuple[int, int, int, int],
                      preview_size: tuple[int, int],
                      monitor: tuple[int, int, int, int]
                      ) -> tuple[int, int]:
    """Pick a screen corner for the preview window that does NOT overlap the
    capture region. Falls back to monitor top-left if every corner overlaps
    (which happens when capture covers the whole screen).
    """
    cl, ct, cr, cb = cap_region
    pw, ph = preview_size
    ml, mt, mr, mb = monitor
    margin = 8
    candidates = [
        (ml + margin,            mt + margin),              # top-left
        (mr - pw - margin,       mt + margin),              # top-right
        (ml + margin,            mb - ph - margin),         # bottom-left
        (mr - pw - margin,       mb - ph - margin),         # bottom-right
    ]
    for x, y in candidates:
        x2, y2 = x + pw, y + ph
        if x2 <= cl or x >= cr or y2 <= ct or y >= cb:
            return x, y
    return ml + margin, mt + margin


def _draw_perception_roi_overlay(frame: np.ndarray,
                                  roi: Roi,
                                  color: tuple[int, int, int] = (0, 220, 255),
                                  label: str = "perception ROI") -> None:
    """Draw a yellow rectangle on `frame` showing where perception will sample."""
    h, w = frame.shape[:2]
    x1 = int(roi.left_pct   * w)
    x2 = int(roi.right_pct  * w)
    y1 = int(roi.top_pct    * h)
    y2 = int(roi.bottom_pct * h)
    import cv2
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)
    cv2.putText(frame, label, (x1 + 4, y1 + 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)


def _cli_list_outputs() -> int:
    outputs = _enumerate_dxcam_outputs()
    if not outputs:
        print("dxcam reported no outputs (or output_info parsing failed).")
        return 1
    print(f"{'DEV':>4} {'OUT':>4}  {'OFFSET':>14}  {'RESOLUTION':>14}")
    print("-" * 50)
    for d, o, ox, oy, w, h in outputs:
        print(f"{d:>4} {o:>4}  ({ox:>5},{oy:>5})  {w:>5}x{h:<5}")
    return 0


def _cli_show(window_title: str, fps: int, duration: float,
              scale: float = 1.0) -> int:
    import cv2

    print(f"Opening capture for window matching {window_title!r}...")
    # --show captures the WHOLE client area so the user can see what's there.
    # The "perception ROI" (where road segmentation will actually look) is
    # drawn as a yellow rectangle overlay.
    full_roi   = Roi(left_pct=0.0, right_pct=1.0, top_pct=0.0, bottom_pct=1.0)
    perc_roi   = Roi()   # config defaults — same one perception modules use
    cap = RoiCapture(window_title, full_roi,
                     target_size=(640, 360), target_fps=fps)
    try:
        cap.start()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1
    print("Capture running. Window 'Vision_Control: RoiCapture'.")
    print("Press Q in the OpenCV window (or Ctrl-C) to quit.")

    win = "Vision_Control: RoiCapture"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    sw, sh = cap.target_size
    pw, ph = int(sw * scale), int(sh * scale)
    cv2.resizeWindow(win, pw, ph)
    # Position the preview window outside the capture region so it can't
    # show up in its own captures (the "infinite mirror" problem).
    mon = get_monitor_rect_for_hwnd(cap._hwnd) or (0, 0, 1920, 1080)
    if cap._region:
        px, py = _safe_preview_pos(cap._region, (pw, ph), mon)
        cv2.moveWindow(win, px, py)
    # Hide the cv2 preview from dxcam itself so it can't recursively
    # capture its own output. WDA_EXCLUDEFROMCAPTURE — Win10 v2004+.
    if _hide_cv2_window_from_capture(win):
        print("[capture] preview window hidden from screen capture (anti-mirror)")
    else:
        print("[capture] WARN: could not hide preview; move it out of the GFN area if you see a mirror")

    t0 = time.perf_counter()
    last_print = t0
    shown = 0
    try:
        while True:
            frame = cap.latest()
            if frame is not None:
                # Overlay simple HUD + perception ROI rectangle
                shown += 1
                hud = frame.copy()
                _draw_perception_roi_overlay(hud, perc_roi)
                cv2.putText(hud, f"{cap.stats['target_size'][0]}x"
                            f"{cap.stats['target_size'][1]}  "
                            f"grabbed={cap.stats['frames_grabbed']}  "
                            f"(yellow box = perception ROI)",
                            (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                            (255, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow(win, hud)
            now = time.perf_counter()
            if now - last_print > 1.0:
                fps_grabbed = cap.stats["frames_grabbed"] / (now - t0)
                print(f"  grabbed={cap.stats['frames_grabbed']:6d}  "
                      f"fps={fps_grabbed:5.1f}  "
                      f"region={cap.stats['region']}")
                last_print = now
            if duration > 0 and now - t0 > duration:
                break
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    except KeyboardInterrupt:
        pass
    finally:
        # Use BaseException so a second Ctrl-C during teardown can't
        # interrupt cleanup and leave a virtual gamepad / preview window
        # hanging around.
        try:
            cap.stop()
        except BaseException:
            pass
        try:
            cv2.destroyAllWindows()
        except BaseException:
            pass

    elapsed = time.perf_counter() - t0
    print(f"\nStopped. Ran {elapsed:.1f}s, grabbed {cap.stats['frames_grabbed']} "
          f"frames (avg {cap.stats['frames_grabbed'] / max(elapsed, 1e-9):.1f} fps).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vision_control.capture.dxcam_roi",
        description="ROI screen-capture demos.",
    )
    sub = parser.add_mutually_exclusive_group(required=True)
    sub.add_argument("--list-windows", action="store_true",
                     help="list every visible window title")
    sub.add_argument("--list-outputs", action="store_true",
                     help="list dxcam outputs (monitors) with their offsets")
    sub.add_argument("--probe", metavar="WINDOW",
                     help="report client rect, monitor + dxcam output for a window")
    sub.add_argument("--show", metavar="WINDOW",
                     help="live OpenCV preview of the ROI capture")
    parser.add_argument("--fps", type=int, default=60,
                        help="target FPS for --show (default 60)")
    parser.add_argument("--duration", type=float, default=0.0,
                        help="auto-quit after N seconds (--show only, 0=forever)")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="preview window size multiplier (1.0 = native 384x216)")
    args = parser.parse_args(argv)

    if args.list_windows:
        return _cli_list()
    if args.list_outputs:
        return _cli_list_outputs()
    if args.probe is not None:
        return _cli_probe(args.probe)
    return _cli_show(args.show, args.fps, args.duration, args.scale)


if __name__ == "__main__":
    sys.exit(main())
