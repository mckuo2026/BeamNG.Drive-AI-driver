# Progress

## Current Release: v0.6.0

`0.6.0` closes M2 by adding the focus watchdog. The package will hold at
`0.6.x` until obstacle handling, stuck recovery, and five-minute scenario
stability evidence are in place.

## Milestones

| Milestone | Status | Notes |
| --- | --- | --- |
| M0: Architecture and project split | Done | Separate visual-driver package with docs, setup scripts, and tests. |
| M1: Capture, perception fallback, control demos | Done | DXGI ROI capture, adaptive LAB road segmentation, and vgamepad control. |
| M2: GUI and engine integration | Done | Multilingual UI, telemetry, start/pause/stop, Auto capture with black-frame fallback, and focus watchdog. |
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
| ISSUE-018 | Fixed | Focus watchdog auto-pauses when Drive is on and the captured game window loses foreground (no auto-resume; 3 s grace period after Start). |

## Open Work

- Obstacle cone: detect non-road hazards in the forward driving corridor.
- Stuck recovery: use visual motion checks and controlled reverse/steer escape.
- ONNX model path: ship or document a lightweight road/obstacle segmentation model.
- Scenario evidence: record repeated five-minute cloud-driving runs before `1.0.0`.
