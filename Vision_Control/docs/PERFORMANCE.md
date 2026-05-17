# Performance

The v1.0 goal is responsive visual control on normal Windows laptops and cloud
gaming setups.

## Targets

- Capture: up to 60 Hz.
- UI preview: 5 Hz to keep Tk lightweight.
- Telemetry: 10 Hz.
- Control output: up to 60 Hz.
- Typical end-to-end response target: below 50 ms when using DXGI ROI and a
  stable preview.

## Practical Tradeoffs

`Window only` capture is overlay-resistant but may be slower or unsupported by
some accelerated clients. `DXGI ROI` is faster and more compatible, but it sees
the composed desktop.

The control panel exposes both paths because cloud clients vary. Users should
start with `Auto`, switch to `Window only` for overlay isolation, and switch to
`DXGI ROI` for maximum speed or compatibility.

## Optimization Rules

- Keep heavy image processing out of the UI thread.
- Keep preview refresh slower than capture.
- Prefer BGR frames to avoid unnecessary color conversion.
- Drop stale frames instead of queueing old visual information.
- Keep control output neutral when perception confidence is low.
