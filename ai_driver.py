#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeamNG.drive AI 自动驾驶员 / BeamNG.drive AI Auto Driver
版本 / Version: 1.1

功能 / Features:
  - 连接 BeamNG.drive 并启动地图 / 生成车辆
  - 使用 BeamNG 内置 AI 实现全图自动巡路驾驶
  - 实时显示车速、状态
  - 支持暂停 / 恢复 / 急停（E 键全局热键）
  - 车辆卡死自动 & 手动恢复（在原地上空落下）
  - 损坏自动停车 + 双闪灯
  - 圆角按钮 + 悬停效果
  - 中 / 英文界面切换
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import json
import os
import datetime

# ──────────────────────────────────────────────
# 依赖检查 / Dependency check
# ──────────────────────────────────────────────
try:
    from beamngpy import BeamNGpy, Scenario, Vehicle
    from beamngpy.sensors import Electrics
    try:
        from beamngpy.sensors import Damage as DamageSensor
    except ImportError:
        DamageSensor = None
    BEAMNG_AVAILABLE = True
except ImportError:
    BEAMNG_AVAILABLE = False
    DamageSensor = None

try:
    from pynput import keyboard as pynput_kb
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

# ──────────────────────────────────────────────
# 各地图安全出生点坐标（避免默认(0,0,0)生成在海里）
# Safe spawn coordinates per map
# ──────────────────────────────────────────────
MAP_SPAWN = {
    "italy":               (-340.0,  133.0, 148.0),
    "west_coast_usa":      ( 375.0, -183.0, 125.0),
    "east_coast_usa":      ( 683.0,   57.0,  30.0),
    "gridmap_v2":          (   0.0,    0.0,   0.2),
    "smallgrid":           (   0.0,    0.0,   0.2),
    "jungle_rock_island":  (  -8.0,   43.0, 116.0),
}
MAP_SPAWN_DEFAULT = (0.0, 0.0, 100.0)

# ──────────────────────────────────────────────
# 多语言字典 / i18n strings
# ──────────────────────────────────────────────
LANG = {
    "zh": {
        "title":              "🚗  BeamNG  AI  自动驾驶员",
        "lang_label":         "语言:",
        "status_idle":        "未连接",
        "status_connecting":  "启动中……",
        "status_driving":     "AI 驾驶中",
        "status_paused":      "已暂停",
        "speed_na":           "车速: --",
        "speed_fmt":          "车速: {speed:.1f} km/h",
        "decelerating":       "减速中 {speed:.0f} km/h…",
        "settings":           " ⚙  游戏设置 ",
        "path_label":         "BeamNG.drive 安装路径:",
        "browse":             " 浏览 ",
        "map_label":          "地图:",
        "vehicle_label":      "车辆:",
        "speed_slider":       "目标速度:",
        "controls":           " ▶  控制 ",
        "launch":             "🚀  启动游戏并开始自动驾驶",
        "pause":              "⏸  暂停",
        "resume":             "▶  继续驾驶",
        "recover":            "🔄 恢复车辆",
        "stop":               "⏹  停止",
        "always_on_top":      "窗口始终置顶",
        "log_title":          " 📋  日志 ",
        "quit":               "✕  退出程序",
        # 对话框
        "msg_no_path_title":  "需要设置路径",
        "msg_no_path":        (
            "请先填写或浏览选择 BeamNG.drive 的安装路径！\n\n"
            "常见路径:\n"
            "  C:\\Program Files (x86)\\Steam\\steamapps\\common\\BeamNG.drive\n"
            "  D:\\SteamLibrary\\steamapps\\common\\BeamNG.drive"
        ),
        "msg_bad_path_title": "路径无效",
        "msg_bad_path":       "找不到文件夹：\n{path}\n\n请重新选择。",
        "msg_no_beamng_title":"缺少依赖",
        "msg_no_beamng":      "未安装 beamngpy！\n\n请先双击运行「install.bat」，再重新启动本程序。",
        "confirm_exit_title": "确认退出",
        "confirm_exit":       "AI 驾驶员正在运行，确认要退出并关闭 BeamNG 吗？",
        "browse_title":       "选择 BeamNG.drive 安装文件夹",
        # 日志消息
        "log_started":        "BeamNG AI 驾驶员 v1.1 已启动",
        "log_no_beamng":      "⚠  未检测到 beamngpy 依赖库",
        "log_install_hint":   "   → 请先双击运行「install.bat」",
        "log_beamng_ok":      "✓  beamngpy 依赖已就绪",
        "log_set_path":       "请设置 BeamNG 路径后点击「启动游戏并开始自动驾驶」",
        "log_hotkey_ok":      "✓  E 键全局热键已启用（暂停 / 继续 驾驶）",
        "log_no_pynput":      "⚠  pynput 未安装，E 键热键不可用（重新运行install.bat）",
    },
    "en": {
        "title":              "🚗  BeamNG  AI  Auto Driver",
        "lang_label":         "Language:",
        "status_idle":        "Not Connected",
        "status_connecting":  "Starting…",
        "status_driving":     "AI Driving",
        "status_paused":      "Paused",
        "speed_na":           "Speed: --",
        "speed_fmt":          "Speed: {speed:.1f} km/h",
        "decelerating":       "Braking {speed:.0f} km/h…",
        "settings":           " ⚙  Settings ",
        "path_label":         "BeamNG.drive install path:",
        "browse":             " Browse ",
        "map_label":          "Map:",
        "vehicle_label":      "Vehicle:",
        "speed_slider":       "Target Speed:",
        "controls":           " ▶  Controls ",
        "launch":             "🚀  Launch & Start Auto Driving",
        "pause":              "⏸  Pause",
        "resume":             "▶  Resume",
        "recover":            "🔄 Recover",
        "stop":               "⏹  Stop",
        "always_on_top":      "Always on top",
        "log_title":          " 📋  Log ",
        "quit":               "✕  Quit",
        # Dialogs
        "msg_no_path_title":  "Path Required",
        "msg_no_path":        (
            "Please set the BeamNG.drive install path!\n\n"
            "Common paths:\n"
            "  C:\\Program Files (x86)\\Steam\\steamapps\\common\\BeamNG.drive\n"
            "  D:\\SteamLibrary\\steamapps\\common\\BeamNG.drive"
        ),
        "msg_bad_path_title": "Invalid Path",
        "msg_bad_path":       "Folder not found:\n{path}\n\nPlease select again.",
        "msg_no_beamng_title":"Missing Dependency",
        "msg_no_beamng":      "beamngpy is not installed!\n\nPlease run install.bat first, then restart.",
        "confirm_exit_title": "Confirm Exit",
        "confirm_exit":       "AI Driver is running. Exit and close BeamNG?",
        "browse_title":       "Select BeamNG.drive Install Folder",
        # Log messages
        "log_started":        "BeamNG AI Driver v1.1 started",
        "log_no_beamng":      "⚠  beamngpy not detected",
        "log_install_hint":   "   → Please run install.bat first",
        "log_beamng_ok":      "✓  beamngpy ready",
        "log_set_path":       "Set BeamNG path, then click Launch to begin",
        "log_hotkey_ok":      "✓  E key hotkey enabled (Pause / Resume)",
        "log_no_pynput":      "⚠  pynput not installed, E key unavailable (run install.bat)",
    },
}

