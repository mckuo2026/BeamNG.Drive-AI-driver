# Changelog

All notable changes to BeamNG and Horizon Driver are documented here.

## [0.7.2] - 2026-05-17

### Added

- `GameProfile.key_layout` records the keyboard binding each game expects
  (`beamng` → arrow keys, `horizon` / `generic` → WASD). The primary gamepad
  path ignores it (XInput is layout-independent); it exists so the keyboard
  control fallback can pick the right keys per game when it's wired up. The
  active layout is printed in the startup log.

## [0.7.1] - 2026-05-17

### Fixed

- Focus watchdog auto-paused as soon as the user enabled the Drive output
  checkbox, because the Vision_Control panel itself becomes foreground at
  that moment. Telemetry then read steer/throttle/brake = 0 even though the
  user expected driving to start. The watchdog now treats the panel's own
  HWND as a legitimate foreground (alongside the game window) — it only
  auto-pauses when focus truly leaves to a third, unrelated window.
- `engine.set_gui_hwnd()` lets the panel hand its top-level HWND to the
  engine on startup so the watchdog can recognize it.

## [0.7.0] - 2026-05-17

### Added

- Game profiles (`beamng`, `horizon`, `generic`) bundling per-title HUD-aware
  perception ROI, Pure Pursuit lookahead row, and steering gain. The Forza
  Horizon preset uses a thinner HUD crop and looks further ahead to suit the
  higher base speed.
- `GameProfile` dataclass and `GAME_PROFILES` registry in `config.py` —
  adding a new profile key automatically populates the panel combobox.
- Profile combobox in the control panel (alongside Capture and Language)
  with Chinese / English / Japanese labels. Selection persists to
  `config.json` via `Config.game_profile`.
- `--profile {beamng,horizon,generic}` flag on `python -m vision_control.main
  --headless` for scripted runs against different games.
- `pure_pursuit.compute()` accepts an optional `steer_gain` parameter so the
  engine can apply the active profile's gain without touching planning code.

### Changed

- `VisionEngine.start()` accepts `game_profile=` and stores the resolved
  `GameProfile` on the engine; the worker thread uses its perception ROI,
  lookahead, and steer gain throughout the main loop.

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
