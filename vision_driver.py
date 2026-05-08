#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeamNG.drive 云电脑视觉 AI 驾驶员 / Cloud Vision AI Driver
版本 / Version: 1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
不需要 BeamNGpy！Does NOT require BeamNGpy!
适用于 GeForce Now、Shadow PC 等云游戏平台
Works with GeForce Now, Shadow PC, and other cloud gaming platforms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

工作原理 / How it works:
  ① 截取云游戏窗口画面   → Capture cloud gaming client window
  ② OpenCV 检测车道线   → Detect lane lines with OpenCV
  ③ YOLOv8 检测障碍物   → Detect obstacles with YOLOv8 (optional)
  ④ 模拟键盘按键控制车辆 → Control vehicle via simulated keypresses (WASD)

使用步骤 / Quick Start:
  1. 运行 install_vision.bat 安装依赖
  2. 打开 GeForce Now 并进入 BeamNG.drive
  3. 在「游戏窗口」下拉框中选择正确的云游戏窗口
  4. 点击「启动视觉驾驶员」即可
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import time
import json
import os
import datetime
import math
from collections import deque

# ─────────────────────────────────────────────
# 依赖检查 / Dependency availability flags
# ─────────────────────────────────────────────
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    np = None

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pygetwindow as gw
    GW_AVAILABLE = True
except ImportError:
    GW_AVAILABLE = False

try:
    from pynput import keyboard as pynput_kb
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# ─────────────────────────────────────────────
# 多语言字典 / i18n strings
# ─────────────────────────────────────────────
LANG = {
    "zh": {
        "title":             "🎮  BeamNG  云电脑视觉驾驶员",
        "lang_label":        "语言:",
        "status_idle":       "未启动",
        "status_starting":   "正在初始化……",
        "status_driving":    "视觉驾驶中",
        "status_paused":     "已暂停",
        "status_no_lane":    "未检测到车道",
        "fps_label":         "FPS: --",
        "fps_fmt":           "FPS: {fps}  偏移: {offset:+.2f}",
        "window_section":    " 🪟  游戏窗口 ",
        "window_label":      "选择云游戏窗口:",
        "refresh_btn":       " 刷新 ",
        "sensitivity_label": "转向灵敏度:",
        "yolo_toggle":       "启用 YOLOv8 障碍物检测（需更多 CPU）",
        "preview_section":   " 📷  实时画面（AI 视角）",
        "preview_waiting":   "等待画面……",
        "controls_section":  " ▶  控制 ",
        "launch_btn":        "🚀  启动视觉驾驶员",
        "pause_btn":         "⏸  暂停",
        "resume_btn":        "▶  继续",
        "stop_btn":          "⏹  停止",
        "always_on_top":     "窗口始终置顶",
        "log_section":       " 📋  日志 ",
        "quit_btn":          "✕  退出",
        # 对话框
        "err_no_cv2_title":  "缺少依赖",
        "err_no_cv2":        "未检测到 OpenCV！\n\n请先双击运行「install_vision.bat」，再重启本程序。",
        "err_no_mss_title":  "缺少依赖",
        "err_no_mss":        "未检测到 mss（屏幕截取库）！\n\n请先双击运行「install_vision.bat」。",
        "err_no_pynput_title": "缺少依赖",
        "err_no_pynput":     "未检测到 pynput（键盘模拟库）！\n\n请先双击运行「install_vision.bat」。",
        "err_no_window_title": "未找到窗口",
        "err_no_window":     "找不到名为「{title}」的窗口。\n\n请确认 GeForce Now 正在运行，然后点「刷新」重新选择。",
        "err_no_select":     "请先在下拉框中选择一个游戏窗口！",
        "confirm_exit_title":"确认退出",
        "confirm_exit":      "视觉驾驶员正在运行，确认退出吗？",
        # 日志消息
        "log_started":       "BeamNG 云电脑视觉驾驶员 v1.0 已启动",
        "log_dep_ok":        "✓  所有核心依赖已就绪",
        "log_dep_missing":   "⚠  缺少依赖库，请运行 install_vision.bat",
        "log_yolo_loading":  "正在加载 YOLOv8 模型（首次运行需下载 ~6MB）……",
        "log_yolo_ok":       "✓  YOLOv8 障碍物检测已就绪",
        "log_yolo_fail":     "⚠  YOLOv8 加载失败，已跳过障碍物检测",
        "log_win_found":     "✓  找到游戏窗口: {title}（{w}×{h}）",
        "log_win_fail":      "✗  找不到窗口: {title}",
        "log_driving":       "✓  视觉驾驶已启动！请将 BeamNG 设置为键盘控制模式。",
        "log_paused":        "⏸  驾驶已暂停（已松开所有按键）",
        "log_resumed":       "▶  驾驶已继续",
        "log_stopped":       "⏹  已停止",
        "log_no_lane":       "⚠  连续 {n} 帧未检测到车道线，保持当前方向",
        "log_obstacle":      "🚧  前方检测到障碍物，制动中……",
        "log_refresh_wins":  "已刷新窗口列表（共 {n} 个可见窗口）",
    },
    "en": {
        "title":             "🎮  BeamNG  Cloud Vision Driver",
        "lang_label":        "Language:",
        "status_idle":       "Not Started",
        "status_starting":   "Initializing…",
        "status_driving":    "Vision Driving",
        "status_paused":     "Paused",
        "status_no_lane":    "No Lane Detected",
        "fps_label":         "FPS: --",
        "fps_fmt":           "FPS: {fps}  Offset: {offset:+.2f}",
        "window_section":    " 🪟  Game Window ",
        "window_label":      "Select cloud gaming window:",
        "refresh_btn":       " Refresh ",
        "sensitivity_label": "Steering Sensitivity:",
        "yolo_toggle":       "Enable YOLOv8 Obstacle Detection (uses more CPU)",
        "preview_section":   " 📷  Live View (AI Vision)",
        "preview_waiting":   "Waiting for frame…",
        "controls_section":  " ▶  Controls ",
        "launch_btn":        "🚀  Start Vision Driver",
        "pause_btn":         "⏸  Pause",
        "resume_btn":        "▶  Resume",
        "stop_btn":          "⏹  Stop",
        "always_on_top":     "Always on top",
        "log_section":       " 📋  Log ",
        "quit_btn":          "✕  Quit",
        "err_no_cv2_title":  "Missing Dependency",
        "err_no_cv2":        "OpenCV not found!\n\nPlease run install_vision.bat first, then restart.",
        "err_no_mss_title":  "Missing Dependency",
        "err_no_mss":        "mss (screen capture) not found!\n\nRun install_vision.bat first.",
        "err_no_pynput_title": "Missing Dependency",
        "err_no_pynput":     "pynput (keyboard simulation) not found!\n\nRun install_vision.bat first.",
        "err_no_window_title": "Window Not Found",
        "err_no_window":     "Cannot find window: '{title}'\n\nMake sure GeForce Now is running, then click Refresh.",
        "err_no_select":     "Please select a game window from the dropdown first!",
        "confirm_exit_title":"Confirm Exit",
        "confirm_exit":      "Vision driver is running. Exit?",
        "log_started":       "BeamNG Cloud Vision Driver v1.0 started",
        "log_dep_ok":        "✓  All core dependencies ready",
        "log_dep_missing":   "⚠  Missing dependencies, run install_vision.bat",
        "log_yolo_loading":  "Loading YOLOv8 model (first run downloads ~6MB)…",
        "log_yolo_ok":       "✓  YOLOv8 obstacle detection ready",
        "log_yolo_fail":     "⚠  YOLOv8 failed to load, skipping obstacle detection",
        "log_win_found":     "✓  Found window: {title} ({w}×{h})",
        "log_win_fail":      "✗  Cannot find window: {title}",
        "log_driving":       "✓  Vision driving started! Make sure BeamNG uses keyboard controls.",
        "log_paused":        "⏸  Driving paused (all keys released)",
        "log_resumed":       "▶  Driving resumed",
        "log_stopped":       "⏹  Stopped",
        "log_no_lane":       "⚠  {n} consecutive frames without lanes, holding direction",
        "log_obstacle":      "🚧  Obstacle detected ahead, braking…",
        "log_refresh_wins":  "Window list refreshed ({n} visible windows found)",
    },
}

