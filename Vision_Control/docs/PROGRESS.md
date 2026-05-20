# Progress

## Current Release: v0.7.2

`0.7.2` is a game-profile refinement on top of the focus-watchdog fix:
profiles now record the keyboard layout expected by each game while the
primary control path remains virtual Xbox gamepad output. M3 still pending
(obstacle / stuck / CPU profile); package stays at `0.7.x` until five-minute
stability evidence is in place.

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
| ISSUE-019 | Fixed | Per-game tuning profiles (`beamng` / `horizon` / `generic`) bundle HUD-aware ROI, lookahead row, and steer gain. Selectable from GUI + `--profile` CLI flag; persisted in config.json. |
| ISSUE-020 | Fixed | Focus watchdog incorrectly auto-paused when the user enabled Drive output, because clicking the panel checkbox makes the panel foreground for a moment. The watchdog now allows the panel's own HWND as a valid foreground; it only pauses when focus leaves both the game and the panel. |

## Open Work

- Obstacle cone: detect non-road hazards in the forward driving corridor.
- Stuck recovery: use visual motion checks and controlled reverse/steer escape.
- ONNX model path: ship or document a lightweight road/obstacle segmentation model.
- Scenario evidence: record repeated five-minute cloud-driving runs before `1.0.0`.
