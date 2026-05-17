# Testing

## Automated Tests

Run:

```bat
pytest
```

Current unit tests cover geometry behavior for drivable-area extraction and
Pure Pursuit style steering output.

## Manual Smoke Tests

1. Run `python -m vision_control.main --selftest`.
2. Start the GUI with `launch.bat`.
3. Select a visible game or cloud-client window.
4. Try `Auto`, `Window only`, and `DXGI ROI` capture modes.
5. Verify that preview frames are live and telemetry updates.
6. Enable drive output only after the preview road mask is stable.

## Capture Checks

- `Window only` should not include overlapping desktop windows.
- `DXGI ROI` should reach the highest capture FPS.
- The control panel itself should not appear recursively in the captured frame
  on supported Windows builds.

## Control Checks

Use `python -m vision_control.control.gamepad --circle` to verify the virtual
controller path before driving.
