"""Vision_Control configuration: dataclasses plus JSON load/save."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"


@dataclass
class Roi:
    # Defaults tuned for BeamNG.drive in 16:9 third-person view:
    #   left/right 0.10/0.90 — drops corner garnish + outside-mirror edges
    #   top    0.35          — drops sky / distant buildings
    #   bottom 0.78          — drops BeamNG HUD (speedometer + tachometer
    #                          dials, gear indicator) and the player car's
    #                          trunk in 3rd person. Was 0.85 — too loose,
    #                          let the gauges leak into the road class.
    left_pct:   float = 0.10
    right_pct:  float = 0.90
    top_pct:    float = 0.35
    bottom_pct: float = 0.78


@dataclass
class CaptureCfg:
    target_size: tuple[int, int] = (384, 216)
    roi:         Roi = field(default_factory=Roi)
    target_fps:  int = 60
    backend:     str = "auto"  # "auto" | "window" | "dxcam"


@dataclass
class PerceptionCfg:
    model_path: str = "models/ddrnet_slim_4class.onnx"
    providers:  list[str] = field(default_factory=lambda: [
        "DmlExecutionProvider", "CPUExecutionProvider"])
    fps_cap:    int = 30
    use_depth:  bool = False


@dataclass
class PlanningCfg:
    lookahead_pct:      float = 0.55
    brake_distance_pct: float = 0.30
    slow_distance_pct:  float = 0.55


@dataclass
class ControlCfg:
    backend:                str  = "gamepad"  # "gamepad" | "keyboard"
    steer_smoothing:        float = 0.65
    throttle_slew_per_tick: float = 0.10
    max_throttle:           float = 1.0


@dataclass
class UICfg:
    preview_hz:    int  = 5
    always_on_top: bool = True


@dataclass
class GameProfile:
    """Per-game tuning bundle: HUD-aware ROI + steering / lookahead overrides.

    Each driving game lays out its HUD differently and runs at different
    average speeds. A profile bundles the three knobs we tune per game so
    the engine can switch presets with a single name.
    """
    name:           str
    perception_roi: Roi          # crop fed into the segmenter
    lookahead_pct:  float = 0.40 # vertical sampling row in the road mask
    steer_gain:     float = 0.80 # multiplied into Pure Pursuit's sin(α)
    # Keyboard layout this game expects, used ONLY by the keyboard control
    # fallback (control/keyboard.py). The primary gamepad path ignores it
    # because XInput is layout-independent. BeamNG.drive defaults to the
    # arrow keys; Forza Horizon defaults to WASD.
    key_layout:     str = "arrow"  # "arrow" | "wasd"


# Profile registry. Add a new key here to support another game without
# touching engine code; the panel picks them up automatically.
GAME_PROFILES: dict[str, GameProfile] = {
    "beamng":  GameProfile(
        name="beamng",
        # Bottom 0.78 cuts BeamNG's round speedometer + tachometer; the
        # player car's trunk in 3rd person also sits below this line.
        perception_roi=Roi(left_pct=0.10, right_pct=0.90,
                           top_pct=0.35,  bottom_pct=0.78),
        lookahead_pct=0.40,
        steer_gain=0.80,
        key_layout="arrow",   # BeamNG.drive default keyboard binding
    ),
    "horizon": GameProfile(
        name="horizon",
        # Forza Horizon's HUD is a thin strip across the bottom — we can
        # keep more of the lower frame. Higher base speed → look further
        # ahead (smaller lookahead_pct = higher in the image).
        perception_roi=Roi(left_pct=0.08, right_pct=0.92,
                           top_pct=0.30,  bottom_pct=0.83),
        lookahead_pct=0.32,
        steer_gain=0.90,
        key_layout="wasd",    # Forza Horizon default keyboard binding
    ),
    "generic": GameProfile(
        name="generic",
        # Middle-ground defaults: works for unfamiliar cloud games where
        # we can't predict the HUD layout in advance.
        perception_roi=Roi(left_pct=0.10, right_pct=0.90,
                           top_pct=0.35,  bottom_pct=0.82),
        lookahead_pct=0.38,
        steer_gain=0.80,
        key_layout="wasd",    # WASD is the more common PC racing default
    ),
}


@dataclass
class Config:
    lang:               str = "en"
    game_profile:       str = "beamng"   # key into GAME_PROFILES
    window_candidates:  list[str] = field(default_factory=lambda: [
        "NVIDIA GeForce NOW", "GeForce NOW", "BeamNG.drive",
        "Forza Horizon", "Xbox Cloud Gaming"])
    capture:    CaptureCfg    = field(default_factory=CaptureCfg)
    perception: PerceptionCfg = field(default_factory=PerceptionCfg)
    planning:   PlanningCfg   = field(default_factory=PlanningCfg)
    control:    ControlCfg    = field(default_factory=ControlCfg)
    ui:         UICfg         = field(default_factory=UICfg)

    # ----- persistence -----
    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        if not path.exists():
            cfg = cls()
            cfg.save(path)
            return cfg
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return cls()
        # Keep user values while filling newly added keys with defaults.
        cfg = cls()
        if isinstance(raw, dict):
            _merge_dataclass(cfg, raw)
        return cfg

    def save(self, path: Path = CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _merge_dataclass(target: Any, raw: dict[str, Any]) -> None:
    """Recursively merge a JSON dict into a dataclass instance."""
    if not is_dataclass(target):
        return
    for f in fields(target):
        if f.name not in raw:
            continue
        current = getattr(target, f.name)
        value = raw[f.name]
        if is_dataclass(current) and isinstance(value, dict):
            _merge_dataclass(current, value)
        elif isinstance(current, tuple) and isinstance(value, list):
            setattr(target, f.name, tuple(value))
        else:
            setattr(target, f.name, value)
