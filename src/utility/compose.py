from __future__ import annotations

import cv2
import numpy as np
import threading
import time
import logging

from dataclasses import dataclass
from typing import Callable, List, Tuple, Optional

BBox = Tuple[int, int, int, int]  # x1, y1, x2, y2 (pixel coords)


@dataclass
class Detections:
    boxes: List[BBox]
    labels: List[str]
    scores: List[float]


class DetectionsCache:
    """
    Thread-safe cache for sharing detections computed on one frame/stream
    (with its source image shape) with another stream that may need to rescale.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._det: Optional[Detections] = None
        self._src_shape: Optional[Tuple[int, int]] = None  # (h, w) of image detections were computed on
        self._t = 0.0

    def publish(self, det: Detections, src_shape: Tuple[int, int]) -> None:
        with self._lock:
            self._det = det
            self._src_shape = src_shape
            self._t = time.time()

    def latest(self) -> Tuple[Optional[Detections], Optional[Tuple[int, int]], float]:
        with self._lock:
            return self._det, self._src_shape, self._t


def _clamp(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else hi if v > hi else v


def _scale_boxes(
    boxes: List[BBox],
    from_shape: Tuple[int, int],  # (h, w)
    to_shape: Tuple[int, int],    # (h, w)
) -> List[BBox]:
    """
    Scale boxes from one image shape to another. Values are clamped to target bounds.
    """
    if not boxes:
        return []
    fh, fw = from_shape
    th, tw = to_shape
    if fh <= 0 or fw <= 0 or th <= 0 or tw <= 0:
        return []

    sx = float(tw) / float(fw)
    sy = float(th) / float(fh)

    out: List[BBox] = []
    max_x = tw - 1
    max_y = th - 1
    for x1, y1, x2, y2 in boxes:
        nx1 = _clamp(int(round(x1 * sx)), 0, max_x)
        ny1 = _clamp(int(round(y1 * sy)), 0, max_y)
        nx2 = _clamp(int(round(x2 * sx)), 0, max_x)
        ny2 = _clamp(int(round(y2 * sy)), 0, max_y)
        # Ensure well-ordered box even if rounding flips order
        if nx2 < nx1:
            nx1, nx2 = nx2, nx1
        if ny2 < ny1:
            ny1, ny2 = ny2, ny1
        out.append((nx1, ny1, nx2, ny2))
    return out


def draw_overlays_bgr(
    frame_bgr: np.ndarray,
    det: Detections,
    *,
    score_thresh: float = 0.0,
    thickness: int = 2,
    font_scale: float = 0.5,
    color: Tuple[int, int, int] = (0, 255, 0),  # BGR
) -> np.ndarray:
    """
    Draws simple rectangle+label overlays. Returns a *copy* of frame_bgr.
    """
    out = frame_bgr.copy()
    h, w = out.shape[:2]

    for (x1, y1, x2, y2), label, score in zip(det.boxes, det.labels, det.scores):
        if score < score_thresh:
            continue
        # Clamp (defensive if caller passed unclamped boxes)
        x1 = _clamp(x1, 0, w - 1); x2 = _clamp(x2, 0, w - 1)
        y1 = _clamp(y1, 0, h - 1); y2 = _clamp(y2, 0, h - 1)
        if x2 <= x1 or y2 <= y1:
            continue

        cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)
        txt = f"{label} {score:.2f}" if label else f"{score:.2f}"
        # Baseline above the box; if too near top, bump inside the box
        ty = y1 - 5 if y1 - 5 >= 10 else min(y1 + 15, h - 2)
        cv2.putText(out, txt, (x1, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, max(1, thickness - 1),
                    cv2.LINE_AA)
    return out


class FrameStore:
    """
    Thread-safe store for the latest raw and composed frames.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.raw_bgr: Optional[np.ndarray] = None
        self.composed_bgr: Optional[np.ndarray] = None
        self.t_raw = 0.0
        self.t_composed = 0.0

    def update_raw(self, bgr: np.ndarray) -> None:
        with self._lock:
            self.raw_bgr = bgr
            self.t_raw = time.time()

    def update_composed(self, bgr: np.ndarray) -> None:
        with self._lock:
            self.composed_bgr = bgr
            self.t_composed = time.time()

    def get_composed(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self.composed_bgr is None else self.composed_bgr.copy()

    def get_composed_jpeg(self, quality: int = 85) -> Optional[bytes]:
        """
        Encode the composed frame as JPEG. Returns None if no frame.
        """
        img = self.get_composed()
        if img is None:
            return None
        q = int(_clamp(int(quality), 1, 100))
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), q])
        return buf.tobytes() if ok else None


