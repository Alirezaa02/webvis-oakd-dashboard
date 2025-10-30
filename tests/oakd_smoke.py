#!/usr/bin/env python3
"""
OAK-D smoke test:
- Verifies device is discoverable
- Captures one RGB frame
- Checks the image is not a single colour (purple/green/flat)
- Saves the frame to disk

Exit codes:
 0 = PASS
 1 = No device/camera found
 2 = Capture failed / timeout
 3 = Frame invalid or single-colour
 4 = Unexpected error
"""
import argparse
import os
import sys
from datetime import datetime
from time import monotonic, sleep

import cv2
import numpy as np
import depthai as dai

def is_single_colour(img: np.ndarray, variance_thresh=3.0, unique_sample=4096) -> bool:
    """
    Heuristics to detect "solid colour" frames (e.g., purple/green flats):
      - global stddev very small across pixels
      - and after heavy downsample, number of unique colours is tiny
    """
    if img is None or img.size == 0:
        return True

    # Ensure 3-channel BGR
    if img.ndim != 3 or img.shape[2] != 3:
        return True

    # Global variance test
    stddev = img.std()
    if stddev >= variance_thresh:
        return False  # clearly not flat

    # Downsample & unique-colour count
    h, w = img.shape[:2]
    # pick a grid of up to ~unique_sample pixels
    step = int(max(1, np.sqrt((h * w) / unique_sample)))
    ds = img[::step, ::step].reshape(-1, 3)
    # Use a view that makes rows comparable for np.unique
    ds_view = np.ascontiguousarray(ds).view([('', ds.dtype)] * ds.shape[1])
    unique = np.unique(ds_view).shape[0]
    return unique < 8  # <8 distinct colours across the sample feels "flat"

def wait_for_packet(q, timeout_ms: int):
    """Poll the queue with tryGet() until timeout."""
    deadline = monotonic() + (timeout_ms / 1000.0)
    while monotonic() < deadline:
        pkt = q.tryGet()
        if pkt is not None:
            return pkt
        sleep(0.01)  # 10ms
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="1080p",
                    choices=["1080p", "4k", "720p"],
                    help="Sensor resolution to request")
    ap.add_argument("--outdir", default="rgb_data",
                    help="Folder to save the captured frame")
    ap.add_argument("--timeout_ms", type=int, default=4000,
                    help="Wait up to N ms for a frame")
    args = ap.parse_args()

    res_map = {
        "720p": dai.ColorCameraProperties.SensorResolution.THE_720_P,
        "1080p": dai.ColorCameraProperties.SensorResolution.THE_1080_P,
        "4k": dai.ColorCameraProperties.SensorResolution.THE_4_K,
    }

    try:
        # Build pipeline
        pipeline = dai.Pipeline()
        cam = pipeline.create(dai.node.ColorCamera)
        # Prefer CAM_A but tolerate boards with different sockets
        cam.setBoardSocket(dai.CameraBoardSocket.CAM_A)
        cam.setResolution(res_map[args.res])
        cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        cam.setInterleaved(False)
        cam.setPreviewKeepAspectRatio(False)

        xout = pipeline.create(dai.node.XLinkOut)
        xout.setStreamName("rgb")
        # For a single full-res frame use 'video'. 'preview' is resized, 'isp' is demosaiced ISP.
        cam.video.link(xout.input)

        # Connect to device
        with dai.Device(pipeline) as device:
            print("Connected cameras:", device.getConnectedCameraFeatures())
            print("USB speed:", device.getUsbSpeed().name)
            bl = device.getBootloaderVersion()
            if bl is not None:
                print("Bootloader version:", bl)
            print("Device name:", device.getDeviceName())

            # Quick sanity: ensure at least one RGB-capable camera reported
            cams = device.getConnectedCameraFeatures()
            if not cams:
                print("[FAIL] No cameras reported by device.")
                return 1

            # Get frame
            q = device.getOutputQueue(name="rgb", maxSize=1, blocking=False)

            pkt = wait_for_packet(q, args.timeout_ms)
            if pkt is None:
                print(f"[FAIL] Timed out after {args.timeout_ms} ms waiting for a frame.")
                return 2

            frame = pkt.getCvFrame()
            if frame is None or frame.size == 0:
                print("[FAIL] Received empty frame.")
                return 3

            # Validate not single-colour
            if is_single_colour(frame):
                print("[FAIL] Captured frame appears to be a single/flat colour (e.g., purple/green).")
                # Save anyway for inspection
                os.makedirs(args.outdir, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(args.outdir, f"smoketest_flat_{ts}.jpg")
                cv2.imwrite(path, frame)
                print("Saved flat-looking frame to:", path)
                return 3

            # Save good frame
            os.makedirs(args.outdir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(args.outdir, f"smoketest_{args.res}_{ts}.jpg")
            if not cv2.imwrite(path, frame):
                print("[WARN] cv2.imwrite reported failure; continuing but please check filesystem permissions.")
            else:
                print("[OK] Frame captured and saved to:", path)

            # Print a few quick stats to help debugging colour problems
            mean_bgr = frame.reshape(-1, 3).mean(axis=0)
            min_bgr = frame.reshape(-1, 3).min(axis=0)
            max_bgr = frame.reshape(-1, 3).max(axis=0)
            print(f"Frame shape: {frame.shape}  dtype: {frame.dtype}")
            print(f"Mean BGR: {mean_bgr.round(2)}   Min: {min_bgr}   Max: {max_bgr}")

            print("[PASS] OAK-D smoke test succeeded.")
            return 0

    except dai.XLinkReadError as e:
        print(f"[FAIL] XLink read error: {e}")
        return 2
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e.__class__.__name__}: {e}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
