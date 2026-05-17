# Architecture

Vision_Control is split into five layers:

1. Capture reads the selected game window.
2. Perception converts frames into road and obstacle signals.
3. Planning extracts a drivable area and lookahead point.
4. Control maps the target into virtual gamepad input.
5. UI displays preview, telemetry, logs, language selection, and safety
   controls.

## Runtime Flow

```text
Game window
  -> capture backend
  -> adaptive road segmentation
  -> drivable-area extraction
  -> Pure Pursuit style steering target
  -> virtual Xbox controller
```

The engine runs the capture and control pipeline on a worker thread. Tk widgets
are touched only from the main UI thread. Cross-thread state is copied through
small locked snapshots so the preview can never block capture.

## Capture Backends

- `WindowClientCapture`: Win32 target-window capture. It is overlay-resistant
  because it asks the selected window to render its own client area.
- `RoiCapture`: `dxcam` DXGI desktop-duplication ROI capture. It is the fastest
  backend, but it sees the composed desktop.

`Auto` tries window capture first and falls back to DXGI ROI when needed.

## Data Contracts

- Frames are BGR `numpy.ndarray` images.
- Perception masks use stable class IDs from `vision_control.perception`.
- Planning returns `DrivableArea` and `ControlTarget` dataclasses.
- Control outputs normalized values: steer `-1..1`, throttle `0..1`, brake
  `0..1`.
