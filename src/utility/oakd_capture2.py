from __future__ import annotations
from typing import Optional, Tuple
import depthai as dai

from pathlib import Path
import sys
import cv2
import numpy as np
import time
import argparse
import json
import blobconverter
import math

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-m", "--model", help="Provide model name or model path for inference",
                    default='yolov4_tiny_coco_320x160', type=str)
parser.add_argument("-c", "--config", help="Provide config path for inference",
                    default='json/yolov4-tiny.json', type=str)
args = parser.parse_args()
# parse config
configPath = Path(args.config)
if not configPath.exists():
    raise ValueError("Path {} does not exist!".format(configPath))
with configPath.open() as f:
    config = json.load(f)
nnConfig = config.get("nn_config", {})

# extract metadata
metadata = nnConfig.get("NN_specific_metadata", {})
classes = metadata.get("classes", {})
coordinates = metadata.get("coordinates", {})
anchors = metadata.get("anchors", {})
anchorMasks = metadata.get("anchor_masks", {})
iouThreshold = metadata.get("iou_threshold", {})
confidenceThreshold = metadata.get("confidence_threshold", {})
print(metadata)
# parse labels
nnMappings = config.get("mappings", {})
labels = nnMappings.get("labels", {})
# get model path
nnPath = args.model
if not Path(nnPath).exists():
    #global x_distance
    print("No blob found at {}. Looking into DepthAI model zoo.".format(nnPath))
    nnPath = str(blobconverter.from_zoo(args.model, shaves = 6, zoo_type = "depthai", use_cache=True))
# sync outputs
syncNN = True



# DepthAI compat shims (works across older/newer SDKs), for camera weirdness we've had.
#XLinkOut = getattr(dai.node, "XLinkOut", None) or getattr(dai, "XLinkOut")
#Camera   = getattr(dai.node, "Camera",   None) or getattr(dai, "Camera")
#ColorCam = getattr(dai.node, "ColorCamera", None) or getattr(dai, "ColorCamera")  # fallback
#CamProps = getattr(dai, "CameraProperties", getattr(dai, "ColorCameraProperties", None))

_RES_MAP = {
    "720p": dai.ColorCameraProperties.SensorResolution.THE_720_P,
    "800p": dai.ColorCameraProperties.SensorResolution.THE_800_P,
    "1080p": dai.ColorCameraProperties.SensorResolution.THE_1080_P,
    #"1200p": dai.ColorCameraProperties.SensorResolution.THE_1200_P,
    #"4k": dai.ColorCameraProperties.SensorResolution.THE_4_K,
}