# ─────────────────────────────────────────────
# 颜色常量 / Color constants (same palette)
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# 颜色辅助 / Color helpers
# ─────────────────────────────────────────────
def _hex_lighten(color, factor=0.25):
    r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(
        min(255, int(r+(255-r)*factor)),
        min(255, int(g+(255-g)*factor)),
        min(255, int(b+(255-b)*factor)),
    )

def _hex_darken(color, factor=0.20):
    r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(
        max(0, int(r*(1-factor))),
        max(0, int(g*(1-factor))),
        max(0, int(b*(1-factor))),
    )


# ─────────────────────────────────────────────
# 圆角按钮 / Rounded button (same as main app)
# ─────────────────────────────────────────────
class RoundButton(tk.Canvas):
    def __init__(self, parent, text, bg, fg="white",
                 command=None, radius=10, font=None,
                 height=34, parent_bg=BG, **kwargs):
        super().__init__(parent, height=height, highlightthickness=0,
                         bd=0, bg=parent_bg, **kwargs)
        self._text      = text
        self._bg_normal = bg
        self._bg_hover  = _hex_lighten(bg, 0.22)
        self._bg_press  = _hex_darken(bg, 0.18)
        self._bg_dis    = _hex_darken(bg, 0.40)
        self._fg        = fg
        self._command   = command
        self._radius    = radius
        self._font      = font or ("Microsoft YaHei UI", 9)
        self._disabled  = False
        self._cur_bg    = bg
        self.bind("<Configure>",       self._redraw)
        self.bind("<Enter>",           self._on_enter)
        self.bind("<Leave>",           self._on_leave)
        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        super().config(cursor="hand2")
        self.after_idle(self._redraw)

    def _rrect(self, x0, y0, x1, y1, r, fill):
        for args in [
            (x0, y0, x0+2*r, y0+2*r, 90, 90),
            (x1-2*r, y0, x1, y0+2*r, 0, 90),
            (x0, y1-2*r, x0+2*r, y1, 180, 90),
            (x1-2*r, y1-2*r, x1, y1, 270, 90),
        ]:
            self.create_arc(*args[:4], start=args[4], extent=args[5],
                            fill=fill, outline=fill)
        self.create_rectangle(x0+r, y0, x1-r, y1, fill=fill, outline=fill)
        self.create_rectangle(x0, y0+r, x1, y1-r, fill=fill, outline=fill)

    def _redraw(self, _e=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        fill = self._bg_dis if self._disabled else self._cur_bg
        fg   = FG_DIM       if self._disabled else self._fg
        self._rrect(0, 0, w, h, self._radius, fill)
        self.create_text(w//2, h//2, text=self._text,
                         fill=fg, font=self._font, anchor="center")

    def _on_enter(self, _e):
        if not self._disabled:
            self._cur_bg = self._bg_hover; self._redraw()
    def _on_leave(self, _e):
        if not self._disabled:
            self._cur_bg = self._bg_normal; self._redraw()
    def _on_press(self, _e):
        if not self._disabled:
            self._cur_bg = self._bg_press; self._redraw()
    def _on_release(self, e):
        if not self._disabled:
            w, h = self.winfo_width(), self.winfo_height()
            inside = (0 <= e.x <= w and 0 <= e.y <= h)
            self._cur_bg = self._bg_hover if inside else self._bg_normal
            self._redraw()
            if inside and self._command:
                self._command()

    def config(self, **kw):
        state = kw.pop("state", None)
        text  = kw.pop("text",  None)
        if kw: super().config(**kw)
        if state is not None:
            self._disabled = (state == tk.DISABLED)
            self._cur_bg   = self._bg_normal
            super().config(cursor="" if self._disabled else "hand2")
            self._redraw()
        if text is not None:
            self._text = text; self._redraw()
    configure = config


# ─────────────────────────────────────────────
# 配置 / Config
# ─────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_vision.json")

DEFAULT_CONFIG = {
    "lang":              "zh",
    "window_title":      "NVIDIA GeForce NOW",
    "sensitivity":       1.0,       # 0.3 ~ 2.0
    "use_yolo":          True,
    "straight_threshold":0.08,      # lane offset < this → go straight
    "max_steer_offset":  0.45,      # offset at which full steering applied
    "roi_top_pct":       0.35,      # ignore top X% of frame (sky)
    "roi_bottom_pct":    0.85,      # ignore bottom X% of frame (car hood)
    "preview_width":     320,
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


# ═════════════════════════════════════════════
# 模块一：屏幕截取 / Screen Capture
# ═════════════════════════════════════════════

class WindowFinder:
    """找到并跟踪游戏窗口位置 / Locate and track the game window."""

    @staticmethod
    def list_all_titles():
        """返回所有可见窗口的标题列表 / List all visible window titles."""
        titles = []
        if GW_AVAILABLE:
            for w in gw.getAllWindows():
                t = w.title.strip()
                if t:
                    titles.append(t)
        else:
            # 备用：win32gui
            try:
                import win32gui
                def _cb(hwnd, lst):
                    if win32gui.IsWindowVisible(hwnd):
                        t = win32gui.GetWindowText(hwnd).strip()
                        if t:
                            lst.append(t)
                win32gui.EnumWindows(_cb, titles)
            except ImportError:
                pass
        # 去重并排序
        return sorted(set(titles))

    @staticmethod
    def get_region(title):
        """
        根据标题返回窗口区域字典（left, top, width, height）。
        找不到时返回 None。
        """
        if GW_AVAILABLE:
            matches = gw.getWindowsWithTitle(title)
            if matches:
                w = matches[0]
                # 有些窗口宽高为负值（最小化），跳过
                if w.width > 0 and w.height > 0:
                    return {"left": w.left, "top": w.top,
                            "width": w.width, "height": w.height}
        else:
            try:
                import win32gui
                hwnd = win32gui.FindWindow(None, title)
                if hwnd:
                    rect = win32gui.GetWindowRect(hwnd)
                    x1, y1, x2, y2 = rect
                    if x2 - x1 > 0 and y2 - y1 > 0:
                        return {"left": x1, "top": y1,
                                "width": x2 - x1, "height": y2 - y1}
            except ImportError:
                pass
        return None


class ScreenCapture:
    """用 mss 截取游戏窗口的每一帧 / Capture frames from game window using mss."""

    def __init__(self, window_title, log_fn):
        self.window_title = window_title
        self.log = log_fn
        self.region = None
        self._sct = None
        self._last_region_update = 0.0

    def find_window(self):
        """定位窗口，成功返回 True / Locate window; returns True on success."""
        region = WindowFinder.get_region(self.window_title)
        if region:
            self.region = region
            if self._sct is None:
                self._sct = mss.mss()
            self.log(self._fmt("log_win_found",
                               title=self.window_title,
                               w=region["width"], h=region["height"]))
            return True
        self.log(self._fmt("log_win_fail", title=self.window_title))
        return False

    def _fmt(self, key, **kw):
        # 简单格式化，不依赖 GUI 语言状态
        return LANG["zh"][key].format(**kw) if kw else LANG["zh"][key]

    def capture(self):
        """
        截取当前帧，返回 BGR numpy 数组。
        失败时返回 None。
        """
        if self._sct is None or self.region is None:
            return None

        # 每隔 3 秒刷新一次窗口位置（防止用户拖动窗口）
        now = time.time()
        if now - self._last_region_update > 3.0:
            updated = WindowFinder.get_region(self.window_title)
            if updated:
                self.region = updated
            self._last_region_update = now

        try:
            shot = self._sct.grab(self.region)
            # mss 返回 BGRA，转 BGR
            frame = np.array(shot)
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        except Exception:
            return None


# ═════════════════════════════════════════════
# 模块二：车道线检测 / Lane Detection
# ═════════════════════════════════════════════

class LaneDetector:
    """
    基于 OpenCV 的车道线检测器。
    OpenCV-based lane line detector.

    算法流程 / Algorithm:
      1. 截取感兴趣区域（ROI）：画面下半部分
      2. HLS 颜色空间提取白色/黄色车道标线
      3. Canny 边缘检测
      4. Hough 概率变换找直线
      5. 按斜率分左/右车道线，取中值平均
      6. 计算车道中心相对于画面中心的偏移量
      7. 输出带可视化叠加的帧
    """

    def __init__(self, config: Config):
        self.config = config
        self._smooth_buf = deque(maxlen=12)   # 平滑偏移量
        self._last_offset = 0.0

    def detect(self, frame):
        """
        主检测入口。

        Returns dict:
          offset    : float, -1.0 ~ +1.0
                      正值 = 车辆偏左，需右转
                      负值 = 车辆偏右，需左转
          confidence: float 0.0 ~ 1.0
          overlay   : BGR ndarray（带检测可视化）
          detected  : bool
        """
        h, w = frame.shape[:2]
        roi_top    = int(h * self.config.get("roi_top_pct"))
        roi_bottom = int(h * self.config.get("roi_bottom_pct"))

        roi = frame[roi_top:roi_bottom, :]
        overlay = frame.copy()

        # ── Step 1: 提取边缘
        edge_map = self._preprocess(roi)

        # ── Step 2: Hough 直线
        lines = cv2.HoughLinesP(
            edge_map,
            rho=2, theta=np.pi / 180,
            threshold=35,
            minLineLength=35,
            maxLineGap=160,
        )

        offset = 0.0
        confidence = 0.0

        if lines is not None and len(lines) > 0:
            left_fit, right_fit = self._classify_lines(lines, roi.shape)
            left_x  = self._eval_at_bottom(left_fit,  roi.shape[0])
            right_x = self._eval_at_bottom(right_fit, roi.shape[0])

            if left_x is not None and right_x is not None:
                lane_cx = (left_x + right_x) / 2
                offset  = (lane_cx - w / 2) / (w / 2)
                confidence = 0.90
                self._draw_fit(overlay, left_fit,  roi_top, roi_bottom, (0, 220, 80))
                self._draw_fit(overlay, right_fit, roi_top, roi_bottom, (0, 220, 80))
                self._draw_center(overlay, int(lane_cx), roi_top, roi_bottom)

            elif left_x is not None:
                # 只看到左侧车道线，估算中心在右
                offset = (left_x - w * 0.25) / (w / 2)
                confidence = 0.55
                self._draw_fit(overlay, left_fit, roi_top, roi_bottom, (0, 200, 200))

            elif right_x is not None:
                # 只看到右侧车道线，估算中心在左
                offset = (right_x - w * 0.75) / (w / 2)
                confidence = 0.55
                self._draw_fit(overlay, right_fit, roi_top, roi_bottom, (0, 200, 200))

        # ── 回退：道路色彩检测
        if confidence < 0.4:
            fb_offset, fb_conf = self._road_color_fallback(roi, w)
            if fb_conf > confidence:
                offset     = fb_offset
                confidence = fb_conf

        # ── 平滑
        self._smooth_buf.append(offset)
        smoothed = sum(self._smooth_buf) / len(self._smooth_buf)
        self._last_offset = smoothed

        # ── HUD 叠加信息
        self._draw_hud(overlay, smoothed, confidence, roi_top, roi_bottom, w)

        return {
            "offset":     smoothed,
            "confidence": confidence,
            "overlay":    overlay,
            "detected":   confidence > 0.35,
        }

    # ── 预处理 ────────────────────────────────
    def _preprocess(self, roi):
        h, w = roi.shape[:2]

        # HLS 颜色空间提取白/黄标线
        hls = cv2.cvtColor(roi, cv2.COLOR_BGR2HLS)
        white_mask  = cv2.inRange(hls,
            np.array([0, 180, 0]),
            np.array([180, 255, 255]))
        yellow_mask = cv2.inRange(hls,
            np.array([10, 90, 80]),
            np.array([40, 210, 255]))
        color_mask = cv2.bitwise_or(white_mask, yellow_mask)

        # Canny 边缘
        gray    = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges   = cv2.Canny(blurred, 40, 130)

        combined = cv2.bitwise_or(color_mask, edges)

        # 梯形 ROI 遮罩（去掉画面两侧极端区域）
        mask = np.zeros_like(combined)
        pts  = np.array([[
            (int(w * 0.02), h),
            (int(w * 0.42), int(h * 0.05)),
            (int(w * 0.58), int(h * 0.05)),
            (int(w * 0.98), h),
        ]], dtype=np.int32)
        cv2.fillPoly(mask, pts, 255)

        return cv2.bitwise_and(combined, mask)

    # ── 直线分类 ──────────────────────────────
    def _classify_lines(self, lines, shape):
        """将 Hough 直线按位置+斜率分为左/右，返回多项式拟合参数。"""
        h, w = shape[:2]
        left_pts, right_pts = [], []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            slope = (y2 - y1) / (x2 - x1)
            # 过滤接近水平的线（斜率绝对值太小为噪声）
            if abs(slope) < 0.25 or abs(slope) > 6.0:
                continue
            # 左侧：负斜率且 x 偏左；右侧：正斜率且 x 偏右
            midx = (x1 + x2) / 2
            if slope < 0 and midx < w * 0.55:
                left_pts.extend([(x1, y1), (x2, y2)])
            elif slope > 0 and midx > w * 0.45:
                right_pts.extend([(x1, y1), (x2, y2)])

        left_fit  = self._polyfit(left_pts,  h)
        right_fit = self._polyfit(right_pts, h)
        return left_fit, right_fit

    def _polyfit(self, pts, h):
        """对点集做一次多项式拟合，返回 (slope, intercept) 或 None。"""
        if len(pts) < 4:
            return None
        xs = np.array([p[0] for p in pts], dtype=float)
        ys = np.array([p[1] for p in pts], dtype=float)
        try:
            coeffs = np.polyfit(ys, xs, 1)   # x = a*y + b
            return coeffs  # [a, b]
        except Exception:
            return None

    def _eval_at_bottom(self, coeffs, roi_h):
        """在 ROI 底部求 x 坐标。"""
        if coeffs is None:
            return None
        return float(coeffs[0] * roi_h + coeffs[1])

    # ── 绘制辅助 ──────────────────────────────
    def _draw_fit(self, frame, coeffs, roi_top, roi_bottom, color):
        if coeffs is None:
            return
        roi_h = roi_bottom - roi_top
        y1_rel, y2_rel = roi_h, int(roi_h * 0.05)
        x1 = int(coeffs[0] * y1_rel + coeffs[1])
        x2 = int(coeffs[0] * y2_rel + coeffs[1])
        cv2.line(frame,
                 (x1, y1_rel + roi_top),
                 (x2, y2_rel + roi_top),
                 color, 3, cv2.LINE_AA)

    def _draw_center(self, frame, cx, roi_top, roi_bottom):
        """画车道中心线和画面中心线。"""
        h = frame.shape[0]
        w = frame.shape[1]
        mid_y_top = roi_top + int((roi_bottom - roi_top) * 0.15)

        # 黄色：车道中心
        cv2.line(frame, (cx, roi_bottom), (cx, mid_y_top),
                 (0, 255, 255), 2, cv2.LINE_AA)
        # 蓝色：画面中心
        cv2.line(frame, (w // 2, roi_bottom), (w // 2, mid_y_top),
                 (255, 100, 0), 1, cv2.LINE_AA)

    def _draw_hud(self, frame, offset, conf, roi_top, roi_bottom, w):
        """在画面上方叠加状态信息。"""
        bar_h = 28
        cv2.rectangle(frame, (0, 0), (w, bar_h), (20, 20, 40), -1)

        # 偏移指示条
        bar_w   = min(w - 20, 300)
        bar_x   = (w - bar_w) // 2
        bar_y   = 6
        bar_mid = bar_x + bar_w // 2
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 14),
                      (50, 50, 70), -1)
        # 指针位置
        ptr_x = int(bar_mid + offset * (bar_w // 2))
        ptr_x = max(bar_x + 2, min(bar_x + bar_w - 2, ptr_x))
        color = (0, 220, 80) if conf > 0.6 else (200, 200, 0) if conf > 0.3 else (80, 80, 80)
        cv2.circle(frame, (ptr_x, bar_y + 7), 6, color, -1)
        # 中心刻度
        cv2.line(frame, (bar_mid, bar_y + 2), (bar_mid, bar_y + 12), (180, 180, 180), 1)

        # 文字
        label = f"Offset: {offset:+.2f}  Conf: {conf:.0%}"
        cv2.putText(frame, label, (6, bar_h - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        # ROI 边界框（半透明）
        cv2.rectangle(frame, (0, roi_top), (w - 1, roi_bottom),
                      (60, 60, 120), 1)

    # ── 道路颜色回退 ──────────────────────────
    def _road_color_fallback(self, roi, frame_w):
        """
        当无法检测到车道线时，通过路面颜色找道路中心。
        BeamNG 中路面通常比草地/泥土更深（灰色沥青）。
        """
        try:
            h, w = roi.shape[:2]
            lower_roi = roi[h // 2:, :]
            gray = cv2.cvtColor(lower_roi, cv2.COLOR_BGR2GRAY)

            # 自适应阈值：找比较暗的区域（路面）
            _, thresh = cv2.threshold(gray, 0, 255,
                                      cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            # 形态学去噪
            kernel = np.ones((5, 5), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            M = cv2.moments(thresh)
            if M["m00"] > 500:
                cx = M["m10"] / M["m00"]
                offset = (cx - w / 2) / (w / 2)
                return float(offset), 0.38
        except Exception:
            pass
        return 0.0, 0.10


# ═════════════════════════════════════════════
# 模块三：障碍物检测 / Obstacle Detection (YOLO)
# ═════════════════════════════════════════════

class ObstacleDetector:
    """
    可选的 YOLOv8 障碍物检测器。
    Optional YOLOv8-based obstacle detector.

    检测范围：画面中央车道区域（横向 30%~70%）内的车辆类目标。
    Detection zone: center lane area (30%~70% width) for vehicle-class objects.
    """

    # COCO 类别 ID：car=2, bus=5, truck=7, motorcycle=3
    VEHICLE_CLASSES = [2, 3, 5, 7]

    def __init__(self, log_fn):
        self.log = log_fn
        self.model = None
        self.available = False
        self._load()

    def _load(self):
        if not YOLO_AVAILABLE:
            return
        self.log(LANG["zh"]["log_yolo_loading"])
        try:
            self.model = YOLO("yolov8n.pt")  # ~6MB，首次自动下载
            # 预热：空跑一帧
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            self.model(dummy, verbose=False)
            self.available = True
            self.log(LANG["zh"]["log_yolo_ok"])
        except Exception as e:
            self.log(f"{LANG['zh']['log_yolo_fail']}: {e}")

    def detect(self, frame):
        """
        Returns list of obstacle dicts:
          bbox      : (x1, y1, x2, y2)
          proximity : float 0~1, 1 = immediately ahead
          cls_name  : str
        """
        if not self.available or self.model is None:
            return []

        h, w = frame.shape[:2]
        lane_left  = int(w * 0.28)
        lane_right = int(w * 0.72)

        try:
            results = self.model(
                frame,
                conf=0.38,
                classes=self.VEHICLE_CLASSES,
                verbose=False,
                imgsz=320,          # 小尺寸加快推理
            )
        except Exception:
            return []

        obstacles = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                cx = (x1 + x2) / 2
                # 只关注处于我方车道内的障碍物
                if not (lane_left <= cx <= lane_right):
                    continue
                # proximity：障碍物底部距画面底部的比例（越大越近）
                proximity = y2 / h
                if proximity > 0.25:
                    obstacles.append({
                        "bbox":      (x1, y1, x2, y2),
                        "proximity": proximity,
                        "cls_name":  r.names[int(box.cls[0])],
                    })

        return obstacles


# ═════════════════════════════════════════════
# 模块四：键盘控制器 / Keyboard Controller
# ═════════════════════════════════════════════

class KeyboardController:
    """
    模拟键盘按键控制 BeamNG 车辆。
    Simulates keyboard input to control the BeamNG vehicle.

    采用 PWM（脉宽调制）实现比例转向：
    Uses PWM (Pulse Width Modulation) for proportional steering:
      - 小偏移 → 短按方向键（占空比低）
      - 大偏移 → 长按方向键（占空比高）
    """

    # PWM 参数：每 200ms 为一个周期，分 10 个 tick
    _PWM_PERIOD_MS  = 200
    _PWM_TICKS      = 10
    _TICK_INTERVAL  = _PWM_PERIOD_MS / 1000.0 / _PWM_TICKS   # 20ms

    def __init__(self):
        if not PYNPUT_AVAILABLE:
            raise RuntimeError("pynput not available")
        self._ctrl       = pynput_kb.Controller()
        self._held       = set()          # 当前按住的键
        self._lock       = threading.Lock()
        self._stop_evt   = threading.Event()
        self._thread     = None

        # 当前控制指令（由外部 set_control 更新）
        self._direction  = "straight"     # "left" | "right" | "straight"
        self._intensity  = 0.0            # 0.0 ~ 1.0
        self._throttle   = False
        self._brake      = False

    def set_control(self, direction, intensity,
                     throttle=True, brake=False):
        """由驾驶逻辑线程调用，更新控制指令（线程安全）。"""
        with self._lock:
            self._direction = direction
            self._intensity = max(0.0, min(1.0, float(intensity)))
            self._throttle  = throttle
            self._brake     = brake

    def start(self):
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._pwm_loop, daemon=True, name="KeyboardCtrl"
        )
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        time.sleep(self._TICK_INTERVAL * 2)
        self.release_all()

    def release_all(self):
        with self._lock:
            for k in list(self._held):
                try:
                    self._ctrl.release(k)
                except Exception:
                    pass
            self._held.clear()

    # ── PWM 主循环（50 Hz）────────────────────
    def _pwm_loop(self):
        tick = 0
        STEER_MAP = {"left": "a", "right": "d"}

        while not self._stop_evt.is_set():
            with self._lock:
                direction = self._direction
                intensity = self._intensity
                throttle  = self._throttle
                brake     = self._brake

            # ── 油门 / 刹车 ──────────────────
            if brake:
                self._release_key("w")
                self._press_key("s")
            elif throttle:
                self._release_key("s")
                self._press_key("w")
            else:
                self._release_key("w")
                self._release_key("s")

            # ── 转向 PWM ─────────────────────
            steer_key = STEER_MAP.get(direction)
            other_key = "d" if direction == "left" else \
                        "a" if direction == "right" else None

            # 先松开对侧方向键
            if other_key:
                self._release_key(other_key)

            if steer_key and intensity > 0.0:
                # 在一个 PWM 周期内，前 intensity * TICKS 个 tick 按键
                if tick < intensity * self._PWM_TICKS:
                    self._press_key(steer_key)
                else:
                    self._release_key(steer_key)
            else:
                self._release_key("a")
                self._release_key("d")

            tick = (tick + 1) % self._PWM_TICKS
            time.sleep(self._TICK_INTERVAL)

    def _press_key(self, k):
        if k not in self._held:
            try:
                self._ctrl.press(k)
                self._held.add(k)
            except Exception:
                pass

    def _release_key(self, k):
        if k in self._held:
            try:
                self._ctrl.release(k)
                self._held.discard(k)
            except Exception:
                pass


# ═════════════════════════════════════════════
# 模块五：视觉驾驶员主控 / Vision AI Driver
# ═════════════════════════════════════════════

class VisionAIDriver:
    """
    整合所有模块，管理驾驶线程。
    Orchestrates all modules and manages driving threads.
    """

    _NO_LANE_WARN_INTERVAL = 30   # 每 N 帧无车道线才记一条日志

    def __init__(self, config: Config, log_fn):
        self.config  = config
        self.log     = log_fn

        # 组件
        self.screen_cap  = None
        self.lane_det    = None
        self.obs_det     = None
        self.kb_ctrl     = None

        # 状态
        self.running    = False
        self.paused     = False
        self.connected  = False

        # 统计
        self.current_offset  = 0.0
        self.current_conf    = 0.0
        self.fps             = 0
        self._no_lane_count  = 0
        self._obstacle_active = False

        # 队列
        self._frame_q   = queue.Queue(maxsize=3)
        self._preview_q = queue.Queue(maxsize=2)

        self._stop_evt  = threading.Event()

    # ── 启动 ──────────────────────────────────
    def start(self, window_title: str, sensitivity: float,
              use_yolo: bool) -> bool:
        """初始化并启动所有驾驶线程。"""
        # 1. 屏幕截取
        self.screen_cap = ScreenCapture(window_title, self.log)
        if not self.screen_cap.find_window():
            return False

        # 2. 车道检测
        self.lane_det = LaneDetector(self.config)

        # 3. 障碍物检测（可选）
        if use_yolo:
            self.obs_det = ObstacleDetector(self.log)

        # 4. 键盘控制器
        try:
            self.kb_ctrl = KeyboardController()
            self.kb_ctrl.start()
        except RuntimeError as e:
            self.log(f"✗ 键盘控制器启动失败: {e}")
            return False

        # 更新配置里的灵敏度
        self.config.set("sensitivity", sensitivity)

        # 5. 启动线程
        self.running   = True
        self.paused    = False
        self.connected = True
        self._stop_evt.clear()
        self._no_lane_count = 0

        threading.Thread(target=self._capture_loop,
                         daemon=True, name="Capture").start()
        threading.Thread(target=self._process_loop,
                         daemon=True, name="Process").start()

        self.log(LANG["zh"]["log_driving"])
        return True

    # ── 截帧线程（~30 fps）────────────────────
    def _capture_loop(self):
        interval = 1.0 / 30
        while not self._stop_evt.is_set():
            t0 = time.time()
            frame = self.screen_cap.capture()
            if frame is not None:
                try:
                    self._frame_q.put_nowait(frame)
                except queue.Full:
                    try:
                        self._frame_q.get_nowait()   # 丢掉最旧的一帧
                        self._frame_q.put_nowait(frame)
                    except queue.Empty:
                        pass
            elapsed = time.time() - t0
            wait = interval - elapsed
            if wait > 0:
                time.sleep(wait)

    # ── 处理线程（~15 fps）────────────────────
    def _process_loop(self):
        interval   = 1.0 / 15
        fps_count  = 0
        fps_timer  = time.time()

        straight_th = self.config.get("straight_threshold")
        max_offset  = self.config.get("max_steer_offset")

        while not self._stop_evt.is_set():
            t0 = time.time()

            try:
                frame = self._frame_q.get(timeout=0.15)
            except queue.Empty:
                continue

            # ── 车道检测 ──────────────────────
            result = self.lane_det.detect(frame)
            self.current_offset = result["offset"]
            self.current_conf   = result["confidence"]
            overlay = result["overlay"]

            # ── 障碍物检测 ────────────────────
            obstacles    = []
            brake_needed = False
            if self.obs_det and self.obs_det.available:
                obstacles    = self.obs_det.detect(frame)
                brake_needed = any(o["proximity"] > 0.62 for o in obstacles)
                if brake_needed and not self._obstacle_active:
                    self.log(LANG["zh"]["log_obstacle"])
                    self._obstacle_active = True
                elif not brake_needed:
                    self._obstacle_active = False

            # ── 无车道线计数 ──────────────────
            if not result["detected"]:
                self._no_lane_count += 1
                if self._no_lane_count % self._NO_LANE_WARN_INTERVAL == 0:
                    self.log(LANG["zh"]["log_no_lane"]
                             .format(n=self._no_lane_count))
            else:
                self._no_lane_count = 0

            # ── 控制决策（暂停时不输出）────────
            if not self.paused:
                sensitivity = self.config.get("sensitivity")
                offset = result["offset"]

                if brake_needed:
                    self.kb_ctrl.set_control("straight", 0.0,
                                              throttle=False, brake=True)
                elif abs(offset) <= straight_th:
                    # 直行
                    self.kb_ctrl.set_control("straight", 0.0,
                                              throttle=True, brake=False)
                else:
                    # 比例转向
                    direction = "right" if offset > 0 else "left"
                    raw_err   = abs(offset) - straight_th
                    intensity = min(raw_err / (max_offset - straight_th)
                                    * sensitivity, 1.0)
                    self.kb_ctrl.set_control(direction, intensity,
                                              throttle=True, brake=False)

            # ── 绘制障碍物框 ──────────────────
            for obs in obstacles:
                x1, y1, x2, y2 = obs["bbox"]
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 40, 255), 2)
                cv2.putText(overlay,
                            f"{obs['cls_name']} {obs['proximity']:.2f}",
                            (x1, max(y1 - 6, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                            (80, 120, 255), 1, cv2.LINE_AA)

            # ── 推送预览帧 ────────────────────
            pw = self.config.get("preview_width")
            ph = int(pw * overlay.shape[0] / overlay.shape[1])
            try:
                small = cv2.resize(overlay, (pw, ph),
                                   interpolation=cv2.INTER_LINEAR)
                rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                self._preview_q.put_nowait(rgb)
            except (queue.Full, Exception):
                pass

            # ── FPS ───────────────────────────
            fps_count += 1
            if time.time() - fps_timer >= 1.0:
                self.fps    = fps_count
                fps_count   = 0
                fps_timer   = time.time()

            wait = interval - (time.time() - t0)
            if wait > 0:
                time.sleep(wait)

    # ── 控制接口 ──────────────────────────────
    def pause(self):
        self.paused = True
        if self.kb_ctrl:
            self.kb_ctrl.set_control("straight", 0.0,
                                      throttle=False, brake=False)
            self.kb_ctrl.release_all()
        self.log(LANG["zh"]["log_paused"])

    def resume(self):
        self.paused = False
        self.log(LANG["zh"]["log_resumed"])

    def stop(self):
        self._stop_evt.set()
        if self.kb_ctrl:
            self.kb_ctrl.stop()
        self.running   = False
        self.connected = False
        self.paused    = False
        self.log(LANG["zh"]["log_stopped"])

    def get_preview(self):
        """非阻塞取预览帧（RGB ndarray 或 None）。"""
        try:
            return self._preview_q.get_nowait()
        except queue.Empty:
            return None


# ═════════════════════════════════════════════
# 模块六：图形界面 / GUI Control Panel
# ═════════════════════════════════════════════

class ControlPanel:
    def __init__(self):
        self.config    = Config()
        self._lang     = self.config.get("lang") or "zh"
        self._ui_state = "idle"     # idle | starting | driving | paused
        self._paused   = False

        self.driver = VisionAIDriver(self.config, self._log)

        self.root = tk.Tk()
        self._build_window()
        self._build_ui()
        self._set_state("idle")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 翻译 ──────────────────────────────────
    def T(self, key, **kw):
        text = LANG[self._lang].get(key, key)
        if kw:
            try:
                text = text.format(**kw)
            except Exception:
                pass
        return text

    # ── 语言切换 ──────────────────────────────
    def _switch_lang(self, _=None):
        self._lang = "zh" if self._lang_var.get() == "中文" else "en"
        self.config.set("lang", self._lang)
        self._apply_lang()

    def _apply_lang(self):
        T = self.T
        self.root.title("BeamNG Cloud Vision Driver v1.0")
        self._title_lbl.config(text=T("title"))
        self._lang_lbl.config(text=T("lang_label"))
        self._win_frame.configure(text=T("window_section"))
        self._win_lbl.config(text=T("window_label"))
        self._refresh_btn.config(text=T("refresh_btn"))
        self._sens_lbl.config(text=T("sensitivity_label"))
        self._yolo_cb.config(text=T("yolo_toggle"))
        self._preview_frame.configure(text=T("preview_section"))
        self._ctrl_frame.configure(text=T("controls_section"))
        self._log_frame.configure(text=T("log_section"))
        self._launch_btn.config(text=T("launch_btn"))
        self._stop_btn.config(text=T("stop_btn"))
        self._topmost_cb.config(text=T("always_on_top"))
        self._quit_btn.config(text=T("quit_btn"))
        # 暂停按钮
        if self._ui_state == "paused":
            self._pause_btn.config(text=T("resume_btn"))
        else:
            self._pause_btn.config(text=T("pause_btn"))
        # 状态栏
        if self._ui_state == "idle":
            self._status_lbl.config(text=T("status_idle"))
            self._info_lbl.config(text=T("fps_label"))

    # ── 窗口属性 ──────────────────────────────
    def _build_window(self):
        self.root.title("BeamNG Cloud Vision Driver v1.0")
        self.root.geometry("460x760")
        self.root.minsize(400, 680)
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
        style.map("TCombobox",
                   fieldbackground=[("readonly", BG2)])
        style.configure("TScale", background=BG, troughcolor=BG2)

        outer = ttk.Frame(self.root)
        outer.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        # ── 标题 + 语言 ───────────────────────
        hdr = tk.Frame(outer, bg=BG)
        hdr.pack(fill=tk.X, pady=(0, 8))
        self._title_lbl = tk.Label(
            hdr, text=self.T("title"),
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=BG, fg=ACCENT,
        )
        self._title_lbl.pack(side=tk.LEFT, expand=True, anchor="w")
        lf = tk.Frame(hdr, bg=BG)
        lf.pack(side=tk.RIGHT)
        self._lang_lbl = tk.Label(lf, text=self.T("lang_label"),
                                   bg=BG, fg=FG_DIM,
                                   font=("Microsoft YaHei UI", 8))
        self._lang_lbl.pack(side=tk.LEFT)
        disp = "中文" if self._lang == "zh" else "English"
        self._lang_var = tk.StringVar(value=disp)
        self._lang_cb  = ttk.Combobox(lf, textvariable=self._lang_var,
                                       values=["中文", "English"],
                                       width=7, state="readonly")
        self._lang_cb.pack(side=tk.LEFT, padx=(4, 0))
        self._lang_cb.bind("<<ComboboxSelected>>", self._switch_lang)

        # ── 状态栏 ────────────────────────────
        sb = tk.Frame(outer, bg=BG2, relief="flat")
        sb.pack(fill=tk.X, pady=(0, 8))
        inner = tk.Frame(sb, bg=BG2)
        inner.pack(fill=tk.X, padx=12, pady=8)
        self._dot = tk.Label(inner, text="●",
                              font=("Arial", 16), bg=BG2, fg="#444444")
        self._dot.pack(side=tk.LEFT)
        txt = tk.Frame(inner, bg=BG2)
        txt.pack(side=tk.LEFT, padx=(10, 0))
        self._status_lbl = tk.Label(txt, text=self.T("status_idle"),
                                     font=("Microsoft YaHei UI", 11, "bold"),
                                     bg=BG2, fg=FG_DIM)
        self._status_lbl.pack(anchor="w")
        self._info_lbl = tk.Label(txt, text=self.T("fps_label"),
                                   font=("Microsoft YaHei UI", 9),
                                   bg=BG2, fg=FG_DIM)
        self._info_lbl.pack(anchor="w")

        # ── 窗口选择 ──────────────────────────
        self._win_frame = ttk.LabelFrame(
            outer, text=self.T("window_section"), padding=(10, 6))
        self._win_frame.pack(fill=tk.X, pady=(0, 6))
        wf = self._win_frame

        self._win_lbl = tk.Label(wf, text=self.T("window_label"),
                                  bg=BG, fg=FG_DIM,
                                  font=("Microsoft YaHei UI", 8))
        self._win_lbl.pack(anchor="w")

        wr = tk.Frame(wf, bg=BG)
        wr.pack(fill=tk.X, pady=(3, 6))
        self._win_var = tk.StringVar(value=self.config.get("window_title"))
        self._win_cb = ttk.Combobox(wr, textvariable=self._win_var,
                                     state="normal", width=32)
        self._win_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._refresh_btn = RoundButton(
            wr, text=self.T("refresh_btn"), bg="#1e3050", fg=FG,
            command=self._refresh_windows,
            radius=6, height=26, parent_bg=BG,
            font=("Microsoft YaHei UI", 8), width=60,
        )
        self._refresh_btn.pack(side=tk.LEFT, padx=(6, 0))

        # 灵敏度
        sr = tk.Frame(wf, bg=BG)
        sr.pack(fill=tk.X)
        self._sens_lbl = tk.Label(sr, text=self.T("sensitivity_label"),
                                   bg=BG, fg=FG_DIM,
                                   font=("Microsoft YaHei UI", 8))
        self._sens_lbl.pack(side=tk.LEFT)
        self._sens_val = tk.Label(sr,
                                   text=f"{self.config.get('sensitivity'):.1f}",
                                   bg=BG, fg=ACCENT, width=4,
                                   font=("Microsoft YaHei UI", 9, "bold"))
        self._sens_scale = ttk.Scale(
            sr, from_=0.3, to=2.0, orient=tk.HORIZONTAL,
            command=self._on_sens_drag,
        )
        self._sens_scale.set(self.config.get("sensitivity"))
        self._sens_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self._sens_val.pack(side=tk.LEFT)

        # YOLO 开关
        self._yolo_var = tk.BooleanVar(value=self.config.get("use_yolo"))
        self._yolo_cb  = tk.Checkbutton(
            wf, text=self.T("yolo_toggle"),
            variable=self._yolo_var,
            bg=BG, fg=FG_DIM, selectcolor=BG2,
            activebackground=BG, activeforeground=FG,
            font=("Microsoft YaHei UI", 8),
        )
        self._yolo_cb.pack(anchor="w", pady=(4, 0))

        # ── 实时预览 ──────────────────────────
        self._preview_frame = ttk.LabelFrame(
            outer, text=self.T("preview_section"), padding=(6, 4))
        self._preview_frame.pack(fill=tk.X, pady=(0, 6))

        pw = self.config.get("preview_width")
        ph = int(pw * 9 / 16)   # 默认 16:9 比例

        self._preview_canvas = tk.Canvas(
            self._preview_frame,
            width=pw, height=ph,
            bg=BG3, highlightthickness=0,
        )
        self._preview_canvas.pack()
        self._preview_canvas.create_text(
            pw // 2, ph // 2,
            text=self.T("preview_waiting"),
            fill=FG_DIM, font=("Microsoft YaHei UI", 9),
            tags="waiting_text",
        )
        self._preview_img_ref = None   # 防止被 GC

        # ── 控制按钮 ──────────────────────────
        self._ctrl_frame = ttk.LabelFrame(
            outer, text=self.T("controls_section"), padding=(10, 8))
        self._ctrl_frame.pack(fill=tk.X, pady=(0, 6))
        cf = self._ctrl_frame

        self._launch_btn = RoundButton(
            cf, text=self.T("launch_btn"), bg=BTN_BLU, fg="white",
            command=self._launch,
            radius=10, height=42, parent_bg=BG,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self._launch_btn.pack(fill=tk.X, pady=(0, 8))

        row2 = tk.Frame(cf, bg=BG)
        row2.pack(fill=tk.X)

        self._pause_btn = RoundButton(
            row2, text=self.T("pause_btn"), bg=BTN_GRN, fg="white",
            command=self._toggle_pause,
            radius=10, height=36, parent_bg=BG,
        )
        self._pause_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self._stop_btn = RoundButton(
            row2, text=self.T("stop_btn"), bg=BTN_RED, fg="white",
            command=self._stop,
            radius=10, height=36, parent_bg=BG,
        )
        self._stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 置顶选项
        opt = tk.Frame(outer, bg=BG)
        opt.pack(fill=tk.X, pady=(0, 4))
        self._topmost_var = tk.BooleanVar(value=True)
        self._topmost_cb = tk.Checkbutton(
            opt, text=self.T("always_on_top"),
            variable=self._topmost_var,
            command=lambda: self.root.attributes(
                "-topmost", self._topmost_var.get()),
            bg=BG, fg=FG_DIM, selectcolor=BG2,
            activebackground=BG, activeforeground=FG,
            font=("Microsoft YaHei UI", 8),
        )
        self._topmost_cb.pack(side=tk.LEFT)

        # ── 日志 ──────────────────────────────
        self._log_frame = ttk.LabelFrame(
            outer, text=self.T("log_section"), padding=(8, 4))
        self._log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self._log_box = scrolledtext.ScrolledText(
            self._log_frame, height=5,
            font=("Consolas", 8),
            bg=BG3, fg="#c9d1d9",
            insertbackground="white",
            relief="flat", state=tk.DISABLED,
        )
        self._log_box.pack(fill=tk.BOTH, expand=True)

        # ── 退出 ──────────────────────────────
        self._quit_btn = RoundButton(
            outer, text=self.T("quit_btn"), bg=BTN_RED, fg="#ff9999",
            command=self._on_close,
            radius=10, height=34, parent_bg=BG,
            font=("Microsoft YaHei UI", 9),
        )
        self._quit_btn.pack(fill=tk.X)

        # 初始化窗口下拉列表
        self.root.after(200, self._refresh_windows)

    # ── UI 状态机 ─────────────────────────────
    def _set_state(self, state: str):
        self._ui_state = state
        T = self.T
        EN, DIS = tk.NORMAL, tk.DISABLED

        if state == "idle":
            self._launch_btn.config(state=EN)
            self._pause_btn.config(state=DIS, text=T("pause_btn"))
            self._stop_btn.config(state=DIS)
            self._win_cb.config(state="normal")
            self._dot.config(fg="#444444")
            self._status_lbl.config(text=T("status_idle"), fg=FG_DIM)
            self._info_lbl.config(text=T("fps_label"), fg=FG_DIM)

        elif state == "starting":
            self._launch_btn.config(state=DIS)
            self._pause_btn.config(state=DIS)
            self._stop_btn.config(state=DIS)
            self._win_cb.config(state="disabled")
            self._dot.config(fg=YELLOW)
            self._status_lbl.config(text=T("status_starting"), fg=YELLOW)

        elif state == "driving":
            self._launch_btn.config(state=DIS)
            self._pause_btn.config(state=EN, text=T("pause_btn"))
            self._stop_btn.config(state=EN)
            self._win_cb.config(state="disabled")
            self._dot.config(fg=GREEN)
            self._status_lbl.config(text=T("status_driving"), fg=GREEN)

        elif state == "paused":
            self._launch_btn.config(state=DIS)
            self._pause_btn.config(state=EN, text=T("resume_btn"))
            self._stop_btn.config(state=EN)
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

    # ── 辅助动作 ──────────────────────────────
    def _refresh_windows(self):
        titles = WindowFinder.list_all_titles()
        self._win_cb["values"] = titles
        self._log(self.T("log_refresh_wins", n=len(titles)))
        # 如果当前值在列表中，保持不变；否则尝试自动匹配 GeForce
        cur = self._win_var.get()
        if cur not in titles:
            for t in titles:
                if "geforce" in t.lower() or "beamng" in t.lower():
                    self._win_var.set(t)
                    break

    def _on_sens_drag(self, val):
        v = round(float(val), 1)
        self._sens_val.config(text=f"{v:.1f}")
        self.config.set("sensitivity", v)

    # ── 按钮动作 ──────────────────────────────
    def _launch(self):
        # 依赖检查
        if not CV2_AVAILABLE:
            messagebox.showerror(self.T("err_no_cv2_title"), self.T("err_no_cv2"))
            return
        if not MSS_AVAILABLE:
            messagebox.showerror(self.T("err_no_mss_title"), self.T("err_no_mss"))
            return
        if not PYNPUT_AVAILABLE:
            messagebox.showerror(self.T("err_no_pynput_title"), self.T("err_no_pynput"))
            return

        win_title = self._win_var.get().strip()
        if not win_title:
            messagebox.showwarning("", self.T("err_no_select"))
            return

        sensitivity = float(self._sens_scale.get())
        use_yolo    = self._yolo_var.get()

        self.config.set("window_title", win_title)
        self.config.set("use_yolo",     use_yolo)
        self.config.save()

        self._set_state("starting")
        self._paused = False

        def _run():
            ok = self.driver.start(win_title, sensitivity, use_yolo)
            self.root.after(0, lambda: self._set_state(
                "driving" if ok else "idle"))

        threading.Thread(target=_run, daemon=True).start()

    def _toggle_pause(self):
        if not self._paused:
            self.driver.pause()
            self._paused = True
            self.root.after(0, lambda: self._set_state("paused"))
        else:
            self.driver.resume()
            self._paused = False
            self.root.after(0, lambda: self._set_state("driving"))

    def _stop(self):
        def _do():
            self.driver.stop()
            self._paused = False
            self.root.after(0, lambda: self._set_state("idle"))
        threading.Thread(target=_do, daemon=True).start()

    def _on_close(self):
        if self.driver.running:
            if not messagebox.askyesno(
                self.T("confirm_exit_title"), self.T("confirm_exit")
            ):
                return
            def _shut():
                self.driver.stop()
                self.root.after(400, self.root.destroy)
            threading.Thread(target=_shut, daemon=True).start()
        else:
            self.root.destroy()

    # ── 实时预览 + 信息刷新 ───────────────────
    def _refresh_preview(self):
        """每 60ms 刷新一次预览画面和状态信息。"""
        d = self.driver

        # 更新预览画面
        if PIL_AVAILABLE and d.running:
            frame = d.get_preview()
            if frame is not None:
                try:
                    img   = Image.fromarray(frame)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self._preview_canvas.delete("waiting_text")
                    self._preview_canvas.config(
                        width=img.width, height=img.height)
                    self._preview_canvas.create_image(
                        0, 0, anchor="nw", image=imgtk)
                    self._preview_img_ref = imgtk   # 防止被 GC
                except Exception:
                    pass

        # 更新状态信息
        if d.running and self._ui_state == "driving":
            fps = d.fps
            off = d.current_offset
            self._info_lbl.config(
                text=self.T("fps_fmt", fps=fps, offset=off),
                fg=FG if d.current_conf > 0.5 else YELLOW,
            )

        self.root.after(60, self._refresh_preview)

    # ── E 键暂停热键 ──────────────────────────
    def _setup_hotkey(self):
        if not PYNPUT_AVAILABLE:
            return
        def _on_press(key):
            try:
                if hasattr(key, "char") and key.char in ("e", "E"):
                    if self.driver.running:
                        self.root.after(0, self._toggle_pause)
            except Exception:
                pass
        pynput_kb.Listener(on_press=_on_press, daemon=True).start()

    # ── 运行 ──────────────────────────────────
    def run(self):
        T = self.T
        self._log(T("log_started"))
        self._log("━" * 44)
        deps_ok = CV2_AVAILABLE and MSS_AVAILABLE and PYNPUT_AVAILABLE
        if deps_ok:
            self._log(T("log_dep_ok"))
            if not PIL_AVAILABLE:
                self._log("⚠  Pillow 未安装，实时预览不可用（run install_vision.bat）")
            if not GW_AVAILABLE:
                self._log("⚠  pygetwindow 未安装，窗口检测功能受限")
            if not YOLO_AVAILABLE:
                self._log("⚠  ultralytics 未安装，YOLOv8 障碍物检测不可用")
        else:
            self._log(T("log_dep_missing"))
        self._log("  → 选择云游戏窗口后点「启动视觉驾驶员」")
        self._setup_hotkey()
        self._refresh_preview()
        self.root.mainloop()


# ─────────────────────────────────────────────
if __name__ == "__main__":
    import traceback as _tb

    _LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_vision.log")

    try:
        app = ControlPanel()
        app.run()
    except Exception:
        err = _tb.format_exc()
        try:
            with open(_LOG, "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
        try:
            import tkinter as _tk, tkinter.messagebox as _mb
            r = _tk.Tk(); r.withdraw()
            _mb.showerror(
                "启动错误 / Startup Error",
                f"程序启动失败，错误已保存到：\n{_LOG}\n\n{err[-800:]}",
            )
            r.destroy()
        except Exception:
            pass
        print(err)
        input("按 Enter 退出 / Press Enter to exit...")
