"""Locate the GFN client window and manage foreground focus.

Win32-only. See docs/CONTROL_DESIGN.md §3.3 for the AttachThreadInput trick.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

Hwnd = int

# ─── Win32 bindings ─────────────────────────────────────────────────────────
user32   = ctypes.WinDLL("user32",   use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.SetWindowDisplayAffinity.restype  = wintypes.BOOL
user32.FindWindowW.argtypes              = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype               = wintypes.HWND

user32.GetWindowTextW.argtypes        = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype         = ctypes.c_int
user32.GetWindowTextLengthW.argtypes  = [wintypes.HWND]
user32.GetWindowTextLengthW.restype   = ctypes.c_int
user32.IsWindowVisible.argtypes       = [wintypes.HWND]
user32.IsWindowVisible.restype        = wintypes.BOOL
user32.IsIconic.argtypes              = [wintypes.HWND]
user32.IsIconic.restype               = wintypes.BOOL
user32.GetForegroundWindow.restype    = wintypes.HWND
user32.SetForegroundWindow.argtypes   = [wintypes.HWND]
user32.SetForegroundWindow.restype    = wintypes.BOOL
user32.BringWindowToTop.argtypes      = [wintypes.HWND]
user32.BringWindowToTop.restype       = wintypes.BOOL
user32.ShowWindow.argtypes            = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype             = wintypes.BOOL
user32.AttachThreadInput.argtypes     = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype      = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype  = wintypes.DWORD
user32.GetClientRect.argtypes         = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype          = wintypes.BOOL
user32.GetWindowRect.argtypes         = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype          = wintypes.BOOL
user32.ClientToScreen.argtypes        = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype         = wintypes.BOOL
kernel32.GetCurrentThreadId.restype   = wintypes.DWORD

SW_RESTORE                = 9
MONITOR_DEFAULTTONEAREST  = 2

# SetWindowDisplayAffinity flags (Win10 v2004 / build 19041 +)
WDA_NONE                  = 0x00000000
WDA_MONITOR               = 0x00000001
WDA_EXCLUDEFROMCAPTURE    = 0x00000011


# ─── DPI awareness ─────────────────────────────────────────────────────────
# Python 3.x on Windows defaults to DPI-unaware. With display scaling != 100%
# that means GetClientRect / ClientToScreen return *logical* pixels (smaller
# than physical), but dxcam captures in *physical* pixels — they don't match
# and our ROI ends up off the screen. Setting per-monitor v2 awareness fixes
# this by making every Win32 query return physical coordinates.
def _enable_dpi_awareness() -> None:
    # Try PROCESS_PER_MONITOR_DPI_AWARE_V2 first (best), fall back gracefully.
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        if shcore.SetProcessDpiAwareness(2) == 0:
            return
    except (OSError, AttributeError):
        pass
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


_enable_dpi_awareness()


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize",    wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork",    wintypes.RECT),
        ("dwFlags",   wintypes.DWORD),
    ]


user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.MonitorFromWindow.restype  = wintypes.HANDLE
user32.GetMonitorInfoW.argtypes   = [wintypes.HANDLE, ctypes.POINTER(_MONITORINFO)]
user32.GetMonitorInfoW.restype    = wintypes.BOOL


def _get_window_text(hwnd: Hwnd) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def list_visible_windows() -> list[tuple[Hwnd, str]]:
    """Return (hwnd, title) for every visible window with a non-empty title."""
    results: list[tuple[Hwnd, str]] = []

    @EnumWindowsProc
    def _cb(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if title:
            results.append((hwnd, title))
        return True

    user32.EnumWindows(_cb, 0)
    return results


def find_window_by_title(candidates: list[str],
                         exact: bool = False) -> tuple[Hwnd, str] | None:
    """Return (hwnd, title) of the first visible window matching any candidate.

    Matching rules:
      - case-insensitive
      - exact=False (default): substring match
      - exact=True: full equality

    Minimised windows are skipped. Candidates are tried in order.
    """
    wins = list_visible_windows()
    needles = [c.lower() for c in candidates]
    for needle in needles:
        for hwnd, title in wins:
            if user32.IsIconic(hwnd):
                continue
            t = title.lower()
            if (exact and t == needle) or (not exact and needle in t):
                return hwnd, title
    return None


def find_gfn_window(candidates: list[str] | None = None) -> tuple[Hwnd, str] | None:
    """Convenience: try the usual GFN / BeamNG window names."""
    if candidates is None:
        candidates = [
            "NVIDIA GeForce NOW",
            "GeForce NOW",
            "BeamNG.drive",
            "BeamNG.tech",
        ]
    return find_window_by_title(candidates, exact=False)


def is_foreground(hwnd: Hwnd) -> bool:
    return user32.GetForegroundWindow() == hwnd


def get_foreground_hwnd() -> Hwnd:
    """Return the HWND of whichever top-level window currently has the focus."""
    return int(user32.GetForegroundWindow() or 0)


def ensure_foreground(hwnd: Hwnd) -> bool:
    """Try hard to put hwnd in the foreground. Returns True iff it is afterwards.

    Uses the AttachThreadInput trick to bypass SetForegroundWindow restrictions
    introduced in Windows 10. Restores from minimised state if needed.
    """
    if not hwnd:
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    if is_foreground(hwnd):
        return True

    fg = user32.GetForegroundWindow()
    fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    target_tid = user32.GetWindowThreadProcessId(hwnd, None)
    self_tid = kernel32.GetCurrentThreadId()

    attached_self_to_target = bool(user32.AttachThreadInput(self_tid, target_tid, True))
    attached_self_to_fg     = bool(user32.AttachThreadInput(self_tid, fg_tid, True)) \
                              if fg_tid else False
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached_self_to_fg:
            user32.AttachThreadInput(self_tid, fg_tid, False)
        if attached_self_to_target:
            user32.AttachThreadInput(self_tid, target_tid, False)
    return is_foreground(hwnd)


def exclude_from_capture(hwnd: Hwnd) -> bool:
    """Hide a window from screen-capture APIs (dxcam, DDA, OBS WGC, etc).

    On Windows 10 v2004 (build 19041) or newer this sets
    `WDA_EXCLUDEFROMCAPTURE` on the window's display affinity — the
    window stays fully visible to the user but appears as a transparent
    hole to anything capturing the screen. That's exactly what we need
    for the Vision_Control GUI panel so dxcam stops seeing its own
    preview inside the next frame (infinite mirror).

    Returns True on success. Returns False on older Windows or when the
    HWND is invalid; callers can use the result to decide whether to
    fall back to repositioning.
    """
    if not hwnd:
        return False
    try:
        return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
    except Exception:
        return False


def find_hwnd_by_exact_title(title: str) -> Hwnd:
    """Win32 FindWindowW — exact title match. Returns 0 if not found.

    Useful for excluding cv2-named windows from capture, since cv2 has
    no API to expose the underlying HWND.
    """
    if not title:
        return 0
    try:
        return int(user32.FindWindowW(None, title) or 0)
    except Exception:
        return 0


def get_monitor_rect_for_hwnd(hwnd: Hwnd) -> tuple[int, int, int, int] | None:
    """Return the virtual-screen rect (l, t, r, b) of the monitor containing hwnd.

    Used to figure out which dxcam output captures the GFN window when the
    user has multiple displays.
    """
    if not hwnd:
        return None
    hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    if not hmon:
        return None
    mi = _MONITORINFO()
    mi.cbSize = ctypes.sizeof(_MONITORINFO)
    if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
        return None
    return (mi.rcMonitor.left,  mi.rcMonitor.top,
            mi.rcMonitor.right, mi.rcMonitor.bottom)


def get_client_rect_screen(hwnd: Hwnd) -> tuple[int, int, int, int] | None:
    """Return (left, top, right, bottom) of hwnd's CLIENT area in screen coords.

    Client area = what dxcam needs to grab, excluding title bar and borders.
    """
    if not hwnd:
        return None
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    pt = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        return None
    width  = rect.right  - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None
    return (pt.x, pt.y, pt.x + width, pt.y + height)


# ─── CLI helper: list windows ───────────────────────────────────────────────
def _cli_list() -> int:
    print(f"{'HWND':>10}   TITLE")
    print("-" * 70)
    for hwnd, title in list_visible_windows():
        flag = " (min)" if user32.IsIconic(hwnd) else ""
        print(f"{hwnd:>10}   {title}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_list())
