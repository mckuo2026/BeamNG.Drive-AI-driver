"""Virtual Xbox 360 gamepad via vgamepad / ViGEm. Primary control path.

See docs/CONTROL_DESIGN.md §2 for the mapping & rationale.

CLI demos (M1 — gamepad shipped, perception/capture stubs still pending):

    python -m vision_control.control.gamepad --circle [--duration 8.0]
        Sweep the left stick X axis as a sine wave so you can visually
        verify BeamNG sees the input. Throttle/brake stay at 0.

    python -m vision_control.control.gamepad --pulse
        Discrete events: hard left, center, hard right, center,
        full throttle 1 s, full brake 1 s.

    python -m vision_control.control.gamepad --hold STEER [THROTTLE BRAKE]
        Apply a fixed (steer, throttle, brake) and wait for Enter.
        Useful for one-axis-at-a-time debugging in BeamNG.
"""
from __future__ import annotations

import argparse
import math
import signal
import sys
import time
from typing import Any

from ..planning import ControlTarget


class GamepadBackend:
    """Analog steer/throttle/brake on a virtual Xbox 360 controller.

    Lifecycle:
        backend = GamepadBackend()
        if not backend.is_available():
            ...
        backend.open()                          # connects ViGEm device
        try:
            backend.set(ControlTarget(...))     # call from your control loop
        finally:
            backend.close()                     # always release

    `set()` applies smoothing + slew-rate limiting (see docs/CONTROL_DESIGN.md
    §2.4). For unit tests and demos that need raw deterministic values, use
    `set_raw()` instead.
    """

    def __init__(self,
                 steer_smoothing: float = 0.85,
                 throttle_slew:   float = 0.10,
                 steer_slew:      float = 0.12) -> None:
        # steer_smoothing  — IIR low-pass coefficient on the steer target.
        #                    At ~60 Hz, 0.85 gives a ~110 ms time constant —
        #                    strong enough to kill per-frame perception jitter
        #                    without feeling laggy.
        # throttle_slew    — per-tick max change in throttle (0..1).
        # steer_slew       — per-tick max change in steer  (−1..1). Hard cap
        #                    on top of the IIR; protects against big target
        #                    jumps when perception suddenly snaps.
        self.steer_smoothing = steer_smoothing
        self.throttle_slew   = throttle_slew
        self.steer_slew      = steer_slew
        self._pad:      Any | None = None
        self._steer:    float = 0.0
        self._throttle: float = 0.0

    # ─── ControlBackend protocol ────────────────────────────────────────────
    def is_available(self) -> bool:
        """True if the vgamepad module imports. Does NOT prove ViGEmBus is loaded;
        `open()` is what surfaces driver-level failures."""
        try:
            import vgamepad  # noqa: F401
        except ImportError:
            return False
        return True

    def open(self) -> None:
        """Allocate the virtual controller. Raises RuntimeError if the ViGEmBus
        driver is missing or unhealthy — install from
        https://github.com/ViGEm/ViGEmBus/releases."""
        try:
            import vgamepad as vg
        except ImportError as exc:
            raise RuntimeError(
                "vgamepad not installed — run install.bat or "
                "`pip install vgamepad`."
            ) from exc

        try:
            self._pad = vg.VX360Gamepad()
        except Exception as exc:  # vgamepad raises various OSError flavours
            raise RuntimeError(
                "Failed to allocate virtual Xbox 360 controller. The most "
                "likely cause is that the ViGEmBus driver is not installed. "
                "Download it from "
                "https://github.com/ViGEm/ViGEmBus/releases and run the .msi."
            ) from exc

        # Send an initial neutral state so the OS sees the device immediately.
        self._pad.reset()
        self._pad.update()
        self._steer    = 0.0
        self._throttle = 0.0

    def close(self) -> None:
        if self._pad is not None:
            try:
                self.release_all()
            except Exception:  # noqa: BLE001
                pass
            # Letting it go out of scope closes the ViGEm connection.
            self._pad = None

    def set(self, target: ControlTarget) -> None:
        """Apply a control target with smoothing + throttle slew limiting."""
        if self._pad is None:
            raise RuntimeError("GamepadBackend.set() called before open()")

        # IIR low-pass on steer to absorb perception jitter.
        a = self.steer_smoothing
        smoothed_target = a * self._steer + (1.0 - a) * float(target.steer)

        # Hard slew-rate cap on top of the IIR — bounds the per-tick
        # change so even a wild perception spike can't yank the wheel.
        delta = smoothed_target - self._steer
        if delta >  self.steer_slew: delta =  self.steer_slew
        if delta < -self.steer_slew: delta = -self.steer_slew
        self._steer = max(-1.0, min(1.0, self._steer + delta))

        # Slew-rate limit on throttle so we don't snap from 0→1 between ticks.
        delta = float(target.throttle) - self._throttle
        delta = max(-self.throttle_slew, min(self.throttle_slew, delta))
        self._throttle = max(0.0, min(1.0, self._throttle + delta))

        brake = max(0.0, min(1.0, float(target.brake)))

        self._pad.left_joystick_float(x_value_float=self._steer, y_value_float=0.0)
        self._pad.right_trigger_float(value_float=self._throttle)
        self._pad.left_trigger_float(value_float=brake)
        self._pad.update()

    def set_raw(self, steer: float, throttle: float, brake: float) -> None:
        """Bypass smoothing/slew — values are written verbatim. For tests/demos."""
        if self._pad is None:
            raise RuntimeError("GamepadBackend.set_raw() called before open()")

        self._steer    = max(-1.0, min(1.0, float(steer)))
        self._throttle = max( 0.0, min(1.0, float(throttle)))
        b              = max( 0.0, min(1.0, float(brake)))

        self._pad.left_joystick_float(x_value_float=self._steer, y_value_float=0.0)
        self._pad.right_trigger_float(value_float=self._throttle)
        self._pad.left_trigger_float(value_float=b)
        self._pad.update()

    def release_all(self) -> None:
        """Zero every axis/trigger and push the update."""
        if self._pad is None:
            return
        self._pad.reset()
        self._pad.update()
        self._steer    = 0.0
        self._throttle = 0.0


