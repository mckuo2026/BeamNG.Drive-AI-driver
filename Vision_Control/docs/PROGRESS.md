# Progress

## Current Release: v0.5.0

This release is a capable visual-driver foundation, not a final stability
release. The package is intentionally versioned as `0.5.0` until the focus
watchdog, obstacle handling, stuck recovery, and five-minute scenario stability
are proven.

## Milestones

| Milestone | Status | Notes |
| --- | --- | --- |
| M0: Architecture and project split | Done | Separate visual-driver package with docs, setup scripts, and tests. |
| M1: Capture, perception fallback, control demos | Done | DXGI ROI capture, adaptive LAB road segmentation, and vgamepad control. |
| M2: GUI and engine integration | Partial | Multilingual UI, telemetry, start/pause/stop, and Auto capture mode are implemented. Focus watchdog remains open. |
| M3: Robust driving behavior | Pending | Obstacle cone, depth, stuck detection, and recovery are not complete. |
| M4: 1.0 hardening | Pending | Requires stable five-minute driving and release-quality scenario evidence. |

## Issue History

| ID | Status | Summary |
| --- | --- | --- |
| ISSUE-005 | Fixed | Adaptive LAB calibration no longer prefers the player car over the road cluster. |
| ISSUE-006 | Fixed | Preview captures the full game client while drawing the perception ROI. |
| ISSUE-007 | Fixed | Preview windows are moved away from the capture area to avoid recursive mirrors. |
| ISSUE-008 | Fixed | Cleanup tolerates repeated Ctrl-C without leaving preview/gamepad resources active. |
| ISSUE-011 | Fixed | UI and preview windows use capture exclusion where Windows supports it. |
| ISSUE-012 | Fixed | `WindowClientCapture` adds target-window capture to avoid desktop overlay contamination. |
| ISSUE-013 | Fixed | UI strings use English, Chinese, and Japanese with English fallback. |
| ISSUE-014 | Fixed | Auto capture mode falls back from window capture to DXGI ROI when startup fails. |
| ISSUE-015 | Fixed | `WindowClientCapture` reuses GDI DC/bitmap resources instead of reallocating every frame. |
| ISSUE-016 | Fixed | Auto capture mode falls back to DXGI ROI after repeated black `PrintWindow` frames. |
| ISSUE-017 | Fixed | `tools.preview` accepts `--capture auto|window|dxcam` to match the GUI/headless path. |

## Open Work

- Focus watchdog: pause or neutralize output when the cloud game window loses focus.
- Obstacle cone: detect non-road hazards in the forward driving corridor.
- Stuck recovery: use visual motion checks and controlled reverse/steer escape.
- ONNX model path: ship or document a lightweight road/obstacle segmentation model.
- Scenario evidence: record repeated five-minute cloud-driving runs before `1.0.0`.
