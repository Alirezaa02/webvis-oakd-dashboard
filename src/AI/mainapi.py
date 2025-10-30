import logging
import signal
import sys
import time
from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont

from uavlcd.display import LCD
from utility.ip_helper import get_ip_address
from utility.display_utils import render_centered_text
import utility.sensors as sensors
import utility.oakd_capture as OakDLite
from pathlib import Path


import cv2
import depthai as dai
import numpy as np
import argparse
import json
import blobconverter
import math


#parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-m", "--model", help="Provide model name or model path for inference",
                    default='yolov4_tiny_coco_416x416', type=str)
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
# parse input shape
if "input_size" in nnConfig:
    W, H = tuple(map(int, nnConfig.get("input_size").split('x')))
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

# Create pipeline
#pipeline = dai.Pipeline()
# Define sources and outputs
#camRgb = pipeline.create(dai.node.ColorCamera)
detectionNetwork = pipeline.create(dai.node.YoloDetectionNetwork)
xoutRgb = pipeline.create(dai.node.XLinkOut)
nnOut = pipeline.create(dai.node.XLinkOut)
xoutRgb.setStreamName("rgb")
nnOut.setStreamName("nn")
nnOut.setStreamName("nn")
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
# Linking
detectionNetwork.passthrough.link(xoutRgb.input)
detectionNetwork.out.link(nnOut.input)


# When adding pages, ensure new if case is added to RENDER_PAGE for functional call.
PAGES = [
    "IP_ADDRESS",
    "SENSORS",
    "CAM_DISP"
]
PAGE_IDX_MAX = len(PAGES)
CAM_CAP_TIMEOUT_MS = 100

PROX_THRESHOLD   = 1500 # The proximity point
PAGE_DEBOUNCE_S  = 0.5  # Seconds between page advances
HOLD_TO_UNLOCK_S = 2.0  # Time to release IP display lock
HOLD_TO_STEP_PAGE= 0.5  # Time to hold to step to next page.
POLL_S           = 0.05 # Sensor heartbeat

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)
    