class FrameComposer:
    """
    detector_fn: Optional callable taking BGR frame -> Detections
      - If provided, we'll run it, draw overlays, and (optionally) publish to a cache.
      - If None, and a det_cache is provided, we reuse latest detections (scaled) to draw overlays.

    det_cache: Optional DetectionsCache to share detections across streams.
    publish_detections: If True, publish detections (computed here) into det_cache.

    cache_max_age_s: maximum age (seconds) for reusing cached detections. If exceeded, no overlays are drawn.
    """
    def __init__(
        self,
        store: FrameStore,
        detector_fn: Optional[Callable[[np.ndarray], Detections]] = None,
        det_cache: Optional[DetectionsCache] = None,
        publish_detections: bool = False,
        *,
        cache_max_age_s: float = 1.0,
        score_thresh: float = 0.0,
        overlay_thickness: int = 2,
        overlay_font_scale: float = 0.5,
        overlay_color: Tuple[int, int, int] = (0, 255, 0),
        logger: Optional[logging.Logger] = None,
    ):
        self.store = store
        self.detector_fn = detector_fn
        self.det_cache = det_cache
        self.publish_detections = publish_detections
        self.cache_max_age_s = float(cache_max_age_s)
        self.score_thresh = float(score_thresh)
        self.overlay_thickness = int(overlay_thickness)
        self.overlay_font_scale = float(overlay_font_scale)
        self.overlay_color = overlay_color
        self.log = logger or logging.getLogger(__name__)

    def ingest_from_camera(self, bgr: np.ndarray) -> None:
        """
        Ingest a frame from the camera, optionally run/consume detections,
        draw overlays, and publish to the FrameStore.
        """
        self.store.update_raw(bgr)
        composed = bgr

        # Path 1: compute detections here (e.g. preview stream)
        if self.detector_fn is not None:
            try:
                det = self.detector_fn(bgr)
                if self.publish_detections and self.det_cache is not None:
                    h, w = bgr.shape[:2]
                    self.det_cache.publish(det, (h, w))
                composed = draw_overlays_bgr(
                    bgr, det,
                    score_thresh=self.score_thresh,
                    thickness=self.overlay_thickness,
                    font_scale=self.overlay_font_scale,
                    color=self.overlay_color,
                )
            except Exception as e:
                # Fail-safe pass-through, but log for debugging
                self.log.exception("FrameComposer: detector/overlay failed: %s", e)
                composed = bgr

        # Path 2: reuse cached detections (e.g. video stream)
        elif self.det_cache is not None:
            try:
                det_latest, src_shape, t_det = self.det_cache.latest()
                if det_latest and src_shape is not None:
                    if (time.time() - t_det) <= self.cache_max_age_s:
                        th, tw = bgr.shape[:2]
                        scaled_boxes = _scale_boxes(det_latest.boxes, src_shape, (th, tw))
                        det_scaled = Detections(
                            boxes=scaled_boxes,
                            labels=det_latest.labels,
                            scores=det_latest.scores,
                        )
                        composed = draw_overlays_bgr(
                            bgr, det_scaled,
                            score_thresh=self.score_thresh,
                            thickness=self.overlay_thickness,
                            font_scale=self.overlay_font_scale,
                            color=self.overlay_color,
                        )
                    else:
                        # Stale cache; pass-through
                        self.log.debug("FrameComposer: skipped stale detections (age=%.3fs)", time.time() - t_det)
            except Exception as e:
                self.log.exception("FrameComposer: reuse/overlay failed: %s", e)
                composed = bgr

        # else: no detector, no cache — pass-through
        self.store.update_composed(composed)