# ──────────────────────────────────────────────
# 地图 / 车辆显示名（双语）
# Map / Vehicle display names (bilingual)
# ──────────────────────────────────────────────
MAPS_ZH = {
    "意大利乡村 (Italy)":           "italy",
    "美国西海岸 (West Coast USA)":  "west_coast_usa",
    "美国东海岸 (East Coast USA)":  "east_coast_usa",
    "网格测试场 (Grid Map)":         "gridmap_v2",
    "丛林岛屿 (Jungle Island)":     "jungle_rock_island",
    "小型测试场 (Small Grid)":      "smallgrid",
}
MAPS_EN = {
    "Italy (Rural)":               "italy",
    "West Coast USA":              "west_coast_usa",
    "East Coast USA":              "east_coast_usa",
    "Grid Map":                    "gridmap_v2",
    "Jungle Rock Island":          "jungle_rock_island",
    "Small Grid":                  "smallgrid",
}
VEHICLES_ZH = {
    "ETK 800 系列（类奥迪轿车）": "etk800",
    "皮卡车 (D-series Pickup)":    "pickup",
    "小型轿车 (Ibishu Covet)":     "covet",
    "面包车 (H-series Van)":       "van",
    "复古美国车 (Burnside)":       "midsize",
}
VEHICLES_EN = {
    "ETK 800 (Sedan)":   "etk800",
    "D-series Pickup":   "pickup",
    "Ibishu Covet":      "covet",
    "H-series Van":      "van",
    "Burnside Special":  "midsize",
}

# ──────────────────────────────────────────────
# 颜色常量 / Color constants
# ──────────────────────────────────────────────
BG      = "#1a1a2e"
BG2     = "#16213e"
BG3     = "#0d1117"
ACCENT  = "#7fbbff"
FG      = "#e0e0e0"
FG_DIM  = "#888888"
GREEN   = "#2ecc71"
YELLOW  = "#f4d03f"
RED     = "#e74c3c"
BTN_BLU = "#0f3460"
BTN_GRN = "#1a4a22"
BTN_RED = "#4a1515"
BTN_YLW = "#4a3a0a"


# ──────────────────────────────────────────────
# 颜色辅助函数 / Color helpers
# ──────────────────────────────────────────────
def _hex_lighten(color: str, factor: float = 0.25) -> str:
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_darken(color: str, factor: float = 0.20) -> str:
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


# ──────────────────────────────────────────────
# 圆角按钮 / Rounded button widget
# ──────────────────────────────────────────────
class RoundButton(tk.Canvas):
    """
    用 Canvas 绘制的圆角按钮，支持悬停变亮、按下变暗效果。
    Canvas-based button with rounded corners, hover (lighten) and
    press (darken) color effects.
    """

    def __init__(self, parent, text: str, bg: str, fg: str = "white",
                 command=None, radius: int = 10, font=None,
                 height: int = 34, parent_bg: str = BG, **kwargs):
        super().__init__(
            parent,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=parent_bg,
            **kwargs,
        )
        self._text       = text
        self._bg_normal  = bg
        self._bg_hover   = _hex_lighten(bg, 0.22)
        self._bg_press   = _hex_darken(bg, 0.18)
        self._bg_disable = _hex_darken(bg, 0.40)
        self._fg         = fg
        self._command    = command
        self._radius     = radius
        self._font       = font or ("Microsoft YaHei UI", 9)
        self._disabled   = False
        self._cur_bg     = bg

        self.bind("<Configure>",         self._redraw)
        self.bind("<Enter>",             self._on_enter)
        self.bind("<Leave>",             self._on_leave)
        self.bind("<ButtonPress-1>",     self._on_press)
        self.bind("<ButtonRelease-1>",   self._on_release)
        super().config(cursor="hand2")
        # 首帧渲染（等布局完成后执行）
        self.after_idle(self._redraw)

    # ── 绘制 ─────────────────────────────────
    def _draw_rrect(self, x0, y0, x1, y1, r, fill):
        """绘制填充圆角矩形"""
        self.create_arc(x0,      y0,      x0+2*r, y0+2*r,
                        start=90,  extent=90,  fill=fill, outline=fill)
        self.create_arc(x1-2*r,  y0,      x1,     y0+2*r,
                        start=0,   extent=90,  fill=fill, outline=fill)
        self.create_arc(x0,      y1-2*r,  x0+2*r, y1,
                        start=180, extent=90,  fill=fill, outline=fill)
        self.create_arc(x1-2*r,  y1-2*r,  x1,     y1,
                        start=270, extent=90,  fill=fill, outline=fill)
        self.create_rectangle(x0+r, y0,   x1-r, y1,   fill=fill, outline=fill)
        self.create_rectangle(x0,   y0+r, x1,   y1-r, fill=fill, outline=fill)

    def _redraw(self, _event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            return
        fill = self._bg_disable if self._disabled else self._cur_bg
        fg   = FG_DIM            if self._disabled else self._fg
        self._draw_rrect(0, 0, w, h, self._radius, fill)
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=fg, font=self._font, anchor="center")

    # ── 鼠标事件 ─────────────────────────────
    def _on_enter(self, _e):
        if not self._disabled:
            self._cur_bg = self._bg_hover
            self._redraw()

    def _on_leave(self, _e):
        if not self._disabled:
            self._cur_bg = self._bg_normal
            self._redraw()

    def _on_press(self, _e):
        if not self._disabled:
            self._cur_bg = self._bg_press
            self._redraw()

    def _on_release(self, e):
        if not self._disabled:
            w, h = self.winfo_width(), self.winfo_height()
            inside = (0 <= e.x <= w and 0 <= e.y <= h)
            self._cur_bg = self._bg_hover if inside else self._bg_normal
            self._redraw()
            if inside and self._command:
                self._command()

    # ── 兼容 tk.Button 的 config/configure 接口 ──
    def config(self, **kwargs):
        state = kwargs.pop("state",   None)
        text  = kwargs.pop("text",    None)
        if kwargs:
            super().config(**kwargs)
        if state is not None:
            self._disabled = (state == tk.DISABLED)
            self._cur_bg   = self._bg_normal
            super().config(cursor="" if self._disabled else "hand2")
            self._redraw()
        if text is not None:
            self._text = text
            self._redraw()

    configure = config


