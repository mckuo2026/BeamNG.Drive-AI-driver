# Changelog

All notable changes to Vision_Control are documented here.

## [1.0.0] - 2026-05-17

### Added

- English-first v1.0 README and project summary.
- Multilingual control panel with English, Chinese, and Japanese UI options.
- Capture backend selector with `Auto`, `Window only`, and `DXGI ROI` modes.
- `WindowClientCapture`, a Win32 target-window capture backend that reads the
  selected game client area without including overlapping desktop windows.
- Capture backend telemetry in the control panel.
- Robust nested JSON config loading for newly added settings.

### Changed

- Version bumped to `1.0.0`.
- Default language changed to English.
- Default window candidates now include GeForce NOW, BeamNG.drive, Forza
  Horizon, and Xbox Cloud Gaming style titles.
- Runtime dependency comments are now English-only.

### Notes

- `Window only` capture depends on the target application's support for
  `PrintWindow`. Some cloud clients may return black frames; use `DXGI ROI`
  when speed or compatibility is more important than overlay isolation.
