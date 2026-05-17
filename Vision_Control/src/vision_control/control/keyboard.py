"""Keyboard fallback via SendInput + scancodes.

ONLY used when ViGEmBus / vgamepad is unavailable.
See docs/CONTROL_DESIGN.md §3 for the rationale and ctypes recipe.
"""
from __future__ import annotations

from ..planning import ControlTarget

# DirectInput scan codes
SC_W      = 0x11
SC_A      = 0x1E
SC_S      = 0x1F
SC_D      = 0x20
SC_UP     = 0xC8
SC_LEFT   = 0xCB
SC_RIGHT  = 0xCD
SC_DOWN   = 0xD0


class KeyboardBackend:
    """SendInput-based keyboard control, focus-aware."""

    def __init__(self, key_mode: str = "arrow", gfn_hwnd_provider=None) -> None:
        self.key_mode = key_mode
        self.gfn_hwnd_provider = gfn_hwnd_provider  # callable -> Hwnd | None
        self._held: set[int] = set()
        if key_mode == "wasd":
            self._FWD, self._BACK, self._LEFT, self._RIGHT = SC_W, SC_S, SC_A, SC_D
        else:
            self._FWD, self._BACK, self._LEFT, self._RIGHT = SC_UP, SC_DOWN, SC_LEFT, SC_RIGHT

    # ----- ControlBackend protocol -----
    def is_available(self) -> bool:
        # Only available on Windows; ctypes always present.
        import sys
        return sys.platform == "win32"

    def open(self) -> None:
        # M1 TODO: nothing to allocate, but verify SendInput accessible.
        raise NotImplementedError("KeyboardBackend.open — M1")

    def close(self) -> None:
        self.release_all()

    def set(self, target: ControlTarget) -> None:
        # M1 TODO:
        #   1. ensure_foreground(GFN). If not, release_all() and return.
        #   2. Event-style: compare desired with self._held → press/release diffs.
        #   3. Throttle: pressed iff target.throttle > 0.5 (binary at fallback layer).
        #   4. Brake: pressed iff target.brake > 0.5.
        #   5. Steer left iff target.steer < -0.15; right iff > +0.15.
        raise NotImplementedError("KeyboardBackend.set — M1")

    def release_all(self) -> None:
        # M1 TODO: send key-up for every scancode in self._held.
        raise NotImplementedError("KeyboardBackend.release_all — M1")
