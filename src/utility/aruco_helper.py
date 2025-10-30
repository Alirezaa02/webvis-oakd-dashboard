# Deps:
#   opencv-contrib-python-headless==4.10.0.84
#   numpy<2.4
from typing import List, Tuple
import cv2
import numpy as np

# Call this by ids, composed = detect_aruco_ids(frame_bgr)  # keep BGR for LCD/web

# Hard-coded settings
DRAW_OVERLAYS: bool = True     # draw markers + IDs if True
MARKER_SIZE_M: float = 0.040   # reserved for future pose (unused here, unsure if ever to be used)

# Build once at import
_ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_200)
_PARAMS = cv2.aruco.DetectorParameters()
_DETECTOR = cv2.aruco.ArucoDetector(_ARUCO_DICT, _PARAMS)

def detect_aruco_ids(frame_bgr: np.ndarray) -> Tuple[List[int], np.ndarray]:
    """Detect ArUco markers (BGR in/BGR out). Returns (ids, composed_frame)."""
    corners, ids_np, _ = _DETECTOR.detectMarkers(frame_bgr)
    ids: List[int] = [] if ids_np is None else ids_np.flatten().astype(int).tolist()

    if DRAW_OVERLAYS and corners:
        composed = frame_bgr.copy()
        cv2.aruco.drawDetectedMarkers(composed, corners, ids_np)
        return ids, composed
    return ids, frame_bgr
