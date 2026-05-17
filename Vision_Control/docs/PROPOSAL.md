# Proposal

Vision_Control should behave like a small, practical driver panel rather than
a research demo. The v1.0 design favors fast setup, clear safety controls, and
good cloud-client compatibility.

## Proposed Pipeline

```text
Window capture -> road segmentation -> lookahead planning -> gamepad output
```

## Design Priorities

- Work without a local game API.
- Prefer target-window frames when overlays must be ignored.
- Provide a fast DXGI path when the cloud client blocks window capture.
- Keep drive output disabled until the user explicitly enables it.
- Keep the UI multilingual but English-first for repository documentation.

## Future Work

- Ship a small ONNX road/obstacle segmentation model.
- Add replay fixtures from several games and streaming services.
- Add automatic ROI calibration.
- Add better stuck detection and recovery.
