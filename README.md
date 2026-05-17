# Vision_Control

Vision_Control is a Windows visual driving assistant for cloud racing games and
local driving simulators. It reads the game window, identifies the drivable
road area, plans a lookahead point, and sends smooth analog steering,
throttle, and brake output through a virtual Xbox controller.

The v1.0 work lives in [`Vision_Control/`](Vision_Control/).

## v1.0 Summary

- English-first project documentation.
- Multilingual control panel with English, Chinese, and Japanese UI options.
- Target-window capture mode that captures the game client area instead of
  the full desktop composition, reducing interference from windows placed over
  the game.
- High-refresh capture and control loop designed for GeForce NOW, Shadow PC,
  Xbox Cloud Gaming, and local simulator windows.
- Adaptive LAB road segmentation fallback that works without a shipped ONNX
  model.
- Pure Pursuit style steering target and virtual Xbox 360 controller output
  through `vgamepad` / ViGEmBus.

## Quick Start

```bat
cd Vision_Control
install.bat
launch.bat
```

For more details, see [`Vision_Control/README.md`](Vision_Control/README.md).