class OakDLite:
    """
    Dual-stream OAK-D Lite capture:
      - preview: small frames for overlays/LCD (low latency, CPU-light)
      - video:   full-res frames for web/archive (high quality)
    """

    def __init__(
        self,
        fps: int = 30,
        #FRAME_SIZE = (640, 360)
        preview_size: Tuple[int, int] = (320, 160),  # (w, h) e.g. 2:1 for LCD
        video_size: Tuple[int, int] = (1280, 720),   # (w, h)
        enable_preview: bool = True,
        enable_video: bool = True,
        stream_preview: str = "preview",
        stream_video: str = "video",
        color_order: dai.ColorCameraProperties.ColorOrder =
            dai.ColorCameraProperties.ColorOrder.BGR,
    ):
        if not enable_preview and not enable_video:
            raise ValueError("At least one of preview or video streams must be enabled.")
        self._fps = int(fps)
        self._preview_size = preview_size
        self._video_size = video_size
        self._enable_preview = enable_preview
        self._enable_video = enable_video
        self._stream_preview = stream_preview
        self._stream_video = stream_video
        self._color_order = color_order

        self._device: Optional[dai.Device] = None
        self._q_preview: Optional[dai.DataOutputQueue] = None
        self._q_video: Optional[dai.DataOutputQueue] = None
        self._intrinsics = None


    def start(self) -> None:
        pipe = dai.Pipeline() #Pipeline
        #nn = pipeline.create(dai.node.NeuralNetwork)
        cam = pipe.create(dai.node.ColorCamera)#camRgb
        cam.setBoardSocket(dai.CameraBoardSocket.RGB)
        cam.setFps(self._fps)
        cam.setInterleaved(False)
        cam.setColorOrder(self._color_order)
        cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_720_P)
        detectionNetwork = pipe.create(dai.node.YoloDetectionNetwork)
        # Network specific settings
        detectionNetwork.setConfidenceThreshold(confidenceThreshold)
        detectionNetwork.setNumClasses(classes)
        detectionNetwork.setCoordinateSize(coordinates)
        detectionNetwork.setAnchors(anchors)
        detectionNetwork.setAnchorMasks(anchorMasks)
        detectionNetwork.setIouThreshold(iouThreshold)
        detectionNetwork.setBlobPath(nnPath)
        detectionNetwork.setNumInferenceThreads(2)
        detectionNetwork.input.setBlocking(False)

        # Configure initial camera controls (compat across SDK versions)
        try:
            # Newer style: set on a temp control and copy into initialControl
            ctrl = dai.CameraControl()
            ctrl.setAntiBandingMode(dai.CameraControl.AntiBandingMode.MAINS_50_HZ)
            if hasattr(cam.initialControl, "setFrom"):
                cam.initialControl.setFrom(ctrl)
            else:
                # Fallback: assign if supported
                try:
                    cam.initialControl = ctrl  # some SDKs allow direct assign
                except Exception:
                    # Old style: call methods directly on initialControl
                    cam.initialControl.setAntiBandingMode(
                        dai.CameraControl.AntiBandingMode.MAINS_50_HZ
                    )
        except AttributeError:
            # Very old style: methods only on initialControl
            cam.initialControl.setAntiBandingMode(
                dai.CameraControl.AntiBandingMode.MAINS_50_HZ
            )

        # PREVIEW (LCD / overlays)
        if self._enable_preview:
            pw, ph = self._preview_size
            #FRAME_SIZE = (640, 360)
            cam.setPreviewSize(pw, ph)
            cam.setPreviewKeepAspectRatio(False)  # Avoid hidden center-crop
            xout_p = pipe.create(dai.node.XLinkOut) #xoutRgb
            nnOut = pipe.create(dai.node.XLinkOut)
            xout_p.setStreamName(self._stream_preview)#=xoutRgb.setStreamName("rgb")
            nnOut.setStreamName("nn")
            xout_p.input.setBlocking(False)
            xout_p.input.setQueueSize(2)
            #cam.preview.link(xout_p.input)
            cam.preview.link(detectionNetwork.input)
            detectionNetwork.passthrough.link(xout_p.input)
            detectionNetwork.out.link(nnOut.input)


                                                # Linking
                                                #camRgb.preview.link(detectionNetwork.input)
                                                #detectionNetwork.passthrough.link(xoutRgb.input)
                                                #detectionNetwork.out.link(nnOut.input)




        # VIDEO (web/recording)
        if self._enable_video:
            vw, vh = self._video_size
            cam.setVideoSize(vw, vh)
            xout_v = pipe.create(dai.node.XLinkOut)
            xout_v.setStreamName(self._stream_video)
            xout_v.input.setBlocking(False)
            xout_v.input.setQueueSize(4)
            cam.video.link(xout_v.input)

        self._device = dai.Device(pipe)
        #with dai.Device(pipeline) as device:

        if self._enable_preview:
            #self._q_preview.get
            self._q_preview = self._device.getOutputQueue(
                self._stream_preview, maxSize=2, blocking=False
            )
            self._device.getOutputQueue(
                name="nn", maxSize=2, blocking=False
            )
            #inRgb = qRgb.get()
            detections = []
            startTime = time.monotonic()
            counter = 0
            color2 = (255, 255, 255)
            # nn data, being the bounding box locations, are in <0..1> range - they need to be normalized with frame width/height
            def frameNorm(frame, bbox):
                normVals = np.full(len(bbox), frame.shape[0])
                normVals[::2] = frame.shape[1]
                return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)
            def displayFrame(name, frame, detections):
                global bar
                color = (255, 0, 0)
                run_once = True
                object_coordinates = []
                foundlabel = []
                for detection in detections:
                    bbox = frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                    cv2.putText(frame, labels[detection.label], (bbox[0] - 25, bbox[1] + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.35, 255)
                    cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] - 25, bbox[1] + 45), cv2.FONT_HERSHEY_TRIPLEX, 0.35, 255)
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                    
                    x1 = detection.xmax - (detection.xmax - detection.xmin)/2
                    y1 = detection.ymax - (detection.ymax - detection.ymin)/2
                    x2 = x1 + (detection.xmax - detection.xmin)
                    y2 = y1 + (detection.ymax - detection.ymin)
                    object_coordinates.append([x1, y1, x2, y2])
                    found = detection.label
                    foundlabel.append(found)
                    print(bbox)
                cv2.imshow(name, frame)
        if self._enable_video:
            self._q_video = self._device.getOutputQueue(
                self._stream_video, maxSize=4, blocking=False
            )#qRgb
                #frame = None
            # Cache intrinsics at video size (optional, for later use)
            calib = None
            if hasattr(self._device, "getCalibration"):
                # Newer SDKs
                calib = self._device.getCalibration()
            elif hasattr(self._device, "readCalibration"):
                # Older SDKs (your build)
                calib = self._device.readCalibration()
            if calib is not None and hasattr(calib, "getCameraIntrinsics"):
                try:
                    self._intrinsics = calib.getCameraIntrinsics(
                        dai.CameraBoardSocket.RGB, vw, vh
                        )
                except TypeError:
                     # Some SDKs take (socket) only, no size
                     self._intrinsics = calib.getCameraIntrinsics(
                         dai.CameraBoardSocket.RGB
                     )
            else:
                 self._intrinsics = None  # Optional; only needed if you use them later



    def close(self) -> None:
        if self._device is not None:
            self._device.close()
        self._device = None
        self._q_preview = None
        self._q_preview = None
        self._q_video = None

    def get_preview_frame(self):
        """Return BGR ndarray (small). Non-blocking."""
        if not self._q_preview:
            raise RuntimeError("Preview stream not enabled.")
        pkt = self._q_preview.tryGet()
        #inDet = qDet.tryGet()
        inDet = self._q_preview.tryGet()
        detections = inDet.detections
        return None if pkt is None else pkt.getCvFrame()
        return None if inDet is None else inDet.getCvFrame()
        



    def get_video_frame(self):
        """Return BGR ndarray (large). Non-blocking."""
        if not self._q_video:
            raise RuntimeError("Video stream not enabled.")
        pkt = self._q_video.tryGet()
        return None if pkt is None else pkt.getCvFrame()

    def get_video_frame(self):
        """Return BGR ndarray (large). Non-blocking."""
        if not self._q_video:
            raise RuntimeError("Video stream not enabled.")
        pkt = self._q_video.tryGet()
        return None if pkt is None else pkt.getCvFrame()
    
    def get_frame(self, timeout_ms: int | None = None):
        """Return preview frame (BGR). Non-blocking by default.
        If timeout_ms is set, poll tryGet() until timeout expires."""
        if not self._q_preview:
            raise RuntimeError("Preview stream not enabled.")

        if timeout_ms is None:
            pkt = self._q_preview.tryGet()
            return None if pkt is None else pkt.getCvFrame()

        # Polling loop for compatibility (some SDKs lack get(timeout))
        import time as _t
        deadline = _t.time() + (timeout_ms / 1000.0)
        while _t.time() < deadline:
            pkt = self._q_preview.tryGet()
            if pkt is not None:
                return pkt.getCvFrame()
            _t.sleep(0.005)  # 5 ms
        return None

    def __enter__(self) -> "OakDLite":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
