"""Control layer — virtual Xbox gamepad (primary) + SendInput keyboard (fallback).

See docs/CONTROL_DESIGN.md for why pynput is intentionally not used.
"""
from __future__ import annotations

from typing import Protocol

from ..planning import ControlTarget


class ControlBackend(Protocol):
    def is_available(self) -> bool: ...
    def open(self) -> None: ...
    def close(self) -> None: ...
    def set(self, target: ControlTarget) -> None: ...
    def release_all(self) -> None: ...
