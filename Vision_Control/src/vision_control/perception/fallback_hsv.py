"""Adaptive LAB road segmenter — last-resort fallback when ONNX is unavailable.

Unlike earlier hard-coded HSV prototypes, this version:
  - calibrates on the first N frames via K-means in LAB space,
  - learns the dominant road-coloured cluster from a lower-mid strip ROI,
  - segments by LAB Mahalanobis-ish distance — robust across day/dusk/dirt,
  - keeps the same `run() -> HxW uint8 class-id mask` API as Segmenter,
    so downstream `planning.drivable_area.from_road_mask` is unchanged.

Cluster selection heuristic:
  Road pixels in BeamNG (and most driving games) cluster around low |a|, |b|
  (de-saturated grey/brown). We pick the cluster whose center has the
  smallest a/b magnitude — that is "the most chromatically neutral region",
  which is almost always the road surface regardless of map.

CLI:
    python -m vision_control.perception.fallback_hsv --image PATH
    python -m vision_control.perception.fallback_hsv --capture WINDOW
"""
from __future__ import annotations

import argparse
import sys
import time

import cv2
import numpy as np

from . import CLASS_OTHER, CLASS_ROAD, apply_perception_roi


class AdaptiveLabSegmenter:
    """Adaptive road segmenter using K-means in LAB color space."""

    def __init__(self,
                 n_calib_frames: int = 24,
                 n_clusters:     int = 4,
                 # Distance radius (in LAB Euclidean units) for road class.
                 # 25 is a sensible default; calibrate() may shrink/grow it.
                 lab_radius:     float = 25.0,
                 # Calibration strip: vertical band of the frame used to
                 # sample road colour. Defaults are tuned for full-window
                 # capture: (0.40, 0.65) = middle horizontal band, avoiding
                 # sky (top ~35%) and the player's car (bottom ~30% in 3rd
                 # person view).
                 calib_strip:    tuple[float, float] = (0.40, 0.65),
                 # Subsample stride during calibration to keep K-means fast.
                 calib_stride:   int = 4) -> None:
        self.n_calib_frames = n_calib_frames
        self.n_clusters     = n_clusters
        self.lab_radius     = float(lab_radius)
        self.calib_strip    = calib_strip
        self.calib_stride   = calib_stride

        self._calibrated:    bool = False
        self._road_lab:      np.ndarray | None = None    # shape (3,) float32
        self._calib_pool:    list[np.ndarray] = []       # accumulated samples

    # ─── public API ─────────────────────────────────────────────────────────
    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def reset(self) -> None:
        self._calibrated = False
        self._road_lab   = None
        self._calib_pool.clear()

    def calibrate(self, frames: list[np.ndarray]) -> None:
        """One-shot calibration from a list of BGR frames."""
        samples = [self._sample_strip(f) for f in frames]
        samples = [s for s in samples if s is not None and len(s) > 0]
        if not samples:
            raise RuntimeError("calibrate(): no usable samples")
        all_pts = np.concatenate(samples, axis=0).astype(np.float32)
        self._fit_kmeans(all_pts)

    def feed_calibration_frame(self, bgr: np.ndarray) -> bool:
        """Stream calibration: feed one frame at a time. Returns True when done."""
        if self._calibrated:
            return True
        s = self._sample_strip(bgr)
        if s is not None and len(s):
            self._calib_pool.append(s)
        if len(self._calib_pool) >= self.n_calib_frames:
            all_pts = np.concatenate(self._calib_pool, axis=0).astype(np.float32)
            self._fit_kmeans(all_pts)
            self._calib_pool.clear()
        return self._calibrated

    def run(self, bgr: np.ndarray) -> np.ndarray:
        """Return HxW uint8 class-id mask (CLASS_ROAD where road-like)."""
        if not self._calibrated or self._road_lab is None:
            # Not yet calibrated — return all-other so downstream knows.
            h, w = bgr.shape[:2]
            return np.full((h, w), CLASS_OTHER, dtype=np.uint8)

        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        # Distance to road cluster center, per pixel.
        d = lab - self._road_lab.reshape(1, 1, 3)
        dist2 = np.einsum("hwc,hwc->hw", d, d, optimize=True)
        road = dist2 < (self.lab_radius * self.lab_radius)

        # Morphological clean-up: open then close with small kernels.
        mask = (road * 255).astype(np.uint8)
        k = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)

        out = np.full(mask.shape, CLASS_OTHER, dtype=np.uint8)
        out[mask > 0] = CLASS_ROAD
        return out

    # ─── internals ──────────────────────────────────────────────────────────
    def _sample_strip(self, bgr: np.ndarray) -> np.ndarray | None:
        if bgr is None or bgr.size == 0:
            return None
        h, w = bgr.shape[:2]
        top    = int(h * self.calib_strip[0])
        bottom = int(h * self.calib_strip[1])
        if bottom - top < 4:
            return None
        strip = bgr[top:bottom, :, :]
        lab   = cv2.cvtColor(strip, cv2.COLOR_BGR2LAB)
        # Subsample for speed.
        pts = lab[::self.calib_stride, ::self.calib_stride, :].reshape(-1, 3)
        return pts

    def _fit_kmeans(self, pts: np.ndarray) -> None:
        """Run K-means on LAB samples and pick the road-like cluster."""
        pts = np.ascontiguousarray(pts, dtype=np.float32)
        if len(pts) < self.n_clusters * 8:
            # Not enough data; bail out.
            return
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 8, 1.0)
        _ret, labels, centers = cv2.kmeans(
            pts, self.n_clusters, None, criteria, 3, cv2.KMEANS_PP_CENTERS
        )
        labels  = labels.flatten()
        centers = centers.astype(np.float32)  # (K, 3)

        # Cluster centers in OpenCV LAB: [L, a, b] where a,b are offset by 128
        # (a=128 b=128 means "neutral grey"). Road pixels in a driving scene
        # are typically (1) achromatic — |a-128|,|b-128| are both small,
        # (2) not too dark / not too bright, (3) the LARGEST cluster by pixel
        # count (road dominates the frame). The previous "smallest ab_dist"
        # heuristic preferred dark cars over the actual road — fixed below.
        ab_dist = np.hypot(centers[:, 1] - 128.0, centers[:, 2] - 128.0)
        L       = centers[:, 0]
        counts  = np.bincount(labels, minlength=self.n_clusters).astype(np.float32)

        valid = (
            (counts  > 0.05 * len(pts)) &   # has decent pixel support
            (ab_dist < 30.0)             &   # achromatic-ish
            (L       > 40)               &   # not pitch-black
            (L       < 230)                  # not sky-bright
        )

        if valid.any():
            # Pick the LARGEST valid cluster — the road normally dominates.
            scores = np.where(valid, counts, -1.0)
            chosen = int(np.argmax(scores))
        else:
            # Fallback: closest-to-grey cluster overall.
            chosen = int(np.argmin(ab_dist))

        self._road_lab   = centers[chosen]
        self._calibrated = True


