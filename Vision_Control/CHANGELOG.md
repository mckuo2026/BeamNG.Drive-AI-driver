# Changelog

All notable changes to BeamNG and Horizon Driver are documented here.

## [0.6.0] - 2026-05-17

### Added

- Focus watchdog in `VisionEngine`: when Drive output is enabled and the
  captured game window loses foreground focus, the engine auto-pauses
  within ~0.5 seconds. Does NOT auto-resume — the user must press
  Resume / the E hotkey, so the car cannot suddenly drive when the user
  alt-tabs back into the game window.
- 3-second grace period after `start()` before the watchdog fires, so
  clicking the game window after pressing Start doesn't trigger an
  immediate auto-pause.
- Watchdog is silent in preview-only mode (Drive switch off) — users can
  monitor telemetry from other windows freely.
- `0.6.0` includes the `0.5.0` capture hardening work: cached GDI resources,
  black-frame fallback to DXGI ROI, and `tools.preview --capture`.

## [0.5.0] - 2026-05-17

### Added

- Multilingual README and project summary.
- Multilingual control panel with English, Chinese, and Japanese UI options.
- Capture backend selector with `Auto`, `Window only`, and `DXGI ROI` modes.
- `WindowClientCapture`, a Win32 target-window capture backend that reads the
  selected game client area without including overlapping desktop windows.
- Capture backend telemetry in the control panel.
- Robust nested JSON config loading for newly added settings.

### Changed

- Version set to `0.5.0`; `1.0.0` is reserved for stable five-minute driving
  with focus watchdog, obstacle handling, and stuck recovery.
- README files now include English, Chinese, and Japanese sections.
- Default language changed to English.
- Default window candidates now include GeForce NOW, BeamNG.drive, Forza
  Horizon, and Xbox Cloud Gaming style titles.
- Runtime dependency comments are now English-only.

### Notes

- `Window only` capture depends on the target application's support for
  `PrintWindow`. Some cloud clients may return black frames; use `DXGI ROI`
  when speed or compatibility is more important than overlay isolation.
