import logging
import signal
import sys
import time

from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont

from uavlcd.display import LCD
from utility.ip_helper import get_ip_address
from utility.display_utils import render_centered_text, lcd_show_image_frame
import utility.sensors as sensors
import utility.oakd_capture as OakDLite
from utility.compose import FrameStore

from utility.telemetry_client import post_sensor_reading, format_payload
from utility.live_api import start_server, set_latest  # optional but handy


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

FRAME_STORE = FrameStore()

CPU_TEMPS = None # type: list[float] | None
factor = 2.75 # Temp Scaling Factor

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)
    
def main():
    logging.info("Starting LCD page cycler ...")

    global CPU_TEMPS
    CPU_TEMPS = [sensors.cpu_temp_c()] * 5 # Initialse for Averaging
    #logging.info(CPU_TEMPS)

    should_cap_frame = True

    start_server(host="0.0.0.0", port=5055)

    lcd = LCD()
    cam = OakDLite.OakDLite(fps=30, enable_preview=True)
    cam.start()
    time.sleep(0.2)  # allow the first preview packets to flow
    # Seed the store once so CAM_DISP can show something immediately
    seed = cam.get_frame(timeout_ms=200)
    if seed is not None:
        FRAME_STORE.update_composed(seed)

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
            
            if should_cap_frame: 
                capture_frame(cam, FRAME_STORE)
            render_page(lcd, PAGES[page_idx])
            
            sensor_data = sensors.get_all_sensor_data(CPU_TEMPS)
            # logging.info(sensor_data)


            try:
                sensor_data = sensors.get_all_sensor_data(CPU_TEMPS)
                ok = post_sensor_reading(sensor_data)
                if not ok:
                    logging.debug("post_sensor_reading: backend not accepting right now")

                    # 2) optional: publish same reading to tiny local JSON API for polling
                    set_latest(format_payload(sensor_data))

            except Exception as e:
                logging.debug("sensor tick error: %s", e)

        return _tick
        

    logging.info("Started successfully. Locking to IP display.")
    wait_for_proximity_hold(PROX_THRESHOLD, HOLD_TO_UNLOCK_S, POLL_S, on_tick=_make_prompt_tick(lcd, 0))

    logging.info("IP Lock satisfied. Progressing to the page cycle.")
    page_idx = 1

   

    # Main loop.
    while True:        
        # Ensure page idx is clean.
        if page_idx <= 0 or page_idx >= PAGE_IDX_MAX:
            page_idx = 1

        logging.info("Page stepped, new page %s", PAGES[page_idx])

        wait_for_proximity_hold(PROX_THRESHOLD, HOLD_TO_STEP_PAGE, POLL_S, on_tick=_make_prompt_tick(lcd, page_idx))
        
        # If escaped hold, we want to step the page displayed.
        page_idx += 1

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
    global CPU_TEMPS
    cpu_temp = sensors.cpu_temp_c()
    # TEMPERATURE
    # Smooth out with some averaging to decrease jitter
    CPU_TEMPS = CPU_TEMPS[1:] + [cpu_temp]
    avg_cpu_temp = sum(CPU_TEMPS) / float(len(CPU_TEMPS))
    raw_temp = sensors.bme_temperature_c()
    enviro_temp = raw_temp - ((avg_cpu_temp - raw_temp) / factor)

    temp_string = f"Pi Temp: {cpu_temp:.1f}°C\nEnviro Temp: {enviro_temp:.1f}°C"
    render_centered_text(lcd, temp_string)

def display_camera(lcd, store = None):
    store = store or FRAME_STORE
     # Try the most recent composed frame (may be just raw, per step 2)
    img = store.get_composed()
    if img is None:
        render_centered_text(lcd, "No camera frame yet.")
        return

    ok = lcd_show_image_frame(lcd, img, rotate_deg=0)
    if not ok:
        render_centered_text(lcd, "Failed to render frame.")

def capture_frame(cam, frame_storage):
    try:
        # Non-blocking (polling inside get_frame if you give a timeout)
        bgr = cam.get_frame(timeout_ms=CAM_CAP_TIMEOUT_MS)
        if bgr is not None:
            frame_storage.update_composed(bgr)
    except Exception as e:
        logging.debug("Main | capture_frame: %s", e)

if __name__ == "__main__":
    main()