# ════════════════════════════════════════════════════════════════════════════
#  CLI demos
# ════════════════════════════════════════════════════════════════════════════

def _overlay_mask(bgr: np.ndarray, mask_classid: np.ndarray,
                  color_bgr: tuple[int, int, int] = (0, 220, 0),
                  alpha: float = 0.45) -> np.ndarray:
    """Return a copy of bgr with road areas tinted color_bgr."""
    out = bgr.copy()
    road = (mask_classid == CLASS_ROAD)
    if road.any():
        tint = np.zeros_like(bgr)
        tint[:] = color_bgr
        out[road] = (alpha * tint[road] + (1.0 - alpha) * out[road]).astype(np.uint8)
    return out


def _cli_image(path: str, out_path: str | None) -> int:
    bgr = cv2.imread(path)
    if bgr is None:
        print(f"ERROR: could not read image: {path}")
        return 1
    seg = AdaptiveLabSegmenter()
    seg.calibrate([bgr])
    mask = seg.run(bgr)
    overlay = _overlay_mask(bgr, mask)
    if out_path is None:
        out_path = path.rsplit(".", 1)[0] + "_road.png"
    cv2.imwrite(out_path, overlay)
    print(f"Calibrated road LAB center: {seg._road_lab}")
    print(f"Wrote: {out_path}")
    return 0


