"""Tk control panel for Vision_Control."""
from __future__ import annotations

import ctypes
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageTk

from ..capture.window_focus import (
    exclude_from_capture,
    find_hwnd_by_exact_title,
    list_visible_windows,
)
from ..config import Config
from ..engine import State, VisionEngine
from ..i18n import LANGUAGES, normalize_lang, text

PREVIEW_W, PREVIEW_H = 640, 360
PREVIEW_REFRESH_MS = 200
TELEMETRY_REFRESH_MS = 100
LOG_REFRESH_MS = 250
CAPTURE_MODES = ("auto", "window", "dxcam")


class _HotkeyPoller:
    """Poll GetAsyncKeyState in a background thread."""

    def __init__(self, keys: dict[str, int], on_press, poll_hz: int = 30) -> None:
        self._keys = keys
        self._on_press = on_press
        self._interval = 1.0 / max(1, poll_hz)
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="HotkeyPoller"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()

    def _run(self) -> None:
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
        except Exception:
            return
        last = {key: False for key in self._keys}
        while not self._stop_evt.is_set():
            for name, vk in self._keys.items():
                down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                if down and not last[name]:
                    try:
                        self._on_press(name)
                    except Exception:
                        pass
                last[name] = down
            time.sleep(self._interval)


class ControlPanel:
    """Multilingual control panel for the background vision engine."""

    def __init__(
        self,
        default_window: str = "GeForce NOW",
        config: Config | None = None,
    ) -> None:
        self.cfg = config or Config.load()
        self.lang = normalize_lang(self.cfg.lang)
        self.engine = VisionEngine()
        self.root = tk.Tk()
        self.root.geometry("1040x720")
        self.root.minsize(940, 640)

        self._default_window = default_window
        self._photo: ImageTk.PhotoImage | None = None
        self._last_state: State = State.IDLE
        self._widgets: list[tuple[Any, str, str]] = []
        self._telemetry_label_keys: dict[str, str] = {}

        self._build_ui()
        self._apply_language()
        self.root.update_idletasks()
        self._exclude_self_from_capture()
        self._wire_hotkeys()
        self._tick_preview()
        self._tick_telemetry()
        self._tick_log()
        self._update_button_states()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _t(self, key: str) -> str:
        return text(self.lang, key)

    def _track(self, widget: Any, key: str, option: str = "text") -> Any:
        self._widgets.append((widget, option, key))
        return widget

    def _build_ui(self) -> None:
        try:
            ttk.Style().theme_use("vista")
        except tk.TclError:
            try:
                ttk.Style().theme_use("clam")
            except tk.TclError:
                pass

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        top = ttk.Frame(outer)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)

        self._track(ttk.Label(top), "label.window").grid(row=0, column=0, padx=(0, 6))
        self.window_var = tk.StringVar(value=self._default_window)
        self.window_cb = ttk.Combobox(top, textvariable=self.window_var, state="normal")
        self.window_cb.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.btn_refresh = self._track(
            ttk.Button(top, command=self._refresh_windows), "button.refresh"
        )
        self.btn_refresh.grid(row=0, column=2, padx=(0, 12))

        self._track(ttk.Label(top), "label.capture").grid(row=0, column=3, padx=(0, 6))
        self.capture_var = tk.StringVar()
        self.capture_cb = ttk.Combobox(
            top, textvariable=self.capture_var, state="readonly", width=14
        )
        self.capture_cb.grid(row=0, column=4, padx=(0, 12))
        self.capture_cb.bind("<<ComboboxSelected>>", self._on_capture_changed)

        self._track(ttk.Label(top), "label.language").grid(row=0, column=5, padx=(0, 6))
        self.lang_var = tk.StringVar(value=LANGUAGES[self.lang])
        self.lang_cb = ttk.Combobox(
            top,
            textvariable=self.lang_var,
            values=list(LANGUAGES.values()),
            state="readonly",
            width=12,
        )
        self.lang_cb.grid(row=0, column=6)
        self.lang_cb.bind("<<ComboboxSelected>>", self._on_language_changed)
        self._refresh_windows()

        mid = ttk.Frame(outer)
        mid.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        mid.columnconfigure(0, weight=1)

        self.preview_frame = self._track(ttk.LabelFrame(mid, padding=4), "frame.preview")
        self.preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.preview_lbl = ttk.Label(self.preview_frame, background="#222")
        self.preview_lbl.pack()
        self._set_preview(np.zeros((PREVIEW_H, PREVIEW_W, 3), dtype=np.uint8))

        self.telemetry_frame = self._track(
            ttk.LabelFrame(mid, padding=8, width=260), "frame.telemetry"
        )
        self.telemetry_frame.grid(row=0, column=1, sticky="ns")
        self.telemetry_frame.grid_propagate(False)
        self._telemetry_vars: dict[str, tk.StringVar] = {}
        rows = [
            ("state", "telemetry.state"),
            ("fps", "telemetry.fps"),
            ("steer", "telemetry.steer"),
            ("throttle", "telemetry.throttle"),
            ("brake", "telemetry.brake"),
            ("road", "telemetry.road"),
            ("conf", "telemetry.confidence"),
            ("calib", "telemetry.calibration"),
            ("drive", "telemetry.drive"),
            ("gamepad", "telemetry.gamepad"),
            ("capture", "telemetry.capture"),
        ]
        for i, (key, label_key) in enumerate(rows):
            label = self._track(
                ttk.Label(self.telemetry_frame, foreground="#666"), label_key
            )
            label.grid(row=i, column=0, sticky="w", pady=2)
            self._telemetry_label_keys[key] = label_key
            var = tk.StringVar(value="-")
            self._telemetry_vars[key] = var
            ttk.Label(
                self.telemetry_frame,
                textvariable=var,
                font=("Segoe UI", 10, "bold"),
            ).grid(row=i, column=1, sticky="e", padx=(8, 0))
        self.telemetry_frame.columnconfigure(1, weight=1)

        bottom = ttk.Frame(outer)
        bottom.grid(row=2, column=0, sticky="nsew")
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=1)

        ctrl = ttk.Frame(bottom)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.btn_start = self._track(ttk.Button(ctrl, command=self._on_start), "button.start")
        self.btn_pause = self._track(ttk.Button(ctrl, command=self._on_pause), "button.pause")
        self.btn_stop = self._track(ttk.Button(ctrl, command=self._on_stop), "button.stop")
        self.drive_var = tk.BooleanVar(value=False)
        self.btn_drive = self._track(
            ttk.Checkbutton(
                ctrl, variable=self.drive_var, command=self._on_drive_toggle
            ),
            "check.drive",
        )
        self.btn_recal = self._track(
            ttk.Button(ctrl, command=self._on_recal), "button.recalibrate"
        )
        for i, widget in enumerate(
            [self.btn_start, self.btn_pause, self.btn_stop, self.btn_drive, self.btn_recal]
        ):
            widget.grid(row=0, column=i, padx=4)
        self.hotkey_label = self._track(
            ttk.Label(ctrl, foreground="#777"), "hint.hotkey"
        )
        self.hotkey_label.grid(row=0, column=5, padx=(16, 0))

        self.log_frame = self._track(ttk.LabelFrame(bottom, padding=4), "frame.log")
        self.log_frame.grid(row=1, column=0, sticky="nsew")
        self.log = scrolledtext.ScrolledText(
            self.log_frame,
            height=8,
            font=("Consolas", 9),
            background="#1a1a1a",
            foreground="#dddddd",
            insertbackground="#dddddd",
        )
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

    def _apply_language(self) -> None:
        self.root.title(self._t("app.title"))
        for widget, option, key in self._widgets:
            try:
                widget.configure(**{option: self._t(key)})
            except tk.TclError:
                pass
        self.lang_var.set(LANGUAGES[self.lang])
        self._refresh_capture_mode_values()
        self._tick_telemetry_once()

    def _refresh_capture_mode_values(self) -> None:
        current_key = self._capture_mode_key()
        values = [self._t(f"capture_mode.{mode}") for mode in CAPTURE_MODES]
        self.capture_cb["values"] = values
        self.capture_var.set(self._t(f"capture_mode.{current_key}"))

    def _capture_mode_key(self) -> str:
        display = self.capture_var.get()
        for mode in CAPTURE_MODES:
            if display == self._t(f"capture_mode.{mode}"):
                return mode
        configured = getattr(self.cfg.capture, "backend", "auto")
        return configured if configured in CAPTURE_MODES else "auto"

    def _on_language_changed(self, _event: object | None = None) -> None:
        selected = self.lang_var.get()
        for code, display in LANGUAGES.items():
            if selected == display:
                self.lang = code
                self.cfg.lang = code
                self.cfg.save()
                self._apply_language()
                return

    def _on_capture_changed(self, _event: object | None = None) -> None:
        self.cfg.capture.backend = self._capture_mode_key()
        self.cfg.save()

    def _exclude_self_from_capture(self) -> None:
        hwnd = int(self.root.winfo_id() or 0)
        ok = exclude_from_capture(hwnd)
        if not ok:
            alt_hwnd = find_hwnd_by_exact_title(self.root.title())
            if alt_hwnd:
                ok = exclude_from_capture(alt_hwnd)
        self._append_log(self._t("log.panel_hidden" if ok else "log.panel_visible_warning"))

    def _wire_hotkeys(self) -> None:
        self._hotkey = _HotkeyPoller(keys={"E": 0x45}, on_press=self._on_hotkey)
        self._hotkey.start()

    def _on_hotkey(self, _name: str) -> None:
        self.root.after(0, self._toggle_pause_from_hotkey)

    def _toggle_pause_from_hotkey(self) -> None:
        state, _ = self.engine.get_state()
        if state == State.RUNNING:
            self.engine.pause()
        elif state == State.PAUSED:
            self.engine.resume()

    def _refresh_windows(self) -> None:
        titles = sorted({title for _, title in list_visible_windows()})
        self.window_cb["values"] = titles
        current = self.window_var.get()
        if current not in titles:
            for hint in self.cfg.window_candidates:
                for title in titles:
                    if hint.lower() in title.lower():
                        self.window_var.set(title)
                        return

    def _on_start(self) -> None:
        title = self.window_var.get().strip()
        if not title:
            self._append_log(self._t("log.select_window"))
            return
        self.engine.start(title, capture_backend=self._capture_mode_key())

    def _on_pause(self) -> None:
        state, _ = self.engine.get_state()
        if state == State.RUNNING:
            self.engine.pause()
        elif state == State.PAUSED:
            self.engine.resume()

    def _on_stop(self) -> None:
        self.engine.stop()

    def _on_drive_toggle(self) -> None:
        self.engine.set_drive(self.drive_var.get())

    def _on_recal(self) -> None:
        self.engine.recalibrate()

    def _tick_preview(self) -> None:
        frame = self.engine.get_preview()
        if frame is not None:
            self._set_preview(frame)
        self.root.after(PREVIEW_REFRESH_MS, self._tick_preview)

    def _tick_telemetry(self) -> None:
        self._tick_telemetry_once()
        self.root.after(TELEMETRY_REFRESH_MS, self._tick_telemetry)

    def _tick_telemetry_once(self) -> None:
        if not hasattr(self, "_telemetry_vars"):
            return
        t = self.engine.get_telemetry()
        state, err = self.engine.get_state()
        if state != self._last_state:
            self._update_button_states()
            self._last_state = state

        state_text = state.value
        if state == State.ERROR and err:
            state_text = f"error: {err[:24]}..." if len(err) > 24 else f"error: {err}"

        self._telemetry_vars["state"].set(state_text)
        self._telemetry_vars["fps"].set(f"{t.fps:5.1f}")
        self._telemetry_vars["steer"].set(f"{t.steer:+0.2f}")
        self._telemetry_vars["throttle"].set(f"{t.throttle:0.2f}")
        self._telemetry_vars["brake"].set(f"{t.brake:0.2f}")
        self._telemetry_vars["road"].set(f"{t.road_pct:4.1f}%")
        self._telemetry_vars["conf"].set(f"{t.confidence:0.2f}")
        if t.calibrated:
            self._telemetry_vars["calib"].set(self._t("status.ready"))
        else:
            self._telemetry_vars["calib"].set(f"{t.calib_seen}/{t.calib_need}")
        self._telemetry_vars["drive"].set(
            self._t("status.on") if t.drive_on else self._t("status.off")
        )
        self._telemetry_vars["gamepad"].set(
            self._t("status.ok") if t.has_gamepad else self._t("status.none")
        )
        self._telemetry_vars["capture"].set(t.capture_backend or self._capture_mode_key())

        if state == State.PAUSED:
            self.btn_pause.configure(text=self._t("button.resume"))
        else:
            self.btn_pause.configure(text=self._t("button.pause"))

    def _tick_log(self) -> None:
        msgs = self.engine.drain_log()
        if msgs:
            self.log.configure(state="normal")
            for msg in msgs:
                self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(LOG_REFRESH_MS, self._tick_log)

    def _append_log(self, msg: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _update_button_states(self) -> None:
        state, _ = self.engine.get_state()
        running_or_paused = state in (State.RUNNING, State.PAUSED, State.STARTING)
        self.btn_start.configure(state="disabled" if running_or_paused else "normal")
        self.btn_pause.configure(
            state="normal" if state in (State.RUNNING, State.PAUSED) else "disabled"
        )
        self.btn_stop.configure(state="normal" if running_or_paused else "disabled")

    def _set_preview(self, bgr: np.ndarray) -> None:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        if img.size != (PREVIEW_W, PREVIEW_H):
            img = img.resize((PREVIEW_W, PREVIEW_H), Image.BILINEAR)
        self._photo = ImageTk.PhotoImage(img)
        self.preview_lbl.configure(image=self._photo)

    def _on_close(self) -> None:
        try:
            self._hotkey.stop()
        except Exception:
            pass
        try:
            self.engine.stop()
        except Exception:
            pass
        try:
            self.root.after(150, self.root.destroy)
        except tk.TclError:
            pass

    def run(self) -> int:
        try:
            self.root.mainloop()
        finally:
            try:
                self._hotkey.stop()
            except Exception:
                pass
            try:
                self.engine.stop()
            except Exception:
                pass
        return 0