# ════════════════════════════════════════════════════════════════════════════
#  CLI demos
# ════════════════════════════════════════════════════════════════════════════

def _print_preamble() -> None:
    print("Vision_Control — virtual Xbox 360 controller demo")
    print("-" * 60)
    print("Setup checklist:")
    print("  [ ] ViGEmBus driver installed")
    print("      (https://github.com/ViGEm/ViGEmBus/releases)")
    print("  [ ] BeamNG.drive open (locally or via GeForce NOW)")
    print("  [ ] A vehicle spawned, free-cam or 3rd-person view")
    print("  [ ] In BeamNG's input options, ensure an Xbox 360 controller")
    print("      is enabled (Settings ▸ Controls ▸ Bindings)")
    print()
    print("Note: gamepad input is GLOBAL — this cmd window does NOT need focus.")
    print("      You can Alt-Tab into BeamNG and still see the wheel move.")
    print("-" * 60)


def _open_or_die() -> GamepadBackend:
    backend = GamepadBackend()
    if not backend.is_available():
        print("\nERROR: vgamepad import failed.\n"
              "Run install.bat from the Vision_Control folder.\n")
        sys.exit(1)
    try:
        backend.open()
    except RuntimeError as exc:
        print(f"\nERROR: {exc}\n")
        sys.exit(1)
    return backend


def _install_signal_handlers(backend: GamepadBackend) -> None:
    """Make sure Ctrl-C still releases the virtual controller."""
    def _cleanup(*_: Any) -> None:
        try:
            backend.release_all()
            backend.close()
        finally:
            sys.exit(130)
    signal.signal(signal.SIGINT, _cleanup)
    try:
        signal.signal(signal.SIGTERM, _cleanup)
    except (AttributeError, ValueError):
        pass  # Windows / non-main thread


def _render_bar(steer: float, width: int = 41) -> str:
    """ASCII steer bar — center marker '|' and current position '#'."""
    bar = ["-"] * width
    mid = width // 2
    bar[mid] = "|"
    pos = max(0, min(width - 1, int(round(mid + steer * mid))))
    bar[pos] = "#"
    return "".join(bar)


def _demo_circle(duration_s: float = 8.0, period_s: float = 4.0,
                 rate_hz: int = 60) -> int:
    _print_preamble()
    print(f"\nDemo: sine sweep, duration={duration_s:.1f}s, period={period_s:.1f}s\n")

    backend = _open_or_die()
    _install_signal_handlers(backend)
    try:
        t0 = time.perf_counter()
        tick_dt = 1.0 / rate_hz
        next_tick = t0
        last_print = 0.0
        while True:
            now = time.perf_counter()
            elapsed = now - t0
            if elapsed >= duration_s:
                break
            steer = math.sin((elapsed / period_s) * 2.0 * math.pi)
            backend.set_raw(steer=steer, throttle=0.0, brake=0.0)
            if now - last_print >= 0.20:
                print(f"  t={elapsed:5.2f}s  steer={steer:+0.2f}  "
                      f"[{_render_bar(steer)}]")
                last_print = now
            next_tick += tick_dt
            sleep_for = next_tick - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_tick = time.perf_counter()  # we fell behind; resync
        print("\n  steer=+0.00  [" + _render_bar(0.0) + "]  (release)")
    finally:
        backend.release_all()
        backend.close()
    print("\nDone. If the BeamNG wheel moved L↔R like a pendulum, M1-control PASSES.")
    return 0


