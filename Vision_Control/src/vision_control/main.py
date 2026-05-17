"""Vision_Control entry point.

Usage:
    python -m vision_control.main              # launch the control panel (GUI)
    python -m vision_control.main --selftest   # verify install, print versions, exit
    python -m vision_control.main --headless --window "GeForce NOW" --capture auto
                                                # run engine without GUI (CI / scripting)
"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import Config


def selftest() -> int:
    """Print module availability so users can verify install."""
    print(f"BeamNG and Horizon Driver v{__version__} — selftest")
    print("-" * 50)

    checks: list[tuple[str, callable]] = [
        ("numpy",              lambda: __import__("numpy")),
        ("opencv-python",      lambda: __import__("cv2")),
        ("dxcam",              lambda: __import__("dxcam")),
        ("onnxruntime",        lambda: __import__("onnxruntime")),
        ("vgamepad",           lambda: __import__("vgamepad")),
        ("Pillow",             lambda: __import__("PIL")),
        ("pywin32 (win32api)", lambda: __import__("win32api")),
    ]

    failures = 0
    for name, importer in checks:
        try:
            importer()
            print(f"  OK    {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {name}: {exc}")
            failures += 1

    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        print(f"  INFO  ONNX providers: {providers}")
        if "DmlExecutionProvider" not in providers:
            print("  WARN  DirectML EP not found — perception will run on CPU.")
    except Exception:  # noqa: BLE001
        pass

    print("-" * 50)
    if failures:
        print(f"selftest FAILED ({failures} missing)")
        return 1
    print("selftest OK")
    return 0


def headless(window: str, capture: str = "auto") -> int:
    """Run the engine without GUI — useful for CI smoke and benchmarking."""
    import time
    from .engine import State, VisionEngine

    engine = VisionEngine()
    engine.start(window, capture_backend=capture)
    print(f"Headless engine started against window: {window!r}")
    print("Press Ctrl-C to stop.")
    try:
        while True:
            state, err = engine.get_state()
            t = engine.get_telemetry()
            print(f"  state={state.value:<8} fps={t.fps:5.1f} "
                  f"steer={t.steer:+0.2f} thr={t.throttle:0.2f} "
                  f"calib={'yes' if t.calibrated else f'{t.calib_seen}/{t.calib_need}'}")
            if state == State.ERROR:
                print(f"ERROR: {err}")
                return 1
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        time.sleep(0.5)
    return 0


def gui() -> int:
    """Launch the tkinter control panel."""
    try:
        from .ui.panel import ControlPanel
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: GUI failed to import: {exc}")
        print("Try: python -m vision_control.main --selftest")
        return 1

    cfg = Config.load()
    # First entry of window_candidates is a sensible default for the combobox.
    default_window = cfg.window_candidates[0] if cfg.window_candidates else "GeForce NOW"
    panel = ControlPanel(default_window=default_window, config=cfg)
    return panel.run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vision_control",
        description="BeamNG and Horizon Driver",
    )
    parser.add_argument("--selftest", action="store_true",
                        help="check installed dependencies and exit")
    parser.add_argument("--headless", action="store_true",
                        help="run engine without the GUI (requires --window)")
    parser.add_argument("--window", metavar="TITLE",
                        help="window title substring (default: GeForce NOW)")
    parser.add_argument("--capture", choices=["auto", "window", "dxcam"],
                        default="auto",
                        help="capture backend for --headless (default: auto)")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.headless:
        if not args.window:
            print("--headless requires --window TITLE")
            return 2
        return headless(args.window, args.capture)

    return gui()


if __name__ == "__main__":
    sys.exit(main())