def main():
    logging.info("Starting LCD page cycler ...")

    should_cap_frame = True

    lcd = LCD()
    cam = OakDLite.OakDLite(resolution="720p", fps=30)
    frame_storage = None # TODO: Set up frame storage here.

    def cleanup(*_):
        logging.info("Exiting ...")
        try:
            lcd.clear()
        except Exception as e:
            logging.warning("Failed to clear LCD screen on exit: %s", e)
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    print("LCD instance?", isinstance(lcd, object), type(lcd), getattr(lcd, "width", None), getattr(lcd, "height", None))

    # Lambda function generator for on_tick behaviour.
    def _make_prompt_tick(lcd, page_idx):
        def _tick():
            if should_cap_frame and frame_storage: 
                capture_frame(cam, frame_storage)
            render_page(lcd, PAGES[page_idx])
        return _tick

    logging.info("Started successfully. Locking to IP display.")
    wait_for_proximity_hold(PROX_THRESHOLD, HOLD_TO_UNLOCK_S, POLL_S, on_tick=_make_prompt_tick(lcd, 0))

    logging.info("IP Lock satisfied. Progressing to the page cycle.")
    page_idx = 1



               #######################################
    qDet = device.getOutputQueue(name="nn", maxSize=4, blocking=False)
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
            #cor = f'Coords: ({bbox[0]},{bbox[1]})-({bbox[2]},{bbox[3]})'#
            #cv2.putText(frame, cor, (bbox[0] + 60, bbox[1] + 90), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)#
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            #cv2.putText(frame, x_distance, (bbox[0] + 30, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            
            x1 = detection.xmax - (detection.xmax - detection.xmin)/2
            y1 = detection.ymax - (detection.ymax - detection.ymin)/2
            x2 = x1 + (detection.xmax - detection.xmin)
            y2 = y1 + (detection.ymax - detection.ymin)
            object_coordinates.append([x1, y1, x2, y2])
            found = detection.label
            foundlabel.append(found)
        if 0 in foundlabel and 3 in foundlabel:
            # Grabs "Center" label coordinates
            center_indexes = [index for index, x in enumerate(foundlabel) if x == foundlabel[0]]
            center_coordinates = object_coordinates[center_indexes[0]]
            # Finds center x and y coordinates for "Center" label bbox
            center_x_center = int(1000*(center_coordinates[0] 
                                  + (center_coordinates[2] - center_coordinates[0])/2
                                  ))
            center_y_center = int(1000*(center_coordinates[1] 
                                  + (center_coordinates[3] - center_coordinates[1])/2
                                  ))
            needle_tip_indexes = [index for index, x in enumerate(foundlabel) if x == foundlabel[1]]
            needle_tip_coordinates = object_coordinates[needle_tip_indexes[0]]
            # Finds center x and y coordinates for "Needle_Tip" label bbox
            center_x_needle_tip = int(1000*(needle_tip_coordinates[0] 
                                      + (needle_tip_coordinates[2] - needle_tip_coordinates[0])/2
                                      ))
            center_y_needle_tip = int(1000*(needle_tip_coordinates[1] 
                                      + (needle_tip_coordinates[3] - needle_tip_coordinates[1])/2
                                      ))
            # Finds angle - look at triginometry and arctangent
            dy = center_y_needle_tip - center_y_center
            dx = center_x_needle_tip - center_x_center
            theta = math.atan2(dy, dx)
            theta = math.degrees(theta)
            theta = round(theta)
            # Changes negative theta to appropriate value
            if theta < 0:
                theta *= -1
                theta = (180 - theta) + 180
            # Sets new starting point
            theta = theta - 90
            # Changes negative thetat to appropriate value
            if theta < 0:
                theta *= -1
                theta = theta + 270
            bar = round(0.0419*theta-2.52, 2) #0.0419*theta-2.52
            print('Gauge Pressure is: ' + str(bar) + 'bar now')
            #run_once = True     
            if run_once:
                  if bar <= 2:
                        print('stop')# def function_name(parameters)
                        run_once = False
            confidence_level_list = []
            for object_coordinate_index, object_coordinate in enumerate(object_coordinates):
                  cv2.putText(frame, 'Gauge:' + str(bar) + 'bar', (bbox[0] + 5, bbox[1] -10 ), cv2.FONT_HERSHEY_TRIPLEX, 0.7, (0, 0, 255))#     
        cv2.imshow(name, frame)



    # Main loop.
    while True:        
        # Ensure page idx is clean.
        if page_idx <= 0 or page_idx >= PAGE_IDX_MAX:
            page_idx = 1

        logging.info("Page stepped, new page %s", PAGES[page_idx])

        wait_for_proximity_hold(PROX_THRESHOLD, HOLD_TO_STEP_PAGE, POLL_S, on_tick=_make_prompt_tick(lcd, page_idx))
        
        # If escaped hold, we want to step the page displayed.
        page_idx += 1


               ###########################
        inRgb = self._q_preview.get()
        inDet = qDet.get()
        if inRgb is not None:
            frame = inRgb.getCvFrame()
            cv2.putText(frame, "NN fps: {:.2f}".format(counter / (time.monotonic() - startTime)),
                        (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color2)
        if inDet is not None:
            detections = inDet.detections
            counter += 1
        if frame is not None:
            displayFrame("rgb", frame, detections)
        if cv2.waitKey(1) == ord('q'):
            break



def render_page(lcd: LCD, page: str):
    if page == "IP_ADDRESS":
        display_ip(lcd)
    elif page == "SENSORS":
        display_sensors(lcd)
    elif page == "CAM_DISP":
        display_camera(lcd)
    else:
        render_centered_text(lcd, "UNKNOWN STATE.")

def wait_for_proximity_hold(threshold: int, hold_s: float, poll_s: float, on_tick=None):
    """
    Block until proximity stays >= threshold seconds continuously
    """
    hold_start = None
    while True:
        if on_tick:
            on_tick()
        
        prox = sensors.proximity()
        now = time.time()

        if prox >= threshold:
            if hold_start is None:
                hold_start = now
            elif (now - hold_start) >= hold_s:
                logging.info("Step hold satisfied. (prox=%s, held=%.2fs)", prox, now - hold_start)
                break
        else:
            hold_start = None
        
        time.sleep(poll_s)

def display_ip(lcd):
    render_centered_text(lcd, f"IP: {get_ip_address()}")

def display_sensors(lcd):
    render_centered_text(lcd, "TODO: \nIMPLEMENT SENSORS")

def display_camera(lcd, store = None):
    render_centered_text(lcd, "TODO: \nIMPLEMENT CAMERA")
    return # Expose below once frame storage implemented.
    frame = store.get()
    if frame is None:
        render_centered_text(lcd, "Awaiting successful capture")
        return
    
    # Try fast render method first
    if lcd_show_image_frame(lcd, frame):
        return
    
    # Fall-back to a PIL image by row renders
    img = Image.fromarray(cv2.cutColor(frame, cv2.COLOR_BGR2RGB))
    if lcd_show_image(lcd, img):
        return
    
    render_centered_text(lcd, "Failed to render frame.")

def capture_frame(cam, frame_storage):
    try:
        frame = cam.get_frame(timeout_ms=CAM_CAP_TIMEOUT_MS)
        # ANY PRE-PARSE CALLS HERE.
        # PARSE TO FRAME STORAGE
    except Exception:
        pass # Quietly fail here, fails loudly earlier in pipe.

if __name__ == "__main__":
    main()
