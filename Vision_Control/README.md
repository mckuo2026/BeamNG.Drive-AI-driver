# BeamNG and Horizon Driver

BeamNG and Horizon Driver is a Windows visual driving assistant for BeamNG.drive,
Forza Horizon style racing games, cloud gaming windows, and local driving
simulators. It does not call a game API. Instead, it captures the visible game
client, detects the drivable road area, computes a lookahead target, and sends
analog driving input through a virtual Xbox controller.

## v1.0 Description

This release is built for low-latency cloud-computer use: GeForce NOW, Shadow
PC, Xbox Cloud Gaming, or any Windows game window with a stable driving camera.
The UI is English by default and includes Chinese and Japanese language
switching from the control panel.

The driver has two capture paths:

- `Window only`: captures the target window client area with Win32
  `PrintWindow`, so other desktop windows placed over the game are not included
  in the frame sent to perception. This is the preferred mode when overlay-free
  capture matters most.
- `DXGI ROI`: uses `dxcam` desktop duplication for maximum speed and high frame
  rate. This mode is faster, but it captures the composed desktop region, so
  visible third-party overlays may be present.
- `Auto`: tries `Window only` first and falls back to `DXGI ROI` if the cloud
  client refuses window capture.

The control panel itself is hidden from screen-capture APIs on supported
Windows builds, so the preview panel does not recursively appear in the game
capture.

## Features

- Multilingual Tk control panel: English, Chinese, Japanese.
- Window selector with refresh for GeForce NOW, BeamNG.drive, Forza Horizon,
  and other visible game windows.
- Capture backend selector: Auto, Window only, DXGI ROI.
- Live preview, telemetry, and log panel.
- Global `E` hotkey for pause/resume.
- Adaptive LAB road segmentation fallback, no model file required.
- Pure Pursuit style lookahead steering.
- Virtual Xbox 360 controller output through `vgamepad` and ViGEmBus.
- Safe drive-output switch: preview can run without sending controls.

## Requirements

- Windows 10 or Windows 11.
- Python 3.10 or newer.
- A cloud game client or local driving simulator window.
- ViGEmBus driver for virtual Xbox controller output:
  <https://github.com/ViGEm/ViGEmBus/releases>

Python dependencies are listed in [`requirements.txt`](requirements.txt).

## Install

```bat
cd Vision_Control
install.bat
```

The installer upgrades `pip`, installs runtime dependencies, installs this
package in editable mode, and runs a basic dependency check.

## Run

```bat
cd Vision_Control
launch.bat
```

Or run it directly:

```bat
python -m vision_control.main
```

Headless mode:

```bat
python -m vision_control.main --headless --window "GeForce NOW" --capture auto
```

Self-test:

```bat
python -m vision_control.main --selftest
```

## Recommended Cloud Setup

1. Open the cloud game client and start the driving game.
2. Use a third-person chase camera with a clear road view.
3. Open `launch.bat`.
4. Select the game window.
5. Keep capture mode on `Auto`; switch to `Window only` if an overlay appears
   over the game; switch to `DXGI ROI` if the cloud client returns black frames.
6. Press `Start` and wait for calibration to reach `ready`.
7. Enable `Drive output` only after the preview road mask looks stable.

## Safety Notes

BeamNG and Horizon Driver sends real controller input to Windows when drive
output is enabled. Keep the game in a safe test area while calibrating, and use the
global `E` hotkey or `Stop` button if the output is not behaving as expected.

Some games and cloud services may restrict automation. Use this project only
where you are allowed to run visual-assistance tools.

## Project Layout

```text
Vision_Control/
  src/vision_control/
    capture/        window-only and DXGI ROI capture backends
    perception/     road segmentation and optional model hooks
    planning/       drivable-area extraction and steering target
    control/        virtual gamepad and keyboard fallback code
    ui/             multilingual control panel
  tests/            focused geometry unit tests
  docs/             architecture and development notes
```

## License

MIT. See [`../LICENSE`](../LICENSE).