def _demo_pulse() -> int:
    _print_preamble()
    print("\nDemo: discrete pulses (left, right, throttle, brake)\n")

    events: list[tuple[str, float, float, float, float]] = [
        ("hold LEFT  (steer = -1.0)", -1.0, 0.0, 0.0, 1.5),
        ("center     (steer =  0.0)",  0.0, 0.0, 0.0, 0.5),
        ("hold RIGHT (steer = +1.0)",  1.0, 0.0, 0.0, 1.5),
        ("center     (steer =  0.0)",  0.0, 0.0, 0.0, 0.5),
        ("full THROTTLE             ",  0.0, 1.0, 0.0, 1.0),
        ("release throttle          ",  0.0, 0.0, 0.0, 0.3),
        ("full BRAKE                ",  0.0, 0.0, 1.0, 1.0),
        ("release brake             ",  0.0, 0.0, 0.0, 0.3),
    ]

    backend = _open_or_die()
    _install_signal_handlers(backend)
    try:
        for label, s, t, b, dur in events:
            print(f"  [{dur:.1f}s] {label}   "
                  f"steer={s:+0.2f}  throttle={t:+0.2f}  brake={b:+0.2f}")
            t0 = time.perf_counter()
            tick_dt = 1.0 / 60
            next_tick = t0
            while time.perf_counter() - t0 < dur:
                backend.set_raw(steer=s, throttle=t, brake=b)
                next_tick += tick_dt
                sleep_for = next_tick - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
    finally:
        backend.release_all()
        backend.close()
    print("\nDone. You should have seen:")
    print("  * the wheel snap all the way LEFT,")
    print("  * back to center, all the way RIGHT, back to center,")
    print("  * the throttle pedal floor for 1s,")
    print("  * the brake pedal floor for 1s.")
    print("If all four happened, M1-control PASSES.")
    return 0


def _demo_hold(steer: float, throttle: float, brake: float) -> int:
    _print_preamble()
    print(f"\nDemo: HOLD steer={steer:+0.2f}, throttle={throttle:+0.2f}, "
          f"brake={brake:+0.2f}")
    print("Will keep applying these values until you press Enter.\n")

    backend = _open_or_die()
    _install_signal_handlers(backend)
    try:
        import threading
        stop_evt = threading.Event()

        def _hold_loop() -> None:
            while not stop_evt.is_set():
                backend.set_raw(steer=steer, throttle=throttle, brake=brake)
                time.sleep(1.0 / 60)

        t = threading.Thread(target=_hold_loop, daemon=True)
        t.start()
        input("Press Enter to release and exit... ")
        stop_evt.set()
        t.join(timeout=1.0)
    finally:
        backend.release_all()
        backend.close()
    print("Released.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vision_control.control.gamepad",
        description="Virtual Xbox 360 controller demos for Vision_Control.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--circle", action="store_true",
                      help="sweep steering as a sine wave (default)")
    mode.add_argument("--pulse",  action="store_true",
                      help="discrete left/right/throttle/brake events")
    mode.add_argument("--hold", nargs="+", type=float, metavar="VAL",
                      help="hold a fixed value: --hold STEER [THROTTLE BRAKE]")
    parser.add_argument("--duration", type=float, default=8.0,
                        help="seconds for --circle (default 8.0)")
    parser.add_argument("--period",   type=float, default=4.0,
                        help="seconds per full sine cycle for --circle (default 4.0)")
    args = parser.parse_args(argv)

    if args.pulse:
        return _demo_pulse()
    if args.hold is not None:
        s = args.hold[0]
        t = args.hold[1] if len(args.hold) > 1 else 0.0
        b = args.hold[2] if len(args.hold) > 2 else 0.0
        return _demo_hold(s, t, b)
    # default
    return _demo_circle(args.duration, args.period)


if __name__ == "__main__":
    sys.exit(main())
