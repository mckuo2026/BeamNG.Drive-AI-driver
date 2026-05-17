# Control Design

Vision_Control uses a virtual Xbox 360 controller as the primary output path.
Cloud clients such as GeForce NOW generally forward XInput-style gamepad input
more reliably than injected keyboard messages.

## Mapping

| Driver signal | Virtual controller channel |
| --- | --- |
| Steering | Left stick X axis |
| Throttle | Right trigger |
| Brake | Left trigger |

Values are normalized before output:

- Steering: `-1.0` left to `+1.0` right.
- Throttle: `0.0` to `1.0`.
- Brake: `0.0` to `1.0`.

## Smoothing

The gamepad backend applies:

- IIR steering smoothing to reduce perception jitter.
- Steering slew limiting to prevent sudden wheel snaps.
- Throttle slew limiting to avoid instant acceleration spikes.

## Safety

Controls are released on pause, stop, error, close, or process interrupt. Drive
output is opt-in; preview and calibration can run without sending any input to
the game.
