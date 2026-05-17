# Problem Analysis

Earlier visual-driver prototypes had three major failure modes:

1. Color thresholds were too brittle for different roads, weather, camera
   angles, and streaming compression.
2. Keyboard injection was unreliable in cloud clients because focus and input
   routing changed during gameplay.
3. Desktop-region capture could include the driver UI or other windows placed
   over the game.

Vision_Control v1.0 addresses these with adaptive LAB road segmentation,
virtual gamepad output, capture-panel exclusion, and a target-window capture
backend.

## Remaining Risk

Some cloud clients do not render useful frames through Win32 `PrintWindow`.
When that happens, `Auto` falls back to DXGI ROI and the user can still run the
driver at high frame rate.