def _cli_capture(window_title: str, duration: float, scale: float = 1.0) -> int:
    # Local imports so this CLI works even if capture deps are missing.
    from ..config import Roi
    from ..capture.dxcam_roi import (
        RoiCapture, _safe_preview_pos, _draw_perception_roi_overlay,
        _hide_cv2_window_from_capture,
    )
    from ..capture.window_focus import get_monitor_rect_for_hwnd

    # Capture the WHOLE client area so K-means sees road, sky AND car —
    # otherwise it can pick the player's car as the "road" cluster.
    full_roi = Roi(left_pct=0.0, right_pct=1.0, top_pct=0.0, bottom_pct=1.0)
    perc_roi = Roi()  # config defaults — drawn as a yellow rectangle overlay
    cap = RoiCapture(window_title, full_roi,
                     target_size=(640, 360), target_fps=60)
    try:
        cap.start()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    seg = AdaptiveLabSegmenter(n_calib_frames=24)
    win = "Vision_Control: fallback_hsv"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    sw, sh = cap.target_size
    pw, ph = int(sw * scale), int(sh * scale)
    cv2.resizeWindow(win, pw, ph)
    mon = get_monitor_rect_for_hwnd(cap._hwnd) or (0, 0, 1920, 1080)
    if cap._region:
        px, py = _safe_preview_pos(cap._region, (pw, ph), mon)
        cv2.moveWindow(win, px, py)
    if _hide_cv2_window_from_capture(win):
        print("[fallback_hsv] preview window hidden from screen capture (anti-mirror)")

    t0 = time.perf_counter()
    print("Calibrating on first 24 frames; keep BeamNG visible.")
    print("Press Q (or Ctrl-C) to quit.")
    try:
        while True:
            frame = cap.latest()
            if frame is None:
                if cv2.waitKey(10) & 0xFF in (ord("q"), 27):
                    break
                continue

            if not seg.is_calibrated:
                seg.feed_calibration_frame(frame)
                hud = frame.copy()
                # Visualise the calibration strip so the user can see what
                # K-means is sampling.
                h_, w_ = hud.shape[:2]
                cs_top    = int(h_ * seg.calib_strip[0])
                cs_bottom = int(h_ * seg.calib_strip[1])
                cv2.rectangle(hud, (0, cs_top), (w_ - 1, cs_bottom),
                              (255, 200, 0), 1, cv2.LINE_AA)
                cv2.putText(hud, "calib strip", (4, cs_top - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                            (255, 200, 0), 1, cv2.LINE_AA)
                _draw_perception_roi_overlay(hud, perc_roi)
                cv2.putText(hud, f"Calibrating  "
                            f"{len(seg._calib_pool)}/{seg.n_calib_frames}",
                            (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                            (0, 220, 255), 1, cv2.LINE_AA)
                cv2.imshow(win, hud)
            else:
                # Mask out HUD / sky / borders before segmentation so the
                # BeamNG gauges aren't classified as road.
                perc_input = apply_perception_roi(frame, perc_roi)
                mask = seg.run(perc_input)
                overlay = _overlay_mask(frame, mask)
                _draw_perception_roi_overlay(overlay, perc_roi)
                road_pct = float((mask == CLASS_ROAD).mean() * 100)
                cv2.putText(overlay, f"road = {road_pct:5.1f}%   "
                            f"R=recalibrate   Q=quit",
                            (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.50,
                            (255, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow(win, overlay)

            if duration > 0 and time.perf_counter() - t0 > duration:
                break
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("r"):
                print("  → recalibrating...")
                seg.reset()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            cap.stop()
        except BaseException:
            pass
        try:
            cv2.destroyAllWindows()
        except BaseException:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vision_control.perception.fallback_hsv",
        description="Adaptive LAB road segmenter demo.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--image", metavar="PATH",
                      help="run on a single image file; writes <name>_road.png")
    mode.add_argument("--capture", metavar="WINDOW",
                      help="live capture from a window + segmentation overlay")
    parser.add_argument("--out", metavar="PATH",
                        help="override output path for --image")
    parser.add_argument("--duration", type=float, default=0.0,
                        help="auto-quit after N seconds (--capture, 0=forever)")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="preview window size multiplier (1.0 = native 384x216)")
    args = parser.parse_args(argv)

    if args.image is not None:
        return _cli_image(args.image, args.out)
    return _cli_capture(args.capture, args.duration, args.scale)


if __name__ == "__main__":
    sys.exit(main())
