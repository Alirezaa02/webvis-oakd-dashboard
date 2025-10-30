"""
Test Map
--------
- test_ids_overlay_on_off
  * Checks IDs are detected correctly for multiple markers.
  * With DRAW_OVERLAYS=False: function returns the SAME numpy array (no copy).
  * With DRAW_OVERLAYS=True: function returns a NEW array and pixel data differs.
  -> Ensures memory/performance correctness in LCD + web pipelines.

- test_small_blurred
  * Verifies detection of smaller markers with Gaussian blur applied.
  -> Guards against regressions when dealing with slight defocus or motion blur.

- test_no_markers
  * On a blank frame: returns ids == [] and the SAME array.
  -> Ensures graceful no-detection behavior without unnecessary copies.
"""


import cv2
import numpy as np
import utility.aruco_helper as mod

def _marker(mid:int, side:int=140) -> np.ndarray:
    img = np.zeros((side, side), dtype=np.uint8)
    cv2.aruco.drawMarker(mod._ARUCO_DICT, mid, side, img, 1)
    return img

def _scene(ids, side=140, gap=16) -> np.ndarray:
    cols = max(1, int(np.ceil(len(ids)/2)))
    rows = 2
    h = rows*side + (rows+1)*gap
    w = cols*side + (cols+1)*gap
    g = np.full((h, w), 255, np.uint8)
    for i, mid in enumerate(ids):
        r, c = divmod(i, cols)
        y, x = gap + r*(side+gap), gap + c*(side+gap)
        g[y:y+side, x:x+side] = _marker(mid, side)
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)

def test_ids_overlay_on_off(monkeypatch):
    img = _scene([3, 77, 150], side=120)
    
    # Off → same object, same pixels
    monkeypatch.setattr(mod, "DRAW_OVERLAYS", False)
    ids0, out0 = mod.detect_aruco_ids(img)
    assert sorted(ids0) == [3, 77, 150]
    assert out0 is img
    
    # On → new buffer, different pixels
    monkeypatch.setattr(mod, "DRAW_OVERLAYS", True)
    ids1, out1 = mod.detect_aruco_ids(img)
    assert sorted(ids1) == [3, 77, 150]
    assert out1 is not img and np.any(out1 != img)

def test_small_blurred(monkeypatch):
    img = _scene([0, 42], side=80)
    img = cv2.GaussianBlur(img, (3,3), 0)
    monkeypatch.setattr(mod, "DRAW_OVERLAYS", False)
    ids, out_img = mod.detect_aruco_ids(img)
    assert set(ids) == {0, 42}
    assert out_img is img

def test_no_markers():
    img = np.full((240, 320, 3), 200, np.uint8)
    ids, out_img = mod.detect_aruco_ids(img)
    assert ids == []
    assert out_img is img