# ──────────────────────────────────────────────
# 配置管理 / Config
# ──────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "beamng_home":    "",
    "host":           "localhost",
    "port":           64256,
    "default_speed":  60,
    "vehicle_model":  "etk800",
    "map_name":       "italy",
    "aggression":     0.4,
    "lang":           "zh",
}


class Config:
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        self._load()

    def _load(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
        except Exception:
            pass

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key):
        return self.data.get(key, DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.data[key] = value


# ──────────────────────────────────────────────
# AI 驾驶员核心 / AI Driver core
# ──────────────────────────────────────────────
class AIDriver:
    """管理 BeamNG 连接、场景、AI 驾驶逻辑"""

    STUCK_THRESHOLD_SEC = 15
    STUCK_CHECK_SPEED   = 1.0   # km/h

    def __init__(self, config: Config, log_fn):
        self.config  = config
        self.log     = log_fn

        self.bng       = None
        self.vehicle   = None
        self.connected = False
        self.ai_active = False
        self.paused    = False

        self.speed_kmh        = 0.0
        self._low_speed_since = None

        self._braking_to_stop = False
        self._damaged         = False
        self._prev_damage     = 0.0

        self._electrics     = None
        self._damage_sensor = None

        self._on_damaged_cb = None

        self._current_speed_ms  = 0.0   # 当前目标速度（m/s），恢复时重用
        self._ai_start_time     = 0.0   # AI 激活时刻，用于启动冷却
        self._last_recover_time = 0.0   # 上次自动恢复时刻，用于恢复冷却

        self._stop_evt       = threading.Event()
        self._monitor_thread = None

    # ── 带超时的阻塞调用辅助 ────────────────────
    def _timed_call(self, fn, timeout_sec, *args, **kwargs):
        """在子线程执行 fn，最多等待 timeout_sec 秒。
        返回 (success: bool, exception | None)"""
        done  = threading.Event()
        exc_box = [None]

        def _run():
            try:
                fn(*args, **kwargs)
            except Exception as e:
                exc_box[0] = e
            finally:
                done.set()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        completed = done.wait(timeout=timeout_sec)
        return completed, exc_box[0]

    # ── 连接并启动 ──────────────────────────────
    def launch(self, beamng_home: str, map_name: str,
               vehicle_model: str, speed_kmh: int) -> bool:
        try:
            self.log("正在启动 BeamNG.drive，请稍候……")
            self.log(f"游戏路径: {beamng_home}")

            self.bng = BeamNGpy(
                self.config.get("host"),
                self.config.get("port"),
                home=beamng_home,
            )
            self.bng.open(launch=True)
            self.log("✓ BeamNG.drive 已启动")

            self.log(f"正在加载地图「{map_name}」……")
            self.log("（大型地图首次加载需 1~3 分钟，请耐心等待）")
            scenario = Scenario(map_name, "ai_drive", description="AI自动驾驶")
            veh = Vehicle("ai_car", model=vehicle_model, color="Red")

            self._electrics = Electrics()
            veh.attach_sensor("electrics", self._electrics)
            if DamageSensor is not None:
                self._damage_sensor = DamageSensor()
                veh.attach_sensor("damage", self._damage_sensor)
            self._prev_damage = 0.0
            self._damaged     = False

            spawn_pos = MAP_SPAWN.get(map_name, MAP_SPAWN_DEFAULT)
            scenario.add_vehicle(veh,
                                  pos=spawn_pos,
                                  rot_quat=(0, 0, 0, 1),
                                  cling=True)
            scenario.make(self.bng)

            # ── 带超时的地图加载（BeamMP 可能导致长时间阻塞）──
            self.log("正在加载场景，最长等待 3 分钟……")
            ok, err = self._timed_call(self.bng.scenario.load, 180, scenario)
            if not ok:
                self.log("⚠ 地图加载等待超时（180 秒）")
                self.log("  常见原因：安装了 BeamMP 多人 MOD，其网络初始化")
                self.log("  会阻塞加载信号。建议：禁用 BeamMP 后重试。")
                self.log("  尝试继续——若游戏画面已显示，驾驶员可能仍可运行。")
            elif err:
                raise err
            else:
                self.log("✓ 地图加载完成")

            # ── 启动场景（带较短超时）──────────────────
            ok2, err2 = self._timed_call(self.bng.scenario.start, 30)
            if not ok2:
                self.log("⚠ 场景启动信号超时，尝试继续……")
            elif err2:
                self.log(f"⚠ 场景启动返回错误（已忽略）: {err2}")

            self.vehicle = veh

            # 等待车辆物理稳定
            time.sleep(4)
            try:
                veh.recover()
                self.log("✓ 车辆已定位到道路上")
            except Exception:
                pass

            self.log(f"✓ 场景已就绪（地图: {map_name} | 车型: {vehicle_model}）")

            self.connected = True
            self._activate_ai(speed_kmh)
            return True

        except Exception as exc:
            self.log(f"✗ 启动失败: {exc}")
            self._safe_close()
            return False

    # ── 激活 AI ────────────────────────────────
    def _activate_ai(self, speed_kmh: int):
        aggression = self.config.get("aggression")
        speed_ms   = speed_kmh / 3.6
        try:
            ai = self.vehicle.ai
            ai.set_mode("span")
            ai.set_speed(speed_ms)
            ai.set_aggression(aggression)
        except AttributeError:
            self.vehicle.set_ai_mode("span")
            self.vehicle.set_ai_speed(speed_ms)

        self._current_speed_ms  = speed_ms
        self._ai_start_time     = time.time()
        self._last_recover_time = 0.0
        self.ai_active = True
        self.paused    = False
        self._low_speed_since = None

        self._stop_evt.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="DriverMonitor",
        )
        self._monitor_thread.start()
        self.log(f"✓ AI 驾驶员已激活！目标速度 {speed_kmh} km/h，开始自动巡路……")

    # ── 监控循环 ────────────────────────────────
    def _monitor_loop(self):
        while not self._stop_evt.is_set():
            try:
                if self.vehicle and self.connected:

                    # 读取传感器
                    try:
                        self.vehicle.sensors.poll()
                        if self._electrics and self._electrics.data:
                            e = self._electrics.data
                            self.speed_kmh = abs(e.get("wheelspeed", 0) * 3.6)
                        else:
                            raise RuntimeError("no electrics data")
                    except Exception:
                        try:
                            self.vehicle.update_vehicle()
                            s = self.vehicle.state
                            if s:
                                v = s.get("vel", [0, 0, 0])
                                self.speed_kmh = (
                                    v[0]**2 + v[1]**2 + v[2]**2
                                ) ** 0.5 * 3.6
                        except Exception:
                            pass

                    # 渐进停车：速度到零后挂 P 档
                    if self._braking_to_stop:
                        if self.speed_kmh < 0.5:
                            try:
                                self.vehicle.control(
                                    throttle=0, brake=0,
                                    parkingbrake=1, steering=0,
                                )
                            except Exception:
                                pass
                            self._braking_to_stop = False
                            self.paused = True
                        else:
                            try:
                                self.vehicle.control(throttle=0, brake=1.0)
                            except Exception:
                                pass

                    # 损坏检测
                    if not self._damaged and self._damage_sensor:
                        try:
                            d = self._damage_sensor.data
                            if d:
                                cur = float(d.get("damage", 0))
                                if cur - self._prev_damage > 0.3 or cur > 0.6:
                                    self._handle_damage()
                                self._prev_damage = cur
                        except Exception:
                            pass

                    # 卡死检测（AI 行驶中）
                    if (self.ai_active
                            and not self.paused
                            and not self._braking_to_stop):
                        now = time.time()
                        # 启动后 25 秒内、上次恢复后 20 秒内，暂停检测
                        in_startup  = now - self._ai_start_time   < 25
                        in_cooldown = now - self._last_recover_time < 20
                        if in_startup or in_cooldown:
                            self._low_speed_since = None
                        elif self.speed_kmh < self.STUCK_CHECK_SPEED:
                            if self._low_speed_since is None:
                                self._low_speed_since = now
                            elif now - self._low_speed_since > self.STUCK_THRESHOLD_SEC:
                                self.log("⚠ 检测到车辆卡死，自动恢复中……")
                                self._do_recover()
                                self._last_recover_time = time.time()
                                self._low_speed_since   = None
                                # 恢复后重新激活 AI，防止传送重置 AI 模式
                                try:
                                    self.vehicle.ai.set_mode("span")
                                    self.vehicle.ai.set_speed(self._current_speed_ms)
                                    self.vehicle.ai.set_aggression(
                                        self.config.get("aggression"))
                                except Exception:
                                    pass
                        else:
                            self._low_speed_since = None

            except Exception:
                pass
            time.sleep(0.4)

    # ── 调速 ───────────────────────────────────
    def set_speed(self, speed_kmh: int):
        if not self.vehicle or not self.ai_active or self.paused:
            return
        try:
            self._current_speed_ms = speed_kmh / 3.6
            try:
                self.vehicle.ai.set_speed(self._current_speed_ms)
            except AttributeError:
                self.vehicle.set_ai_speed(self._current_speed_ms)
            self.log(f"目标速度已调整为 {speed_kmh} km/h")
        except Exception as exc:
            self.log(f"调速失败: {exc}")

    # ── 暂停 ───────────────────────────────────
    def pause(self):
        if not self.vehicle or not self.ai_active:
            return
        try:
            try:
                self.vehicle.ai.set_mode("disabled")
            except AttributeError:
                self.vehicle.set_ai_mode("disabled")
            self.vehicle.control(throttle=0, brake=1.0, steering=0)
            self.ai_active        = False
            self._braking_to_stop = True
            self.log("⏸  正在减速停车，速度到零后挂 P 档……")
        except Exception as exc:
            self.log(f"暂停失败: {exc}")

    # ── 恢复 ───────────────────────────────────
    def resume(self, speed_kmh: int):
        # 允许在：已完全停车、受损、或仍在减速过程中 恢复
        if not self.vehicle:
            return
        if not self.paused and not self._damaged and not self._braking_to_stop:
            return
        try:
            # 先取消减速状态，再松开所有制动
            self._braking_to_stop = False
            self.vehicle.control(throttle=0, brake=0, parkingbrake=0, steering=0)
            try:
                self.vehicle.ai.set_mode("span")
                self.vehicle.ai.set_speed(speed_kmh / 3.6)
                self.vehicle.ai.set_aggression(self.config.get("aggression"))
            except AttributeError:
                self.vehicle.set_ai_mode("span")
                self.vehicle.set_ai_speed(speed_kmh / 3.6)
            self._current_speed_ms  = speed_kmh / 3.6
            self._ai_start_time     = time.time()
            self._last_recover_time = 0.0
            self.ai_active        = True
            self.paused           = False
            self._damaged         = False
            self._braking_to_stop = False
            self._low_speed_since = None
            self._set_hazard(False)
            self.log("▶  AI 驾驶已恢复")
        except Exception as exc:
            self.log(f"恢复失败: {exc}")

    # ── 恢复车辆位置 ───────────────────────────
    def _do_recover(self):
        """在当前 XY 正上方 30 米传送，让物理引擎自然落地"""
        try:
            self.vehicle.update_vehicle()
            state = self.vehicle.state
            if state and state.get("pos"):
                x, y, z = state["pos"]
                self.vehicle.teleport(
                    (x, y, z + 30),
                    rot_quat=(0, 0, 0, 1),
                    reset=True,
                )
            else:
                self.vehicle.recover()
        except Exception:
            try:
                self.vehicle.recover()
            except Exception:
                pass

    def recover_vehicle(self):
        if not self.vehicle:
            return
        self._do_recover()
        self.log("🔄 已在原地上方重新落地")

    # ── 损坏处理 ───────────────────────────────
    def _handle_damage(self):
        try:
            try:
                self.vehicle.ai.set_mode("disabled")
            except Exception:
                pass
            self.vehicle.control(throttle=0, brake=1.0, steering=0)
        except Exception:
            pass
        self.ai_active        = False
        self._braking_to_stop = True
        self._damaged         = True
        self._set_hazard(True)
        self.log("⚠  车辆受损！已停车并开启双闪")
        if self._on_damaged_cb:
            self._on_damaged_cb()

    def _set_hazard(self, on: bool):
        if not self.vehicle:
            return
        val = 1 if on else 0
        cmds = [
            f'electrics.values["hazard_enabled"] = {val}',
            f'input.event("hazard", {val}, FILTER_DIRECT)',
        ]
        for cmd in cmds:
            try:
                self.vehicle.queue_lua_command(cmd)
            except Exception:
                pass

    # ── 停止 ───────────────────────────────────
    def stop(self):
        self._stop_evt.set()
        try:
            if self.vehicle:
                try:
                    self.vehicle.ai.set_mode("disabled")
                except Exception:
                    pass
                try:
                    self.vehicle.control(throttle=0, brake=1.0, steering=0)
                except Exception:
                    pass
        except Exception:
            pass
        self._safe_close()
        self.ai_active = False
        self.paused    = False
        self.connected = False
        self.log("⏹  已停止，连接已断开")

    def _safe_close(self):
        try:
            if self.bng:
                self.bng.close()
        except Exception:
            pass
        self.bng     = None
        self.vehicle = None


