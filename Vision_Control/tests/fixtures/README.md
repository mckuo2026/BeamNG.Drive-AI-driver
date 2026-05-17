# Fixtures

Real GFN screenshots used to anchor perception + planning behaviour.
Each `.png` must have a matching `.json` describing the expected outcome.

`*.png` is **not** checked into git (see `.gitignore`); coordinate via:

- internal storage (OneDrive `Vision_Control/fixtures-shared/`), or
- a release-attached zip downloaded by a setup script (M2+).

`*.json` **is** checked in — it captures the expectations.

## JSON schema

```json
{
  "description": "Italy dirt road, sunny midday, third-person ETK800",
  "scenario_tags": ["italy", "dirt", "day", "tpv"],
  "expected_road_pixel_ratio": [0.18, 0.45],
  "expected_lookahead_x_pct":  [0.40, 0.60],
  "expected_steer":            [-0.20, 0.20],
  "expected_throttle":         [0.50, 1.00],
  "expected_brake":            [0.0, 0.10],
  "expected_brake_required":   false
}
```

## Suggested naming

```
<map>_<surface>_<situation>_<3-digit-seq>.png
italy_dirt_straight_001.png
italy_dirt_right_curve_002.png
west_coast_freeway_night_001.png
jungle_uphill_sharp_left_003.png
```
