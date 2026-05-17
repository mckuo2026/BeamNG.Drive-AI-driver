"""Target-window capture backend.

This backend uses Win32 PrintWindow against the target HWND, so overlapping
desktop windows are not part of the captured frame. It is slower and less
compatible than DXGI Desktop Duplication, but it is the right first choice
when the driver must see only the game client area.
"""
from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from typing import Any

import numpy as np

from ..config import Roi
from .window_focus import find_window_by_title, get_client_rect_screen

PW_CLIENTONLY = 0x00000001
PW_RENDERFULLCONTENT = 0x00000002

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
_user32.PrintWindow.restype = wintypes.BOOL


class WindowClientCapture:
    """Capture a target window's client area without desktop overlays."""

    backend_name = "window"

    def __init__(
        self,
        window_title: str,
        roi: Roi,
        target_size: tuple[int, int] = (384, 216),
        target_fps: int = 45,
    ) -> None:
        self.window_title = window_title
        self.roi = roi
        self.target_size = target_size
        self.target_fps = target_fps

        self._hwnd: int = 0
        self._title: str = ""
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
        self._frames_grabbed = 0
        self._frames_returned = 0
        self._last_error: str = ""

    def start(self) -> None:
        """Find the window, verify one frame, then spawn the capture thread."""
        if self._thread is not None:
            return
        match = find_window_by_title([self.window_title], exact=False)
        if match is None:
            raise RuntimeError(f"No visible window matching {self.window_title!r}.")
        self._hwnd, self._title = match
        probe = self._grab_once()
        if probe is None:
            detail = f": {self._last_error}" if self._last_error else ""
            raise RuntimeError(f"Window-only capture failed{detail}")
        with self._lock:
            self._latest = probe
            self._frames_grabbed = 1
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._grab_loop, name="WindowClientCapture", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None

    def latest(self) -> np.ndarray | None:
        """Most recent BGR frame at target_size, or None if no frame exists."""
        with self._lock:
            if self._latest is None:
                return None
            self._frames_returned += 1
            return self._latest.copy()

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "backend": self.backend_name,
            "frames_grabbed": self._frames_grabbed,
            "frames_returned": self._frames_returned,
            "target_size": self.target_size,
            "last_error": self._last_error,
            "window_title": self._title,
        }

    def _grab_loop(self) -> None:
        tick_dt = 1.0 / max(1, self.target_fps)
        next_tick = time.perf_counter()
        while not self._stop.is_set():
            frame = self._grab_once()
            if frame is not None:
                with self._lock:
                    self._latest = frame
                    self._frames_grabbed += 1
            next_tick += tick_dt
            sleep_for = next_tick - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_tick = time.perf_counter()

    def _grab_once(self) -> np.ndarray | None:
        try:
            import cv2
            import win32gui
            import win32ui
        except ImportError as exc:
            self._last_error = f"missing dependency: {exc}"
            return None

        client = get_client_rect_screen(self._hwnd)
        if client is None:
            self._last_error = "client rect unavailable"
            return None
        width = client[2] - client[0]
        height = client[3] - client[1]
        if width <= 0 or height <= 0:
            self._last_error = "client rect is empty"
            return None

        hwnd_dc = mfc_dc = save_dc = bitmap = None
        try:
            hwnd_dc = win32gui.GetWindowDC(self._hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            flags = PW_CLIENTONLY | PW_RENDERFULLCONTENT
            ok = bool(_user32.PrintWindow(self._hwnd, save_dc.GetSafeHdc(), flags))
            if not ok:
                self._last_error = "PrintWindow returned false"
                return None

            raw = bitmap.GetBitmapBits(True)
            bgra = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 4))
            bgr = bgra[:, :, :3].copy()
            cropped = self._crop_roi(bgr)
            tw, th = self.target_size
            if cropped.shape[1] != tw or cropped.shape[0] != th:
                cropped = cv2.resize(cropped, (tw, th), interpolation=cv2.INTER_AREA)
            self._last_error = ""
            return cropped
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            return None
        finally:
            if bitmap is not None:
                try:
                    win32gui.DeleteObject(bitmap.GetHandle())
                except Exception:
                    pass
            if save_dc is not None:
                try:
                    save_dc.DeleteDC()
                except Exception:
                    pass
            if mfc_dc is not None:
                try:
                    mfc_dc.DeleteDC()
                except Exception:
                    pass
            if hwnd_dc is not None:
                try:
                    win32gui.ReleaseDC(self._hwnd, hwnd_dc)
                except Exception:
                    pass

    def _crop_roi(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        x1 = max(0, min(w, int(self.roi.left_pct * w)))
        x2 = max(0, min(w, int(self.roi.right_pct * w)))
        y1 = max(0, min(h, int(self.roi.top_pct * h)))
        y2 = max(0, min(h, int(self.roi.bottom_pct * h)))
        if x2 <= x1 or y2 <= y1:
            return frame
        return frame[y1:y2, x1:x2]