# ──────────────────────────────────────────────
# GUI 控制面板 / GUI Control Panel
# ──────────────────────────────────────────────
class ControlPanel:
    def __init__(self):
        self.config  = Config()
        self._cur_lang = self.config.get("lang") or "zh"
        self._ui_state = "idle"

        self.driver  = AIDriver(self.config, self._log)
        self._paused = False
        self.driver._on_damaged_cb = self._on_driver_damaged

        self.root = tk.Tk()
        self._build_window()
        self._build_ui()
        self._set_state("idle")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 翻译辅助 ─────────────────────────────
    def T(self, key: str, **kwargs) -> str:
        text = LANG[self._cur_lang].get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    # ── 语言切换 ─────────────────────────────
    def _switch_lang(self, _event=None):
        # 保存当前地图/车辆的内部名称
        old_maps = MAPS_ZH if self._cur_lang == "zh" else MAPS_EN
        old_vehs = VEHICLES_ZH if self._cur_lang == "zh" else VEHICLES_EN
        cur_map = old_maps.get(self._map_var.get(), "italy")
        cur_veh = old_vehs.get(self._veh_var.get(), "etk800")

        # 切换语言
        self._cur_lang = "zh" if self._lang_var.get() == "中文" else "en"
        self.config.set("lang", self._cur_lang)

        # 更新地图/车辆下拉框
        new_maps = MAPS_ZH if self._cur_lang == "zh" else MAPS_EN
        new_vehs = VEHICLES_ZH if self._cur_lang == "zh" else VEHICLES_EN
        new_map_disp = next(
            (k for k, v in new_maps.items() if v == cur_map),
            list(new_maps.keys())[0],
        )
        new_veh_disp = next(
            (k for k, v in new_vehs.items() if v == cur_veh),
            list(new_vehs.keys())[0],
        )
        self._map_cb["values"] = list(new_maps.keys())
        self._map_var.set(new_map_disp)
        self._veh_cb["values"] = list(new_vehs.keys())
        self._veh_var.set(new_veh_disp)

        # 重新应用所有文本
        self._apply_lang()

    def _apply_lang(self):
        """刷新所有界面文字为当前语言"""
        T = self.T
        self.root.title("BeamNG AI Driver v1.1")
        self._title_lbl.config(text=T("title"))
        self._lang_lbl.config(text=T("lang_label"))
        self._path_lbl.config(text=T("path_label"))
        self._browse_btn.config(text=T("browse"))
        self._map_lbl.config(text=T("map_label"))
        self._veh_lbl.config(text=T("vehicle_label"))
        self._speed_slider_lbl.config(text=T("speed_slider"))
        self._settings_frame.configure(text=T("settings"))
        self._controls_frame.configure(text=T("controls"))
        self._log_frame.configure(text=T("log_title"))
        self._topmost_cb.config(text=T("always_on_top"))
        self._launch_btn.config(text=T("launch"))
        self._recover_btn.config(text=T("recover"))
        self._stop_btn.config(text=T("stop"))
        self._quit_btn.config(text=T("quit"))

        # 暂停按钮文字取决于当前状态
        if self._ui_state == "paused":
            self._pause_btn.config(text=T("resume"))
        else:
            self._pause_btn.config(text=T("pause"))

        # 状态栏文字
        if self._ui_state == "idle":
            self._status_lbl.config(text=T("status_idle"))
            self._speed_bar_lbl.config(text=T("speed_na"))
        elif self._ui_state == "connecting":
            self._status_lbl.config(text=T("status_connecting"))
        elif self._ui_state == "driving":
            self._status_lbl.config(text=T("status_driving"))
        elif self._ui_state == "paused":
            self._status_lbl.config(text=T("status_paused"))

    # ── 窗口设置 ──────────────────────────────
    def _build_window(self):
        self.root.title("BeamNG AI Driver v1.1")
        self.root.geometry("440x650")
        self.root.minsize(380, 540)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)

    # ── 构建界面 ──────────────────────────────
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        for w in ("TFrame", "TLabel", "TCheckbutton"):
            style.configure(w, background=BG, foreground=FG)
        style.configure("TLabelframe",
                         background=BG, foreground=ACCENT)
        style.configure("TLabelframe.Label",
                         background=BG, foreground=ACCENT,
                         font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("TCombobox",
                         fieldbackground=BG2, background=BG2,
                         foreground=FG, selectbackground=BG2)
        style.map("TCombobox", fieldbackground=[("readonly", BG2)])
        style.configure("TScale", background=BG, troughcolor=BG2)

        outer = ttk.Frame(self.root)
        outer.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # ─ 标题行 + 语言切换 ────────────────────
        header = tk.Frame(outer, bg=BG)
        header.pack(fill=tk.X, pady=(0, 8))

        self._title_lbl = tk.Label(
            header, text=self.T("title"),
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=BG, fg=ACCENT,
        )
        self._title_lbl.pack(side=tk.LEFT, expand=True, anchor="w")

        lang_fr = tk.Frame(header, bg=BG)
        lang_fr.pack(side=tk.RIGHT)
        self._lang_lbl = tk.Label(
            lang_fr, text=self.T("lang_label"),
            bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 8),
        )
        self._lang_lbl.pack(side=tk.LEFT)
        # 从配置读取默认语言
        lang_display = "中文" if self._cur_lang == "zh" else "English"
        self._lang_var = tk.StringVar(value=lang_display)
        self._lang_cb = ttk.Combobox(
            lang_fr, textvariable=self._lang_var,
            values=["中文", "English"], width=7, state="readonly",
        )
        self._lang_cb.pack(side=tk.LEFT, padx=(4, 0))
        self._lang_cb.bind("<<ComboboxSelected>>", self._switch_lang)

        # ─ 状态栏 ────────────────────────────────
        sb = tk.Frame(outer, bg=BG2, relief="flat")
        sb.pack(fill=tk.X, pady=(0, 10))
        inner = tk.Frame(sb, bg=BG2)
        inner.pack(fill=tk.X, padx=12, pady=10)

        self._dot = tk.Label(inner, text="●", font=("Arial", 18),
                              bg=BG2, fg="#444444")
        self._dot.pack(side=tk.LEFT)

        txt = tk.Frame(inner, bg=BG2)
        txt.pack(side=tk.LEFT, padx=(10, 0))
        self._status_lbl = tk.Label(
            txt, text=self.T("status_idle"),
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=BG2, fg=FG_DIM,
        )
        self._status_lbl.pack(anchor="w")
        self._speed_bar_lbl = tk.Label(
            txt, text=self.T("speed_na"),
            font=("Microsoft YaHei UI", 9),
            bg=BG2, fg=FG_DIM,
        )
        self._speed_bar_lbl.pack(anchor="w")

        # ─ 设置区 ────────────────────────────────
        self._settings_frame = ttk.LabelFrame(
            outer, text=self.T("settings"), padding=(10, 6),
        )
        self._settings_frame.pack(fill=tk.X, pady=(0, 8))
        sf = self._settings_frame

        self._path_lbl = tk.Label(
            sf, text=self.T("path_label"),
            bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 8),
        )
        self._path_lbl.pack(anchor="w")

        pr = tk.Frame(sf, bg=BG)
        pr.pack(fill=tk.X, pady=(2, 8))
        self._path_var = tk.StringVar(value=self.config.get("beamng_home"))
        tk.Entry(
            pr, textvariable=self._path_var,
            bg=BG2, fg=FG, insertbackground="white",
            relief="flat", font=("Consolas", 9),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._browse_btn = RoundButton(
            pr, text=self.T("browse"), bg="#1e2f50", fg=FG,
            command=self._browse, radius=6, height=26,
            parent_bg=BG, font=("Microsoft YaHei UI", 8), width=68,
        )
        self._browse_btn.pack(side=tk.LEFT, padx=(6, 0))

        # 地图 + 车辆
        mv = tk.Frame(sf, bg=BG)
        mv.pack(fill=tk.X, pady=(0, 8))

        maps = MAPS_ZH if self._cur_lang == "zh" else MAPS_EN
        vehs = VEHICLES_ZH if self._cur_lang == "zh" else VEHICLES_EN

        self._map_lbl = tk.Label(mv, text=self.T("map_label"),
                                  bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 8))
        self._map_lbl.grid(row=0, column=0, sticky="w")
        self._map_var = tk.StringVar()
        default_map = next(
            (k for k, v in maps.items() if v == self.config.get("map_name")),
            list(maps.keys())[0],
        )
        self._map_var.set(default_map)
        self._map_cb = ttk.Combobox(
            mv, textvariable=self._map_var,
            values=list(maps.keys()), width=26, state="readonly",
        )
        self._map_cb.grid(row=0, column=1, sticky="w", padx=(6, 16))

        self._veh_lbl = tk.Label(mv, text=self.T("vehicle_label"),
                                  bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 8))
        self._veh_lbl.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._veh_var = tk.StringVar()
        default_veh = next(
            (k for k, v in vehs.items() if v == self.config.get("vehicle_model")),
            list(vehs.keys())[0],
        )
        self._veh_var.set(default_veh)
        self._veh_cb = ttk.Combobox(
            mv, textvariable=self._veh_var,
            values=list(vehs.keys()), width=26, state="readonly",
        )
        self._veh_cb.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(4, 0))

        # 速度滑块（先建标签再建 Scale，避免 set() 回调时标签不存在）
        sr = tk.Frame(sf, bg=BG)
        sr.pack(fill=tk.X)
        self._speed_slider_lbl = tk.Label(
            sr, text=self.T("speed_slider"),
            bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 8),
        )
        self._speed_slider_lbl.pack(side=tk.LEFT)
        self._speed_val_lbl = tk.Label(
            sr,
            text=f"{int(self.config.get('default_speed'))} km/h",
            bg=BG, fg=ACCENT, width=9,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self._speed_scale = ttk.Scale(
            sr, from_=10, to=150, orient=tk.HORIZONTAL,
            command=self._on_speed_drag,
        )
        self._speed_scale.set(self.config.get("default_speed"))
        self._speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self._speed_val_lbl.pack(side=tk.LEFT)

        # ─ 控制按钮 ──────────────────────────────
        self._controls_frame = ttk.LabelFrame(
            outer, text=self.T("controls"), padding=(10, 8),
        )
        self._controls_frame.pack(fill=tk.X, pady=(0, 8))
        cf = self._controls_frame

        self._launch_btn = RoundButton(
            cf, text=self.T("launch"), bg=BTN_BLU, fg="white",
            command=self._launch, radius=10, height=44, parent_bg=BG,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self._launch_btn.pack(fill=tk.X, pady=(0, 8))

        row2 = tk.Frame(cf, bg=BG)
        row2.pack(fill=tk.X)

        self._pause_btn = RoundButton(
            row2, text=self.T("pause"), bg=BTN_GRN, fg="white",
            command=self._toggle_pause, radius=10, height=36, parent_bg=BG,
        )
        self._pause_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self._recover_btn = RoundButton(
            row2, text=self.T("recover"), bg=BTN_YLW, fg="white",
            command=self._recover, radius=10, height=36, parent_bg=BG,
        )
        self._recover_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self._stop_btn = RoundButton(
            row2, text=self.T("stop"), bg=BTN_RED, fg="white",
            command=self._stop, radius=10, height=36, parent_bg=BG,
        )
        self._stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 选项行
        opt = tk.Frame(outer, bg=BG)
        opt.pack(fill=tk.X, pady=(0, 4))
        self._topmost_var = tk.BooleanVar(value=True)
        self._topmost_cb = tk.Checkbutton(
            opt, text=self.T("always_on_top"),
            variable=self._topmost_var,
            command=self._toggle_topmost,
            bg=BG, fg=FG_DIM, selectcolor=BG2,
            activebackground=BG, activeforeground=FG,
            font=("Microsoft YaHei UI", 8),
        )
        self._topmost_cb.pack(side=tk.LEFT)

        # ─ 日志 ──────────────────────────────────
        self._log_frame = ttk.LabelFrame(
            outer, text=self.T("log_title"), padding=(8, 4),
        )
        self._log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self._log_box = scrolledtext.ScrolledText(
            self._log_frame, height=7,
            font=("Consolas", 8),
            bg=BG3, fg="#c9d1d9",
            insertbackground="white",
            relief="flat", state=tk.DISABLED,
        )
        self._log_box.pack(fill=tk.BOTH, expand=True)

        # ─ 退出按钮 ──────────────────────────────
        self._quit_btn = RoundButton(
            outer, text=self.T("quit"), bg=BTN_RED, fg="#ff9999",
            command=self._on_close, radius=10, height=36, parent_bg=BG,
            font=("Microsoft YaHei UI", 9),
        )
        self._quit_btn.pack(fill=tk.X)

    # ── 状态机 ────────────────────────────────
    def _set_state(self, state: str):
        self._ui_state = state
        T = self.T
        s, d = tk.NORMAL, tk.DISABLED

        if state == "idle":
            self._launch_btn.config(state=s)
            self._pause_btn.config(state=d, text=T("pause"))
            self._recover_btn.config(state=d)
            self._stop_btn.config(state=d)
            self._dot.config(fg="#444444")
            self._status_lbl.config(text=T("status_idle"),   fg=FG_DIM)
            self._speed_bar_lbl.config(text=T("speed_na"),   fg=FG_DIM)

        elif state == "connecting":
            self._launch_btn.config(state=d)
            self._pause_btn.config(state=d)
            self._recover_btn.config(state=d)
            self._stop_btn.config(state=d)
            self._dot.config(fg=YELLOW)
            self._status_lbl.config(text=T("status_connecting"), fg=YELLOW)

        elif state == "driving":
            self._launch_btn.config(state=d)
            self._pause_btn.config(state=s, text=T("pause"))
            self._recover_btn.config(state=s)
            self._stop_btn.config(state=s)
            self._dot.config(fg=GREEN)
            self._status_lbl.config(text=T("status_driving"), fg=GREEN)

        elif state == "paused":
            self._launch_btn.config(state=d)
            self._pause_btn.config(state=s, text=T("resume"))
            self._recover_btn.config(state=s)
            self._stop_btn.config(state=s)
            self._dot.config(fg=YELLOW)
            self._status_lbl.config(text=T("status_paused"), fg=YELLOW)

    # ── 日志 ──────────────────────────────────
    def _log(self, msg: str):
        def _do():
            self._log_box.config(state=tk.NORMAL)
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._log_box.insert(tk.END, f"[{ts}]  {msg}\n")
            self._log_box.see(tk.END)
            self._log_box.config(state=tk.DISABLED)

        if threading.current_thread() is threading.main_thread():
            _do()
        else:
            self.root.after(0, _do)

    # ── 工具 ──────────────────────────────────
    def _browse(self):
        p = filedialog.askdirectory(title=self.T("browse_title"))
        if p:
            self._path_var.set(p.replace("/", "\\"))

    def _on_speed_drag(self, val):
        spd = int(float(val))
        self._speed_val_lbl.config(text=f"{spd} km/h")
        if self.driver.ai_active and not self.driver.paused:
            self.driver.set_speed(spd)

    def _toggle_topmost(self):
        self.root.attributes("-topmost", self._topmost_var.get())

    # ── 按钮动作 ──────────────────────────────
    def _launch(self):
        home = self._path_var.get().strip()
        if not home:
            messagebox.showwarning(
                self.T("msg_no_path_title"),
                self.T("msg_no_path"),
            )
            return
        if not os.path.isdir(home):
            messagebox.showerror(
                self.T("msg_bad_path_title"),
                self.T("msg_bad_path", path=home),
            )
            return
        if not BEAMNG_AVAILABLE:
            messagebox.showerror(
                self.T("msg_no_beamng_title"),
                self.T("msg_no_beamng"),
            )
            return

        maps = MAPS_ZH if self._cur_lang == "zh" else MAPS_EN
        vehs = VEHICLES_ZH if self._cur_lang == "zh" else VEHICLES_EN
        map_name      = maps.get(self._map_var.get(), "italy")
        vehicle_model = vehs.get(self._veh_var.get(), "etk800")
        speed         = int(self._speed_scale.get())

        self.config.set("beamng_home",   home)
        self.config.set("map_name",      map_name)
        self.config.set("vehicle_model", vehicle_model)
        self.config.set("default_speed", speed)
        self.config.save()

        self._set_state("connecting")
        self._paused = False

        def _run():
            ok = self.driver.launch(home, map_name, vehicle_model, speed)
            self.root.after(0, lambda: self._set_state("driving" if ok else "idle"))

        threading.Thread(target=_run, daemon=True).start()

    def _toggle_pause(self):
        spd = int(self._speed_scale.get())
        if not self._paused:
            self.driver.pause()
            self._paused = True
            self.root.after(0, lambda: self._set_state("paused"))
        else:
            self.driver.resume(spd)
            self._paused = False
            self.root.after(0, lambda: self._set_state("driving"))

    def _recover(self):
        threading.Thread(target=self.driver.recover_vehicle, daemon=True).start()

    def _stop(self):
        def _do():
            self.driver.stop()
            self._paused = False
            self.root.after(0, lambda: self._set_state("idle"))
        threading.Thread(target=_do, daemon=True).start()

    def _on_close(self):
        if self.driver.connected:
            if not messagebox.askyesno(
                self.T("confirm_exit_title"),
                self.T("confirm_exit"),
            ):
                return
            def _shutdown():
                self.driver.stop()
                self.root.after(600, self.root.destroy)
            threading.Thread(target=_shutdown, daemon=True).start()
        else:
            self.root.destroy()

    # ── 速度 + 状态刷新 ───────────────────────
    def _refresh_speed(self):
        d = self.driver
        if d.connected:
            spd = d.speed_kmh
            self._speed_bar_lbl.config(
                text=self.T("speed_fmt", speed=spd), fg=FG,
            )
            if d._braking_to_stop:
                self._status_lbl.config(
                    text=self.T("decelerating", speed=spd), fg=YELLOW,
                )
            elif self._paused and d.paused and not d.ai_active:
                self._set_state("paused")

        self.root.after(500, self._refresh_speed)

    # ── 损坏回调 ──────────────────────────────
    def _on_driver_damaged(self):
        self._paused = True
        self.root.after(0, lambda: self._set_state("paused"))

    # ── E 键全局热键 ──────────────────────────
    def _setup_hotkey(self):
        if not PYNPUT_AVAILABLE:
            self._log(self.T("log_no_pynput"))
            return

        def on_press(key):
            try:
                if hasattr(key, "char") and key.char in ("e", "E"):
                    self.root.after(0, self._hotkey_e)
            except Exception:
                pass

        listener = pynput_kb.Listener(on_press=on_press, daemon=True)
        listener.start()
        self._log(self.T("log_hotkey_ok"))

    def _hotkey_e(self):
        if not self.driver.connected:
            return
        d = self.driver
        # 有效状态：正在行驶、减速中、已停车、或受损
        if not d.ai_active and not d.paused and not d._damaged and not d._braking_to_stop:
            return
        self._toggle_pause()

    # ── 运行 ──────────────────────────────────
    def run(self):
        T = self.T
        self._log(T("log_started"))
        self._log("━" * 42)
        if not BEAMNG_AVAILABLE:
            self._log(T("log_no_beamng"))
            self._log(T("log_install_hint"))
        else:
            self._log(T("log_beamng_ok"))
        self._log(T("log_set_path"))
        self._setup_hotkey()
        self._refresh_speed()
        self.root.mainloop()


# ──────────────────────────────────────────────
if __name__ == "__main__":
    import traceback as _tb

    _LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")

    try:
        app = ControlPanel()
        app.run()
    except Exception:
        err = _tb.format_exc()
        try:
            with open(_LOG, "w", encoding="utf-8") as _f:
                _f.write(err)
        except Exception:
            pass
        try:
            import tkinter as _tk
            import tkinter.messagebox as _mb
            _r = _tk.Tk()
            _r.withdraw()
            _mb.showerror(
                "启动错误 / Startup Error",
                f"程序启动失败，详细信息已保存到：\n{_LOG}\n\n{err[-800:]}",
            )
            _r.destroy()
        except Exception:
            pass
        print(err)
        input("按 Enter 键退出 / Press Enter to exit...")
